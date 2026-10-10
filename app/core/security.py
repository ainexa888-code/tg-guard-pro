import html
import time
import unicodedata

_THROTTLE_CACHE: dict[tuple[int, str], float] = {}


def sanitize_telegram_html(text: str) -> str:
    """Safely escapes arbitrary user content so it won't break Telegram HTML formatting."""
    if not text:
        return ""
    return html.escape(text)


def normalize_unicode(text: str) -> str:
    """Normalizes Unicode text to NFKC to uncover hidden/spoofed characters and fancy fonts."""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text)


def is_rate_limited(user_id: int, action: str, cooldown_seconds: float = 1.0) -> bool:
    """
    Simple per-user action rate limiter to protect against button or command spamming.
    Returns True if user is rate limited, False if allowed.
    """
    key = (user_id, action)
    now = time.time()
    last_time = _THROTTLE_CACHE.get(key, 0.0)
    if now - last_time < cooldown_seconds:
        return True
    _THROTTLE_CACHE[key] = now
    # Cleanup stale entries periodically
    if len(_THROTTLE_CACHE) > 5000:
        cutoff = now - 60
        stale = [k for k, v in _THROTTLE_CACHE.items() if v < cutoff]
        for k in stale:
            _THROTTLE_CACHE.pop(k, None)
    return False
