import asyncio
import logging
import uuid
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter

from app.database.repositories.broadcast_repo import (
    complete_campaign,
    create_campaign,
    get_opted_in_groups,
    record_delivery,
)
from app.database.session import AsyncSessionLocal

logger = logging.getLogger("tg_guard_pro.broadcast")


class BroadcastService:
    @staticmethod
    async def run_broadcast(
        bot: Bot,
        creator_id: int,
        message_text: str,
    ) -> dict[str, Any]:
        """
        Executes a controlled broadcast across opted-in groups with rate limiting and retry backoff.
        """
        campaign_id = str(uuid.uuid4())[:8]

        async with AsyncSessionLocal() as session:
            target_groups = await get_opted_in_groups(session)
            await create_campaign(
                session=session,
                campaign_id=campaign_id,
                creator_id=creator_id,
                text=message_text,
                total_groups=len(target_groups),
            )

        success_count = 0
        failed_count = 0

        for chat_id in target_groups:
            sent = False
            for attempt in range(3):
                try:
                    await bot.send_message(chat_id=chat_id, text=message_text)
                    sent = True
                    success_count += 1
                    async with AsyncSessionLocal() as session:
                        await record_delivery(
                            session, campaign_id, chat_id, status="sent"
                        )
                    break
                except TelegramRetryAfter as e:
                    logger.warning(
                        f"Telegram flood limit hit. Sleeping for {e.retry_after} seconds."
                    )
                    await asyncio.sleep(e.retry_after + 1)
                except TelegramAPIError as e:
                    logger.warning(
                        f"Failed to deliver broadcast to chat {chat_id}: {e}"
                    )
                    async with AsyncSessionLocal() as session:
                        await record_delivery(
                            session,
                            campaign_id,
                            chat_id,
                            status="failed",
                            error_message=str(e),
                        )
                    break
                except Exception as e:
                    logger.error(
                        f"Unexpected error delivering broadcast to {chat_id}: {e}"
                    )
                    break

            if not sent:
                failed_count += 1

            # Controlled inter-message delay (25 messages per second max)
            await asyncio.sleep(0.05)

        async with AsyncSessionLocal() as session:
            await complete_campaign(
                session=session,
                campaign_id=campaign_id,
                successful_groups=success_count,
                failed_groups=failed_count,
            )

        return {
            "campaign_id": campaign_id,
            "total": len(target_groups),
            "success": success_count,
            "failed": failed_count,
        }
