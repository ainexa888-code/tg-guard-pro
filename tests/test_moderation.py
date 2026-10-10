import pytest

from app.database.repositories.group_repo import get_or_create_group
from app.database.repositories.moderation_repo import get_warnings_count
from app.services.moderation import ModerationService


@pytest.mark.asyncio
async def test_warning_escalation_to_mute(test_session, mock_bot):
    chat_id = -100111
    user_id = 12345

    _, settings = await get_or_create_group(test_session, chat_id, "Test Group 1")
    settings.warn_limit = 3
    settings.warn_action = "mute"
    await test_session.commit()

    # Warn 1
    cnt, esc = await ModerationService.warn_user(
        bot=mock_bot,
        session=test_session,
        chat_id=chat_id,
        user_id=user_id,
        reason="Rule violation 1",
        settings=settings,
    )
    assert cnt == 1
    assert esc is None

    # Warn 2
    cnt, esc = await ModerationService.warn_user(
        bot=mock_bot,
        session=test_session,
        chat_id=chat_id,
        user_id=user_id,
        reason="Rule violation 2",
        settings=settings,
    )
    assert cnt == 2
    assert esc is None

    # Warn 3 -> Hits limit 3 -> Escalation action taken!
    cnt, esc = await ModerationService.warn_user(
        bot=mock_bot,
        session=test_session,
        chat_id=chat_id,
        user_id=user_id,
        reason="Rule violation 3",
        settings=settings,
    )
    assert cnt == 3
    assert esc == "mute"
    # Warnings reset after escalation
    new_cnt = await get_warnings_count(test_session, chat_id, user_id)
    assert new_cnt == 0


@pytest.mark.asyncio
async def test_group_isolation(test_session, mock_bot):
    chat1 = -100111
    chat2 = -100222
    user_id = 99999

    _, s1 = await get_or_create_group(test_session, chat1, "Chat 1")
    _, s2 = await get_or_create_group(test_session, chat2, "Chat 2")

    # Add warning in Chat 1
    await ModerationService.warn_user(
        bot=mock_bot,
        session=test_session,
        chat_id=chat1,
        user_id=user_id,
        reason="Chat 1 violation",
        settings=s1,
    )

    # Chat 1 has 1 warning, Chat 2 has 0 warnings for the same user
    cnt1 = await get_warnings_count(test_session, chat1, user_id)
    cnt2 = await get_warnings_count(test_session, chat2, user_id)

    assert cnt1 == 1
    assert cnt2 == 0
