#!/usr/bin/env python3
"""
CollectLoop · 入口（纯标准库，零依赖）
------------------------------------------------------------
为什么不用 Flask：Replit 上装依赖是我见过最常见的部署失败原因。
标准库 http.server 打开就能跑，代价是路由要自己写 30 行，值得。

运行：python src/app.py     → http://0.0.0.0:$PORT

链路对应：
  POST /scan        ① 触发      手动点击 / 可挂定时任务
  store.load_state  ② 取数      读发票库
  logic + llm       ③ 逻辑      分层 + 算优先级 + 起草文案
  GET/POST /review  ④ 人工审批  人改、人批准、人可跳过
  store.append_audit⑤ 留痕      追加式 + 哈希链
"""
import html
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import llm
import logic
import intake
import orbyte
import store

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL_DIR = os.path.join(BASE_DIR, "templates")
APP_NAME = "CollectLoop"
TEAM = "RREF COLLECTION"

# ---------------------------------------------------------------- 响应头
# 导师给的判断：Mozilla Observatory 现在 D+，目标 B+。
# 缺的就是下面这几条 —— 它们不改任何页面内容，只改浏览器怎么对待这个页面。
#
# CSP 说明：页面里没有任何 <script>，样式全部内联，所以脚本源可以收到 'none'
# （default-src 'none' 兜住了 script-src）。style-src 必须允许 inline，
# 因为 CSS 是塞在模板里的 —— 这是唯一一处妥协，且不影响脚本执行。
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "X-Permitted-Cross-Domain-Policies": "none",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}

# ---------------------------------------------------------------- 导航
# 导师的原话：「我找不到这个页面」。所以导航必须把五件事全列出来，
# 而且用业务词命名（Work queue / Upload invoice / How the AI works / Audit log）。
NAV = [
    ("/", "Work queue", "queue"),
    ("/upload", "Upload invoice", "upload"),
    ("/ai", "How the AI works", "ai"),
    ("/audit", "Audit log", "audit"),
]


def nav_html(active: str = "") -> str:
    out = []
    for href, label, key in NAV:
        cur = ' aria-current="page"' if key == active else ""
        out.append(f'<a href="{href}"{cur}>{label}</a>')
    return "".join(out)


# ---------------------------------------------------------------- 模板
def render(name: str, nav_active: str = "", **ctx) -> str:
    with open(os.path.join(TPL_DIR, name), "r", encoding="utf-8") as f:
        tpl = f.read()
    tpl = tpl.replace("{{nav}}", nav_html(nav_active))
    for k, v in ctx.items():
        tpl = tpl.replace("{{" + k + "}}", str(v))
    tpl = tpl.replace("{{app}}", APP_NAME).replace("{{team}}", TEAM)
    try:
        with open(os.path.join(BASE_DIR, "static", "style.css"), "r", encoding="utf-8") as f:
            tpl = tpl.replace("{{style}}", f.read())
    except FileNotFoundError:
        tpl = tpl.replace("{{style}}", "")
    return tpl


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


# ---------------------------------------------------------------- 片段
STATUS_CHIP = {
    "pending": ("Pending", "chip-gray"),
    "drafted": ("Needs review", "chip-amber"),
    "approved": ("Approved", "chip-green"),
    "skipped": ("Skipped", "chip-gray"),
}

BUCKET_CHIP = {
    "Gentle reminder": "chip-blue",
    "Formal reminder": "chip-blue",
    "Escalation": "chip-amber",
    "Pre-legal": "chip-red",
    "Not due": "chip-gray",
}


def cards(s: dict) -> str:
    items = [
        ("Overdue invoices", f'{s["overdue_count"]}', "on the books"),
        ("Overdue value", f'{s["overdue_amount"]:,.0f}', "MYR total"),
        ("On promise · held", f'{s["held"]}', "not contacted"),
        ("Promises broken", f'{s["broken"]}', "dates that slipped"),
    ]
    return "".join(
        f'<div class="card"><div class="k">{esc(k)}</div>'
        f'<div class="v">{esc(v)}<span class="u">{esc(u)}</span></div></div>'
        for k, v, u in items
    )


