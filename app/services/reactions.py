import re
import time

from aiogram import Bot
from aiogram.types import ReactionTypeEmoji

from app.core.security import normalize_unicode

# Cache to avoid reacting twice to the same message: (chat_id, message_id) -> float
_REACTED_MESSAGES: dict[tuple[int, int], float] = {}

# Cooldown per user: (chat_id, user_id) -> float
_USER_REACTION_COOLDOWNS: dict[tuple[int, int], float] = {}


class ReactionEngine:
    @staticmethod
    def match_keyword(text: str, keyword_map: dict[str, str]) -> str | None:
        """
        Matches keywords in text using word boundaries and Unicode normalization.
        Returns the corresponding emoji if found, or None.
        """
        if not text or not keyword_map:
            return None

        normalized = normalize_unicode(text).lower()

        for kw, emoji in keyword_map.items():
            pattern = r"(?<!\w)" + re.escape(kw.lower().strip()) + r"(?!\w)"
            if re.search(pattern, normalized):
                return emoji

        return None

    @staticmethod
    def is_cooldown_active(
        chat_id: int, user_id: int, cooldown_seconds: int = 10
    ) -> bool:
        now = time.time()
        key = (chat_id, user_id)
        last_time = _USER_REACTION_COOLDOWNS.get(key, 0.0)
        if now - last_time < cooldown_seconds:
            return True
        _USER_REACTION_COOLDOWNS[key] = now
        return False

    @classmethod
    async def try_react(
        cls,
        bot: Bot,
        chat_id: int,
        message_id: int,
        user_id: int,
        text: str,
        keyword_map: dict[str, str],
        cooldown_seconds: int = 10,
    ) -> bool:
        """
        Attempts to react to a message if a keyword matches and cooldown allows.
        Avoids reacting to the same message more than once.
        """
        # Guard against duplicate reactions on the exact message
        msg_key = (chat_id, message_id)
        if msg_key in _REACTED_MESSAGES:
            return False

        emoji = cls.match_keyword(text, keyword_map)
        if not emoji:
            return False

        if cls.is_cooldown_active(chat_id, user_id, cooldown_seconds):
            return False

        try:
            await bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction=[ReactionTypeEmoji(emoji=emoji)],
            )
            _REACTED_MESSAGES[msg_key] = time.time()
            # Prune old cache if oversized
            if len(_REACTED_MESSAGES) > 3000:
                cutoff = time.time() - 3600
                stale = [k for k, v in _REACTED_MESSAGES.items() if v < cutoff]
                for k in stale:
                    _REACTED_MESSAGES.pop(k, None)
            return True
        except Exception:
            # Telegram API error or unsupported emoji
            return False
