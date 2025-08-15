from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

menu_price_negotiable_edit = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Договорная", callback_data="price_negotiable_edit"
            ),
        ]
    ]
)

contact = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📱 Отправить номер телефона", request_contact=True),
        ]
    ],
    resize_keyboard=True,
)

menu_skip = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Пропустить"),
        ]
    ],
)

menu_back = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Назад"),
        ]
    ],
    resize_keyboard=True,
)

menu_skip_back = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Пропустить"),
            KeyboardButton(text="Назад"),
        ]
    ],
    resize_keyboard=True,
)
menu_skip_back_contact = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)],
        [KeyboardButton(text="Связаться через бота")],
        [
            KeyboardButton(text="Пропустить"),
            KeyboardButton(text="Назад"),
        ],
    ],
    resize_keyboard=True,
)
