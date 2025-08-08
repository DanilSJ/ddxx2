from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
)

from rovmarket_bot.app.start.keyboard import menu_start
from rovmarket_bot.core.cache import check_rate_limit
from rovmarket_bot.core.models import db_helper
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from rovmarket_bot.app.ads.crud import (
    get_user_products_paginated,
    get_user_products_count,
    unpublish_user_product,
    publish_user_product,
    get_user_product_with_photos,
)
from rovmarket_bot.app.settings.crud import get_or_create_bot_settings
from rovmarket_bot.app.admin.crud import get_admin_users
from rovmarket_bot.core.logger import get_component_logger


router = Router()
logger = get_component_logger("ads")


class UserAdsState(StatesGroup):
    viewing_ads = State()


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
        # Формируем описание объявления
        price_text = f"Цена: {product.price} ₽" if product.price else "Цена: Договорная"
        category_text = f"Категория: {product.category.name}"
        date_text = f"Дата: {product.created_at.strftime('%d.%m.%Y %H:%M')}"
        views_count = len(product.views) if product.views else 0
        views_text = f"Просмотры: {views_count}"

        caption = (
            f"📋 {product.name}\n\n"
            f"📝 {product.description}\n\n"
            f"💰 {price_text}\n"
            f"📂 {category_text}\n"
            f"📞 {product.contact}\n"
            f"📅 {date_text}\n"
            f"👥 {views_text}"
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
                        text="Показать фотографию",
                        callback_data=f"show_photos_{product.id}",
                    )
                ],
            ]
        )
        if product.photos:
            first_photo_url = product.photos[0].photo_url
            await message.answer_photo(
                photo=first_photo_url, caption=caption, reply_markup=actions_keyboard
            )
        else:
            await message.answer(caption, reply_markup=actions_keyboard)

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
        updated = await unpublish_user_product(
            product_id=product_id, telegram_id=callback.from_user.id, session=session
        )

    if updated:
        logger.info(
            "Unpublished product_id=%s by user_id=%s", product_id, callback.from_user.id
        )
        await callback.answer("Объявление снято с публикации")
    else:
        logger.warning(
            "Unpublish failed (not owner or already unpublished): product_id=%s user_id=%s",
            product_id,
            callback.from_user.id,
        )
        await callback.answer("Не удалось снять с публикации", show_alert=False)


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
        product = await publish_user_product(
            product_id=product_id, telegram_id=callback.from_user.id, session=session
        )
        if product is None:
            logger.warning(
                "Publish failed: product not found or not owned. product_id=%s user_id=%s",
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

    # Сообщение пользователю
    if product.publication is True:
        logger.info("Product published immediately product_id=%s", product.id)
        await callback.answer("Объявление опубликовано сразу ✅")
    elif product.publication is None:
        logger.info("Product sent to moderation product_id=%s", product.id)
        await callback.answer("Отправлено на модерацию ⏳")
    else:
        logger.info("Product publication status updated product_id=%s", product.id)
        await callback.answer("Статус объявления обновлён")


@router.callback_query(F.data.startswith("show_photos_"))
async def show_product_photos(callback: CallbackQuery):
    """Показать одну фотографию объявления (первую)."""
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

    first_photo = product.photos[0]
    await callback.message.answer_photo(
        photo=first_photo.photo_url, caption=product.name
    )
    await callback.answer()
