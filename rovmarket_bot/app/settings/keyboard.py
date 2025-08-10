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

menu_notifications = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📂 Категории"),
        ],
        [
            KeyboardButton(text="📢 Все объявления"),
        ],
    ],
    resize_keyboard=True,
)
