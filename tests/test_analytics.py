import pytest

from app.database.repositories.analytics_repo import (
    get_stats_summary,
    increment_daily_stat,
)


@pytest.mark.asyncio
async def test_analytics_increment_and_aggregation(test_session):
    chat_id = -100777

    await increment_daily_stat(test_session, chat_id, "messages_count", 5)
    await increment_daily_stat(test_session, chat_id, "spam_blocked_count", 2)
    await increment_daily_stat(test_session, chat_id, "links_blocked_count", 1)

    summary = await get_stats_summary(test_session, chat_id, days=7)
    assert summary["total_messages"] == 5
    assert summary["spam_blocked"] == 2
    assert summary["links_blocked"] == 1
    assert summary["captcha_success"] == 0
