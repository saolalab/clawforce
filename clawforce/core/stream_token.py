"""Short-lived single-use tokens for SSE and WebSocket endpoints.

EventSource and WebSocket connections cannot carry custom Authorization headers
from the browser. To avoid exposing long-lived JWTs in URL query parameters
(which appear in server access logs and browser history), clients should:

1. Call POST /api/stream-token to obtain a short-lived token (TTL: 5 minutes).
2. Pass that token as the ?token= query parameter on SSE/WebSocket URLs.

Stream tokens carry the same claims as the originating JWT but expire quickly
and are stored only in memory — they are invalidated on server restart.
"""

import secrets
import time
from threading import Lock

_lock = Lock()
_tokens: dict[str, tuple[dict, float]] = {}

_TTL_SECONDS = 300  # 5 minutes


def create_stream_token(claims: dict) -> str:
    """Generate a short-lived stream token carrying the given claims."""
    token = secrets.token_urlsafe(32)
    expires_at = time.monotonic() + _TTL_SECONDS
    with _lock:
        _purge_expired()
        _tokens[token] = (claims, expires_at)
    return token


def verify_stream_token(token: str) -> dict | None:
    """Return claims if the token is valid and not expired, else None."""
    with _lock:
        entry = _tokens.get(token)
        if not entry:
            return None
        claims, expires_at = entry
        if time.monotonic() > expires_at:
            _tokens.pop(token, None)
            return None
        return claims


def _purge_expired() -> None:
    """Remove all expired tokens. Must be called under _lock."""
    now = time.monotonic()
    expired = [t for t, (_, exp) in _tokens.items() if exp < now]
    for t in expired:
        del _tokens[t]
