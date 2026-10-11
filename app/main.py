import asyncio
import signal
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers import register_all_handlers
from app.bot.middlewares import (
    DatabaseSessionMiddleware,
    ThrottlingMiddleware,
    UserTrackingMiddleware,
)
from app.config import get_settings
from app.core.logging import setup_logger
from app.database.session import close_db, init_db
from app.services.scheduler import SchedulerService

settings = get_settings()
logger = setup_logger(
    log_level=settings.log_level,
    bot_token=settings.bot_token,
    use_json=(settings.environment == "production"),
)

# Initialize Sentry if configured
if settings.sentry_dsn:
    try:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.2)
        logger.info("Sentry monitoring initialized successfully.")
    except Exception as e:
        logger.warning(f"Failed to initialize Sentry: {e}")

import os
from aiohttp import web


async def start_web_health_server(port: int) -> web.AppRunner:
    """Provides a lightweight HTTP endpoint so Render free web services remain active."""
    app = web.Application()

    async def health_handler(request: web.Request) -> web.Response:
        return web.json_response({"status": "healthy", "service": "Group Predictor Bot V4"})

    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check HTTP server listening on 0.0.0.0:{port}")
    return runner


async def main() -> None:
    """Main application lifecycle runner."""
    logger.info("Initializing Group Predictor Bot V4...")
    logger.info(
        f"Environment: {settings.environment} | Database: {settings.database_url.split('@')[-1] if '@' in settings.database_url else 'local'}"
    )

    # Check for bot token
    if not settings.bot_token:
        logger.error(
            "BOT_TOKEN is not configured! Please provide BOT_TOKEN in .env or environment variables."
        )
        sys.exit(1)

    # Initialize Database Schema
    try:
        await init_db()
        logger.info("Database schema initialized and verified.")
    except Exception as e:
        logger.error(f"Fatal error initializing database: {e}", exc_info=True)
        sys.exit(1)

    # Initialize Aiogram Bot & Dispatcher
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Register Middlewares
    dp.update.middleware(DatabaseSessionMiddleware())
    dp.update.middleware(ThrottlingMiddleware(cooldown=0.5))
    dp.update.middleware(UserTrackingMiddleware())

    # Register all Handlers
    register_all_handlers(dp)

    # Initialize background scheduler for auto-deletion and maintenance
    scheduler = SchedulerService(bot)
    scheduler.start()

    # Register graceful shutdown signals
    stop_event = asyncio.Event()

    def signal_handler() -> None:
        logger.info("Shutdown signal received. Initiating graceful termination...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Signal handling on Windows event loop
            pass

    web_runner = None
    try:
        # Launch health server if deployed as web service (Render, Koyeb, Hugging Face, etc.)
        port_env = os.getenv("PORT") or ("7860" if os.getenv("SPACE_ID") else None)
        if port_env and port_env.isdigit():
            web_runner = await start_web_health_server(int(port_env))

        # Clear webhook and discard stale pending updates to prevent conflicts
        await bot.delete_webhook(drop_pending_updates=True)
        bot_info = await bot.get_me()
        logger.info(
            f"Bot successfully authenticated as @{bot_info.username} (ID: {bot_info.id})"
        )
        logger.info("Starting Telegram Bot API long polling consumer...")

        # Start Polling
        polling_task = asyncio.create_task(
            dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        )

        # Wait until stop event is triggered
        while not stop_event.is_set():
            await asyncio.sleep(1)

        logger.info("Stopping polling consumer...")
        await dp.stop_polling()
        await polling_task

    except Exception as e:
        logger.error(f"Unexpected runtime error: {e}", exc_info=True)
    finally:
        logger.info("Performing cleanup tasks...")
        if web_runner:
            await web_runner.cleanup()
        await scheduler.stop()
        await close_db()
        await bot.session.close()
        logger.info("TG GUARD PRO V3 safely terminated.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
