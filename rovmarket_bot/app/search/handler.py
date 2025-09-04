from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    InputMediaPhoto,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from .crud import *
from .keyboard import (
    menu_search,
    pagination_keyboard,
    build_filter_options_keyboard,
    build_filter_pagination_keyboard,
    get_menu_page,
    menu_search_inline,
)
from .redis_search import search_in_redis
from rovmarket_bot.core.models import db_helper
import datetime
from aiogram.types import InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from rovmarket_bot.core.cache import check_rate_limit
from rovmarket_bot.core.logger import get_component_logger
from ..start.handler import cmd_start
from ..start.keyboard import menu_start, menu_ad_inline_write
from rovmarket_bot.app.advertisement.crud import get_next_listings_ad

router = Router()
logger = get_component_logger("search")
PAGE_SIZE = 5


class Search(StatesGroup):
    text = State()
    category = State()
    price_min = State()
    price_max = State()
    complaint = State()


def format_price(price):
    try:
        # Попытка преобразовать в число
        price_int = int(price)
        # Форматируем с пробелами для тысяч и добавляем ₽
        return f"{price_int:,}".replace(",", " ") + " ₽"
    except (ValueError, TypeError):
        # Если цена не число, возвращаем её как есть
        return price


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    logger.info("/search requested by user_id=%s", message.from_user.id)
    allowed, retry_after = await check_rate_limit(message.from_user.id, "search_cmd")
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await button_search(message, state)


@router.message(Command("filter"))
async def cmd_filter(message: Message, state: FSMContext):
    logger.info("/filter requested by user_id=%s", message.from_user.id)
    allowed, retry_after = await check_rate_limit(message.from_user.id, "filter_cmd")
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await send_filter_category_page(message, state, 1)


@router.message(Command("all_ads"))
async def cmd_all_ads(message: Message, state: FSMContext):
    logger.info("/all_ads requested by user_id=%s", message.from_user.id)
    allowed, retry_after = await check_rate_limit(message.from_user.id, "all_ads_cmd")
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await button_all(message, state)


@router.message(Command("categories"))
async def cmd_categories(message: Message, state: FSMContext):
    logger.info("/categories requested by user_id=%s", message.from_user.id)
    allowed, retry_after = await check_rate_limit(
        message.from_user.id, "categories_cmd"
    )
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await button_categories(message, state)


@router.callback_query(F.data == "menu_start_inline_search_ads")
async def menu_start_inline_search_ads(callback: CallbackQuery, state: FSMContext):
    await button_search(callback.message, state)


@router.message(F.text == "🔍 Найти объявление")
async def button_search(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Search.text)

    await message.answer(
        "✍️ Введите текст для поиска или воспользуйтесь меню ниже:",
        reply_markup=menu_search,
    )
    await message.answer(
        "👇 Выберите действие:",
        reply_markup=menu_search_inline,
    )
    logger.info("Search flow started for user_id=%s", message.from_user.id)


@router.message(F.text == "📣 Реклама")
async def button_advertisement(message: Message, state: FSMContext):
    await state.clear()
    text = (
        "✨ **Реклама в нашем боте** ✨\n\n"
        "🔹 Хотите рассказать о своём товаре или услуге нашей аудитории?\n"
        "🔹 Получите прямой доступ к активным пользователям.\n\n"
        "📬 Свяжитесь со мной для обсуждения условий размещения рекламы:"
    )
    await message.answer(text, reply_markup=menu_ad_inline_write, parse_mode="Markdown")


@router.callback_query(F.data == "menu_ad_inline_write_callback")
async def menu_ad_inline_write_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        "✨ <b>Реклама в нашем боте</b> ✨\n\n"
        "🔹 Хотите рассказать о своём товаре или услуге нашей аудитории?\n"
        "🔹 Получите прямой доступ к активным пользователям.\n\n"
        "📬 Свяжитесь со мной для обсуждения условий размещения рекламы:"
    )
    try:
        await callback.message.answer(
            text, reply_markup=menu_ad_inline_write, parse_mode="HTML"
        )
    except Exception:
        # Fallback: отправим двумя сообщениями без форматирования
        await callback.message.answer("Реклама в нашем боте")
        await callback.message.answer(
            "Свяжитесь со мной для обсуждения условий",
            reply_markup=menu_ad_inline_write,
        )
    await callback.answer()


