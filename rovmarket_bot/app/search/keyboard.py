from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

menu_search = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🔍 Показать все"),
        ],
        [
            KeyboardButton(text="🎛 Фильтры"),
        ],
        [
            KeyboardButton(text="📂 Категории"),
        ],
        [
            KeyboardButton(text="📋 Меню"),
        ],
    ],
    resize_keyboard=True,
)

menu_search_inline = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔍 Показать все", callback_data="menu_search_inline_all_ads"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🎛 Фильтры", callback_data="menu_search_inline_filter_ads"
            ),
        ],
        [
            InlineKeyboardButton(
                text="📂 Категории", callback_data="menu_search_inline_categories_ads"
            ),
        ],
    ],
    resize_keyboard=True,
)

pagination_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⬅️"), KeyboardButton(text="➡️")],
        [
            KeyboardButton(text="📋 Меню"),
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


def get_menu_page(page: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для пагинации с текущей страницей page.
    """
    menu_pagination_inline = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️", callback_data=f"page_inline_button:{page-1}"  # уменьшение
                ),
                InlineKeyboardButton(
                    text="➡️", callback_data=f"page_inline_button:{page+1}"  # увеличение
                ),
            ]
        ]
    )
    return menu_pagination_inline


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
        InlineKeyboardButton(
            text="🔙 Фильтры", callback_data=f"filter_show:{category_name}"
        )
    ]

    inline_rows = []
    if buttons_row:
        inline_rows.append(buttons_row)
    inline_rows.append(buttons_bottom)

    return InlineKeyboardMarkup(inline_keyboard=inline_rows)
