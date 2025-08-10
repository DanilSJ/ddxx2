import re
from datetime import timedelta, timezone

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
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
from sqlalchemy import or_

from rovmarket_bot.core.models import db_helper
from .crud import *
from .keyboard import menu_admin, menu_stats, menu_back, build_admin_settings_keyboard
from rovmarket_bot.app.settings.crud import (
    get_or_create_bot_settings,
    update_bot_settings,
)
from .states import AdCreationStates
from rovmarket_bot.core.cache import (
    invalidate_cache_on_new_ad,
    invalidate_categories_cache,
)
from rovmarket_bot.app.search.redis_search import index_product_in_redis
from rovmarket_bot.core.config import bot

router = Router()


def format_price(price):
    try:
        # Попытка преобразовать в число
        price_int = int(price)
        # Форматируем с пробелами для тысяч и добавляем ₽
        return f"{price_int:,}".replace(",", " ") + " ₽"
    except (ValueError, TypeError):
        # Если цена не число, возвращаем её как есть
        return price


# Состояния FSM для рассылки
class BroadcastStates(StatesGroup):
    waiting_for_text = State()


# Состояния для просмотра опубликованных объявлений (поиск внутри раздела)
class AdsListStates(StatesGroup):
    waiting_for_search = State()


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
        try:
            await callback.message.edit_text(
                "👑 Добро пожаловать в админ-панель!", reply_markup=menu_admin
            )
        except TelegramBadRequest:
            # Сообщение без текста (например, медиа) — отправим новое сообщение
            await callback.message.answer(
                "👑 Добро пожаловать в админ-панель!", reply_markup=menu_admin
            )
    await callback.answer()


@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    async with db_helper.session_factory() as session:
        settings_row = await get_or_create_bot_settings(session)
    kb = build_admin_settings_keyboard(
        moderation=bool(settings_row.moderation),
        logging=bool(settings_row.logging),
    )
    await callback.message.edit_text("⚙️ Настройки бота", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "toggle_moderation")
async def toggle_moderation_handler(callback: CallbackQuery):
    async with db_helper.session_factory() as session:
        current = (await get_or_create_bot_settings(session)).moderation
        updated = await update_bot_settings(session, moderation=not bool(current))
    kb = build_admin_settings_keyboard(
        moderation=bool(updated.moderation), logging=bool(updated.logging)
    )
    await callback.message.edit_text("⚙️ Настройки бота", reply_markup=kb)
    await callback.answer(
        "Модерация: включена" if updated.moderation else "Модерация: выключена"
    )


@router.callback_query(F.data == "toggle_logging")
async def toggle_logging_handler(callback: CallbackQuery):
    async with db_helper.session_factory() as session:
        current = (await get_or_create_bot_settings(session)).logging
        updated = await update_bot_settings(session, logging=not bool(current))
    kb = build_admin_settings_keyboard(
        moderation=bool(updated.moderation), logging=bool(updated.logging)
    )
    await callback.message.edit_text("⚙️ Настройки бота", reply_markup=kb)
    await callback.answer(
        "Логирование: включено" if updated.logging else "Логирование: выключено"
    )


