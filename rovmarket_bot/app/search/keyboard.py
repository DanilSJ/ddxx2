from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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


def build_filter_options_keyboard(category_name: str) -> InlineKeyboardMarkup:
    """Inline keyboard with sorting and price range options for selected category."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🆕 Новые",
                    callback_data=f"filter_sort:new:{category_name}",
                ),
                InlineKeyboardButton(
                    text="🗂 Старые",
                    callback_data=f"filter_sort:old:{category_name}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💰 Цена: от/до",
                    callback_data=f"filter_price:start:{category_name}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 К категориям",
                    callback_data="filter_back_to_categories",
                )
            ],
        ]
    )


def build_filter_pagination_keyboard(
    category_name: str,
    page: int,
    total_pages: int,
    sort: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
) -> InlineKeyboardMarkup:
    """Pagination keyboard that preserves filter context."""
    # encode min/max as '-' if not set to keep callback compact
    min_str = str(price_min) if price_min is not None else "-"
    max_str = str(price_max) if price_max is not None else "-"
    sort_str = sort or "-"

    buttons_row = []
    if page > 1:
        buttons_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"filter_products:{category_name}:{page-1}:{sort_str}:{min_str}:{max_str}",
            )
        )
    if page < total_pages:
        buttons_row.append(
            InlineKeyboardButton(
                text="➡️ Далее",
                callback_data=f"filter_products:{category_name}:{page+1}:{sort_str}:{min_str}:{max_str}",
            )
        )

    # Always include return to filter options
    buttons_bottom = [
        InlineKeyboardButton(text="🔙 Фильтры", callback_data=f"filter_show:{category_name}")
    ]

    inline_rows = []
    if buttons_row:
        inline_rows.append(buttons_row)
    inline_rows.append(buttons_bottom)

    return InlineKeyboardMarkup(inline_keyboard=inline_rows)