@router.callback_query(F.data == "menu_search_inline_all_ads")
async def menu_search_inline_all_ads(callback: CallbackQuery, state: FSMContext):
    await button_all(callback.message, state)


@router.callback_query(F.data == "menu_search_inline_filter_ads")
async def menu_search_inline_filter_ads(callback: CallbackQuery, state: FSMContext):
    await button_filters(callback.message, state)


@router.callback_query(F.data == "menu_search_inline_categories_ads")
async def menu_search_inline_categories_ads(callback: CallbackQuery, state: FSMContext):
    await button_categories(callback.message, state)


@router.callback_query(F.data == "menu_search_inline_menu")
async def menu_search_inline_menu(callback: CallbackQuery, state: FSMContext):
    message = callback.message

    await cmd_start(message, state)


@router.message(F.text == "🔍 Показать все")
async def button_all(message: Message, state: FSMContext):
    allowed, retry_after = await check_rate_limit(message.from_user.id, "show_all")
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await state.clear()
    await state.set_state(Search.text)
    await state.update_data(page=0)
    await show_ads_page(message, state, 0)
    logger.info("Show all ads page=0 for user_id=%s", message.from_user.id)


@router.message(F.text == "📂 Категории")
async def button_categories(message: Message, state: FSMContext):
    allowed, retry_after = await check_rate_limit(
        message.from_user.id, "categories_btn"
    )
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await state.clear()
    await state.set_state(Search.category)
    await send_category_page(message, state, 1)
    logger.info("Search categories opened for user_id=%s", message.from_user.id)


@router.message(F.text == "🎛 Фильтры")
async def button_filters(message: Message, state: FSMContext):
    allowed, retry_after = await check_rate_limit(message.from_user.id, "filters_btn")
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await state.clear()
    await state.set_state(Search.category)
    await send_filter_category_page(message, state, 1)
    logger.info("Search filters opened for user_id=%s", message.from_user.id)


@router.callback_query(lambda c: c.data and c.data.startswith("page_inline_button:"))
async def paginate_ads_inline(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    await state.update_data(page=page)
    await callback.answer()  # чтобы убрать "часики" на кнопке
    message = callback.message
    await show_ads_page(message, state, page)
    logger.info("Ads inline pagination user_id=%s page=%s", callback.from_user.id, page)


@router.message(F.text.in_(["⬅️", "➡️"]))
async def paginate_ads(message: Message, state: FSMContext):
    allowed, retry_after = await check_rate_limit(message.from_user.id, "search_cmd")
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    data = await state.get_data()
    page = data.get("page", 0)
    if message.text == "➡️":
        page += 1
    elif message.text == "⬅️" and page > 0:
        page -= 1
    await state.update_data(page=page)
    await show_ads_page(message, state, page)
    logger.info("Ads pagination user_id=%s page=%s", message.from_user.id, page)


async def show_ads_page(message: Message, state: FSMContext, page: int):
    async with db_helper.session_factory() as session:
        cached_data = await get_all_ads_data(session)

        if cached_data:
            product_ids = cached_data["product_ids"]
            products = cached_data["products"]
            photos_map = cached_data["photos"]

            total = len(product_ids)
            start = page * PAGE_SIZE
            end = start + PAGE_SIZE
            page_ids = product_ids[start:end]

            if not page_ids:
                page = max(0, page)
                while True:
                    start = page * PAGE_SIZE
                    end = start + PAGE_SIZE
                    page_ids = product_ids[start:end]

                    if page_ids:
                        break  # есть данные — выходим из цикла

                    # корректируем страницу
                    if page > 0:
                        page -= 1
                    else:
                        await message.answer("Нет доступных объявлений")
                        return

            for idx, pid in enumerate(page_ids, start=1):
                product_data = products.get(str(pid), {})
                name = product_data.get("name", "Без названия")
                desc = product_data.get("description", "Без описания")
                if len(desc) > 100:
                    desc = desc[:100] + "..."
                price = product_data.get("price")
                if price:
                    price = format_price(price)
                else:
                    price = "договорная"
                text = f"📌 {name}\n" f"💬 {desc}\n" f"💰 Цена: {price}"
                photos = photos_map.get(pid, [])

                details_markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Подробнее", callback_data=f"details:{pid}"
                            ),
                            InlineKeyboardButton(
                                text="Пожаловаться", callback_data=f"complaint:{pid}"
                            ),
                        ]
                    ]
                )
                if photos:
                    await message.answer_photo(
                        photos[0], caption=text, reply_markup=details_markup
                    )
                else:
                    await message.answer(text, reply_markup=details_markup)

                # Insert listings advertisement after every 3rd product
                if idx % 3 == 0:
                    ad = await get_next_listings_ad(session)
                    if ad:
                        ad_text = ad.text
                        try:
                            if getattr(ad, "media", None):
                                from aiogram.types import (
                                    InputMediaPhoto,
                                    InputMediaVideo,
                                )

                                media_group = []
                                for i, m in enumerate(ad.media[:10]):
                                    if m.media_type == "photo":
                                        item = InputMediaPhoto(media=m.file_id)
                                    else:
                                        item = InputMediaVideo(media=m.file_id)
                                    if i == 0:
                                        item.caption = ad_text
                                    media_group.append(item)
                                await message.answer_media_group(media_group)
                            else:
                                await message.answer(ad_text)
                        except Exception:
                            # Fallback to text if media fails
                            await message.answer(ad_text)

            await message.answer(
                f"Страница {page+1} из {((total-1)//PAGE_SIZE)+1}",
                reply_markup=pagination_keyboard,
            )
            await message.answer(
                "Используйте кнопки для перелистывания страниц ⬅️➡️",
                reply_markup=get_menu_page(page),
            )
            await session.commit()
        else:
            await show_ads_page(message, state, 0)
            logger.info(
                "Cache miss, fallback to page=0 for user_id=%s", message.from_user.id
            )


