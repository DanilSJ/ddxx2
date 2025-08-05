from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
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
            KeyboardButton(text="⚙️ Настройки"),
        ],
    ]
)
