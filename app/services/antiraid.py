import time
from collections import deque

# Sliding window of join timestamps per group: chat_id -> deque([timestamp, ...])
_JOIN_TIMESTAMPS: dict[int, deque] = {}

# Active raid alert flags: chat_id -> until_timestamp
_ACTIVE_RAID_LOCKDOWNS: dict[int, float] = {}


class AntiRaidService:
    @staticmethod
    def record_join_and_check_raid(
        chat_id: int,
        raid_limit: int = 15,
        raid_window: int = 60,
    ) -> tuple[bool, int]:
        """
        Records a new member join and verifies whether join rate triggers anti-raid protection.
        Returns (is_raid_detected, joins_in_window).
        """
        now = time.time()
        if chat_id not in _JOIN_TIMESTAMPS:
            _JOIN_TIMESTAMPS[chat_id] = deque()

        q = _JOIN_TIMESTAMPS[chat_id]
        cutoff = now - raid_window
        while q and q[0] < cutoff:
            q.popleft()

        q.append(now)
        current_count = len(q)

        is_raid = current_count >= raid_limit
        if is_raid:
            # Set a 5-minute lockdown indicator
            _ACTIVE_RAID_LOCKDOWNS[chat_id] = now + 300

        return is_raid, current_count

    @staticmethod
    def is_lockdown_active(chat_id: int) -> bool:
        """Returns True if the group is currently in temporary raid lockdown."""
        now = time.time()
        expiry = _ACTIVE_RAID_LOCKDOWNS.get(chat_id, 0.0)
        return now < expiry

    @staticmethod
    def clear_lockdown(chat_id: int) -> None:
        """Manually lifts raid lockdown status."""
        _ACTIVE_RAID_LOCKDOWNS.pop(chat_id, None)
        _JOIN_TIMESTAMPS.pop(chat_id, None)
