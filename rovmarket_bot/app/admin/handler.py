from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from rovmarket_bot.core.models import db_helper
from rovmarket_bot.core.models.user import User
from .crud import *
from .keyboard import menu_admin, menu_stats, menu_back
from .states import AdCreationStates
from rovmarket_bot.core.cache import invalidate_cache_on_new_ad
from ..search.redis_search import index_product_in_redis

router = Router()


# Состояния FSM для рассылки
class BroadcastStates(StatesGroup):
    waiting_for_text = State()


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    telegram_id = message.from_user.id
    async with db_helper.session_factory() as session:
        is_user_admin = await is_admin(telegram_id, session)
    if is_user_admin:
        await message.answer(
            "👑 Добро пожаловать в админ-панель!", reply_markup=menu_admin
        )


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    telegram_id = callback.from_user.id
    async with db_helper.session_factory() as session:
        is_user_admin = await is_admin(telegram_id, session)
    if is_user_admin:
        await callback.message.edit_text(
            "👑 Добро пожаловать в админ-панель!", reply_markup=menu_admin
        )


@router.callback_query(F.data == "broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastStates.waiting_for_text)
    await callback.message.answer(
        "📝 Введите текст, который хотите разослать всем пользователям:",
        reply_markup=menu_back,
    )
    await callback.answer()


@router.message(BroadcastStates.waiting_for_text)
async def send_broadcast(message: Message, state: FSMContext):
    text = message.text
    await state.clear()

    async with db_helper.session_factory() as session:
        users = await get_all_users(session)

    success_count = 0
    for user in users:
        try:
            await message.bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode="Markdown",
            )
            success_count += 1
        except Exception as e:
            print(e)
            pass

    await message.answer(
        f"📬 Рассылка завершена!\nСообщение доставлено {success_count} пользователям.",
        reply_markup=menu_back,
    )


@router.callback_query(F.data.startswith("all_users"))
async def all_users_paginated(callback: CallbackQuery):
    data_parts = callback.data.split("=")
    try:
        page = int(data_parts[1]) if len(data_parts) > 1 else 1
    except ValueError:
        page = 1

    async with db_helper.session_factory() as session:
        total_users = await get_users_count(session)
        users = await get_users_page(session, page)
        view_counts = await get_users_view_counts(session)

    if not users:
        await callback.message.answer("🙁 Пользователи не найдены.")
        await callback.answer()
        return

    lines = [f"👥 <b>Всего пользователей:</b> {total_users}\n🔻 Список:"]

    for user in users:
        views = view_counts.get(user.id, 0)

        lines.append(
            f"🆔 <b>ID:</b> {user.id}\n"
            f"👤 <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
            f"🔗 <b>Username:</b> @{user.username if user.username else '—'}\n"
            f"🛡️ <b>Админ:</b> {'✅' if user.admin else '❌'}\n"
            f"👁️ <b>Просмотров:</b> {views}\n"
            f"🕓 <b>Зарегистрирован:</b> {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"──────────────"
        )

    text = "\n".join(lines)

    # Пагинация
    # Пагинация
    total_pages = (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE
    keyboard = []

    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"all_users?page={page - 1}")
        )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"all_users?page={page + 1}")
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    # Отправка
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    await callback.answer()