@router.message(
    Search.text,
    ~F.text.startswith("/"),
    F.text != "🔔 Уведомления",
    F.text != "📋 Меню",
    F.text != "📱 Отправить номер телефона",
    F.text != "🔙 Назад",
    F.text != "🔍 Показать все",
    F.text != "🎛 Фильтры",
    F.text != "📂 Категории",
    F.text != "⚙️ Настройки",
    F.text != "📋 Мои объявления",
    F.text != "📢 Разместить объявление",
    F.text != "🔍 Найти объявление",
)
async def search_ads(message: Message, state: FSMContext):
    query = message.text
    logger.info("Search query by user_id=%s: %s", message.from_user.id, query)
    async with db_helper.session_factory() as session:
        results = await search_in_redis(query, session)
    if not results:
        logger.info("No search results for user_id=%s", message.from_user.id)
        await message.answer("Ничего не найдено 😔")
        return
    for item in results:
        name = item.get("name", "Без названия")
        desc = item.get("description", "Без описания")
        # Обрезаем описание до 100 символов
        if len(desc) > 100:
            desc = desc[:100] + "..."
        product_id = item.get("id")
        price = item.get("price")
        if price:
            price = format_price(price)
        else:
            price = "договорная"
        text = f"📌 {name}\n" f"💬 {desc}\n" f"💰 {price}"
        photos = item.get("photos", [])

        details_markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Подробнее", callback_data=f"details:{product_id}"
                    ),
                    InlineKeyboardButton(
                        text="Пожаловаться", callback_data=f"complaint:{product_id}"
                    ),
                ]
            ]
        )
        if photos:
            await message.answer_photo(
                photos[0], caption=text, reply_markup=details_markup
            )
        else:
            await message.answer(text, reply_markup=details_markup)


