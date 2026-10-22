"""
CollectLoop · 业务逻辑层（链路第 3 段：规则判断）
------------------------------------------------------------
这一层刻意做成纯函数、无副作用、无网络请求，好处有三个：
  1. 可以单测（见 tests/test_logic.py）
  2. 演示时哪怕模型挂了、网断了，分类和建议动作依然算得出来
  3. 评委问"哪部分是 AI、哪部分是规则"时，你能指着文件回答

本版核心不是"账龄"，而是**承诺（promise-to-pay）**：
  每张发票都带一本承诺台账。系统真正要回答的问题是
  「这个客户答应过什么，还算数吗，现在该不该催」——
  而不是「逾期了多少天，该写哪一种口气的信」。
"""
from datetime import date, datetime

# 账龄分层：(下限天数, 上限天数, 层级名, 建议动作)
AGING_BUCKETS = [
    (0, 7, "Gentle reminder", "A friendly nudge — assume they simply forgot"),
    (8, 30, "Formal reminder", "Formal tone, with the invoice detail and due date restated"),
    (31, 60, "Escalation", "State the consequence: further orders on hold, with a deadline"),
    (61, 99999, "Pre-legal", "Flag legal review; needs owner sign-off before anything is sent"),
]

# 承诺状态机
PROMISE_STATES = ("none", "open", "broken")


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def days_overdue(due_date: str, today: date = None) -> int:
    """逾期天数。未到期返回负数。"""
    today = today or datetime.now().date()
    return (today - parse_date(due_date)).days


def bucket_of(days: int):
    """返回 (层级名, 建议动作)。days<=0 视为未逾期。"""
    if days <= 0:
        return ("Not due", "No action")
    for lo, hi, name, action in AGING_BUCKETS:
        if lo <= days <= hi:
            return (name, action)
    return ("Pre-legal", AGING_BUCKETS[-1][3])


# ---------------------------------------------------------------- 承诺台账
def promise_state(inv: dict, today: date = None) -> dict:
    """
    读一本承诺台账，返回它的状态。四种结果：

      none   从未记录过承诺 → 该发第一封
      open   有承诺且还没到期 → **不催**，这是产品最反直觉的价值
      broken 承诺到期未兑现 → 该催，而且口气要跟着"第几次失约"升级
      (kept 的承诺只进统计，不参与决策)

    返回字段：
      state / label / days_left / broken / kept / total / last_promised_for / relationship
    """
    today = today or datetime.now().date()
    ps = inv.get("promises") or []
    open_ps = [p for p in ps if p.get("kept") is None]
    broken = [p for p in ps if p.get("kept") is False]
    kept = [p for p in ps if p.get("kept") is True]

    base = {
        "broken": len(broken),
        "kept": len(kept),
        "total": len(ps),
        "last_promised_for": None,
        "days_left": 0,
        "channel": None,
        "note": None,
    }

    if open_ps:
        p = max(open_ps, key=lambda x: x.get("promised_for", ""))
        left = (parse_date(p["promised_for"]) - today).days
        if left >= 0:
            return dict(base, state="open", days_left=left,
                        last_promised_for=p["promised_for"],
                        channel=p.get("channel"), note=p.get("note"),
                        label=f"Promised {p['promised_for']}")
        # 承诺日已过但仍标记为"未兑现" → 按失约处理
        return dict(base, state="broken", last_promised_for=p["promised_for"],
                    channel=p.get("channel"), note=p.get("note"),
                    broken=len(broken) + 1,
                    label=f"Promise due {p['promised_for']} passed")

    if broken:
        last = max(broken, key=lambda x: x.get("promised_for", ""))
        return dict(base, state="broken", last_promised_for=last["promised_for"],
                    channel=last.get("channel"), note=last.get("note"),
                    label=f"Promise broken {last['promised_for']}")

    return dict(base, state="none", label="No promise on record")


def should_contact(inv: dict, today: date = None) -> bool:
    """只有两种情况下才值得打扰客户：没承诺过，或者承诺没兑现。"""
    return promise_state(inv, today)["state"] != "open"


def hold_reason(inv: dict, today: date = None) -> str:
    """给"暂不催"的一句话理由。评委点开就能看到逻辑。"""
    ps = promise_state(inv, today)
    if ps["state"] != "open":
        return ""
    who = inv.get("contact_name") or "The customer"
    return (f"{who} promised payment on {ps['last_promised_for']} "
            f"({ps['days_left']} day(s) left, recorded via {ps['channel'] or 'n/a'}). "
            f"Chasing now would spend goodwill for nothing. The system waits.")