# Вывод жалоб
@router.callback_query(F.data == "complaints")
async def complaints_list(callback: CallbackQuery):
    async with db_helper.session_factory() as session:
        complaints = await get_all_complaints(session)

    if not complaints:
        await callback.message.answer("✅ Все жалобы были рассмотрены. Ничего нового.")
        await callback.answer()
        return

    total_complaints = len(complaints)
    await callback.message.answer(
        f"🚨 <b>Всего жалоб:</b> {total_complaints}\n🗂 Список жалоб:", parse_mode="HTML"
    )

    for complaint in complaints:
        user = complaint.user

        text = (
            f"📝 <b>Жалоба:</b> {complaint.title}\n"
            f"👤 <b>Пользователь:</b> @{user.username if user.username else '—'} (ID {user.id})\n"
            f"📅 <b>Дата:</b> {complaint.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"──────────────"
        )

        buttons = [
            [
                InlineKeyboardButton(
                    text=f"❌ Закрыть жалобу #{complaint.id}",
                    callback_data=f"complaint_close:{complaint.id}",
                )
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
        ]
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.answer(text, parse_mode="HTML", reply_markup=markup)

    await callback.answer()


# Обработка кнопки закрытия жалобы
@router.callback_query(F.data.startswith("complaint_close:"))
async def complaint_close(callback: CallbackQuery):
    complaint_id_str = callback.data.split(":")[1]
    try:
        complaint_id = int(complaint_id_str)
    except ValueError:
        await callback.answer("Некорректный ID жалобы.", show_alert=True)
        return

    async with db_helper.session_factory() as session:
        await delete_complaint(session, complaint_id)

    await callback.answer("✅ Жалоба закрыта.")
    # Обновляем список жалоб
    await complaints_list(callback)


@router.callback_query(F.data.startswith("stats"))
async def stats_handler(callback: CallbackQuery):
    period_map = {
        "week": timedelta(days=7),
        "month": timedelta(days=30),
        "year": timedelta(days=365),
    }

    # Парсим период из callback_data: "stats?period=week"
    period_str = "week"  # дефолт
    parts = callback.data.split("=")
    if len(parts) == 2 and parts[1] in period_map:
        period_str = parts[1]

    now = datetime.now(timezone.utc)
    period_start = now - period_map[period_str]

    async with db_helper.session_factory() as session:
        stats = await get_stats_for_period(session, period_start)

        # Получим имя пользователя с top_user_id (если есть)
        top_user_name = "—"
        if stats["top_user_id"] is not None:
            user = await session.get(User, stats["top_user_id"])
            if user:
                top_user_name = user.username or f"ID {user.telegram_id}"

    text = (
        f"📊 *Статистика за {period_str}:*\n\n"
        f"👥 Зарегистрировано пользователей: **{stats['users_count']}**\n"
        f"📢 Создано объявлений: **{stats['products_count']}**\n"
        f"🏆 Топ пользователь по объявлениям: **{top_user_name}** — "
        f"**{stats['top_user_products_count']}** объявлений\n"
    )

    await callback.message.edit_text(text, reply_markup=menu_stats)
    await callback.answer()


@router.callback_query(F.data == "ads")
async def ads_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AdCreationStates.waiting_for_text)
    await callback.message.answer(
        "📣 Введите рекламный текст:",
        reply_markup=menu_back,
    )
    await callback.answer()


# Получаем текст рекламы
@router.message(AdCreationStates.waiting_for_text)
async def ad_text_received(message: Message, state: FSMContext):
    await state.update_data(ad_text=message.text, photos=[])
    await state.set_state(AdCreationStates.waiting_for_photos)
    await message.answer(
        "✅ Текст сохранён!\n📷 Теперь пришлите до 10 фото одним альбомом или по одной.\nКогда закончите, введите команду /done.",
        reply_markup=menu_back,
    )


# Приём фото (поддержка альбомов)
@router.message(AdCreationStates.waiting_for_photos, F.photo)
async def ad_photos_received(
    message: Message, state: FSMContext, album_messages: list[Message] | None = None
):
    data = await state.get_data()
    photos = data.get("photos", [])

    messages = album_messages if album_messages else [message]

    for msg in messages:
        if len(photos) >= 10:
            await message.answer(
                "📸 Вы уже добавили 10 фото. Нажмите /done чтобы перейти к подтверждению.",
                reply_markup=menu_back,
            )
            break
        photo_id = msg.photo[-1].file_id
        photos.append(photo_id)

    await state.update_data(photos=photos)
    await message.answer(
        f"✅ Фото добавлено ({len(photos)}/10). Можно отправить ещё или нажмите /done",
        reply_markup=menu_back,
    )


# Команда /done для перехода к предпросмотру
@router.message(AdCreationStates.waiting_for_photos, F.text == "/done")
async def ad_photos_done(message: Message, state: FSMContext):
    data = await state.get_data()
    text = data.get("ad_text")
    photos = data.get("photos", [])

    if not photos:
        await message.answer(
            "❌ Вы не отправили ни одного фото. Пожалуйста, отправьте хотя бы одно фото.",
            reply_markup=menu_back,
        )
        return

    media_group = [
        InputMediaPhoto(
            media=photos[0],
            caption=f"{text}\n\nЕсли всё верно, отправьте команду /okay для создания рекламы.\nИли /cancel для отмены.",
            parse_mode="Markdown",
        ),
    ]
    media_group += [InputMediaPhoto(media=file_id) for file_id in photos]

    await message.answer_media_group(media_group)
    await state.set_state(AdCreationStates.waiting_for_confirmation)


