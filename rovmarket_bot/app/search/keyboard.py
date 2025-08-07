from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)

menu_search = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Показать все"),
        ],
        [
            KeyboardButton(text="Фильтры"),
        ],
        [
            KeyboardButton(text="Категории"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

pagination_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⬅️"), KeyboardButton(text="➡️")],
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
)
