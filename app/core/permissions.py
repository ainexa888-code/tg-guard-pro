import time

from aiogram import Bot
from aiogram.types import ChatMember, ChatMemberAdministrator, ChatMemberOwner

# In-memory fast cache for group admins: (chat_id, user_id) -> (is_admin, is_owner, can_restrict, can_delete, timestamp)
_ADMIN_CACHE: dict[tuple[int, int], tuple[bool, bool, bool, bool, float]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


async def get_user_chat_permissions(
    bot: Bot, chat_id: int, user_id: int, force_refresh: bool = False
) -> tuple[bool, bool, bool, bool]:
    """
    Returns (is_admin, is_owner, can_restrict, can_delete) for a user in a chat.
    Uses cached data unless expired or explicitly refreshed.
    """
    cache_key = (chat_id, user_id)
    now = time.time()
    if not force_refresh and cache_key in _ADMIN_CACHE:
        is_admin, is_owner, can_restrict, can_delete, ts = _ADMIN_CACHE[cache_key]
        if now - ts < CACHE_TTL_SECONDS:
            return is_admin, is_owner, can_restrict, can_delete

    try:
        member: ChatMember = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if isinstance(member, ChatMemberOwner):
            res = (True, True, True, True)
            _ADMIN_CACHE[cache_key] = (*res, now)
            return res
        elif isinstance(member, ChatMemberAdministrator):
            can_restrict = bool(member.can_restrict_members)
            can_delete = bool(member.can_delete_messages)
            res = (True, False, can_restrict, can_delete)
            _ADMIN_CACHE[cache_key] = (*res, now)
            return res
        else:
            res = (False, False, False, False)
            _ADMIN_CACHE[cache_key] = (*res, now)
            return res
    except Exception:
        # On Telegram API failures, fail safely
        return (False, False, False, False)


def invalidate_admin_cache(chat_id: int, user_id: int | None = None) -> None:
    """Invalidates cached administrator rights when role changes occur."""
    if user_id:
        _ADMIN_CACHE.pop((chat_id, user_id), None)
    else:
        keys_to_del = [k for k in _ADMIN_CACHE if k[0] == chat_id]
        for k in keys_to_del:
            _ADMIN_CACHE.pop(k, None)


async def is_user_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Verifies if the user is a chat administrator, owner, or global super admin."""
    from app.config import get_settings

    if user_id == get_settings().owner_id:
        return True
    is_admin, is_owner, _, _ = await get_user_chat_permissions(bot, chat_id, user_id)
    return is_admin or is_owner


async def can_user_moderate(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Checks if the user has rights to restrict/moderate chat members or is global super admin."""
    from app.config import get_settings

    if user_id == get_settings().owner_id:
        return True
    is_admin, is_owner, can_restrict, _ = await get_user_chat_permissions(
        bot, chat_id, user_id
    )
    return is_owner or (is_admin and can_restrict)


async def can_bot_moderate(bot: Bot, chat_id: int) -> bool:
    """Checks if the bot itself possesses permissions to restrict members and delete messages."""
    try:
        bot_member = await bot.get_chat_member(chat_id=chat_id, user_id=bot.id)
        if isinstance(bot_member, (ChatMemberAdministrator, ChatMemberOwner)):
            return bool(
                bot_member.can_restrict_members and bot_member.can_delete_messages
            )
        return False
    except Exception:
        return False
