"""
CollectLoop · 发票录入（手工上传）
------------------------------------------------------------
导师的原话是「至少让人能手动上传发票，这才是最基础的 MVP」。
这个模块只做一件事：把一张脏表单变成一条干净的发票记录，或者拒绝它。

为什么单独成文件而不是塞进 app.py：
  - 纯函数、无 IO、无 HTTP，可以单测（tests/test_intake.py）
  - 演示时如果学生手输一张离谱的金额，这里负责挡住，页面只负责显示错误
  - 评委问「上传的东西怎么校验」，你指这个文件

刻意不做的事：
  - 不解析 PDF、不做 OCR、不接摄像头。这些是路线图，不是 36 小时内能交付的东西。
    表单一共六个字段，和 Orbyte 导出结构里的字段一一对应，OCR 将来只是它的填充器。
"""
import re

import logic

MAX_AMOUNT = 100_000_000.0      # 一亿，超过基本是手滑
MAX_TEXT = 80

_INVOICE_NO = re.compile(r"^[A-Z0-9][A-Z0-9\-/_.]{1,23}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def next_id(invoice_no: str, taken=()) -> str:
    """
    从发票号派生一个稳定、可读的 id（INV-2026-0888 → inv-0888）。
    冲突就加后缀。id 只用于 URL，不参与业务判断。
    """
    stem = re.sub(r"[^a-z0-9]", "", (invoice_no or "").lower())[-4:] or "new"
    base = f"inv-{stem}"
    cand, n = base, 1
    taken = set(taken or ())
    while cand in taken:
        n += 1
        cand = f"{base}-{n}"
    return cand


def clean(raw: dict, taken_ids=(), existing_nos=()) -> tuple:
    """
    校验并归一化一张上传的发票。

    返回 (invoice, errors)：
      有错 → invoice 为 None，errors 是给人看的一句话列表
      没错 → invoice 是可直接存进 state 的完整字典，errors 为空

    校验规则故意宽松到「够用」：不查公司名真伪、不联网验地址。
    越严格，演示时越容易被自己人卡住。
    """
    errors = []

    invoice_no = (raw.get("invoice_no") or "").strip().upper()
    customer = (raw.get("customer") or "").strip()
    contact = (raw.get("contact_name") or "").strip()
    email = (raw.get("contact_email") or "").strip()
    amount_raw = (raw.get("amount") or "").strip()
    due_raw = (raw.get("due_date") or "").strip()
    currency = (raw.get("currency") or "MYR").strip().upper() or "MYR"

    if not invoice_no:
        errors.append("Invoice number is required.")
    elif not _INVOICE_NO.match(invoice_no):
        errors.append("Invoice number: letters, digits and - / _ . only, 2–24 characters.")
    elif invoice_no in {str(x).upper() for x in (existing_nos or ())}:
        errors.append(f"{invoice_no} is already in the ledger. Use a different number.")

    if not customer:
        errors.append("Customer name is required.")

    amount = None
    if not amount_raw:
        errors.append("Amount is required.")
    else:
        try:
            amount = float(amount_raw.replace(",", "").replace(" ", ""))
        except ValueError:
            errors.append("Amount must be a number, e.g. 12500 or 12,500.00")
        else:
            if amount <= 0:
                errors.append("Amount must be greater than zero.")
            elif amount > MAX_AMOUNT:
                errors.append("Amount looks too large — check for a typo.")

    due_date = due_raw
    if not due_raw:
        errors.append("Due date is required.")
    else:
        try:
            logic.parse_date(due_raw)
        except (ValueError, TypeError):
            errors.append("Due date must look like 2026-09-30.")

    if email and not _EMAIL.match(email):
        errors.append("Contact email does not look like an email address.")

    if errors:
        return None, errors

    inv = {
        "id": next_id(invoice_no, taken_ids),
        "invoice_no": invoice_no,
        "customer": customer[:MAX_TEXT],
        "contact_name": contact[:MAX_TEXT] or "the accounts contact",
        "contact_email": email,
        "amount": round(amount, 2),
        "currency": currency[:3],
        "due_date": due_date,
        "paid": False,
        "company": "RREF Supply & Trading",
        # 新客户没有历史 —— 这一点很重要：系统不会假装知道这个客户守不守承诺
        "history_note": ("Added manually from the upload form. No collection history on file yet, "
                         "so the first message carries no promise reference."),
        "relationship": {"months": 0, "invoices_total": 1,
                         "promises_total": 0, "promises_kept": 0},
        "promises": [],
        "status": "pending",
        "draft": None,
        "draft_source": None,
        "draft_model": None,
        "draft_tone": None,
        "decided_by": None,
        "decided_at": None,
        "uploaded": True,
    }
    return inv, []
