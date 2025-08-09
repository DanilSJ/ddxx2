from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InputMediaPhoto,
)
from html import escape

from aiogram.utils.keyboard import InlineKeyboardBuilder

from rovmarket_bot.app.ads.keyboard import (
    contact,
    menu_price_negotiable_edit,
    menu_skip,
)
from rovmarket_bot.app.start.keyboard import menu_start
from rovmarket_bot.core.cache import check_rate_limit, invalidate_all_ads_cache
from rovmarket_bot.core.models import db_helper
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from rovmarket_bot.app.ads.crud import (
    get_user_products_paginated,
    get_user_products_count,
    unpublish_user_product,
    publish_user_product,
    get_user_product_with_photos,
    get_user_product_by_id,
    update_user_product,
)
from rovmarket_bot.app.settings.crud import get_or_create_bot_settings
from rovmarket_bot.app.admin.crud import get_admin_users
from rovmarket_bot.core.logger import get_component_logger
from aiogram.exceptions import TelegramBadRequest
import re


router = Router()
logger = get_component_logger("ads")


class UserAdsState(StatesGroup):
    viewing_ads = State()


class EditProductState(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_price = State()
    waiting_contact = State()


CONTACT_REGEX = r"^(?:\+7\d{10}|\+380\d{9}|\+8\d{10}|@[\w\d_]{5,32}|[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$"


async def clean_phone(text: str) -> str:
    """Очистка вручную введённого номера от лишних символов."""
    return (
        "+" + re.sub(r"[^\d]", "", text) if "+" in text else re.sub(r"[^\d]", "", text)
    )


@router.message(Command("my_ads"))
async def cmd_my_ads(message: Message, state: FSMContext):
    logger.info("/my_ads requested by user_id=%s", message.from_user.id)
    allowed, retry_after = await check_rate_limit(message.from_user.id, "search_cmd")
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await state.clear()
    await button_my_ads(message, state)


@router.message(F.text == "📋 Мои объявления")
async def button_my_ads(message: Message, state: FSMContext):
    allowed, retry_after = await check_rate_limit(message.from_user.id, "search_cmd")
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await state.clear()

    async with db_helper.session_factory() as session:
        # Получаем объявления пользователя
        products = await get_user_products_paginated(
            telegram_id=message.from_user.id, session=session, page=1, limit=5
        )

        total_count = await get_user_products_count(
            telegram_id=message.from_user.id, session=session
        )
        logger.info(
            "Loaded %s ads for user_id=%s (first page)",
            total_count,
            message.from_user.id,
        )

    if not products:
        await message.answer("У вас пока нет объявлений.")
        return

    # Сохраняем текущую страницу в состоянии
    await state.update_data(current_page=1, total_count=total_count)
    await state.set_state(UserAdsState.viewing_ads)

    # Отправляем объявления
    await send_user_products(message, products, 1, total_count)


async def send_user_products(
    message: Message, products, current_page: int, total_count: int
):
    """Отправить объявления пользователя с пагинацией"""

    for product in products:
        # Формируем красивое описание объявления (HTML)
        name = escape(product.name or "")
        description = escape(product.description or "")
        category_name = escape(getattr(product.category, "name", "—") or "—")
        price_str = (
            f"{product.price:,}".replace(",", " ") + " ₽"
            if product.price
            else "Договорная"
        )
        contact = escape(product.contact or "")
        date_str = product.created_at.strftime("%d.%m.%Y %H:%M")
        views_count = len(product.views) if getattr(product, "views", None) else 0

        caption = (
            f"<b>📋 {name}</b>\n\n"
            f"📝 {description}\n\n"
            f"💰 <b>Цена:</b> {price_str}\n"
            f"📂 <b>Категория:</b> {category_name}\n"
            f"📞 <b>Контакты:</b> {contact}\n"
            f"📅 <b>Дата:</b> {date_str}\n"
            f"👥 <b>Просмотры:</b> {views_count}"
        )

        # Отправляем единое сообщение с кнопками действий
        actions_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Снять с публикации",
                        callback_data=f"unpublish_{product.id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Опубликовать объявление",
                        callback_data=f"publish_{product.id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Показать фотографии",
                        callback_data=f"show_photos_{product.id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✏ Редактировать",
                        callback_data=f"edit_product_{product.id}",
                    )
                ],
            ]
        )

        if product.photos:
            first_photo_url = product.photos[0].photo_url
            try:
                await message.answer_photo(
                    photo=first_photo_url,
                    caption=caption,
                    reply_markup=actions_keyboard,
                    parse_mode="HTML",
                )
            except TelegramBadRequest:
                await message.answer(
                    caption, reply_markup=actions_keyboard, parse_mode="HTML"
                )
        else:
            await message.answer(
                caption, reply_markup=actions_keyboard, parse_mode="HTML"
            )

    # Создаем клавиатуру для навигации
    keyboard = create_pagination_keyboard(current_page, total_count)
    await message.answer("Навигация по объявлениям:", reply_markup=keyboard)


