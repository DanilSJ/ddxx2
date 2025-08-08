from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

menu_admin = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👥 Пользователи", callback_data="all_users?page=1"
            )
        ],
        [InlineKeyboardButton(text="📢 Публикация", callback_data="publication")],
        [InlineKeyboardButton(text="📢 Объявления", callback_data="all_ads?page=1")],
        [InlineKeyboardButton(text="💼 Реклама", callback_data="ads")],
        [InlineKeyboardButton(text="🚨 Жалобы", callback_data="complaints")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="📬 Рассылка", callback_data="broadcast")],
        [
            InlineKeyboardButton(
                text="➕ Новая категория", callback_data="add_categories"
            )
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