def promise_kept_rate(inv: dict) -> dict:
    """这个客户历史上守不守承诺。用来决定口气，也用来给演示讲故事。"""
    rel = inv.get("relationship") or {}
    total = int(rel.get("promises_total") or 0)
    kept = int(rel.get("promises_kept") or 0)
    pct = round(100.0 * kept / total) if total else None
    return {"total": total, "kept": kept, "pct": pct}


def tone_of(days: int, promise: dict) -> str:
    """
    口气不只由账龄决定，还由"失约次数"决定。
    两次失约之后，同一张单的口气要比单纯逾期更硬 —— 这是本产品的核心判断。
    """
    base = bucket_of(days)[0]
    b = promise.get("broken", 0)
    if b >= 2:
        return "Pre-legal" if base == "Pre-legal" else "Escalation"
    if b == 1 and base in ("Gentle reminder", "Formal reminder"):
        return "Formal reminder"
    return base


# ---------------------------------------------------------------- 排序与汇总
def priority_score(amount: float, days: int, broken: int = 0) -> float:
    """
    排序用的优先级：金额 × √逾期天数 × (1 + 0.6 × 失约次数)。
    用平方根而不是线性，是为了不让一笔巨额发票永远压住所有小额单，
    实操中"一堆小额长逾期"才是拖垮现金流的主因。
    失约次数是乘数：同一个客户第二次说话不算数，就该排到前面。
    """
    if days <= 0:
        return 0.0
    base = amount * (days ** 0.5) / 1000.0
    return round(base * (1 + 0.6 * int(broken or 0)), 2)


def build_queue(invoices: list, today: date = None) -> list:
    """
    链路第 2–3 段：筛选逾期 → 读承诺台账 → 分层 → 算优先级 → 排序。
    三种行都会出现在队列里，各有各的用处：
      - 该处理的（无承诺 / 失约）
      - 暂不催的（承诺未到期）  ← 证明系统会克制
      - 已处理的（供演示回看）
    """
    out = []
    for inv in invoices:
        days = days_overdue(inv["due_date"], today)
        ps = promise_state(inv, today)
        name, action = bucket_of(days)
        tone = tone_of(days, ps)
        item = dict(
            inv,
            days=days,
            bucket=name,
            tone=tone,
            suggested_action=action,
            promise=ps,
            kept_rate=promise_kept_rate(inv),
            held=(ps["state"] == "open" and days > 0),
            priority=priority_score(float(inv.get("amount", 0)), days, ps["broken"]),
        )
        if inv.get("status") in ("approved", "skipped"):
            out.append(item)          # 已决的仍然显示，账龄也要正确
            continue
        if days <= 0 or inv.get("paid"):
            continue
        out.append(item)
    out.sort(key=lambda x: x.get("priority", 0), reverse=True)
    return out


def summary(queue: list) -> dict:
    """给首页顶部用的汇总数字。"""
    active = [q for q in queue
              if q.get("status") not in ("approved", "skipped") and q.get("days", 0) > 0]
    held = [q for q in active if q.get("held")]
    to_act = [q for q in active if not q.get("held")]
    return {
        "overdue_count": len(active),
        "overdue_amount": round(sum(float(q.get("amount", 0)) for q in active), 2),
        "held": len(held),
        "held_amount": round(sum(float(q.get("amount", 0)) for q in held), 2),
        "to_act": len(to_act),
        "broken": sum(int(q.get("promise", {}).get("broken", 0)) for q in active),
        "pending_review": len([q for q in to_act if q.get("status") == "drafted"]),
        "avg_days": round(sum(q["days"] for q in active) / len(active), 1) if active else 0,
        "approved_today": len([q for q in queue if q.get("status") == "approved"]),
    }


def savings_estimate(approved: int) -> dict:
    """
    每次人工催收约 12 分钟（翻记录、查付款、写信、核对、留档）。
    系统把它压到约 1 分钟（读一下草稿、点批准）。
    """
    manual_min = 12
    system_min = 1
    saved = max(0, approved) * (manual_min - system_min)
    return {
        "per_invoice_manual_min": manual_min,
        "per_invoice_system_min": system_min,
        "approved": approved,
        "minutes_saved": saved,
        "hours_saved": round(saved / 60, 1),
    }