PROMISE_CHIP = {"open": "chip-green", "broken": "chip-red", "none": "chip-gray"}


def promise_cell(q: dict) -> str:
    """队列里的"承诺"列。这一列是整个产品的差异点，所以信息密度给足。"""
    ps = q.get("promise") or {}
    st = ps.get("state", "none")
    rel = q.get("kept_rate") or {}
    rate = (f"{rel.get('kept')}/{rel.get('total')} kept"
            if rel.get("total") else "no history")
    if st == "open":
        main = f"Promised {ps.get('last_promised_for')}"
        sub = f"{ps.get('days_left')} day(s) left · {rate}"
    elif st == "broken":
        main = f"Broken ×{ps.get('broken', 1)}"
        sub = f"was {ps.get('last_promised_for')} · {rate}"
    else:
        main = "No promise"
        sub = rate
    return (f'<span class="chip {PROMISE_CHIP.get(st, "chip-gray")}">{esc(main)}</span>'
            f'<div class="sub">{esc(sub)}</div>')


def rows(queue: list) -> str:
    if not queue:
        return ('<tr><td colspan="8" class="empty">No data yet. Click '
                '"Run today\'s scan" above to start.</td></tr>')
    out = []
    for q in queue:
        label, cls = STATUS_CHIP.get(q.get("status", "pending"), ("—", "chip-gray"))
        tone = q.get("tone") or q.get("bucket") or ""
        bcls = BUCKET_CHIP.get(tone, "chip-gray")
        age_sub = (f'<div class="sub">age: {esc(q.get("bucket"))}</div>'
                   if tone != q.get("bucket") else "")
        if q.get("held"):
            action = (f'<a class="btn-sm ghost" href="/review/{esc(q["id"])}">Why?</a>')
        elif q.get("status") == "drafted":
            action = f'<a class="btn-sm" href="/review/{esc(q["id"])}">Review</a>'
        elif q.get("status") in ("approved", "skipped"):
            action = f'<a class="btn-sm ghost" href="/review/{esc(q["id"])}">View</a>'
        else:
            action = '<span class="muted">—</span>'
        out.append(f"""<tr>
          <td class="mono">{esc(q.get('invoice_no'))}</td>
          <td><b>{esc(q.get('customer'))}</b><div class="sub">{esc(q.get('contact_name'))}</div></td>
          <td class="num">{float(q.get('amount', 0)):,.2f}<div class="sub">{esc(q.get('currency', 'MYR'))}</div></td>
          <td class="num">{esc(q.get('days', 0))}<div class="sub">{esc(q.get('due_date'))}</div></td>
          <td>{promise_cell(q)}</td>
          <td><span class="chip {bcls}">{esc(tone or '—')}</span>{age_sub}</td>
          <td><span class="chip {cls}">{esc(label)}</span></td>
          <td class="right">{action}</td>
        </tr>""")
    return "".join(out)


def orbyte_rows() -> str:
    """
    "How this plugs into Orbyte" 面板。
    Domain 2 的 must-have 里有 "Orbyte fit and reuse" —— 这张表就是答案：
    我们不重造身份、审批、审计，而是复用平台的这些原语。
    """
    out = []
    for cap, how, kind in orbyte.capability_map():
        out.append('<div class="fact"><span class="l">%s<div class="sub">%s</div></span>'
                   '<span class="r"><span class="chip chip-gray">%s</span></span></div>'
                   % (esc(cap), esc(how), esc(kind)))
    return "".join(out)


def audit_rows(entries: list) -> str:
    if not entries:
        return '<div class="empty">还没有审批记录。批准第一张发票后，这里会出现不可篡改的留痕。</div>'
    out = []
    for e in entries:
        out.append(f"""<div class="tl-item">
          <div class="tl-dot"></div>
          <div class="tl-body">
            <div class="tl-head"><b>{esc(e.get('invoice_id'))}</b>
              <span class="chip chip-gray">{esc(e.get('action'))}</span>
              <span class="tl-time">{esc(e.get('ts'))}</span></div>
            <div class="tl-detail">{esc(e.get('detail'))}</div>
            <div class="tl-meta">by {esc(e.get('actor'))} · chain hash <code>{esc(e.get('hash'))}</code></div>
          </div>
        </div>""")
    return "".join(out)


