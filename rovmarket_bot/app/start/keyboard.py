from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

menu_start = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🔍 Найти объявление"),
        ],
        [
            KeyboardButton(text="📢 Разместить объявление"),
        ],
        [
            KeyboardButton(text="📋 Мои объявления"),
        ],
        [
            KeyboardButton(text="👥 Мои чаты"),
        ],
        [
            KeyboardButton(
                text="📣 Реклама",
            ),
        ],
        [
            KeyboardButton(text="⚙️ Настройки"),
        ],
    ],
    resize_keyboard=True,
)

menu_ad_inline_write = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📣 Написать",
                url="https://t.me/DanilRov",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📋 Меню", callback_data="menu_search_inline_menu"
            ),
        ],
    ]
)

menu_start_inline = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔍 Найти объявление",
                callback_data="menu_start_inline_search_ads",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📢 Разместить объявление",
                callback_data="menu_start_inline_post_ads",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📋 Мои объявления",
                callback_data="menu_start_inline_my_ads",
            ),
        ],
        [
            InlineKeyboardButton(
                text="👥 Мои чаты",
                callback_data="menu_start_inline_my_chats",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📣 Реклама",
                callback_data="menu_ad_inline_write_callback",
            ),
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Настройки",
                callback_data="menu_start_inline_settings",
            ),
        ],
    ],
)
