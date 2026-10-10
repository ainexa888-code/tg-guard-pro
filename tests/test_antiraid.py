from app.services.antiraid import AntiRaidService


def test_anti_raid_detection():
    chat_id = -100444
    limit = 5
    window = 10

    # 4 joins: under limit
    for _ in range(4):
        is_raid, cnt = AntiRaidService.record_join_and_check_raid(
            chat_id, raid_limit=limit, raid_window=window
        )
        assert is_raid is False

    # 5th join: hits limit!
    is_raid, cnt = AntiRaidService.record_join_and_check_raid(
        chat_id, raid_limit=limit, raid_window=window
    )
    assert is_raid is True
    assert cnt >= 5
    assert AntiRaidService.is_lockdown_active(chat_id) is True

    # Manual clear
    AntiRaidService.clear_lockdown(chat_id)
    assert AntiRaidService.is_lockdown_active(chat_id) is False
