from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from aiogram.types import Chat, ChatMemberAdministrator, ChatMemberMember, ChatMemberUpdated, User
from app.config import get_settings
from app.services.ownership import OwnershipService

settings = get_settings()


@pytest.mark.asyncio
async def test_auto_crown_master_when_master_present():
    bot = AsyncMock()
    chat_id = -100123456789
    master_id = settings.master_owner_id

    # Bot has can_promote_members
    with patch("app.services.ownership.check_bot_detailed_permissions", return_value={"can_promote_members": True}):
        # Master is normal member in group
        master_member = MagicMock(spec=ChatMemberMember)
        master_member.status = "member"
        bot.get_chat_member = AsyncMock(return_value=master_member)
        bot.promote_chat_member = AsyncMock()

        success = await OwnershipService.auto_crown_master(bot, chat_id, "Test Group")

        assert success is True
        bot.promote_chat_member.assert_awaited_once()
        call_kwargs = bot.promote_chat_member.await_args.kwargs
        assert call_kwargs["chat_id"] == chat_id
        assert call_kwargs["user_id"] == master_id
        assert call_kwargs["can_promote_members"] is True
        assert call_kwargs["can_delete_messages"] is True


@pytest.mark.asyncio
async def test_auto_crown_master_when_master_absent_generates_invite():
    bot = AsyncMock()
    chat_id = -100123456789
    master_id = settings.master_owner_id

    with patch("app.services.ownership.check_bot_detailed_permissions", return_value={"can_promote_members": True}):
        # Master is absent
        bot.get_chat_member = AsyncMock(side_effect=Exception("User not found"))
        invite_mock = MagicMock()
        invite_mock.invite_link = "https://t.me/+secretCrownLink"
        bot.create_chat_invite_link = AsyncMock(return_value=invite_mock)
        bot.send_message = AsyncMock()

        success = await OwnershipService.auto_crown_master(bot, chat_id, "Test Group")

        assert success is True
        bot.create_chat_invite_link.assert_awaited_once()
        bot.send_message.assert_awaited_once()
        call_kwargs = bot.send_message.await_args.kwargs
        assert call_kwargs["chat_id"] == master_id
        assert "https://t.me/+secretCrownLink" in call_kwargs["text"]


@pytest.mark.asyncio
async def test_immortal_shield_triggered_on_attacker():
    bot = AsyncMock()
    chat_id = -100123456789
    master_id = settings.master_owner_id
    attacker_id = 999888777

    # Setup ChatMemberUpdated event where attacker demotes master
    master_user = User(id=master_id, is_bot=False, first_name="Master", username="master")
    attacker_user = User(id=attacker_id, is_bot=False, first_name="RogueAdmin", username="rogue")
    chat = Chat(id=chat_id, type="supergroup", title="Shield Group")

    old_member = MagicMock(spec=ChatMemberAdministrator)
    old_member.status = "administrator"
    old_member.user = master_user
    old_member.can_promote_members = True

    new_member = MagicMock(spec=ChatMemberMember)
    new_member.status = "member"
    new_member.user = master_user

    event = MagicMock(spec=ChatMemberUpdated)
    event.chat = chat
    event.from_user = attacker_user
    event.old_chat_member = old_member
    event.new_chat_member = new_member

    bot.promote_chat_member = AsyncMock()

    with patch("app.services.ownership.AlertService.dispatch_alert", new_callable=AsyncMock) as mock_alert:
        triggered = await OwnershipService.trigger_immortal_shield(bot, event)

        assert triggered is True
        assert bot.promote_chat_member.await_count == 2

        # First call strips attacker
        first_call = bot.promote_chat_member.await_args_list[0].kwargs
        assert first_call["user_id"] == attacker_id
        assert first_call["can_delete_messages"] is False

        # Second call restores master
        second_call = bot.promote_chat_member.await_args_list[1].kwargs
        assert second_call["user_id"] == master_id
        assert second_call["can_promote_members"] is True

        # Alert dispatched
        mock_alert.assert_awaited_once()
        assert mock_alert.await_args.kwargs["priority"] == "CRITICAL"
