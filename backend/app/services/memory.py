import time
from collections import deque
from shared.constants import MAX_SESSION_HISTORY
from backend.app.logger import get_logger

logger = get_logger(__name__)
_sessions: dict = {}


def get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "session_id": session_id,
            "history":    deque(maxlen=MAX_SESSION_HISTORY),
            "created_at": time.time(),
            "updated_at": time.time(),
        }
    return _sessions[session_id]


def update_session(session_id: str, query: str, action: str, answer_brief: str) -> None:
    session = get_session(session_id)
    session["history"].append({
        "timestamp":    time.time(),
        "query":        query,
        "action":       action,
        "answer_brief": answer_brief[:200],
    })
    session["updated_at"] = time.time()


def get_history(session_id: str) -> list:
    return list(_sessions.get(session_id, {}).get("history", []))


def clear_session(session_id: str) -> bool:
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False
