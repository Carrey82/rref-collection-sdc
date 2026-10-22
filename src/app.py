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
import orbyte
import store

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL_DIR = os.path.join(BASE_DIR, "templates")
APP_NAME = "CollectLoop"
TEAM = "RREF COLLECTION"


# ---------------------------------------------------------------- 模板
def render(name: str, **ctx) -> str:
    with open(os.path.join(TPL_DIR, name), "r", encoding="utf-8") as f:
        tpl = f.read()
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

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # ---------- 工具
    def _send(self, body: str, code: int = 200):
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _json(self, obj, code: int = 200):
        import json
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _redirect(self, to: str):
        self.send_response(303)
        self.send_header("Location", to)
        self.send_header("Content-Length", "0")
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
            banner = (f'<div class="banner ok">Scan complete — <b>{esc(n)} draft(s)</b> written, '
                      f'and <b>{esc(h)} customer(s) deliberately left alone</b> because they are '
                      f'still inside a payment date they promised. Nothing has been sent: every '
                      f'draft waits for a person to read it and approve it.</div>')
        stats = logic.savings_estimate(s["approved_today"])
        return self._send(render(
            "index.html",
            cards=cards(s),
            rows=rows(queue),
            banner=banner,
            scans=state.get("total_scans", 0),
            llm_state=("Model connected" if llm.llm_configured() else "No model configured · template fallback"),
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
        src_label = "Model-generated" if src == "llm" else "Template fallback (no model configured)"

        banner = ""
        if q.get("promised"):
            banner += ('<div class="banner ok">Promise recorded. This invoice is now on hold — '
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
            promise_label=esc(ps.get("label")),
        ))

    def page_audit(self):
        entries = store.read_audit(200)
        return self._send(render("audit.html", rows=audit_rows(entries), count=len(entries)))


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
