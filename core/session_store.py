import json
import os
from dataclasses import asdict

from core.session import SessionState

try:
    import redis
except ImportError:
    redis = None

REDIS_URL = os.getenv("REDIS_URL", "")
TTL_SECONDS = 60 * 60 * 4  # 4 hours

_redis = None
_mem_store: dict[str, SessionState] = {}


def get_redis():
    global _redis
    if redis is None or not REDIS_URL:
        return None
    if _redis is None:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def session_get(sid: str) -> SessionState | None:
    r = get_redis()
    if r is None:
        return _mem_store.get(sid)
    raw = r.get(f"session:{sid}")
    if not raw:
        return None
    data = json.loads(raw)
    state = SessionState()
    state.__dict__.update(data)
    return state


def session_set(sid: str, state: SessionState | None = None):
    state = state or SessionState()
    r = get_redis()
    if r is None:
        _mem_store[sid] = state
        return
    r.setex(f"session:{sid}", TTL_SECONDS, json.dumps(asdict(state)))


def session_exists(sid: str) -> bool:
    return session_get(sid) is not None


def session_delete(sid: str):
    r = get_redis()
    if r is None:
        _mem_store.pop(sid, None)
        return
    r.delete(f"session:{sid}")