@router.callback_query(F.data.startswith("details:"))
async def show_details(callback: CallbackQuery):
    try:
        parts = callback.data.split(":")
        product_id = int(parts[-1])
    except (ValueError, IndexError):
        logger.warning("Details: invalid callback data=%s", callback.data)
        await callback.answer("Ошибка: неверный формат данных.", show_alert=True)
        return

    async with db_helper.session_factory() as session:
        product = await get_product_by_id(product_id, session)

        if not product:
            logger.info("Details: product not found product_id=%s", product_id)
            await callback.answer("Данные не найдены", show_alert=True)
            return

        user_id = await get_user_id_by_telegram_id(callback.from_user.id, session)
        if user_id:
            await add_product_view(product_id, user_id, session)
            logger.info(
                "Recorded product view product_id=%s by user_id=%s",
                product_id,
                user_id,
            )

    name = product.get("name", "Без названия")
    desc = product.get("description", "Без описания")

    price = product.get("price")
    if price:
        price = format_price(price)
    else:
        price = "договорная"
    contact = product.get("contact", "-")

    geo = product.get("geo")
    geo_str = "-"
    geo_link = None
    if geo and isinstance(geo, dict):
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        if lat is not None and lon is not None:
            geo_str = f"{lat}, {lon}"
            geo_link = f"https://maps.google.com/?q={lat},{lon}"

    created_at = product.get("created_at")
    created_str = "-"
    if created_at:
        if isinstance(created_at, str):
            try:
                created_at = datetime.datetime.fromisoformat(created_at)
            except Exception:
                created_at = None
        if isinstance(created_at, datetime.datetime):
            created_str = created_at.strftime("%d.%m.%Y")

    # Формируем текст с HTML-разметкой для кликабельной ссылки на геолокацию
    if geo_link:
        geo_text = f"<a href='{geo_link}'>Нажми, чтобы открыть карту</a>"
    else:
        geo_text = "-"

    contact_text = "Связь через бота" if contact == "via_bot" else contact

    full_text = (
        f"📌 {name}\n"
        f"💬 {desc}\n"
        f"💰 Цена: {price}\n"
        f"\n📞 Контакт: {contact_text}\n"
        f"📍 Геолокация: {geo_text}\n"
        f"🕒 Дата создания: {created_str}"
    )

    photos = product.get("photos", [])
    videos = product.get("videos", [])

    await callback.answer()

    # Кнопки для деталей объявления
    details_buttons = [
        [
            InlineKeyboardButton(
                text="Просмотреть фотографии", callback_data=f"show_photos:{product_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="Пожаловаться", callback_data=f"complaint:{product_id}"
            )
        ],
    ]
    # Если контакт анонимный — добавить кнопку чата

    if contact == "via_bot":
        details_buttons.append(
            [
                InlineKeyboardButton(
                    text="Начать чат", callback_data=f"start_chat:{product_id}"
                )
            ]
        )

    details_markup = InlineKeyboardMarkup(inline_keyboard=details_buttons)
    try:
        # Если исходное сообщение с фото/видео — редактируем подпись, иначе редактируем текст
        if (
            callback.message.photo
            or callback.message.video
            or callback.message.animation
        ):
            await callback.message.edit_caption(
                caption=full_text, reply_markup=details_markup, parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                full_text, reply_markup=details_markup, parse_mode="HTML"
            )
    except Exception:
        logger.warning(
            "Failed to edit in-place for details product_id=%s, sending new message",
            product_id,
        )
        await callback.message.answer(
            full_text, reply_markup=details_markup, parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("show_photos:"))
async def show_photos(callback: CallbackQuery):
    product_id = int(callback.data.split(":", 1)[1])
    async with db_helper.session_factory() as session:
        product = await get_product_by_id(product_id, session)

    if not product:
        logger.info("Show photos: product not found product_id=%s", product_id)
        await callback.answer("Данные не найдены", show_alert=True)
        return

    name = product.get("name", "Без названия")
    desc = product.get("description", "Без описания")
    price = product.get("price")
    if price:
        price = format_price(price)
    else:
        price = "договорная"
    contact = product.get("contact", "-")

    geo = product.get("geo")
    geo_link = None
    geo_str = "-"
    if geo and isinstance(geo, dict):
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        if lat is not None and lon is not None:
            geo_str = f"{lat}, {lon}"
            geo_link = f"https://maps.google.com/?q={lat},{lon}"

    created_at = product.get("created_at")
    created_str = "-"
    if created_at:
        if isinstance(created_at, str):
            try:
                created_at = datetime.datetime.fromisoformat(created_at)
            except Exception:
                created_at = None
        if isinstance(created_at, datetime.datetime):
            created_str = created_at.strftime("%d.%m.%Y")

    if geo_link:
        geo_text = f"<a href='{geo_link}'>Нажми, чтобы открыть карту</a>"
    else:
        geo_text = "-"

    contact_text = "Связь через бота" if contact == "via_bot" else contact

    full_text = (
        f"📌 {name}\n"
        f"💬 {desc}\n"
        f"💰 Цена: {price}\n"
        f"\n📞 Контакт: {contact_text}\n"
        f"📍 Геолокация: {geo_text}\n"
        f"🕒 Дата создания: {created_str}"
    )

    photos = product.get("photos", [])
    videos = product.get("videos", [])
    combo = [("photo", fid) for fid in photos] + [("video", fid) for fid in videos]
    combo = combo[:10]

    if not combo:
        logger.info("Show media: none product_id=%s", product_id)
        await callback.answer("Медиа нет", show_alert=True)
        return
    if len(combo) == 1:
        await callback.answer()
        kind, fid = combo[0]
        if kind == "photo":
            await callback.message.answer_photo(
                fid, caption=full_text, parse_mode="HTML"
            )
        else:
            await callback.message.answer_video(
                fid, caption=full_text, parse_mode="HTML"
            )
        return

    # Формируем медиагруппу: первое с подписью, остальные без
    from aiogram.types import InputMediaPhoto, InputMediaVideo

    media_group = []
    for idx, (kind, fid) in enumerate(combo):
        item = (
            InputMediaPhoto(media=fid)
            if kind == "photo"
            else InputMediaVideo(media=fid)
        )
        if idx == 0:
            item.caption = full_text
            item.parse_mode = "HTML"
        media_group.append(item)

    await callback.answer()
    await callback.message.answer_media_group(media_group)


