from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
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
            KeyboardButton(text="📂 Категории (уведомления)"),
        ],
        [
            KeyboardButton(text="📢 Все объявления (уведомления)"),
        ],
        [
            KeyboardButton(text="📋 Меню"),
        ],
    ],
    resize_keyboard=True,
)