# ---------------------------------------------------------------- 业务动作
def do_scan():
    """链路第 1–3 段。返回 (起草条数, 主动不联系的条数)。"""
    state = store.load_state()
    state["total_scans"] = state.get("total_scans", 0) + 1
    count = 0
    held = 0
    for inv in state["invoices"]:
        if inv.get("status") in ("approved", "skipped"):
            continue
        days = logic.days_overdue(inv["due_date"])
        if days <= 0 or inv.get("paid"):
            continue
        ps = logic.promise_state(inv)
        if ps["state"] == "open":
            # 承诺未到期 → 故意不草拟、不打扰。这是产品的核心克制。
            held += 1
            continue
        tone = logic.tone_of(days, ps)
        if inv.get("status") == "drafted" and inv.get("draft"):
            continue  # 已经起草过，不重复消耗模型调用
        d = llm.draft_for(inv, days, tone, ps)
        inv["draft"] = d["text"]
        inv["draft_source"] = d["source"]
        inv["draft_model"] = d["model"]
        inv["draft_tone"] = tone
        inv["status"] = "drafted"
        count += 1
    store.save_state(state)
    store.append_audit({
        "invoice_id": "—", "action": "SCAN",
        "actor": "system",
        "detail": (f"Scan complete — {count} draft(s) waiting for human review, "
                   f"{held} customer(s) deliberately not contacted (promise still open)"),
    })
    return count, held


def decide(inv_id: str, action: str, final_text: str, actor: str):
    state = store.load_state()
    target = next((i for i in state["invoices"] if i.get("id") == inv_id), None)
    if not target:
        return False
    if action == "approve":
        target["status"] = "approved"
        target["final_text"] = final_text
        target["edited"] = final_text.strip() != (target.get("draft") or "").strip()
        verb = "Approved and logged" + (" (human edited the draft)" if target["edited"] else "")
    else:
        target["status"] = "skipped"
        verb = "Skipped — nothing sent"
    target["decided_by"] = actor
    target["decided_at"] = store.now_iso()
    store.save_state(state)
    store.append_audit({
        "invoice_id": target.get("invoice_no") or inv_id,
        "action": "APPROVE" if action == "approve" else "SKIP",
        "actor": actor,
        "detail": f"{verb} | customer {target.get('customer')} | "
                  f"{target.get('amount')} {target.get('currency', 'MYR')} | "
                  f"{logic.days_overdue(target['due_date'])} days overdue",
    })
    return True


def record_promise(inv_id: str, promised_for: str, channel: str, note: str, actor: str):
    """
    人把客户的口头承诺记进台账 —— 这是全系统唯一新增的数据写入动作，
    而且它必须由人来完成：系统不会替客户"答应"任何事。
    """
    try:
        logic.parse_date(promised_for)
    except (ValueError, TypeError):
        return False, "Date must look like 2026-10-26"
    state = store.load_state()
    target = next((i for i in state["invoices"] if i.get("id") == inv_id), None)
    if not target:
        return False, "Invoice not found"
    target.setdefault("promises", []).append({
        "recorded_at": store.now_iso()[:10],
        "promised_for": promised_for,
        "channel": channel or "Phone",
        "recorded_by": actor,
        "note": note or "",
        "kept": None,
    })
    # 有承诺在身 → 这张单退回"暂不催"，草稿作废，避免有人误点发送
    target["status"] = "pending"
    target["draft"] = None
    target["draft_tone"] = None
    target["decided_by"] = None
    target["decided_at"] = None
    store.save_state(state)
    store.append_audit({
        "invoice_id": target.get("invoice_no") or inv_id,
        "action": "PROMISE",
        "actor": actor,
        "detail": (f"Promise recorded — customer undertakes to pay by {promised_for} "
                   f"via {channel or 'Phone'}; drafting suspended until that date"),
    })
    return True, ""


