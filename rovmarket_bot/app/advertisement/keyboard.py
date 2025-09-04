from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


ad_type_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📣 Рассылка", callback_data="ad_type:broadcast")],
        [
            InlineKeyboardButton(
                text="📌 Рассылка с закреплением", callback_data="ad_type:broadcast_pinned"
            )
        ],
        [InlineKeyboardButton(text="📋 Реклама в меню", callback_data="ad_type:menu")],
        [
            InlineKeyboardButton(
                text="📰 Реклама в объявлениях", callback_data="ad_type:listings"
            )
        ],
    ]
)


duration_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🗓 1 день", callback_data="ad_duration:day")],
        [InlineKeyboardButton(text="📅 Неделя", callback_data="ad_duration:week")],
        [InlineKeyboardButton(text="🗓 Месяц", callback_data="ad_duration:month")],
    ]
)


confirm_media_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить", callback_data="ad_photos_done")]]
)