async def send_category_page(message_or_callback, state: FSMContext, page: int):
    """Отправить страницу категорий"""
    async with db_helper.session_factory() as session:
        categories = await get_categories_page(session, page=page)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        for cat in categories:
            keyboard.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=cat.name, callback_data=f"search_category:{cat.name}"
                    )
                ]
            )

        # Добавляем кнопки "назад" и "вперед"
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"search_category_page:{page-1}"
                )
            )
        if len(categories) == 10:  # возможно есть еще страницы
            nav_buttons.append(
                InlineKeyboardButton(
                    text="➡️ Далее", callback_data=f"search_category_page:{page+1}"
                )
            )

        if nav_buttons:
            keyboard.inline_keyboard.append(nav_buttons)

        text = "📂 Выберите категорию для просмотра объявлений:"
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(text, reply_markup=keyboard)
        else:
            await message_or_callback.message.edit_text(text, reply_markup=keyboard)


async def send_filter_category_page(message_or_callback, state: FSMContext, page: int):
    """Отправить страницу категорий для фильтров"""
    async with db_helper.session_factory() as session:
        categories = await get_categories_page(session, page=page)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        for cat in categories:
            keyboard.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=cat.name, callback_data=f"filter_category:{cat.name}"
                    )
                ]
            )

        # Добавляем кнопки "назад" и "вперед"
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"filter_category_page:{page-1}"
                )
            )
        if len(categories) == 10:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="➡️ Далее", callback_data=f"filter_category_page:{page+1}"
                )
            )

        if nav_buttons:
            keyboard.inline_keyboard.append(nav_buttons)

        text = "🧭 Выберите категорию для фильтрации:"
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(text, reply_markup=keyboard)
        else:
            await message_or_callback.message.edit_text(text, reply_markup=keyboard)


