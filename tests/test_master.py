import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, CallbackQuery, User, Chat
from app.config import get_settings
from app.core.permissions import is_master_owner, check_bot_detailed_permissions
from app.bot.handlers.master import _verify_master_access, cmd_master

settings = get_settings()


def test_is_master_owner():
    assert is_master_owner(settings.master_owner_id) is True
    assert is_master_owner(999999999) is False
    assert is_master_owner(0) is False


@pytest.mark.asyncio
async def test_verify_master_access_owner(mock_bot):
    msg = MagicMock(spec=Message)
    msg.from_user = User(id=settings.master_owner_id, is_bot=False, first_name="Master")

    allowed = await _verify_master_access(msg, mock_bot)
    assert allowed is True


@pytest.mark.asyncio
async def test_verify_master_access_unauthorized_user(mock_bot):
    msg = MagicMock(spec=Message)
    msg.from_user = User(id=555555555, is_bot=False, first_name="Intruder", username="intruder")
    msg.reply = AsyncMock()

    allowed = await _verify_master_access(msg, mock_bot)
    assert allowed is False
    msg.reply.assert_called_with("❌ यह कमांड उपलब्ध नहीं है।")


@pytest.mark.asyncio
async def test_master_command_rejected_in_group(mock_bot, test_session):
    msg = MagicMock(spec=Message)
    msg.chat = Chat(id=-100123456, type="supergroup", title="Test Group")
    msg.from_user = User(id=settings.master_owner_id, is_bot=False, first_name="Master")
    msg.reply = AsyncMock()

    await cmd_master(msg, mock_bot, test_session)
    msg.reply.assert_called_with("🔒 सुरक्षा कारणों से मास्टर पैनल केवल बॉट के साथ प्राइवेट चैट में ही खुलता है।")


@pytest.mark.asyncio
async def test_check_bot_detailed_permissions(mock_bot):
    chat_id = -100999
    # Bot not admin
    mock_bot.get_chat_member.return_value = MagicMock(status="member")
    perms = await check_bot_detailed_permissions(mock_bot, chat_id)
    assert perms["is_admin"] is False