# Команда /okay — создание рекламы
@router.message(AdCreationStates.waiting_for_confirmation, F.text == "/okay")
async def ad_confirmed(message: Message, state: FSMContext):
    data = await state.get_data()
    text = data.get("ad_text")
    photos = data.get("photos", [])

    if not text or not photos:
        await message.answer("Ошибка: нет текста или фотографий. Начните заново.")
        await state.clear()
        return

    async with db_helper.session_factory() as session:
        await create_advertisement(session, text=text, photos_file_ids=photos)

    await message.answer("✅ Реклама успешно создана и сохранена!")
    await state.clear()


# Команда /cancel — отмена создания рекламы (в любой стадии AdCreationStates)
@router.message(
    StateFilter(
        AdCreationStates.waiting_for_text,
        AdCreationStates.waiting_for_photos,
        AdCreationStates.waiting_for_confirmation,
        AdCreationStates.waiting_for_name,
        AdCreationStates.waiting_for_description,
    ),
    F.text == "/cancel",
)
async def ad_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Создание рекламы отменено.")


@router.callback_query(F.data == "all_ads")
async def show_all_ads(callback: CallbackQuery):
    async with db_helper.session_factory() as session:
        products = await get_unpublished_products(session)

    for product in products:
        first_photo = product.photos[0].photo_url if product.photos else None
        caption = (
            f"<b>{product.name}</b>\n\n"
            f"{product.description}\n\n"
            f"<b>Цена:</b> {product.price or 'Не указана'}\n"
            f"<b>Контакт:</b> {product.contact}"
        )

        buttons = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📷 Показать фото",
                        callback_data=f"show_photos:{product.id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Отклонить", callback_data=f"decline:{product.id}"
                    ),
                    InlineKeyboardButton(
                        text="✅ Принять", callback_data=f"approve:{product.id}"
                    ),
                ],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
            ]
        )

        if first_photo:
            await callback.message.answer_photo(
                first_photo, caption=caption, parse_mode="HTML", reply_markup=buttons
            )
        else:
            await callback.message.answer(
                caption, parse_mode="HTML", reply_markup=buttons
            )

    await callback.answer()


@router.callback_query(F.data.startswith("show_photos:"))
async def show_photos(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    async with db_helper.session_factory() as session:
        product = await get_product_with_photos_and_user(session, product_id)

    if not product or not product.photos:
        await callback.answer("Фотографии не найдены", show_alert=True)
        return

    media = [InputMediaPhoto(media=photo.photo_url) for photo in product.photos]
    await callback.message.answer_media_group(media)
    await callback.answer()


@router.callback_query(F.data.startswith("approve:"))
async def approve_ad(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    async with db_helper.session_factory() as session:
        product = await get_product_with_photos(session, product_id)

        if not product:
            await callback.answer("Объявление не найдено", show_alert=True)
            return

        product.publication = True
        await session.commit()

    await invalidate_cache_on_new_ad()
    await index_product_in_redis(product)

    await callback.answer("Объявление принято ✅", show_alert=True)


@router.callback_query(F.data.startswith("decline:"))
async def decline_ad(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    async with db_helper.session_factory() as session:
        product = await get_product_with_photos(session, product_id)

        if not product:
            await callback.answer("Объявление не найдено", show_alert=True)
            return

        product.publication = False
        await session.commit()

        try:
            await callback.bot.send_message(
                chat_id=product.user.telegram_id,
                text="Ваше объявление было отклонено модератором ❌",
            )
        except Exception as e:
            print(f"Не удалось отправить уведомление: {e}")

    await callback.answer("Объявление отклонено ❌", show_alert=True)


@router.callback_query(F.data == "add_categories")
async def start_add_category(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введите название категории:",
        reply_markup=menu_back,
    )
    await state.set_state(AdCreationStates.waiting_for_name)


@router.message(AdCreationStates.waiting_for_name)
async def category_name_entered(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AdCreationStates.waiting_for_description)
    await message.answer(
        "Теперь введите описание категории:",
        reply_markup=menu_back,
    )


@router.message(AdCreationStates.waiting_for_description)
async def category_description_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    description = message.text

    async with db_helper.session_factory() as session:
        await create_category(session, name, description)

    await message.answer(
        "Категория успешно создана ✅",
        reply_markup=menu_back,
    )
    await state.clear()