async def show_products_by_category(
    message_or_callback, state: FSMContext, category_name: str, page: int
):
    """Показать товары по категории с пагинацией"""
    async with db_helper.session_factory() as session:
        product_ids = await get_products_by_category(
            session, category_name, page=page, limit=PAGE_SIZE
        )
        total = await get_total_products_by_category(session, category_name)

        if not product_ids:
            text = f"В категории '{category_name}' нет объявлений на этой странице."
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 Назад к категориям",
                            callback_data="search_back_to_categories",
                        )
                    ]
                ]
            )

            if isinstance(message_or_callback, Message):
                await message_or_callback.answer(text, reply_markup=keyboard)
            else:
                await message_or_callback.message.edit_text(text, reply_markup=keyboard)
            return

        # Получаем данные для объявлений
        fields_map = await get_fields_for_products(product_ids, session)
        photos_map = await get_photos_for_products(product_ids, session)

        for pid in product_ids:
            fields = fields_map.get(pid, {})
            name = fields.get("name", "Без названия")
            desc = fields.get("description", "Без описания")
            if len(desc) > 100:
                desc = desc[:100] + "..."
            price = fields.get("price")
            if price:
                price = format_price(price)
            else:
                price = "договорная"
            text = f"📌 {name}\n" f"💬 {desc}\n" f"💰 Цена: {price}"
            photos = photos_map.get(pid, [])

            details_markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Подробнее", callback_data=f"details:{pid}"
                        ),
                        InlineKeyboardButton(
                            text="Пожаловаться", callback_data=f"complaint:{pid}"
                        ),
                    ]
                ]
            )

            if isinstance(message_or_callback, Message):
                if photos:
                    await message_or_callback.answer_photo(
                        photos[0], caption=text, reply_markup=details_markup
                    )
                else:
                    await message_or_callback.answer(text, reply_markup=details_markup)
            else:
                # Для callback_query отправляем новое сообщение
                if photos:
                    await message_or_callback.message.answer_photo(
                        photos[0], caption=text, reply_markup=details_markup
                    )
                else:
                    await message_or_callback.message.answer(
                        text, reply_markup=details_markup
                    )

        # Создаем клавиатуру для пагинации
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        nav_buttons = []

        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"search_category_products:{category_name}:{page-1}",
                )
            )

        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="➡️ Далее",
                    callback_data=f"search_category_products:{category_name}:{page+1}",
                )
            )

        # Добавляем кнопку возврата к категориям
        nav_buttons.append(
            InlineKeyboardButton(
                text="🔙 К категориям", callback_data="search_back_to_categories"
            )
        )

        pagination_keyboard = InlineKeyboardMarkup(inline_keyboard=[nav_buttons])

        info_text = (
            f"📂 Категория: {category_name}\n"
            f"Страница {page} из {total_pages} (в этой категории {total} товаров)"
        )

        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(
                info_text, reply_markup=pagination_keyboard
            )
            await message_or_callback.answer(
                "Используйте кнопки для перелистывания страниц ⬅️➡️",
                reply_markup=get_menu_page(page),
            )
        else:
            await message_or_callback.message.answer(
                info_text, reply_markup=pagination_keyboard
            )
            await message_or_callback.message.answer(
                "Используйте кнопки для перелистывания страниц ⬅️➡️",
                reply_markup=get_menu_page(page),
            )


async def show_products_by_category_filtered(
    message_or_callback,
    state: FSMContext,
    category_name: str,
    page: int,
    *,
    sort: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
):
    """Показать товары по категории с учетом сортировки и цены"""
    async with db_helper.session_factory() as session:
        product_ids = await get_products_by_category_filtered(
            session,
            category_name,
            page=page,
            limit=PAGE_SIZE,
            sort=sort,
            price_min=price_min,
            price_max=price_max,
        )
        total = await get_total_products_by_category_filtered(
            session, category_name, price_min=price_min, price_max=price_max
        )

        if not product_ids:
            text = f"В категории '{category_name}' нет объявлений на этой странице по заданным фильтрам."
            keyboard = build_filter_options_keyboard(category_name)
            if isinstance(message_or_callback, Message):
                await message_or_callback.answer(text, reply_markup=keyboard)
            else:
                await message_or_callback.message.edit_text(text, reply_markup=keyboard)
            return

        fields_map = await get_fields_for_products(product_ids, session)
        photos_map = await get_photos_for_products(product_ids, session)

        for pid in product_ids:
            fields = fields_map.get(pid, {})
            name = fields.get("name", "Без названия")
            desc = fields.get("description", "Без описания")
            if len(desc) > 100:
                desc = desc[:100] + "..."
            price = fields.get("price")
            if price:
                price = format_price(price)
            else:
                price = "договорная"
            text = f"📌 {name}\n" f"💬 {desc}\n" f"💰 Цена: {price}"
            photos = photos_map.get(pid, [])

            details_markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Подробнее", callback_data=f"details:{pid}"
                        ),
                        InlineKeyboardButton(
                            text="Пожаловаться", callback_data=f"complaint:{pid}"
                        ),
                    ]
                ]
            )
            if isinstance(message_or_callback, Message):
                if photos:
                    await message_or_callback.answer_photo(
                        photos[0], caption=text, reply_markup=details_markup
                    )
                else:
                    await message_or_callback.answer(text, reply_markup=details_markup)
            else:
                if photos:
                    await message_or_callback.message.answer_photo(
                        photos[0], caption=text, reply_markup=details_markup
                    )
                else:
                    await message_or_callback.message.answer(
                        text, reply_markup=details_markup
                    )

        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        pagination_kb = build_filter_pagination_keyboard(
            category_name,
            page,
            total_pages,
            sort=sort,
            price_min=price_min,
            price_max=price_max,
        )
        info_text = (
            f"📂 Категория: {category_name}\n"
            f"Страница {page} из {total_pages} (в этой категории {total} товаров)"
        )

        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(info_text, reply_markup=pagination_kb)
            await message_or_callback.answer(
                "Используйте кнопки для перелистывания страниц ⬅️➡️",
                reply_markup=get_menu_page(page),
            )
        else:
            await message_or_callback.message.answer(
                info_text, reply_markup=pagination_kb
            )
            await message_or_callback.message.answer(
                "Используйте кнопки для перелистывания страниц ⬅️➡️",
                reply_markup=get_menu_page(page),
            )


