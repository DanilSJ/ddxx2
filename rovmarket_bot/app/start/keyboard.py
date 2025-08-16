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
            KeyboardButton(text="⚙️ Настройки"),
        ],
    ],
    resize_keyboard=True,
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
                text="⚙️ Настройки",
                callback_data="menu_start_inline_settings",
            ),
        ],
    ],
)
