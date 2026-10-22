"""
CollectLoop · 业务逻辑层（链路第 3 段：规则判断）
------------------------------------------------------------
这一层刻意做成纯函数、无副作用、无网络请求，好处有三个：
  1. 可以单测（见 tests/test_logic.py）
  2. 演示时哪怕模型挂了、网断了，分类和建议金额依然算得出来
  3. 评委问"哪部分是 AI、哪部分是规则"时，你能指着文件回答
"""
from datetime import date, datetime

# 账龄分层：(下限天数, 上限天数, 层级名, 建议动作)
AGING_BUCKETS = [
    (0, 7, "Gentle reminder", "A friendly nudge — assume they simply forgot"),
    (8, 30, "Formal reminder", "Formal tone, with the invoice detail and due date restated"),
    (31, 60, "Escalation", "State the consequence: further orders on hold, with a deadline"),
    (61, 99999, "Pre-legal", "Flag legal review; needs owner sign-off before anything is sent"),
]


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


def priority_score(amount: float, days: int) -> float:
    """
    排序用的优先级：金额 × 逾期天数的平方根。
    用平方根而不是线性，是为了不让一笔巨额发票永远压住所有小额单，
    实操中"一堆小额长逾期"才是拖垮现金流的主因。
    """
    if days <= 0:
        return 0.0
    return round(amount * (days ** 0.5) / 1000.0, 2)


def build_queue(invoices: list) -> list:
    """
    链路第 2–3 段：筛选逾期 → 分层 → 算优先级 → 排序。
    只把需要人处理的放进队列；已处理过的保留在表里（供演示回看）。
    """
    out = []
    for inv in invoices:
        days = days_overdue(inv["due_date"])
        name, action = bucket_of(days)
        item = dict(
            inv,
            days=days,
            bucket=name,
            suggested_action=action,
            priority=priority_score(float(inv.get("amount", 0)), days),
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
    open_items = [q for q in queue if q.get("status") not in ("approved", "skipped") and q.get("days", 0) > 0]
    return {
        "overdue_count": len(open_items),
        "overdue_amount": round(sum(float(q.get("amount", 0)) for q in open_items), 2),
        "pending_review": len([q for q in open_items if q.get("status") == "drafted"]),
        "avg_days": round(sum(q["days"] for q in open_items) / len(open_items), 1) if open_items else 0,
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
