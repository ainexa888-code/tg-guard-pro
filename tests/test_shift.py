from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from aiogram.types import Chat, ChatMemberAdministrator, ChatMemberOwner, Message, User
from app.config import get_settings
from app.bot.handlers.admin import cmd_shiftadmin, cmd_shiftowner, cmd_evacuateadmins

settings = get_settings()


@pytest.mark.asyncio
async def test_shiftadmin_swaps_permissions():
    bot = AsyncMock()
    chat_id = -100123456789
    caller_id = settings.master_owner_id
    old_admin_id = 111111
    new_admin_id = 222222

    chat = Chat(id=chat_id, type="supergroup", title="Shift Group")
    caller = User(id=caller_id, is_bot=False, first_name="Master")
    old_admin = User(id=old_admin_id, is_bot=False, first_name="OldAdmin")

    reply_msg = MagicMock(spec=Message)
    reply_msg.from_user = old_admin

    msg = MagicMock(spec=Message)
    msg.chat = chat
    msg.from_user = caller
    msg.reply_to_message = reply_msg
    msg.text = f"/shiftadmin {new_admin_id}"
    msg.reply = AsyncMock()

    old_member_mock = MagicMock(spec=ChatMemberAdministrator)
    old_member_mock.status = "administrator"
    old_member_mock.can_delete_messages = True
    old_member_mock.can_promote_members = True
    old_member_mock.can_restrict_members = True

    bot.get_chat_member = AsyncMock(return_value=old_member_mock)
    bot.promote_chat_member = AsyncMock()

    with patch("app.bot.handlers.admin.can_user_moderate", new_callable=AsyncMock, return_value=True), \
         patch("app.bot.handlers.admin.check_bot_detailed_permissions", new_callable=AsyncMock, return_value={"can_promote_members": True}):
        
        await cmd_shiftadmin(msg, bot)

        # Promoted new admin and demoted old admin
        assert bot.promote_chat_member.await_count == 2
        call_promote = bot.promote_chat_member.await_args_list[0].kwargs
        assert call_promote["user_id"] == new_admin_id
        assert call_promote["can_delete_messages"] is True

        call_demote = bot.promote_chat_member.await_args_list[1].kwargs
        assert call_demote["user_id"] == old_admin_id
        assert call_demote["can_delete_messages"] is False


@pytest.mark.asyncio
async def test_shiftowner_promotes_supreme():
    bot = AsyncMock()
    chat_id = -100123456789
    caller_id = settings.master_owner_id
    new_owner_id = 333333

    chat = Chat(id=chat_id, type="supergroup", title="Shift Group")
    caller = User(id=caller_id, is_bot=False, first_name="Master")

    msg = MagicMock(spec=Message)
    msg.chat = chat
    msg.from_user = caller
    msg.reply_to_message = None
    msg.text = f"/shiftowner {new_owner_id}"
    msg.reply = AsyncMock()

    bot.promote_chat_member = AsyncMock()

    with patch("app.bot.handlers.admin.can_user_moderate", new_callable=AsyncMock, return_value=True), \
         patch("app.bot.handlers.admin.check_bot_detailed_permissions", new_callable=AsyncMock, return_value={"can_promote_members": True}):

        await cmd_shiftowner(msg, bot)

        assert bot.promote_chat_member.await_count == 1
        call_kwargs = bot.promote_chat_member.await_args.kwargs
        assert call_kwargs["user_id"] == new_owner_id
        assert call_kwargs["can_promote_members"] is True
        assert call_kwargs["can_restrict_members"] is True


@pytest.mark.asyncio
async def test_evacuateadmins_demotes_only_non_master_admins():
    bot = AsyncMock()
    bot.id = 8832895009
    chat_id = -100123456789
    master_id = settings.master_owner_id
    rogue_admin_id = 444444

    chat = Chat(id=chat_id, type="supergroup", title="Shift Group")
    caller = User(id=master_id, is_bot=False, first_name="Master")

    msg = MagicMock(spec=Message)
    msg.chat = chat
    msg.from_user = caller
    msg.text = "/evacuateadmins"
    msg.reply = AsyncMock()

    creator_mock = MagicMock(spec=ChatMemberOwner)
    creator_mock.status = "creator"
    creator_mock.user = User(id=10001, is_bot=False, first_name="Creator")

    master_mock = MagicMock(spec=ChatMemberAdministrator)
    master_mock.status = "administrator"
    master_mock.user = User(id=master_id, is_bot=False, first_name="Master")

    rogue_mock = MagicMock(spec=ChatMemberAdministrator)
    rogue_mock.status = "administrator"
    rogue_mock.user = User(id=rogue_admin_id, is_bot=False, first_name="Rogue")

    bot.get_chat_administrators = AsyncMock(return_value=[creator_mock, master_mock, rogue_mock])
    bot.promote_chat_member = AsyncMock()

    with patch("app.bot.handlers.admin.check_bot_detailed_permissions", new_callable=AsyncMock, return_value={"can_promote_members": True}):
        await cmd_evacuateadmins(msg, bot)

        # Only rogue admin demoted (creator and master skipped!)
        assert bot.promote_chat_member.await_count == 1
        demote_kwargs = bot.promote_chat_member.await_args.kwargs
        assert demote_kwargs["user_id"] == rogue_admin_id
        assert demote_kwargs["can_delete_messages"] is False
