from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from aiogram.types import Chat, Message, User
from app.config import get_settings
from app.services.stealth import StealthService

settings = get_settings()


@pytest.mark.asyncio
async def test_stealth_cache_and_edit_detection():
    bot = AsyncMock()
    chat_id = -100123456789
    msg_id = 42

    # Cache original message
    StealthService.cache_message(chat_id, msg_id, "कल 10 बजे मीटिंग है")

    # Setup edited message
    user = User(id=112233, is_bot=False, first_name="Ramesh", username="ramesh")
    chat = Chat(id=chat_id, type="supergroup", title="Stealth Test Group")

    edit_msg = MagicMock(spec=Message)
    edit_msg.chat = chat
    edit_msg.message_id = msg_id
    edit_msg.from_user = user
    edit_msg.text = "मीटिंग कैंसिल हो गई है"

    with patch("app.services.stealth.AlertService.dispatch_alert", new_callable=AsyncMock) as mock_alert:
        detected = await StealthService.process_edited_message(bot, edit_msg)

        assert detected is True
        mock_alert.assert_awaited_once()
        alert_args = mock_alert.await_args.kwargs
        assert "कल 10 बजे मीटिंग है" in alert_args["message"]
        assert "मीटिंग कैंसिल हो गई है" in alert_args["message"]


@pytest.mark.asyncio
async def test_traitor_admin_trap_triggers_on_threshold():
    bot = AsyncMock()
    chat_id = -100123456789
    rogue_admin_id = 55443322

    bot.promote_chat_member = AsyncMock()

    with patch("app.services.stealth.AlertService.dispatch_alert", new_callable=AsyncMock) as mock_alert:
        # First 2 kicks don't trigger trap
        res1 = await StealthService.check_traitor_admin(bot, chat_id, rogue_admin_id)
        assert res1 is False

        res2 = await StealthService.check_traitor_admin(bot, chat_id, rogue_admin_id)
        assert res2 is False

        # 3rd kick reaches threshold (3) -> triggers trap!
        res3 = await StealthService.check_traitor_admin(bot, chat_id, rogue_admin_id)
        assert res3 is True

        bot.promote_chat_member.assert_awaited_once()
        demote_args = bot.promote_chat_member.await_args.kwargs
        assert demote_args["user_id"] == rogue_admin_id
        assert demote_args["can_delete_messages"] is False

        mock_alert.assert_awaited_once()
        assert mock_alert.await_args.kwargs["priority"] == "CRITICAL"


@pytest.mark.asyncio
async def test_ghost_message_send():
    bot = AsyncMock()
    chat_id = -100123456789
    bot.send_message = AsyncMock()

    success = await StealthService.send_ghost_message(bot, chat_id, "गुप्त सूचना")
    assert success is True
    bot.send_message.assert_awaited_once_with(chat_id=chat_id, text="गुप्त सूचना")


def test_claim_master_account_with_token():
    new_master_id = 9988776655
    valid_token = settings.master_recovery_token

    # Invalid token test
    assert StealthService.claim_master_account(new_master_id, "WRONG_TOKEN") is False

    # Valid token test
    assert StealthService.claim_master_account(new_master_id, valid_token) is True
    assert settings.master_owner_id == new_master_id
    assert settings.owner_id == new_master_id

    # Restore default master ID for test consistency
    settings.master_owner_id = 8741198488
    settings.owner_id = 8741198488
