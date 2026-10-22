"""
CollectLoop · 数据存取层
------------------------------------------------------------
设计原则：不接数据库，全部落本地 JSON。理由是演示可靠性优先——
评委点开链接的那一刻，任何一次数据库连接失败都是致命的。

data/invoices.json  只读种子数据（已提交进仓库）
data/state.json     运行时状态（首次运行时从种子复制，已 .gitignore）
data/audit_log.jsonl 审计留痕，追加写，永不修改历史
"""
import json
import os
import threading
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SEED_PATH = os.path.join(DATA_DIR, "invoices.json")
STATE_PATH = os.path.join(DATA_DIR, "state.json")
AUDIT_PATH = os.path.join(DATA_DIR, "audit_log.jsonl")

_lock = threading.Lock()
MYT = timezone(timedelta(hours=8))  # 马来西亚时间 UTC+8


def now_iso() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S")


def _read(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)  # 原子替换，避免半写坏文件


def load_state():
    """读运行时状态；不存在则从种子初始化。"""
    with _lock:
        state = _read(STATE_PATH, None)
        if state is None:
            seed = _read(SEED_PATH, {"invoices": []})
            state = {
                "created_at": now_iso(),
                "total_scans": 0,
                "invoices": [
                    dict(inv, status="pending", draft=None, decided_by=None,
                         decided_at=None, channel=None)
                    for inv in seed.get("invoices", [])
                ],
            }
            _write(STATE_PATH, state)
        return state


def save_state(state):
    with _lock:
        _write(STATE_PATH, state)


def reset_state():
    with _lock:
        if os.path.exists(STATE_PATH):
            os.remove(STATE_PATH)
        if os.path.exists(AUDIT_PATH):
            os.remove(AUDIT_PATH)


def append_audit(entry: dict):
    """追加一条审计记录。附带前一条的哈希，形成可校验的链条。"""
    last_hash = "GENESIS"
    try:
        with open(AUDIT_PATH, "r", encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
        if lines:
            last_hash = json.loads(lines[-1]).get("hash", "GENESIS")
    except FileNotFoundError:
        pass
    entry = dict(entry)
    entry["ts"] = now_iso()
    entry["prev_hash"] = last_hash
    entry["hash"] = _chain_hash(last_hash, entry)
    with _lock:
        with open(AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def _chain_hash(prev: str, entry: dict) -> str:
    import hashlib
    raw = prev + "|" + "|".join(
        str(entry.get(k, "")) for k in ("ts", "invoice_id", "action", "actor", "detail")
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def read_audit(limit: int = 200):
    try:
        with open(AUDIT_PATH, "r", encoding="utf-8") as f:
            lines = [json.loads(ln) for ln in f.read().splitlines() if ln.strip()]
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return list(reversed(lines))[:limit]
