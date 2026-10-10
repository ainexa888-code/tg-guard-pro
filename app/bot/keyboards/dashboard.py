from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_dashboard_main_menu(chat_id: int) -> InlineKeyboardMarkup:
    """Builds the 16-section main dashboard control panel."""
    buttons = [
        [
            InlineKeyboardButton(
                text="🏢 Group Overview", callback_data=f"dash:overview:{chat_id}"
            ),
            InlineKeyboardButton(
                text="👮 Admin Management", callback_data=f"dash:admins:{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🛡️ Security Settings", callback_data=f"dash:security:{chat_id}"
            ),
            InlineKeyboardButton(
                text="⚡ Auto Reactions", callback_data=f"dash:reactions:{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔤 Fancy Font Filter", callback_data=f"dash:fonts:{chat_id}"
            ),
            InlineKeyboardButton(
                text="🚫 Anti-Spam", callback_data=f"dash:antispam:{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔗 Anti-Link", callback_data=f"dash:antilink:{chat_id}"
            ),
            InlineKeyboardButton(
                text="👋 Welcome System", callback_data=f"dash:welcome:{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🤖 Captcha", callback_data=f"dash:captcha:{chat_id}"
            ),
            InlineKeyboardButton(
                text="🚨 Anti-Raid", callback_data=f"dash:antiraid:{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🤬 Bad Words", callback_data=f"dash:badwords:{chat_id}"
            ),
            InlineKeyboardButton(
                text="⏳ Auto Delete", callback_data=f"dash:autodelete:{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="📊 Analytics", callback_data=f"dash:analytics:{chat_id}"
            ),
            InlineKeyboardButton(
                text="📋 Audit Logs", callback_data=f"dash:audit:{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="📢 Broadcast Settings", callback_data=f"dash:broadcast:{chat_id}"
            ),
            InlineKeyboardButton(
                text="💚 Bot Health", callback_data=f"dash:health:{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="❌ Close Panel", callback_data=f"dash:close:{chat_id}"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_toggle_keyboard(
    chat_id: int,
    section: str,
    is_enabled: bool,
    extra_buttons: list = None,
) -> InlineKeyboardMarkup:
    """Constructs a submenu keyboard with toggle and navigation."""
    status_text = (
        "🟢 Enabled (Click to Disable)"
        if is_enabled
        else "🔴 Disabled (Click to Enable)"
    )
    toggle_val = "0" if is_enabled else "1"

    rows = [
        [
            InlineKeyboardButton(
                text=status_text,
                callback_data=f"dash:toggle:{section}:{chat_id}:{toggle_val}",
            )
        ]
    ]
    if extra_buttons:
        rows.extend(extra_buttons)

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Back to Main Menu", callback_data=f"dash:main:{chat_id}"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_audit_logs_keyboard(
    chat_id: int, offset: int = 0, has_next: bool = False
) -> InlineKeyboardMarkup:
    """Pagination keyboard for audit logs."""
    nav_row = []
    if offset > 0:
        prev_offset = max(0, offset - 5)
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Previous",
                callback_data=f"dash:audit_page:{chat_id}:{prev_offset}",
            )
        )
    if has_next:
        next_offset = offset + 5
        nav_row.append(
            InlineKeyboardButton(
                text="Next ➡️", callback_data=f"dash:audit_page:{chat_id}:{next_offset}"
            )
        )

    rows = []
    if nav_row:
        rows.append(nav_row)
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Back to Main Menu", callback_data=f"dash:main:{chat_id}"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
