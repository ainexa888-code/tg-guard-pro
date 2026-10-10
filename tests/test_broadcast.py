import pytest

from app.database.repositories.broadcast_repo import get_opted_in_groups
from app.database.repositories.group_repo import (
    get_or_create_group,
    update_group_settings,
)


@pytest.mark.asyncio
async def test_broadcast_opt_in_out(test_session):
    chat1 = -100101
    chat2 = -100102

    await get_or_create_group(test_session, chat1, "Group 1")
    await get_or_create_group(test_session, chat2, "Group 2")

    # Group 1 is opted-in (default)
    # Group 2 opts out
    await update_group_settings(test_session, chat2, broadcast_optin=False)

    opted_in = await get_opted_in_groups(test_session)
    assert chat1 in opted_in
    assert chat2 not in opted_in