@router.callback_query(F.data.startswith("complaint:"))
async def start_complaint(callback: CallbackQuery, state: FSMContext):
    try:
        product_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Ошибка данных", show_alert=True)
        return
    await state.update_data(complaint_product_id=product_id)
    await state.set_state(Search.complaint)
    await callback.message.answer(
        "Опишите вашу жалобу текстом. Введите детали проблемы:"
    )
    await callback.answer()


@router.message(
    Search.complaint,
    ~F.text.startswith("/"),
    F.text != "🔔 Уведомления",
    F.text != "📋 Меню",
    F.text != "📱 Отправить номер телефона",
    F.text != "🔙 Назад",
    F.text != "🔍 Показать все",
    F.text != "🎛 Фильтры",
    F.text != "📂 Категории",
    F.text != "⚙️ Настройки",
    F.text != "📋 Мои объявления",
    F.text != "📢 Разместить объявление",
    F.text != "🔍 Найти объявление",
)
async def receive_complaint_text(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пожалуйста, введите текст жалобы.")
        return
    data = await state.get_data()
    product_id = data.get("complaint_product_id")
    async with db_helper.session_factory() as session:
        user_id = await get_user_id_by_telegram_id(message.from_user.id, session)
        if not user_id:
            await message.answer("Не удалось определить пользователя для жалобы.")
            await state.clear()
            return
        # Сохраняем жалобу. В заголовок добавим ID объявления.
        full_title = f"Объявление #{product_id}: {text}" if product_id else text
        try:
            await create_complaint(user_id=user_id, text=full_title, session=session)
        except Exception:
            await message.answer("Ошибка при сохранении жалобы. Попробуйте позже.")
            await state.clear()
            return
    await message.answer("Спасибо! Ваша жалоба отправлена модераторам.")
    await state.clear()
    await state.set_state(Search.text)


@router.callback_query(F.data.startswith("search_category:"))
async def handle_category_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора категории для поиска"""
    category_name = callback.data.split(":", 1)[1]
    await state.update_data(selected_category=category_name)
    await show_products_by_category(callback, state, category_name, 1)
    await callback.answer()
    logger.info(
        "Search: category selected by user_id=%s category=%s",
        callback.from_user.id,
        category_name,
    )


@router.callback_query(F.data.startswith("filter_category:"))
async def handle_filter_category_selection(callback: CallbackQuery, state: FSMContext):
    """Выбор категории в режиме фильтров"""
    category_name = callback.data.split(":", 1)[1]
    await state.update_data(
        selected_category=category_name, sort=None, price_min=None, price_max=None
    )
    keyboard = build_filter_options_keyboard(category_name)
    await callback.message.edit_text(
        f"Категория: {category_name}\nВыберите опции фильтрации:", reply_markup=keyboard
    )
    await callback.answer()
    logger.info(
        "Search: filter category selected by user_id=%s category=%s",
        callback.from_user.id,
        category_name,
    )


@router.callback_query(F.data.startswith("filter_category_page:"))
async def handle_filter_category_pagination(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":", 1)[1])
    await send_filter_category_page(callback, state, page)
    await callback.answer()


@router.callback_query(F.data.startswith("filter_show:"))
async def handle_filter_show(callback: CallbackQuery, state: FSMContext):
    category_name = callback.data.split(":", 1)[1]
    keyboard = build_filter_options_keyboard(category_name)
    await callback.message.edit_text(
        f"Категория: {category_name}\nВыберите опции фильтрации:", reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("filter_sort:"))
async def handle_filter_sort(callback: CallbackQuery, state: FSMContext):
    # format: filter_sort:<new|old>:<category>
    parts = callback.data.split(":")
    sort_key = parts[1]
    category_name = parts[2]
    await state.update_data(selected_category=category_name, sort=sort_key)
    await show_products_by_category_filtered(
        callback, state, category_name, 1, sort=sort_key
    )
    await callback.answer()


@router.callback_query(F.data.startswith("filter_price:start:"))
async def handle_filter_price_start(callback: CallbackQuery, state: FSMContext):
    category_name = callback.data.split(":", 2)[2]
    await state.update_data(selected_category=category_name)
    await state.set_state(Search.price_min)
    await callback.message.edit_text(
        f"Категория: {category_name}\nВведите минимальную цену (число, 0 — без минимума):"
    )
    await callback.answer()


@router.message(Search.price_min)
async def handle_price_min_input(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())
        if value < 0:
            raise ValueError
    except Exception:
        await message.answer("Введите корректное число (0 или больше)")
        return
    await state.update_data(price_min=value if value != 0 else None)
    await state.set_state(Search.price_max)
    await message.answer("Введите максимальную цену (число, 0 — без максимума):")


@router.message(Search.price_max)
async def handle_price_max_input(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())
        if value < 0:
            raise ValueError
    except Exception:
        await message.answer("Введите корректное число (0 или больше)")
        return

    data = await state.get_data()
    category_name = data.get("selected_category")
    sort_key = data.get("sort") or "new"
    price_min = data.get("price_min")
    price_max = value if value != 0 else None
    await state.update_data(price_max=price_max)

    await show_products_by_category_filtered(
        message,
        state,
        category_name,
        1,
        sort=sort_key,
        price_min=price_min,
        price_max=price_max,
    )


@router.callback_query(F.data.startswith("search_category_page:"))
async def handle_category_pagination(callback: CallbackQuery, state: FSMContext):
    """Обработчик пагинации категорий для поиска"""
    page = int(callback.data.split(":", 1)[1])
    await send_category_page(callback, state, page)
    await callback.answer()


@router.callback_query(F.data.startswith("search_category_products:"))
async def handle_category_products_pagination(
    callback: CallbackQuery, state: FSMContext
):
    """Обработчик пагинации товаров в категории для поиска"""
    parts = callback.data.split(":")
    category_name = parts[1]
    page = int(parts[2])
    await show_products_by_category(callback, state, category_name, page)
    await callback.answer()


@router.callback_query(F.data == "search_back_to_categories")
async def handle_back_to_categories(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата к списку категорий для поиска"""
    await send_category_page(callback, state, 1)
    await callback.answer()


@router.callback_query(F.data.startswith("filter_products:"))
async def handle_filter_products_pagination(callback: CallbackQuery, state: FSMContext):
    # format: filter_products:<category>:<page>:<sort or ->:<min or ->:<max or ->
    parts = callback.data.split(":")
    category_name = parts[1]
    page = int(parts[2])
    sort = parts[3] if parts[3] != "-" else None
    price_min = int(parts[4]) if parts[4] != "-" else None
    price_max = int(parts[5]) if parts[5] != "-" else None
    await state.update_data(
        selected_category=category_name,
        sort=sort,
        price_min=price_min,
        price_max=price_max,
    )
    await show_products_by_category_filtered(
        callback,
        state,
        category_name,
        page,
        sort=sort,
        price_min=price_min,
        price_max=price_max,
    )
    await callback.answer()
    logger.info(
        "Search: filter pagination user_id=%s category=%s page=%s sort=%s min=%s max=%s",
        callback.from_user.id,
        category_name,
        page,
        sort,
        price_min,
        price_max,
    )


@router.callback_query(F.data == "filter_back_to_categories")
async def handle_filter_back_to_categories(callback: CallbackQuery, state: FSMContext):
    await send_filter_category_page(callback, state, 1)
    await callback.answer()
