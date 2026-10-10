import asyncio
import logging
from datetime import UTC, datetime, timedelta

from aiogram import Bot

from app.database.repositories.moderation_repo import (
    get_due_message_deletions,
    mark_deletion_processed,
    schedule_message_deletion,
)
from app.database.session import AsyncSessionLocal

logger = logging.getLogger("tg_guard_pro.scheduler")


class SchedulerService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self._running = False
        self._task: asyncio.Task | None = None

    async def schedule_auto_delete(
        self,
        chat_id: int,
        message_id: int,
        delay_seconds: int = 60,
        reason: str | None = "auto_delete",
    ) -> None:
        """Saves a scheduled deletion persistently in the database."""
        delete_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
        async with AsyncSessionLocal() as session:
            await schedule_message_deletion(
                session=session,
                chat_id=chat_id,
                message_id=message_id,
                delete_at=delete_at,
                reason=reason,
            )

    async def _worker_loop(self) -> None:
        """Continuously inspects database for due scheduled deletions."""
        while self._running:
            try:
                async with AsyncSessionLocal() as session:
                    due_items = await get_due_message_deletions(session)
                    for item in due_items:
                        try:
                            await self.bot.delete_message(
                                chat_id=item.group_id,
                                message_id=item.message_id,
                            )
                        except Exception:
                            pass  # Already deleted or missing delete rights
                        finally:
                            await mark_deletion_processed(session, item.id)
            except Exception as e:
                logger.error(f"Error in scheduler worker loop: {e}", exc_info=True)

            await asyncio.sleep(5)

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._worker_loop())
            logger.info("Scheduler service worker started.")

    async def stop(self) -> None:
        if self._running:
            self._running = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            logger.info("Scheduler service worker stopped.")