def create_pagination_keyboard(
    current_page: int, total_count: int
) -> InlineKeyboardMarkup:
    """Создать клавиатуру для пагинации"""
    keyboard = []

    # Кнопки навигации
    nav_buttons = []

    if current_page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀️ Назад", callback_data=f"ads_page_{current_page - 1}"
            )
        )

    nav_buttons.append(
        InlineKeyboardButton(
            text=f"{current_page}/{max(1, (total_count + 4) // 5)}",
            callback_data="current_page",
        )
    )

    if current_page * 5 < total_count:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Вперед ▶️", callback_data=f"ads_page_{current_page + 1}"
            )
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Кнопка закрытия
    keyboard.append(
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_ads")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.callback_query(F.data.startswith("ads_page_"))
async def handle_ads_pagination(callback: CallbackQuery, state: FSMContext):
    """Обработка пагинации объявлений"""
    page = int(callback.data.split("_")[-1])
    logger.info(
        "Ads pagination: user_id=%s requested page=%s", callback.from_user.id, page
    )

    async with db_helper.session_factory() as session:
        products = await get_user_products_paginated(
            telegram_id=callback.from_user.id, session=session, page=page, limit=5
        )

        total_count = await get_user_products_count(
            telegram_id=callback.from_user.id, session=session
        )

    if not products:
        await callback.answer("Объявления не найдены")
        return

    # Обновляем состояние
    await state.update_data(current_page=page, total_count=total_count)

    # Удаляем предыдущее сообщение с клавиатурой
    await callback.message.delete()

    # Отправляем новые объявления
    await send_user_products(callback.message, products, page, total_count)
    await callback.answer()


@router.callback_query(F.data == "close_ads")
async def close_ads_view(callback: CallbackQuery, state: FSMContext):
    """Закрыть просмотр объявлений"""
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Просмотр объявлений закрыт", reply_markup=menu_start)


@router.callback_query(F.data == "current_page")
async def current_page_info(callback: CallbackQuery):
    """Информация о текущей странице"""
    await callback.answer("Текущая страница")


@router.callback_query(F.data.startswith("unpublish_"))
async def unpublish_product(callback: CallbackQuery):
    """Снять объявление с публикации (publication=False)."""
    try:
        product_id = int(callback.data.split("_")[-1])
    except ValueError:
        logger.warning(
            "Unpublish: invalid product id in callback data=%s", callback.data
        )
        await callback.answer("Некорректный запрос", show_alert=False)
        return

    async with db_helper.session_factory() as session:
        # Проверяем текущее состояние публикации
        current_product = await get_user_product_with_photos(
            product_id=product_id, telegram_id=callback.from_user.id, session=session
        )

        if current_product is None:
            logger.warning(
                "Unpublish failed: product not found or not owned. product_id=%s user_id=%s",
                product_id,
                callback.from_user.id,
            )
            await callback.message.answer("Не удалось снять с публикации")
            await callback.answer()
            return

        if current_product.publication is False:
            await callback.message.answer("Объявление уже снято с публикации")
            await callback.answer()
            return

        updated = await unpublish_user_product(
            product_id=product_id, telegram_id=callback.from_user.id, session=session
        )

    if updated:
        logger.info(
            "Unpublished product_id=%s by user_id=%s", product_id, callback.from_user.id
        )
        await callback.message.answer("Объявление снято с публикации ✅")
        await callback.answer()
    else:
        logger.warning(
            "Unpublish failed (not owner or already unpublished): product_id=%s user_id=%s",
            product_id,
            callback.from_user.id,
        )
        await callback.message.answer("Не удалось снять с публикации")
        await callback.answer()


@router.callback_query(F.data.startswith("publish_"))
async def publish_product(callback: CallbackQuery):
    """Опубликовать объявление с учётом настроек модерации."""
    try:
        product_id = int(callback.data.split("_")[-1])
    except ValueError:
        logger.warning("Publish: invalid product id in callback data=%s", callback.data)
        await callback.answer("Некорректный запрос", show_alert=False)
        return

    async with db_helper.session_factory() as session:
        # Предварительно проверяем текущее состояние
        current_product = await get_user_product_with_photos(
            product_id=product_id, telegram_id=callback.from_user.id, session=session
        )
        if current_product is None:
            logger.warning(
                "Publish failed: product not found or not owned. product_id=%s user_id=%s",
                product_id,
                callback.from_user.id,
            )
            await callback.answer("Не удалось опубликовать", show_alert=False)
            return

        if current_product.publication is True:
            await callback.message.answer("Объявление уже находится в публикации")
            await callback.answer()
            return

        product = await publish_user_product(
            product_id=product_id, telegram_id=callback.from_user.id, session=session
        )
        if product is None:
            logger.warning(
                "Publish failed after pre-check: product not found or not owned. product_id=%s user_id=%s",
                product_id,
                callback.from_user.id,
            )
            await callback.answer("Не удалось опубликовать", show_alert=False)
            return

        # Отправляем уведомления админам только если модерация включена (publication=None)
        settings_row = await get_or_create_bot_settings(session)
        if bool(settings_row.moderation) and product.publication is None:
            admins = await get_admin_users(session)
            notify_text = (
                "🔔 Объявление отправлено на модерацию\n\n"
                f"ID: {product.id}\n"
                f"Название: {product.name}\n"
                f"Цена: {('Договорная' if product.price is None else product.price)}\n\n"
                "Перейдите в админ-панель для проверки."
            )
            for admin in admins:
                try:
                    await callback.bot.send_message(
                        chat_id=admin.telegram_id, text=notify_text
                    )
                except Exception:
                    logger.warning(
                        "Failed to notify admin telegram_id=%s about moderation",
                        admin.telegram_id,
                    )

    # Сообщение пользователю в чат
    if product.publication is True:
        logger.info("Product published immediately product_id=%s", product.id)
        await callback.message.answer("Объявление опубликовано сразу ✅")
    elif product.publication is None:
        logger.info("Product sent to moderation product_id=%s", product.id)
        await callback.message.answer("Объявление отправлено на модерацию ⏳")
    else:
        logger.info("Product publication status updated product_id=%s", product.id)
        await callback.message.answer("Статус объявления обновлён")
    await callback.answer()


@router.callback_query(F.data.startswith("show_photos_"))
async def show_product_photos(callback: CallbackQuery):
    """Показать все фотографии объявления медиа-группой."""
    try:
        product_id = int(callback.data.split("_")[-1])
    except ValueError:
        logger.warning(
            "Show photos: invalid product id in callback data=%s", callback.data
        )
        await callback.answer("Некорректный запрос", show_alert=False)
        return

    async with db_helper.session_factory() as session:
        product = await get_user_product_with_photos(
            product_id=product_id, telegram_id=callback.from_user.id, session=session
        )

    if product is None:
        logger.warning(
            "Show photos: product not found or not owned product_id=%s user_id=%s",
            product_id,
            callback.from_user.id,
        )
        await callback.answer("Объявление не найдено", show_alert=False)
        return

    if not product.photos:
        logger.info(
            "Show photos: no photos for product_id=%s (user_id=%s)",
            product_id,
            callback.from_user.id,
        )
        await callback.answer("Фотографии отсутствуют", show_alert=False)
        return

    # Подготовим красивую подпись (HTML)
    name = escape(product.name or "")
    description = escape(product.description or "")
    category_name = escape(getattr(product.category, "name", "—") or "—")
    price_str = (
        f"{product.price:,}".replace(",", " ") + " ₽" if product.price else "Договорная"
    )
    contact = escape(product.contact or "")
    date_str = product.created_at.strftime("%d.%m.%Y %H:%M")
    views_count = len(product.views) if getattr(product, "views", None) else 0

    full_caption = (
        f"<b>📋 {name}</b>\n\n"
        f"📝 {description}\n\n"
        f"💰 <b>Цена:</b> {price_str}\n"
        f"📂 <b>Категория:</b> {category_name}\n"
        f"📞 <b>Контакты:</b> {contact}\n"
        f"📅 <b>Дата:</b> {date_str}\n"
        f"👥 <b>Просмотры:</b> {views_count}"
    )

    # Собираем и отправляем медиа-группу (батчами по 10)
    photo_urls = [p.photo_url for p in product.photos]

    if len(photo_urls) == 1:
        try:
            await callback.message.answer_photo(
                photo=photo_urls[0], caption=full_caption, parse_mode="HTML"
            )
        except TelegramBadRequest:
            await callback.message.answer(full_caption, parse_mode="HTML")
        await callback.answer()
        return

    first_batch = True
    for start in range(0, len(photo_urls), 10):
        chunk = photo_urls[start : start + 10]
        media = []
        for idx, url in enumerate(chunk):
            if first_batch and idx == 0:
                media.append(
                    InputMediaPhoto(media=url, caption=full_caption, parse_mode="HTML")
                )
            else:
                media.append(InputMediaPhoto(media=url))
        try:
            await callback.bot.send_media_group(
                chat_id=callback.message.chat.id, media=media
            )
        except TelegramBadRequest:
            await callback.message.answer(full_caption, parse_mode="HTML")
        first_batch = False

    await callback.answer()


@router.callback_query(F.data.startswith("edit_product_"))
async def start_edit_product(callback: CallbackQuery, state: FSMContext):
    try:
        product_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("Некорректный ID объявления", show_alert=True)
        return

    async with db_helper.session_factory() as session:
        product = await get_user_product_by_id(
            product_id, callback.from_user.id, session
        )
        if not product:
            await callback.answer("Объявление не найдено", show_alert=True)
            return

    await state.update_data(edit_product_id=product_id)
    await callback.message.answer(
        "✏️ Введите **новое название** для вашего объявления:",
        reply_markup=menu_skip,
    )
    await state.set_state(EditProductState.waiting_name)
    await callback.answer()


@router.message(EditProductState.waiting_name)
async def edit_name(message: Message, state: FSMContext):
    if message.text == "Пропустить":
        # Не обновляем имя, пропускаем
        await state.update_data(new_name=None)
    else:
        await state.update_data(new_name=message.text)
    await message.answer(
        "✏️ Введите **новое описание** для вашего объявления:",
        reply_markup=menu_skip,
    )
    await state.set_state(EditProductState.waiting_description)


@router.message(EditProductState.waiting_description)
async def edit_description(message: Message, state: FSMContext):
    if message.text == "Пропустить":
        await state.update_data(new_description=None)
    else:
        await state.update_data(new_description=message.text)

    await message.answer(
        "💰 Введите **новую цену** (только цифры) или нажмите кнопку «Договорная» ниже:",
        reply_markup=menu_price_negotiable_edit,
    )
    await message.answer(
        "Можете пропустить цену",
        reply_markup=menu_skip,
    )
    await state.set_state(EditProductState.waiting_price)


@router.message(EditProductState.waiting_price)
async def edit_price(message: Message, state: FSMContext):
    if message.text == "Пропустить":
        await state.update_data(new_price=None)
    else:
        price_text = message.text.strip().lower()
        if price_text == "договорная":
            price = None
        else:
            clean_text = re.sub(r"[ \.\-_]", "", price_text)
            match = re.match(r"(\d+)(к*)$", clean_text)
            if not match:
                await message.answer(
                    "❌ Некорректный формат цены.\n\n"
                    "Введите только цифры или используйте формат типа:\n"
                    "• `100к` (100 000)\n"
                    "• `250кк` (250 000 000)\n"
                    "или нажмите кнопку «💬 Договорная» или «Пропустить»."
                )
                return
            number_part = int(match.group(1))
            k_multiplier = 1000 ** len(match.group(2))
            price = number_part * k_multiplier
        await state.update_data(new_price=price)

    await message.answer(
        "📞 Укажите ваши контактные данные:\n\n"
        "— Номер телефона (начиная с `+7`, `+380` или `+8`)\n"
        "— Email (например, `example@mail.com`)\n"
        "— Telegram username (начиная с `@`)\n\n"
        "Чтобы быстро поделиться номером телефона, нажмите кнопку «📱 Отправить номер телефона» ниже 👇\n"
        "Или напишите «Пропустить», если не хотите менять контакт.",
        reply_markup=contact,
    )
    await message.answer(
        "Можете пропустить контакты",
        reply_markup=menu_skip,
    )
    await state.set_state(EditProductState.waiting_contact)


@router.callback_query(F.data == "price_negotiable_edit")
async def set_price_negotiable_edit(callback: CallbackQuery, state: FSMContext):
    await state.update_data(new_price=None)
    await callback.message.answer(
        "🤝 Цена установлена как **договорная**.\n\n"
        "📞 Теперь укажите, как с вами связаться:\n"
        "— Телефон (`+7`, `+380`, `+8`)\n"
        "— Email (`example@mail.com`)\n"
        "— Telegram (`@username`)\n\n"
        "Или нажмите кнопку «📱 Отправить номер телефона» ниже 👇",
        reply_markup=contact,
    )
    await state.set_state(EditProductState.waiting_contact)
    await callback.answer()


@router.message(
    EditProductState.waiting_contact,
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
async def edit_contact(message: Message, state: FSMContext):
    if message.text == "Пропустить":
        contact_value = None
    else:
        if message.contact:
            contact_value = message.contact.phone_number
        else:
            raw = message.text.strip()
            cleaned = await clean_phone(raw) if raw.startswith("+") else raw

            if not re.match(CONTACT_REGEX, cleaned):
                await message.answer(
                    "❌ Неверный формат контактных данных.\n\n"
                    "Введите один из вариантов:\n"
                    "• Телефон (`+7`, `+380`, `+8`)\n"
                    "• Email (`example@mail.com`)\n"
                    "• Telegram (`@username`)"
                )
                return
            contact_value = cleaned

    user_data = await state.get_data()
    product_id = user_data["edit_product_id"]

    # Формируем kwargs для обновления только с теми полями, что были изменены
    update_kwargs = {}
    for key in ("new_name", "new_description", "new_price"):
        if user_data.get(key) is not None:
            update_kwargs[key[4:]] = user_data[key]  # убираем "new_"
    if contact_value is not None:
        update_kwargs["contact"] = contact_value

    if not update_kwargs:
        await message.answer(
            "⚠️ Вы не изменили ни одного поля объявления.",
            reply_markup=menu_start,
        )
        await state.clear()
        return

    async with db_helper.session_factory() as session:
        updated_product = await update_user_product(
            product_id=product_id,
            telegram_id=message.from_user.id,
            session=session,
            **update_kwargs,
        )

    if updated_product:
        await invalidate_all_ads_cache()
        await message.answer(
            "✅ Объявление успешно обновлено!\n\nТеперь его увидят другие пользователи 📢",
            reply_markup=menu_start,
        )
    else:
        await message.answer(
            "❌ Произошла ошибка при обновлении объявления. Попробуйте ещё раз.",
            reply_markup=menu_start,
        )

    await state.clear()
