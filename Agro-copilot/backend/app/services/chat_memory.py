import json
import time
from collections import deque
from pathlib import Path
from threading import Lock
from uuid import uuid4


MAX_TURNS_PER_SESSION = 20
SESSION_TTL_SECONDS = 5 * 24 * 60 * 60
DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "chat_sessions.json"
_STORE: dict[str, dict] = {}
_LOADED = False
_LOCK = Lock()


def normalize_session_id(session_id: str | None) -> str:
    if not session_id:
        return ""
    return session_id.strip()[:120]


def new_session_id() -> str:
    return f"sess_{uuid4().hex}"


def _now() -> float:
    return time.time()


def _serialize() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, dict] = {"sessions": {}}
    for session_id, row in _STORE.items():
        payload["sessions"][session_id] = {
            "created_at": float(row.get("created_at", _now())),
            "updated_at": float(row.get("updated_at", _now())),
            "turns": list(row.get("turns", [])),
        }
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _prune_expired_unlocked() -> None:
    cutoff = _now() - SESSION_TTL_SECONDS
    to_delete = [k for k, v in _STORE.items() if float(v.get("updated_at", 0.0)) < cutoff]
    for key in to_delete:
        _STORE.pop(key, None)


def _load_if_needed_unlocked() -> None:
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    if not DATA_FILE.exists():
        return
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    sessions = raw.get("sessions", {})
    if not isinstance(sessions, dict):
        return
    for session_id, row in sessions.items():
        key = normalize_session_id(session_id)
        if not key or not isinstance(row, dict):
            continue
        turns_raw = row.get("turns", [])
        turns = deque(maxlen=MAX_TURNS_PER_SESSION)
        if isinstance(turns_raw, list):
            for item in turns_raw[-MAX_TURNS_PER_SESSION:]:
                if not isinstance(item, dict):
                    continue
                turns.append(
                    {
                        "user": str(item.get("user", ""))[:800],
                        "assistant": str(item.get("assistant", ""))[:1200],
                        "at": str(item.get("at", ""))[:40],
                    }
                )
        _STORE[key] = {
            "created_at": float(row.get("created_at", _now())),
            "updated_at": float(row.get("updated_at", _now())),
            "turns": turns,
        }
    _prune_expired_unlocked()


def _touch_session_unlocked(session_id: str) -> None:
    row = _STORE.get(session_id)
    if row is None:
        ts = _now()
        _STORE[session_id] = {"created_at": ts, "updated_at": ts, "turns": deque(maxlen=MAX_TURNS_PER_SESSION)}
        return
    row["updated_at"] = _now()


def ensure_session(session_id: str | None) -> str:
    key = normalize_session_id(session_id) or new_session_id()
    with _LOCK:
        _load_if_needed_unlocked()
        _prune_expired_unlocked()
        _touch_session_unlocked(key)
        _serialize()
    return key


def get_conversation_history(session_id: str | None) -> list[dict[str, str]]:
    key = normalize_session_id(session_id)
    if not key:
        return []
    with _LOCK:
        _load_if_needed_unlocked()
        _prune_expired_unlocked()
        row = _STORE.get(key)
        turns = list(row.get("turns", deque())) if row else []
    return [dict(item) for item in turns]


def append_turn(
    session_id: str | None,
    user_message: str,
    assistant_summary: str,
    entry_id: str | None = None,
    category: str | None = None,
    language: str | None = None,
) -> None:
    key = normalize_session_id(session_id)
    if not key:
        return
    record = {
        "user": " ".join(user_message.strip().split())[:800],
        "assistant": " ".join(assistant_summary.strip().split())[:1200],
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "entry_id": (entry_id or "").strip()[:120],
        "category": (category or "").strip()[:80],
        "language": (language or "").strip()[:12],
    }
    with _LOCK:
        _load_if_needed_unlocked()
        _prune_expired_unlocked()
        _touch_session_unlocked(key)
        bucket = _STORE[key]["turns"]
        bucket.append(record)
        _STORE[key]["updated_at"] = _now()
        _serialize()


def build_memory_hint(session_id: str | None) -> str:
    history = get_conversation_history(session_id)
    if not history:
        return ""
    lines = []
    for turn in history[-3:]:
        user = turn.get("user", "")
        assistant = turn.get("assistant", "")
        if user:
            lines.append(f"user: {user}")
        if assistant:
            lines.append(f"assistant: {assistant}")
    return " | ".join(lines)


def get_last_turn(session_id: str | None) -> dict[str, str] | None:
    rows = get_conversation_history(session_id)
    if not rows:
        return None
    last = rows[-1]
    return {k: str(v) for k, v in last.items()}


def clear_memory() -> None:
    with _LOCK:
        _load_if_needed_unlocked()
        _STORE.clear()
        _serialize()


def list_sessions() -> list[dict[str, str]]:
    with _LOCK:
        _load_if_needed_unlocked()
        _prune_expired_unlocked()
        rows: list[dict[str, str]] = []
        for session_id, row in _STORE.items():
            turns = list(row.get("turns", []))
            preview = ""
            if turns:
                preview = str(turns[-1].get("user", ""))[:80]
            rows.append(
                {
                    "session_id": session_id,
                    "preview": preview,
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(row.get("updated_at", _now())))),
                }
            )
        rows.sort(key=lambda x: x["updated_at"], reverse=True)
        _serialize()
    return rows


def delete_session(session_id: str | None) -> bool:
    key = normalize_session_id(session_id)
    if not key:
        return False
    with _LOCK:
        _load_if_needed_unlocked()
        _prune_expired_unlocked()
        existed = key in _STORE
        if existed:
            _STORE.pop(key, None)
            _serialize()
    return existed
