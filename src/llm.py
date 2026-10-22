"""
CollectLoop · 文案生成层（链路第 3 段的"AI"部分）
------------------------------------------------------------
两个硬性设计：
  1. **永远有兜底**。没配 key、模型超时、返回异常，都退回模板文案。
     演示时网断了也不白屏——这一条比文案质量重要得多。
  2. **模型只写草稿，不发送**。发送动作必须由人在 /review 页面点击完成。
     这是 Domain 2 的"人在环内"底线，也对应官方 AI 政策里"不让系统编造事实"。

环境变量（Replit 里放 Secrets，不要写进代码）：
  LLM_BASE_URL  例如 https://api.openai.com/v1
  LLM_API_KEY   你的 key
  LLM_MODEL     例如 gpt-4o-mini / deepseek-chat
"""
import json
import os
import urllib.request
import urllib.error

TIMEOUT = 20

TONE_BY_BUCKET = {
    "Gentle reminder": "friendly and light",
    "Formal reminder": "polite but firm and formal",
    "Escalation": "firm, states consequences and a deadline",
    "Pre-legal": "formal, legal-adjacent, no threats",
}


def _promise_paragraph(promise: dict) -> str:
    """
    承诺失约时多出来的那一段。这是全篇最"不像模板"的地方，
    因为它引用的是真实记录下来的日期，模型是编不出来的。
    """
    if not promise or promise.get("state") != "broken":
        return ""
    last = promise.get("last_promised_for") or ""
    n = int(promise.get("broken") or 1)
    if n <= 1:
        return (f"You mentioned that payment would be made by {last}. That date has "
                f"passed and nothing has arrived, so I wanted to check what happened.\n\n")
    return (f"To be direct: {last} was the second date we agreed on, and again nothing "
            f"has arrived. We are not looking for another estimate — we need one date "
            f"in writing that you can hold to, and we will work around it.\n\n")


def _template_draft(inv: dict, days: int, bucket: str, contact: str, promise: dict = None) -> str:
    """兜底模板。占位符少，读起来像真人写的。"""
    amount = inv.get("amount", 0)
    due = inv.get("due_date", "")
    no = inv.get("invoice_no", "")
    company = inv.get("company", "your company")
    pp = _promise_paragraph(promise)

    if bucket == "Gentle reminder":
        return (f"Hi {contact},\n\n"
                f"Hope you're doing well. Just a gentle nudge — invoice {no} "
                f"({amount:,.2f}) was due on {due} and is now {days} days past that date.\n\n"
                f"{pp}"
                f"If it's already been processed on your side, please ignore this. "
                f"Otherwise a quick update would help us close the loop.\n\n"
                f"Thanks,\n{company}")
    if bucket == "Formal reminder":
        return (f"Dear {contact},\n\n"
                f"This is a formal reminder that invoice {no} for {amount:,.2f}, "
                f"due {due}, remains unpaid {days} days after the due date.\n\n"
                f"{pp}"
                f"Could you confirm the expected payment date, or let us know if any "
                f"document is missing on our side?\n\n"
                f"Regards,\n{company}")
    if bucket == "Escalation":
        return (f"Dear {contact},\n\n"
                f"Invoice {no} for {amount:,.2f} is now {days} days overdue.\n\n"
                f"{pp}"
                f"As per our terms, we will need to place further orders on hold until "
                f"this balance is settled. We would like to avoid that — please confirm "
                f"a payment date within the next 5 working days.\n\n"
                f"Regards,\n{company}")
    return (f"Dear {contact},\n\n"
            f"Invoice {no} for {amount:,.2f} has remained unpaid for {days} days "
            f"despite previous reminders.\n\n"
            f"{pp}"
            f"This account is now being reviewed for escalation to our legal advisor. "
            f"If there are circumstances we are not aware of, please reply so we can "
            f"resolve this before that step is taken.\n\n"
            f"Regards,\n{company}")


SYSTEM_PROMPT = (
    "You draft accounts-receivable reminder emails for a small business. "
    "Rules: under 130 words; use ONLY the facts given, never invent payment "
    "details, discounts, or legal threats; if a previously promised payment date "
    "is given, refer to it explicitly and do not accept another vague answer; "
    "one clear ask at the end; sign with the company name; no subject line; "
    "plain text only."
)


def _call_llm(prompt: str) -> str:
    base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    if not key:
        return ""
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 400,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode("utf-8"))
        return (data["choices"][0]["message"]["content"] or "").strip()
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError, TimeoutError, OSError):
        return ""


def draft_for(inv: dict, days: int, bucket: str, promise: dict = None) -> dict:
    """
    返回 {text, source, model}
      source = "llm"      → 模型写的
      source = "template" → 兜底模板
    这个 source 字段会原样显示在审核页面上，让评审看到系统在哪一步用了 AI。
    """
    contact = inv.get("contact_name", "there")
    rel = inv.get("relationship") or {}
    promise_lines = ""
    if promise and promise.get("state") == "broken":
        promise_lines = (
            f"Promises on record: {promise.get('broken')} broken, {promise.get('kept')} kept\n"
            f"Last promised payment date (now missed): {promise.get('last_promised_for')}\n"
            f"Promised via: {promise.get('channel')}\n"
            f"What they said at the time: {promise.get('note')}\n"
            f"Customer's historical promise-keeping: {rel.get('promises_kept', 0)}"
            f"/{rel.get('promises_total', 0)} kept\n"
            f"Instruction: refer to that missed date explicitly and refuse another vague answer.\n"
        )
    prompt = (
        f"Invoice: {inv.get('invoice_no')}\n"
        f"Customer: {inv.get('customer')}\n"
        f"Amount due: {inv.get('amount'):,.2f} {inv.get('currency', 'MYR')}\n"
        f"Due date: {inv.get('due_date')}\n"
        f"Days overdue: {days}\n"
        f"Aging bucket: {bucket}\n"
        f"Tone required: {TONE_BY_BUCKET.get(bucket, 'polite and firm')}\n"
        f"{promise_lines}"
        f"Contact's name: {contact}\n"
        f"Our company: {inv.get('company')}\n\n"
        f"Write the reminder email body."
    )
    try:
        text = _call_llm(prompt)
    except Exception:
        text = ""
    if text and len(text) > 40:
        return {"text": text, "source": "llm", "model": os.environ.get("LLM_MODEL", "")}
    return {"text": _template_draft(inv, days, bucket, contact, promise),
            "source": "template", "model": ""}


def llm_configured() -> bool:
    return bool(os.environ.get("LLM_API_KEY"))
