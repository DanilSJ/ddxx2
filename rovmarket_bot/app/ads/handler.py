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

from rovmarket_bot.app.start.keyboard import menu_start
from rovmarket_bot.core.models import db_helper
import datetime
from aiogram.types import InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from rovmarket_bot.app.ads.crud import (
    get_user_products_paginated,
    get_user_products_count,
)


router = Router()


class UserAdsState(StatesGroup):
    viewing_ads = State()


@router.message(F.text == "Мои объявления")
async def button_search(message: Message, state: FSMContext):
    await state.clear()

    async with db_helper.session_factory() as session:
        # Получаем объявления пользователя
        products = await get_user_products_paginated(
            telegram_id=message.from_user.id, session=session, page=1, limit=5
        )

        total_count = await get_user_products_count(
            telegram_id=message.from_user.id, session=session
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

        caption = (
            f"📋 {product.name}\n\n"
            f"📝 {product.description}\n\n"
            f"💰 {price_text}\n"
            f"📂 {category_text}\n"
            f"📞 {product.contact}\n"
            f"📅 {date_text}"
        )

        # Отправляем фотографии
        if product.photos:
            media_group = []
            for i, photo in enumerate(product.photos):
                if i == 0:
                    media_group.append(
                        InputMediaPhoto(
                            media=photo.photo_url, caption=caption if i == 0 else None
                        )
                    )
                else:
                    media_group.append(InputMediaPhoto(media=photo.photo_url))

            await message.answer_media_group(media_group)
        else:
            await message.answer(caption)

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