def add_invoice(raw: dict, actor: str = "team"):
    """
    链路第 0 段：发票怎么进来。

    种子数据是 7 张写死的样本；这个函数让人真的能加一张进去。
    校验逻辑在 intake.py（纯函数、有单测），这里只负责落库和留痕。
    """
    state = store.load_state()
    inv, errors = intake.clean(
        raw,
        taken_ids=[i.get("id") for i in state["invoices"]],
        existing_nos=[i.get("invoice_no") for i in state["invoices"]],
    )
    if errors:
        return None, errors
    state["invoices"].append(inv)
    store.save_state(state)
    store.append_audit({
        "invoice_id": inv["invoice_no"],
        "action": "UPLOAD",
        "actor": actor,
        "detail": (f"Invoice added manually — {inv['customer']} | "
                   f"{inv['amount']:,.2f} {inv['currency']} | due {inv['due_date']} | "
                   f"no promise on record yet"),
    })
    return inv, []


def promise_ledger(inv: dict):
    """审核页右侧的承诺台账。返回 (html, 兑现率说明)。"""
    ps_list = sorted(inv.get("promises") or [], key=lambda x: x.get("promised_for", ""))
    if not ps_list:
        body = ('<div class="empty" style="padding:14px 0">Nothing promised yet on this '
                'invoice. Record one below the first time the customer gives you a date.</div>')
    else:
        parts = []
        for p in ps_list:
            kept = p.get("kept")
            chip = ('<span class="chip chip-green">kept</span>' if kept is True
                    else '<span class="chip chip-red">broken</span>' if kept is False
                    else '<span class="chip chip-blue">open</span>')
            parts.append(
                f'<div class="fact"><span class="l">{esc(p.get("promised_for"))}'
                f'<div class="sub">{esc(p.get("channel") or "—")} · logged '
                f'{esc(p.get("recorded_at"))} by {esc(p.get("recorded_by") or "—")}</div>'
                + (f'<div class="sub" style="font-style:italic">“{esc(p.get("note"))}”</div>'
                   if p.get("note") else "")
                + f'</span><span class="r">{chip}</span></div>')
        body = "".join(parts)
    rel = logic.promise_kept_rate(inv)
    rate = (f"This customer has kept {rel['kept']} of {rel['total']} promises "
            f"({rel['pct']}%)" if rel["total"] else "No promise history on this customer yet")
    return body, rate


