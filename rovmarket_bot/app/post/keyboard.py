from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

contractual = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Договорная", callback_data="price_negotiable")]
    ]
)

contact = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📱 Отправить номер телефона", request_contact=True),
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)
