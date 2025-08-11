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
            KeyboardButton(text="⚙️ Настройки"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

menu_start_inline = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Все объявления", callback_data="menu_start_inline_all_ads"
            )
        ],
        [
            InlineKeyboardButton(
                text="Создать объявление", callback_data="menu_start_inline_post_ads"
            )
        ],
    ]
)
