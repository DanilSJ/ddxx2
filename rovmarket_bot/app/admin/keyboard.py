from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

menu_admin = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👥 Пользователи", callback_data="all_users?page=1"
            )
        ],
        [
            InlineKeyboardButton(text="📢 Публикация", callback_data="publication"),
        ],
        [
            InlineKeyboardButton(
                text="📋 Объявления",
                callback_data="all_ads_admin?page=1",
            )
        ],
        [
            InlineKeyboardButton(
                text="💼 Реклама",
                callback_data="ads",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🚨 Жалобы",
                callback_data="complaints",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📊 Статистика",
                callback_data="stats",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📬 Рассылка",
                callback_data="broadcast",
            ),
        ],
        [
            InlineKeyboardButton(
                text="➕ Новая категория",
                callback_data="add_categories",
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Настройки",
                callback_data="admin_settings",
            ),
        ],
    ]
)

menu_stats = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Неделя", callback_data="stats?period=week"),
            InlineKeyboardButton(text="🗓️ Месяц", callback_data="stats?period=month"),
            InlineKeyboardButton(text="📈 Год", callback_data="stats?period=year"),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back"),
        ],
    ]
)
menu_back = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back"),
        ]
    ]
)


def build_admin_settings_keyboard(
    *, moderation: bool, logging: bool, notifications_all: bool
) -> InlineKeyboardMarkup:
    mod_status = "✅" if moderation else "❌"
    log_status = "✅" if logging else "❌"
    notifications_status = "✅" if notifications_all else "❌"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🛡 Модерация: {mod_status}", callback_data="toggle_moderation"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"📝 Логирование: {log_status}", callback_data="toggle_logging"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🔔 Уведомления: {notifications_status}",
                    callback_data="toggle_notifications",
                )
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
        ]
    )
