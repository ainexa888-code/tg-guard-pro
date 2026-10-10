import hashlib
import time
import unicodedata
from collections import deque

from aiogram.types import Message

from app.config import get_settings

settings = get_settings()

# Optional Redis connection
_redis_client = None
if settings.redis_url:
    try:
        import redis.asyncio as aioredis

        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        _redis_client = None

# In-memory fallbacks:
# Message timestamps: (chat_id, user_id) -> deque([timestamp, ...])
_USER_MESSAGE_TIMESTAMPS: dict[tuple[int, int], deque] = {}
# Recent message hashes: (chat_id, user_id) -> deque([(hash, timestamp), ...])
_USER_MESSAGE_HASHES: dict[tuple[int, int], deque] = {}


def count_emojis(text: str) -> int:
    """Counts emoji symbols in the text."""
    if not text:
        return 0
    emoji_count = 0
    for char in text:
        # Common emoji category symbols & pictographs
        cat = unicodedata.category(char)
        if cat in ("So", "Sk") or (0x1F300 <= ord(char) <= 0x1FAFF):
            emoji_count += 1
    return emoji_count


def count_mentions(message: Message) -> int:
    """Counts user mentions in a message from text entities and '@' signs."""
    entities = (message.entities or []) + (message.caption_entities or [])
    entity_mentions = sum(1 for e in entities if e.type in ("mention", "text_mention"))
    text = (message.text or "") + " " + (message.caption or "")
    at_mentions = text.count("@")
    return max(entity_mentions, at_mentions)


class AntiSpamService:
    @staticmethod
    async def check_flood(
        chat_id: int,
        user_id: int,
        limit: int = 5,
        interval: int = 5,
    ) -> bool:
        """
        Returns True if the user exceeds the message rate limit (flood).
        Uses Redis if configured, otherwise high-performance in-memory sliding window.
        """
        now = time.time()
        if _redis_client:
            try:
                key = f"spam:flood:{chat_id}:{user_id}"
                pipeline = _redis_client.pipeline()
                pipeline.zremrangebyscore(key, 0, now - interval)
                pipeline.zadd(key, {str(now): now})
                pipeline.zcard(key)
                pipeline.expire(key, interval + 2)
                results = await pipeline.execute()
                count = results[2]
                return count > limit
            except Exception:
                pass  # Fall back to memory on Redis errors

        key = (chat_id, user_id)
        if key not in _USER_MESSAGE_TIMESTAMPS:
            _USER_MESSAGE_TIMESTAMPS[key] = deque()

        q = _USER_MESSAGE_TIMESTAMPS[key]
        cutoff = now - interval
        while q and q[0] < cutoff:
            q.popleft()

        q.append(now)
        return len(q) > limit

    @staticmethod
    async def check_duplicate(
        chat_id: int,
        user_id: int,
        text: str,
        threshold: int = 3,
        window: int = 30,
    ) -> bool:
        """
        Returns True if the user sends identical messages repeatedly within a time window.
        """
        if not text or len(text.strip()) < 3:
            return False

        msg_hash = hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest()
        now = time.time()
        key = (chat_id, user_id)

        if key not in _USER_MESSAGE_HASHES:
            _USER_MESSAGE_HASHES[key] = deque()

        q = _USER_MESSAGE_HASHES[key]
        cutoff = now - window
        while q and q[0][1] < cutoff:
            q.popleft()

        match_count = sum(1 for h, _ in q if h == msg_hash)
        q.append((msg_hash, now))

        return (match_count + 1) >= threshold

    @classmethod
    async def inspect_message(
        cls,
        message: Message,
        spam_limit: int = 5,
        spam_interval: int = 5,
        emoji_limit: int = 12,
        mention_limit: int = 5,
    ) -> tuple[bool, str | None]:
        """
        Runs comprehensive anti-spam inspection.
        Returns (is_spam, reason).
        """
        chat_id = message.chat.id
        user_id = message.from_user.id
        text = message.text or message.caption or ""

        # 1. Flood check
        if await cls.check_flood(
            chat_id, user_id, limit=spam_limit, interval=spam_interval
        ):
            return True, "Message flooding detected"

        # 2. Duplicate text check
        if await cls.check_duplicate(chat_id, user_id, text, threshold=3, window=30):
            return True, "Repeated identical messages"

        # 3. Emoji flood
        if count_emojis(text) > emoji_limit:
            return True, "Excessive emoji flooding"

        # 4. Mention flood
        if count_mentions(message) > mention_limit:
            return True, "Excessive user mentions"

        return False, None
