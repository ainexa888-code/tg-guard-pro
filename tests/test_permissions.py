from unittest.mock import MagicMock

import pytest
from aiogram.types import ChatMemberAdministrator, ChatMemberMember, ChatMemberOwner

from app.core.permissions import (
    can_user_moderate,
    get_user_chat_permissions,
    is_user_admin,
)


@pytest.mark.asyncio
async def test_owner_permissions(mock_bot):
    chat_id = -100123
    owner_id = 11111

    owner_member = MagicMock(spec=ChatMemberOwner)
    owner_member.status = "creator"
    mock_bot.get_chat_member.return_value = owner_member

    is_adm, is_own, can_res, can_del = await get_user_chat_permissions(
        mock_bot, chat_id, owner_id, force_refresh=True
    )
    assert is_adm is True
    assert is_own is True
    assert can_res is True
    assert can_del is True
    assert await is_user_admin(mock_bot, chat_id, owner_id) is True
    assert await can_user_moderate(mock_bot, chat_id, owner_id) is True


@pytest.mark.asyncio
async def test_admin_with_restrict_rights(mock_bot):
    chat_id = -100123
    admin_id = 22222

    admin_member = MagicMock(spec=ChatMemberAdministrator)
    admin_member.status = "administrator"
    admin_member.can_restrict_members = True
    admin_member.can_delete_messages = True
    mock_bot.get_chat_member.return_value = admin_member

    is_adm, is_own, can_res, can_del = await get_user_chat_permissions(
        mock_bot, chat_id, admin_id, force_refresh=True
    )
    assert is_adm is True
    assert is_own is False
    assert can_res is True
    assert can_del is True
    assert await can_user_moderate(mock_bot, chat_id, admin_id) is True


@pytest.mark.asyncio
async def test_regular_member_cannot_moderate(mock_bot):
    chat_id = -100123
    member_id = 33333

    regular_member = MagicMock(spec=ChatMemberMember)
    regular_member.status = "member"
    mock_bot.get_chat_member.return_value = regular_member

    is_adm, is_own, can_res, can_del = await get_user_chat_permissions(
        mock_bot, chat_id, member_id, force_refresh=True
    )
    assert is_adm is False
    assert is_own is False
    assert can_res is False
    assert can_del is False
    assert await is_user_admin(mock_bot, chat_id, member_id) is False
    assert await can_user_moderate(mock_bot, chat_id, member_id) is False