# ---------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "CollectLoop/1.0"
    sys_version = ""          # 不对外暴露 Python 版本

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # ---------- 工具
    def _common_headers(self):
        """每一条响应都带上安全头 —— 包括 404 和 500，漏洞最常藏在错误页上。"""
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)

    def _send(self, body: str, code: int = 200):
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self._common_headers()
        self.end_headers()
        self.wfile.write(raw)

    def _json(self, obj, code: int = 200):
        import json
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self._common_headers()
        self.end_headers()
        self.wfile.write(raw)

    def _redirect(self, to: str):
        self.send_response(303)
        self.send_header("Location", to)
        self.send_header("Content-Length", "0")
        self._common_headers()
        self.end_headers()

    def _parse(self):
        p = urllib.parse.urlparse(self.path)
        return p.path.rstrip("/") or "/", urllib.parse.parse_qs(p.query)

    # ---------- GET
    def do_GET(self):
        path, q = self._parse()
        try:
            if path == "/":
                return self.page_index(q)
            if path == "/upload":
                return self.page_upload(q)
            if path == "/ai":
                return self.page_ai()
            if path == "/audit":
                return self.page_audit()
            if path.startswith("/review/"):
                return self.page_review(path.split("/")[-1], q)
            if path == "/reset":
                if q.get("yes") == ["1"]:
                    store.reset_state()
                    return self._redirect("/")
                return self._send(render("confirm_reset.html"))
            if path == "/api/health":
                return self._json({"ok": True, "llm_configured": llm.llm_configured()})
            if path == "/api/queue":
                state = store.load_state()
                return self._json({"queue": logic.build_queue(state["invoices"])})
            return self._send(render("error.html", msg="Page not found"), 404)
        except Exception as e:  # 兜底：任何异常都不让演示白屏
            import traceback
            traceback.print_exc()
            return self._send(render("error.html", msg=f"{type(e).__name__}: {e}"), 500)

    # ---------- POST
    def do_POST(self):
        path, _ = self._parse()
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        form = urllib.parse.parse_qs(raw)
        try:
            if path == "/scan":
                count, held = do_scan()
                return self._redirect(f"/?scanned={count}&held={held}")
            if path == "/upload":
                flat = {k: (v[0] if isinstance(v, list) and v else v)
                        for k, v in form.items()}
                inv, errors = add_invoice(flat,
                                          actor=((form.get("actor") or ["team"])[0]).strip() or "team")
                if errors:
                    return self.page_upload({}, errors=errors, sticky=flat, code=400)
                return self._redirect(f"/?added={urllib.parse.quote(inv['invoice_no'])}")
            if path == "/promise":
                inv_id = (form.get("id") or [""])[0]
                promised_for = (form.get("promised_for") or [""])[0]
                channel = (form.get("channel") or ["Phone"])[0]
                note = (form.get("note") or [""])[0]
                actor = ((form.get("actor") or ["team"])[0]).strip() or "team"
                ok, err = record_promise(inv_id, promised_for, channel, note, actor)
                if not ok:
                    return self._send(render("error.html", msg=err), 400)
                return self._redirect(f"/review/{inv_id}?promised=1")
            if path == "/decide":
                inv_id = (form.get("id") or [""])[0]
                action = (form.get("action") or ["approve"])[0]
                text = (form.get("text") or [""])[0]
                actor = ((form.get("actor") or ["team"])[0]).strip() or "team"
                decide(inv_id, action, text, actor)
                return self._redirect("/" if action != "approve" else f"/review/{inv_id}?done=1")
            return self._send(render("error.html", msg="Unknown action"), 404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return self._send(render("error.html", msg=f"{type(e).__name__}: {e}"), 500)

    # ---------- 页面
    def page_index(self, q):
        state = store.load_state()
        queue = logic.build_queue(state["invoices"])
        s = logic.summary(queue)
        banner = ""
        if q.get("scanned"):
            n = (q.get("scanned") or ["0"])[0]
            h = (q.get("held") or ["0"])[0]
            banner = (f'<div class="banner ok" role="status">Scan complete — <b>{esc(n)} draft(s)</b> '
                      f'written, <b>{esc(h)} customer left alone</b> because they are still inside a '
                      f'date they promised. Nothing sent: every draft waits for a person.</div>')
        if q.get("added"):
            no = (q.get("added") or [""])[0]
            banner += (f'<div class="banner info" role="status">Invoice <b>{esc(no)}</b> added to the ledger. '
                       f'It has no promise on record yet, so the next scan will draft a first '
                       f'message for it. <a href="/upload">Add another →</a></div>')
        stats = logic.savings_estimate(s["approved_today"])
        return self._send(render(
            "index.html",
            nav_active="queue",
            cards=cards(s),
            rows=rows(queue),
            banner=banner,
            scans=state.get("total_scans", 0),
            llm_state=("Model connected" if llm.llm_configured() else "AI: template fallback · see how it works"),
            llm_cls=("chip-green" if llm.llm_configured() else "chip-gray"),
            saved_hours=stats["hours_saved"],
            held=s["held"],
            held_clause=(f'{s["held"]} row above is' if s["held"] == 1
                         else f'{s["held"]} rows above are'),
            data_source=orbyte.source_label(),
            orbyte_rows=orbyte_rows(),
            approved=stats["approved"],
            audit_tail=audit_rows(store.read_audit(3)),
        ))

    def page_review(self, inv_id, q):
        state = store.load_state()
        inv = next((i for i in state["invoices"] if i.get("id") == inv_id), None)
        if not inv:
            return self._send(render("error.html", msg="Invoice not found"), 404)
        days = logic.days_overdue(inv["due_date"])
        ps = logic.promise_state(inv)
        tone = inv.get("draft_tone") or logic.tone_of(days, ps)
        _, suggestion = logic.bucket_of(days)
        src = inv.get("draft_source") or "template"
        if src == "llm":
            src_label = f'AI-written · {inv.get("draft_model") or "model"}'
        else:
            src_label = "Template fallback · no model key here"
        # 导师问「AI 到底做了什么」——这一小块就是答案，且用的是这条草稿的真实来源
        trace = (
            f'<div class="fact"><span class="l">Decided who to chase</span>'
            f'<span class="r">rules, not a model</span></div>'
            f'<div class="fact"><span class="l">Wrote this text</span>'
            f'<span class="r">{esc("a language model" if src == "llm" else "the fallback template")}</span></div>'
            f'<div class="fact"><span class="l">Can it change a date?</span>'
            f'<span class="r">no — dates come from the ledger</span></div>'
            f'<div class="fact"><span class="l">Who presses send</span>'
            f'<span class="r">a person, on this page</span></div>'
            f'<p class="hint" style="margin-top:9px">'
            f'<a href="/ai">See exactly what the model was given →</a></p>'
        )

        banner = ""
        if q.get("promised"):
            banner += ('<div class="banner ok" role="status">Promise recorded. This invoice is now on hold — '
                       'no message will be drafted until that date passes, and the record is in '
                       'the audit log.</div>')
        if q.get("done"):
            banner += ('<div class="banner ok">Approved and written to the audit log. In production '
                       'the next step would be an email API call — deliberately not wired here.</div>')
        if ps["state"] == "open":
            banner += (f'<div class="banner info"><b>Nothing to send.</b> '
                       f'{esc(logic.hold_reason(inv))}</div>')
        decided = ""
        if inv.get("decided_at"):
            decided = (f'<div class="banner warn">Already handled by <b>{esc(inv.get("decided_by"))}</b> '
                       f'at {esc(inv.get("decided_at"))} — status <b>{esc(inv.get("status"))}</b>. '
                       f'Approving again will overwrite that decision.</div>')
        ledger_html, rate_text = promise_ledger(inv)
        return self._send(render(
            "review.html",
            nav_active="queue",
            banner=banner + decided,
            id=esc(inv["id"]),
            invoice_no=esc(inv.get("invoice_no")),
            customer=esc(inv.get("customer")),
            contact=esc(inv.get("contact_name")),
            email=esc(inv.get("contact_email")),
            amount=f'{float(inv.get("amount", 0)):,.2f}',
            currency=esc(inv.get("currency", "MYR")),
            due_date=esc(inv.get("due_date")),
            days=days,
            bucket=esc(tone),
            bucket_cls=BUCKET_CHIP.get(tone, "chip-gray"),
            suggestion=esc(suggestion),
            draft=esc(inv.get("draft") or ""),
            src_label=esc(src_label),
            history=esc(inv.get("history_note") or "No collection history on file"),
            ledger=ledger_html,
            kept_rate=esc(rate_text),
            ai_trace=trace,
            promise_label=esc(ps.get("label")),
        ))

    def page_upload(self, q, errors=None, sticky=None, code: int = 200):
        sticky = sticky or {}
        err_html = ""
        if errors:
            items = "".join(f"<li>{esc(e)}</li>" for e in errors)
            err_html = (f'<div class="banner warn" role="alert"><b>Nothing was saved yet.</b> '
                        f'<ul class="errs">{items}</ul></div>')

        def val(k, default=""):
            v = sticky.get(k)
            return esc(v if v not in (None, "") else default)

        state = store.load_state()
        mine = [i for i in state["invoices"] if i.get("uploaded")]
        recent = "".join(
            f'<div class="fact"><span class="l">{esc(i.get("invoice_no"))}'
            f'<div class="sub">{esc(i.get("customer"))}</div></span>'
            f'<span class="r">{float(i.get("amount", 0)):,.2f} {esc(i.get("currency", "MYR"))}'
            f'<div class="sub">due {esc(i.get("due_date"))}</div></span></div>'
            for i in mine[-4:]
        ) or ('<div class="empty" style="padding:12px 0">Nothing uploaded this session — '
              'the seven sample invoices are still the only ones in the ledger.</div>')

        return self._send(render(
            "upload.html",
            nav_active="upload",
            errors=err_html,
            invoice_no=val("invoice_no"),
            customer=val("customer"),
            contact=val("contact_name"),
            email=val("contact_email"),
            amount=val("amount"),
            due_date=val("due_date"),
            currency=val("currency", "MYR"),
            recent=recent,
            uploaded_count=len(mine),
        ), code)

    def page_ai(self):
        state = store.load_state()
        invoices = state["invoices"]
        queue = logic.build_queue(invoices)

        # 真实计数：这一轮里哪些草稿是模型写的，哪些是模板兜底的
        drafted = [i for i in invoices if i.get("draft")]
        n_llm = sum(1 for i in drafted if (i.get("draft_source") == "llm"))
        n_tpl = len(drafted) - n_llm

        # 拿一条真实发票来展示「模型到底看到了什么」——
        # 显示的必须是实际发出去的那段 prompt，不是另写的示意图
        sample = next((i for i in invoices if i.get("draft")), None)
        if sample is None:
            sample = next((q for q in queue if q.get("days", 0) > 0), None) or \
                     (invoices[0] if invoices else None)
        prompt, sample_label = "(no invoice in the ledger yet)", "—"
        if sample:
            days = logic.days_overdue(sample["due_date"])
            ps = logic.promise_state(sample)
            tone = sample.get("draft_tone") or logic.tone_of(days, ps)
            prompt = llm.build_prompt(sample, days, tone, ps)
            sample_label = f'{sample.get("invoice_no")} · {sample.get("customer")}'

        flow = [
            ("1", "A person clicks <b>Run today's scan</b>", "human", "There is no background worker. The trigger is a button, so nothing happens unless somebody decides it should."),
            ("2", "Read the invoice book and the promise ledger", "code", "store.py reads JSON. Every promise, its date and what the customer said are already on record."),
            ("3", "Decide <b>who</b> to chase and in <b>what tone</b>", "rule", "logic.py — aging bucket × promises broken. Deterministic, unit-tested, the same answer every time."),
            ("4", "Write the sentence", "ai", "llm.py — one chat completion. This is the only place a model is called, and it returns text, nothing else."),
            ("5", "A person reads it and approves, skips, or records a promise", "human", "Nothing leaves the system on its own. Approval is a click, and it is logged with a name."),
        ]
        owners = {
            "human": ("human", "chip-blue"),
            "code": ("code", "chip-gray"),
            "rule": ("rule", "chip-amber"),
            "ai": ("AI", "chip-green"),
        }
        flow_rows = "".join(
            f'<div class="flow-row"><span class="n">{n}</span>'
            f'<span class="what">{what}</span>'
            f'<span class="chip {owners[who][1]}">{owners[who][0]}</span>'
            f'<span class="why">{esc(why)}</span></div>'
            for n, what, who, why in flow
        )
        facts = "".join(
            f'<div class="fact"><span class="l">{esc(k)}</span>'
            f'<span class="r">{esc(v)}</span></div>'
            for k, v in llm.FACT_FIELDS
        )
        rules = "".join(f"<li>{esc(r)}</li>" for r in llm.RULES)

        return self._send(render(
            "ai.html",
            nav_active="ai",
            flow_rows=flow_rows,
            facts=facts,
            rules=rules,
            prompt_block=esc(prompt),
            sample_label=esc(sample_label),
            model_label=esc(llm.model_label()),
            model_cls=("chip-green" if llm.llm_configured() else "chip-gray"),
            n_drafted=len(drafted),
            n_llm=n_llm,
            n_tpl=n_tpl,
        ))

    def page_audit(self):
        entries = store.read_audit(200)
        return self._send(render("audit.html", nav_active="audit",
                                 rows=audit_rows(entries), count=len(entries)))


def main():
    port = int(os.environ.get("PORT", "8080"))
    host = "0.0.0.0"  # 必须监听 0.0.0.0，否则 Replit 部署后打不开
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"CollectLoop running on http://{host}:{port}  (team {TEAM})")
    print("LLM:", "configured" if llm.llm_configured() else "not configured → template fallback")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
