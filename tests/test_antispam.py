import pytest

from app.services.antispam import AntiSpamService, count_emojis


@pytest.mark.asyncio
async def test_flood_detection():
    chat_id = -100999
    user_id = 111

    # Sending 3 messages quickly with limit=3, interval=5
    assert (
        await AntiSpamService.check_flood(chat_id, user_id, limit=3, interval=5)
        is False
    )
    assert (
        await AntiSpamService.check_flood(chat_id, user_id, limit=3, interval=5)
        is False
    )
    assert (
        await AntiSpamService.check_flood(chat_id, user_id, limit=3, interval=5)
        is False
    )
    # 4th message exceeds limit!
    assert (
        await AntiSpamService.check_flood(chat_id, user_id, limit=3, interval=5) is True
    )


@pytest.mark.asyncio
async def test_duplicate_message_detection():
    chat_id = -100888
    user_id = 222
    text = "Join my promo channel now!"

    # Send identical text
    assert (
        await AntiSpamService.check_duplicate(chat_id, user_id, text, threshold=3)
        is False
    )
    assert (
        await AntiSpamService.check_duplicate(chat_id, user_id, text, threshold=3)
        is False
    )
    assert (
        await AntiSpamService.check_duplicate(chat_id, user_id, text, threshold=3)
        is True
    )


def test_count_emojis():
    assert count_emojis("Hello ❤️🔥🎉👍") == 4
    assert count_emojis("Just plain english text") == 0
    assert count_emojis("🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥") == 13
