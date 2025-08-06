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
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)
