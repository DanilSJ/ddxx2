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
