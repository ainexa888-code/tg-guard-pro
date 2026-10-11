from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from app.database.models import Group


def build_master_main_menu() -> InlineKeyboardMarkup:
    """Builds the comprehensive Master Operator Dashboard control panel."""
    buttons = [
        [
            InlineKeyboardButton(text="🏢 Connected Groups", callback_data="mstr:groups:0"),
            InlineKeyboardButton(text="📢 Channels", callback_data="mstr:channels:0"),
        ],
        [
            InlineKeyboardButton(text="💚 Bot Health & System", callback_data="mstr:health"),
            InlineKeyboardButton(text="🔑 Bot Permissions", callback_data="mstr:permissions"),
        ],
        [
            InlineKeyboardButton(text="📊 Global Analytics", callback_data="mstr:analytics"),
            InlineKeyboardButton(text="🛡️ Security Center", callback_data="mstr:security"),
        ],
        [
            InlineKeyboardButton(text="👮 Admin Management", callback_data="mstr:admins"),
            InlineKeyboardButton(text="🔨 Moderation Center", callback_data="mstr:moderation"),
        ],
        [
            InlineKeyboardButton(text="⚡ Auto Reactions", callback_data="mstr:reactions"),
            InlineKeyboardButton(text="👋 Welcome & Captcha", callback_data="mstr:welcome"),
        ],
        [
            InlineKeyboardButton(text="🚫 Anti-Spam & Flood", callback_data="mstr:antispam"),
            InlineKeyboardButton(text="🔗 Anti-Link Shield", callback_data="mstr:antilink"),
        ],
        [
            InlineKeyboardButton(text="🚨 Anti-Raid Engine", callback_data="mstr:antiraid"),
            InlineKeyboardButton(text="🤬 Bad Words Filter", callback_data="mstr:badwords"),
        ],
        [
            InlineKeyboardButton(text="🔤 Fancy Font Filter", callback_data="mstr:fonts"),
            InlineKeyboardButton(text="📢 Broadcast Center", callback_data="mstr:broadcast"),
        ],
        [
            InlineKeyboardButton(text="🔔 Live Alerts & Logs", callback_data="mstr:alerts"),
            InlineKeyboardButton(text="📋 Audit Logs", callback_data="mstr:logs:0"),
        ],
        [
            InlineKeyboardButton(text="👑 Ownership Info", callback_data="mstr:ownership"),
            InlineKeyboardButton(text="🗄️ Database & Tasks", callback_data="mstr:database"),
        ],
        [
            InlineKeyboardButton(text="🚧 Maintenance Mode", callback_data="mstr:maintenance"),
            InlineKeyboardButton(text="❌ Close Panel", callback_data="mstr:close"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_groups_pagination_keyboard(
    groups: List[Group],
    page: int = 0,
    page_size: int = 5,
) -> InlineKeyboardMarkup:
    """Builds a paginated list of connected groups for the master operator."""
    start_idx = page * page_size
    end_idx = start_idx + page_size
    current_page_groups = groups[start_idx:end_idx]

    rows = []
    for g in current_page_groups:
        title_str = g.title[:24] if g.title else f"Chat {g.id}"
        admin_badge = "👑 Admin" if g.bot_is_admin else "⚠️ Member"
        rows.append([
            InlineKeyboardButton(
                text=f"{title_str} ({admin_badge})",
                callback_data=f"mstr:group_inspect:{g.id}"
            )
        ])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"mstr:groups:{page - 1}"))
    if end_idx < len(groups):
        nav_row.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"mstr:groups:{page + 1}"))

    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="⬅️ Back to Master Menu", callback_data="mstr:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_group_detail_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Action buttons for a selected group in the master panel."""
    buttons = [
        [
            InlineKeyboardButton(text="🎛️ Open Group Settings Panel", callback_data=f"dash:main:{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="🔑 Check Bot Permissions", callback_data=f"mstr:check_perm:{chat_id}"),
            InlineKeyboardButton(text="📊 View Group Stats", callback_data=f"dash:analytics:{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="👮 View Admins", callback_data=f"dash:admins:{chat_id}"),
            InlineKeyboardButton(text="📋 Audit Logs", callback_data=f"dash:audit:{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Back to Groups List", callback_data="mstr:groups:0"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_back_to_master() -> InlineKeyboardMarkup:
    """Simple back button returning to master main menu."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back to Master Menu", callback_data="mstr:main")]]
    )
