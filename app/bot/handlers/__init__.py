from aiogram import Dispatcher

from app.bot.handlers import (
    admin,
    analytics,
    antilink,
    antiraid,
    antispam,
    broadcast,
    captcha,
    dashboard,
    fonts,
    groups,
    moderation_pipeline,
    reactions,
    welcome,
    words,
)


def register_all_handlers(dp: Dispatcher) -> None:
    """Registers all routers in order of precedence."""
    dp.include_router(dashboard.router)
    dp.include_router(admin.router)
    dp.include_router(reactions.router)
    dp.include_router(fonts.router)
    dp.include_router(antispam.router)
    dp.include_router(antilink.router)
    dp.include_router(welcome.router)
    dp.include_router(captcha.router)
    dp.include_router(antiraid.router)
    dp.include_router(words.router)
    dp.include_router(analytics.router)
    dp.include_router(broadcast.router)
    dp.include_router(groups.router)
    # Message pipeline registered last so command handlers get prioritized
    dp.include_router(moderation_pipeline.router)
