from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)

menu_settings = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🔔 Уведомления"),
        ],
        [
            KeyboardButton(text="📋 Меню"),
        ],
    ],
    resize_keyboard=True,
)