@router.callback_query(F.data == "broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastStates.waiting_for_text)
    await callback.message.answer(
        "📝 Введите текст, который хотите разослать всем пользователям:",
        reply_markup=menu_back,
    )
    await callback.answer()


@router.message(
    BroadcastStates.waiting_for_text,
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

    USERS_PER_PAGE = 5  # Показываем по 5 пользователей за раз

    async with db_helper.session_factory() as session:
        total_users = await get_users_count(session)
        users = await get_users_page(session, page, USERS_PER_PAGE)
        view_counts = await get_users_view_counts(session)

    if not users:
        await callback.message.answer("🙁 Пользователи не найдены.")
        await callback.answer()
        return

    # Заголовок с общей информацией (только для первой страницы)
    if page == 1:
        header = f"👥 <b>Всего пользователей:</b> {total_users}\n🔻 Список (страница {page}):\n\n"
    else:
        header = f"🔻 Список (страница {page}):\n\n"

    # Формируем сообщение для текущей страницы
    current_message = header
    messages = []

    for user in users:
        views = view_counts.get(user.id, 0)
        user_info = (
            f"🆔 <b>ID:</b> {user.id}\n"
            f"👤 <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
            f"🔗 <b>Username:</b> @{user.username if user.username else '—'}\n"
            f"🛡️ <b>Админ:</b> {'✅' if user.admin else '❌'}\n"
            f"👁️ <b>Просмотров:</b> {views}\n"
            f"🕓 <b>Зарегистрирован:</b> {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"──────────────\n\n"
        )

        # Если добавление нового пользователя превысит лимит, сохраняем текущее сообщение и начинаем новое
        if len(current_message + user_info) > 4000:
            messages.append(current_message)
            current_message = user_info
        else:
            current_message += user_info

    if current_message:
        messages.append(current_message)

    # Пагинация
    total_pages = (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE
    keyboard = []

    # Кнопка "Загрузить еще" если есть еще пользователи
    if page < total_pages:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="⬇️ Загрузить еще", callback_data=f"all_users={page + 1}"
                )
            ]
        )

    # Кнопка "Назад"
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    # Отправляем все сообщения
    for i, message_text in enumerate(messages):
        # Для последнего сообщения добавляем клавиатуру
        reply_markup = markup if i == len(messages) - 1 else None

        if page == 1 and i == 0:
            # Первое сообщение первой страницы - редактируем
            await callback.message.edit_text(
                message_text, parse_mode="HTML", reply_markup=reply_markup
            )
        else:
            # Все остальные сообщения - отправляем новые
            await callback.message.answer(
                message_text, parse_mode="HTML", reply_markup=reply_markup
            )

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
@router.message(
    AdCreationStates.waiting_for_text,
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
async def ad_text_received(message: Message, state: FSMContext):
    await state.update_data(ad_text=message.text, photos=[])
    await state.set_state(AdCreationStates.waiting_for_photos)
    await message.answer(
        "✅ Текст сохранён!\n📷 Теперь пришлите до 10 фото одним альбомом или по одной.\nКогда закончите, введите команду /done.",
        reply_markup=menu_back,
    )


# Приём фото (поддержка альбомов)
@router.message(
    AdCreationStates.waiting_for_photos,
    F.photo,
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
@router.message(
    AdCreationStates.waiting_for_photos,
    F.text == "/done",
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
@router.message(
    AdCreationStates.waiting_for_confirmation,
    F.text == "/okay",
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
async def ad_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Создание рекламы отменено.")


@router.callback_query(F.data == "publication")
async def show_publication(callback: CallbackQuery):
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
                        callback_data=f"button_show_photos_admin:{product.id}",
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


@router.callback_query(F.data.startswith("button_show_photos_admin:"))
async def show_photos_admin(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    async with db_helper.session_factory() as session:
        product = await get_product_with_photos_and_user(session, product_id)

    if not product or not product.photos:
        await callback.answer("Фотографии не найдены", show_alert=True)
        return

    media = [InputMediaPhoto(media=photo.photo_url) for photo in product.photos]
    try:
        await callback.message.answer_media_group(media)
    except Exception as e:
        await callback.answer(f"Ошибка при показе фото: {e}", show_alert=True)
        return

    await callback.answer()


@router.callback_query(F.data.startswith("approve:"))
async def approve_ad(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    async with db_helper.session_factory() as session:
        product = await get_product_with_photos(session, product_id)

        if not product:
            await callback.answer("Объявление не найдено", show_alert=True)
            return

        if product.publication:
            await callback.answer("Объявление уже опубликовано", show_alert=True)
            return

        product.publication = True
        await session.commit()

        # Получаем всех пользователей, подписанных на все объявления
        users_stmt = select(User).where(
            or_(
                User.notifications_all_ads == True, User.notifications_all_ads.is_(None)
            )
        )
        result = await session.execute(users_stmt)
        subscribed_users = result.scalars().all()

    await invalidate_cache_on_new_ad()
    await index_product_in_redis(product)

    # Формируем текст рассылки

    # Контакт
    contact = product.contact.strip() if product.contact else ""
    if (
        re.fullmatch(r"\d{6,}", contact)
        or re.fullmatch(r"[78]\d{6,}", contact)
        or re.fullmatch(r"380\d{6,}", contact)
    ):
        if not contact.startswith("+"):
            contact = "+" + contact
    elif re.match(r"^(8\d{6,}|7\d{6,}|380\d{6,})$", contact):
        contact = "+" + contact

    price = product.price
    if price:
        price = format_price(price)
    else:
        price = "договорная"

    geo_text = "-"
    if product.geo and isinstance(product.geo, dict):
        lat = product.geo.get("latitude")
        lon = product.geo.get("longitude")
        if lat is not None and lon is not None:
            geo_text = f"<a href='https://maps.google.com/?q={lat},{lon}'>Нажми, чтобы открыть карту</a>"

    created_str = product.created_at.strftime("%d.%m.%Y") if product.created_at else "-"

    full_text = (
        f"📌 {product.name}\n"
        f"💬 {product.description or 'Без описания'}\n"
        f"💰 Цена: {price}\n"
        f"\n📞 Контакт: {contact}\n"
        f"📍 Геолокация: {geo_text}\n"
        f"🕒 Дата создания: {created_str}"
    )

    # Берём первые 10 фото, если есть
    photos = [p.photo_url for p in product.photos][:10]

    # Рассылаем всем подписчикам, кроме автора
    for user in subscribed_users:
        try:
            if not photos:
                await callback.bot.send_message(
                    user.telegram_id, full_text, parse_mode="HTML"
                )
            elif len(photos) == 1:
                await callback.bot.send_photo(
                    user.telegram_id,
                    photos[0],
                    caption=full_text,
                    parse_mode="HTML",
                )
            else:
                media_group = [
                    InputMediaPhoto(
                        media=photos[0], caption=full_text, parse_mode="HTML"
                    )
                ]
                media_group += [InputMediaPhoto(media=photo) for photo in photos[1:]]
                await callback.bot.send_media_group(user.telegram_id, media_group)
        except Exception as e:
            print(e)

    await callback.answer("Объявление принято ✅", show_alert=True)


@router.callback_query(F.data.startswith("decline:"))
async def decline_ad(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    async with db_helper.session_factory() as session:
        product = await get_product_with_photos(session, product_id)

        if not product:
            await callback.answer("Объявление не найдено", show_alert=True)
            return

        if not product.publication:
            await callback.answer("Объявление уже отклонено", show_alert=True)
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


@router.message(
    AdCreationStates.waiting_for_name,
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
async def category_name_entered(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AdCreationStates.waiting_for_description)
    await message.answer(
        "Теперь введите описание категории:",
        reply_markup=menu_back,
    )


@router.message(
    AdCreationStates.waiting_for_description,
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
    await invalidate_categories_cache()
    await state.clear()


# ===== Публикованные объявления: список, пагинация, поиск, показ фото, снятие с публикации =====


@router.callback_query(F.data.startswith("all_ads"))
async def all_ads_paginated(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdsListStates.waiting_for_search)

    page = 1
    parts = callback.data.split("?")
    if len(parts) == 2 and parts[1].startswith("page="):
        try:
            page = int(parts[1].split("=")[1])
        except ValueError:
            page = 1

    async with db_helper.session_factory() as session:
        total_ads = await get_published_products_count(session)
        products = await get_published_products_page(session, page)

        # Подсчёт просмотров для каждого объявления в списке (чтобы не делать отдельный запрос на каждый)
        product_ids = [p.id for p in products]
        if product_ids:
            result = await session.execute(
                select(ProductView.product_id, func.count(ProductView.user_id))
                .where(ProductView.product_id.in_(product_ids))
                .group_by(ProductView.product_id)
            )
            views_counts = dict(result.all())  # {product_id: views_count}
        else:
            views_counts = {}

    header_lines = [
        f"📢 <b>Опубликованные объявления</b>",
        f"Всего: <b>{total_ads}</b>",
        "Введите название или ID объявления в чат для поиска",
    ]
    header_text = "\n".join(header_lines)

    total_pages = (total_ads + ADS_PER_PAGE - 1) // ADS_PER_PAGE if total_ads else 1
    nav_keyboard = []
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"all_ads?page={page - 1}")
        )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"all_ads?page={page + 1}")
        )
    if nav_buttons:
        nav_keyboard.append(nav_buttons)
    nav_keyboard.append(
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    )
    nav_markup = InlineKeyboardMarkup(inline_keyboard=nav_keyboard)

    await callback.message.edit_text(
        header_text, parse_mode="HTML", reply_markup=nav_markup
    )

    if not products:
        await callback.message.answer("На этой странице нет объявлений.")
        await callback.answer()
        return

    for product in products:
        first_photo = product.photos[0].photo_url if product.photos else None
        views = views_counts.get(product.id, 0)  # исправлено: убрал str()
        caption = (
            f"<b>#{product.id} — {product.name}</b>\n\n"
            f"{product.description}\n\n"
            f"<b>Цена:</b> {product.price if product.price is not None else 'Не указана'}\n"
            f"<b>Контакт:</b> {product.contact}\n"
            f"<b>Дата:</b> {product.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"<b>Просмотры:</b> {views}\n"
        )

        buttons = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📷 Показать фото",
                        callback_data=f"show_photos_pub:{product.id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🛑 Снять с публикации",
                        callback_data=f"unpublish:{product.id}",
                    )
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


@router.callback_query(F.data.startswith("show_photos_pub:"))
async def show_photos_published(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    async with db_helper.session_factory() as session:
        product = await get_published_product_by_id(session, product_id)

    if not product or not product.photos:
        await callback.answer("Фотографии не найдены", show_alert=True)
        return

    if len(product.photos) == 1:
        await callback.message.answer_photo(product.photos[0].photo_url)
    else:
        media = [InputMediaPhoto(media=photo.photo_url) for photo in product.photos]
        await callback.message.answer_media_group(media)
    await callback.answer()


@router.callback_query(F.data.startswith("unpublish:"))
async def unpublish_ad(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    async with db_helper.session_factory() as session:
        product = await get_product_with_photos(session, product_id)
        if not product or product.publication is not True:
            await callback.answer(
                "Объявление не найдено или уже снято", show_alert=True
            )
            return
        # Снять с публикации
        product.publication = False
        await session.commit()

    await callback.answer("Снято с публикации ✅", show_alert=True)


@router.message(
    AdsListStates.waiting_for_search,
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
async def ads_search_handler(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    if not query:
        return

    async with db_helper.session_factory() as session:
        products: list[Product] = []

        # Поиск по ID, если число
        if query.isdigit():
            product = await get_published_product_by_id(session, int(query))
            if product:
                products = [product]
        # По названию
        if not products:
            products = await search_published_products_by_name(session, query, limit=10)

    if not products:
        await message.answer("Ничего не найдено по вашему запросу.")
        return

    for product in products:
        first_photo = product.photos[0].photo_url if product.photos else None
        caption = (
            f"<b>#{product.id} — {product.name}</b>\n\n"
            f"{product.description}\n\n"
            f"<b>Цена:</b> {product.price if product.price is not None else 'Не указана'}\n"
            f"<b>Контакт:</b> {product.contact}\n"
            f"<b>Дата:</b> {product.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )

        buttons = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📷 Показать фото",
                        callback_data=f"show_photos_pub:{product.id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🛑 Снять с публикации",
                        callback_data=f"unpublish:{product.id}",
                    )
                ],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
            ]
        )

        if first_photo:
            await message.answer_photo(
                first_photo, caption=caption, parse_mode="HTML", reply_markup=buttons
            )
        else:
            await message.answer(caption, parse_mode="HTML", reply_markup=buttons)
