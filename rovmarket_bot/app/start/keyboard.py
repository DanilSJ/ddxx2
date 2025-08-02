from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

menu_start = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🔍 Найти объявление",  callback_data="find"),
        InlineKeyboardButton(text="📢 Разместить объявление", callback_data="post"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
    ]
])