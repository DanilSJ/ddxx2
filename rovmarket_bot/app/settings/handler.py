from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from rovmarket_bot.core.models import db_helper
from rovmarket_bot.app.start.handler import cmd_start
from .crud import (
    get_categories_page,
    is_user_subscribed_to_category,
    toggle_category_subscription,
)
from .keyboard import menu_settings
from rovmarket_bot.core.cache import check_rate_limit
from rovmarket_bot.core.logger import get_component_logger

router = Router()
logger = get_component_logger("settings")


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    logger.info("/settings requested by user_id=%s", message.from_user.id)
    allowed, retry_after = await check_rate_limit(message.from_user.id, "search_cmd")
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await state.clear()
    await button_settings(message, state)


@router.message(F.text == "⚙️ Настройки")
async def button_settings(message: Message, state: FSMContext):
    allowed, retry_after = await check_rate_limit(message.from_user.id, "search_cmd")
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await state.clear()
    await message.answer("🛠 Настройки бота", reply_markup=menu_settings)
    logger.info("Settings menu opened by user_id=%s", message.from_user.id)


@router.message(F.text == "🔔 Уведомления")
async def button_notifications(message: Message, state: FSMContext):
    allowed, retry_after = await check_rate_limit(message.from_user.id, "search_cmd")
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await state.clear()
    await send_notifications_categories(message, state, 1)
    logger.info("Notifications settings opened by user_id=%s", message.from_user.id)


@router.message(F.text == "📋 Меню")
async def button_menu(message: Message, state: FSMContext):
    allowed, retry_after = await check_rate_limit(message.from_user.id, "search_cmd")
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await state.clear()
    await cmd_start(message, state)
    logger.info("Back to main menu by user_id=%s", message.from_user.id)


async def send_notifications_categories(
    message_or_callback, state: FSMContext, page: int
):
    async with db_helper.session_factory() as session:
        categories = await get_categories_page(session, page=page)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        # For each category, add a toggle button with checkmark if subscribed
        for cat in categories:
            subscribed = await is_user_subscribed_to_category(
                telegram_id=(
                    message_or_callback.from_user.id
                    if isinstance(message_or_callback, Message)
                    else message_or_callback.from_user.id
                ),
                category_id=cat.id,
                session=session,
            )
            title = ("✅ " if subscribed else "") + cat.name
            keyboard.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=title,
                        callback_data=f"notif_toggle:{cat.id}:{page}",
                    )
                ]
            )

        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"notif_page:{page-1}"
                )
            )
        if len(categories) == 10:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="➡️ Далее", callback_data=f"notif_page:{page+1}"
                )
            )
        if nav_buttons:
            keyboard.inline_keyboard.append(nav_buttons)

        text = (
            "🔔 *Выберите категории, по которым хотите получать уведомления о новых объявлениях.*\n\n"
            "Повторное нажатие — отключение уведомления.\n\n"
            "Вы всегда можете изменить свой выбор."
        )
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(text, reply_markup=keyboard)
        else:
            await message_or_callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("notif_page:"))
async def notifications_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":", 1)[1])
    await send_notifications_categories(callback, state, page)
    await callback.answer()
    logger.info(
        "Notifications categories page=%s for user_id=%s", page, callback.from_user.id
    )


@router.callback_query(F.data.startswith("notif_toggle:"))
async def notifications_toggle(callback: CallbackQuery, state: FSMContext):
    # format: notif_toggle:<category_id>:<page>
    parts = callback.data.split(":")
    category_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1
    async with db_helper.session_factory() as session:
        now_sub = await toggle_category_subscription(
            telegram_id=callback.from_user.id, category_id=category_id, session=session
        )
    # Refresh same page to update checkmarks
    await send_notifications_categories(callback, state, page)
    await callback.answer("Включены" if now_sub else "Выключены", show_alert=False)
    logger.info(
        "Toggled notification for user_id=%s category_id=%s now_subscribed=%s",
        callback.from_user.id,
        category_id,
        now_sub,
    )
