from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from .crud import create_product
from rovmarket_bot.core.cache import (
    get_categories_page_cached as get_categories_page,
    check_rate_limit,
)
from rovmarket_bot.core.models import db_helper
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ContentType,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from rovmarket_bot.app.start.keyboard import menu_start
from .keyboard import contractual, contact
import re
from rovmarket_bot.core.censorship.bad_words.en import text as bad_words_en
from rovmarket_bot.core.censorship.bad_words.ru import text as bad_words_ru
from rovmarket_bot.app.admin.crud import get_admin_users
from rovmarket_bot.app.settings.crud import get_or_create_bot_settings
from rovmarket_bot.core.logger import get_component_logger

router = Router()
logger = get_component_logger("post")

CONTACT_REGEX = r"^(?:\+7\d{10}|\+380\d{9}|\+8\d{10}|@[\w\d_]{5,32}|[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$"


class Post(StatesGroup):
    categories = State()
    name = State()
    description = State()
    photo = State()
    photos: list = State()
    price = State()
    contact = State()
    geo = State()


async def clean_phone(text: str) -> str:
    """Очистка вручную введённого номера от лишних символов."""
    return (
        "+" + re.sub(r"[^\d]", "", text) if "+" in text else re.sub(r"[^\d]", "", text)
    )


ALL_BAD_WORDS = [
    line.strip().lower()
    for line in (bad_words_en + "\n" + bad_words_ru).splitlines()
    if line.strip()
]


def contains_profanity(text: str) -> bool:
    text_lower = text.lower()
    for word in ALL_BAD_WORDS:
        if word in text_lower:
            return True
    return False


async def send_category_page(message_or_callback, state: FSMContext, page: int):
    async with db_helper.session_factory() as session:
        categories = await get_categories_page(session, page=page)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        for cat in categories:
            keyboard.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=cat.name, callback_data=f"select_category:{cat.name}"
                    )
                ]
            )

        # Добавляем кнопки "назад" и "вперед"
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page:{page-1}")
            )
        if len(categories) == 10:  # возможно есть еще страницы
            nav_buttons.append(
                InlineKeyboardButton(text="➡️ Далее", callback_data=f"page:{page+1}")
            )

        if nav_buttons:
            keyboard.inline_keyboard.append(nav_buttons)

        text = "📂 Выберите категорию для вашего объявления:"
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(text, reply_markup=keyboard)
        else:
            await message_or_callback.message.edit_text(text, reply_markup=keyboard)


@router.message(Command("post"))
async def cmd_post(message: Message, state: FSMContext):
    logger.info("/post requested by user_id=%s", message.from_user.id)
    allowed, retry_after = await check_rate_limit(message.from_user.id, "search_cmd")
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await button_post(message=message, state=state)


@router.message(F.text == "📢 Разместить объявление")
async def button_post(message: Message, state: FSMContext):
    logger.info("User_id=%s started posting flow", message.from_user.id)
    allowed, retry_after = await check_rate_limit(message.from_user.id, "search_cmd")
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await state.clear()
    await state.set_state(Post.categories)
    await send_category_page(message, state, page=1)


@router.callback_query(F.data.startswith("page:"))
async def paginate_categories(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    logger.info("Post categories pagination user_id=%s page=%s", callback.from_user.id, page)
    await send_category_page(callback, state, page=page)
    await callback.answer()


@router.callback_query(F.data.startswith("select_category:"))
async def category_selected(callback: CallbackQuery, state: FSMContext):
    category_name = callback.data.split(":")[1]
    logger.info(
        "Category selected for post user_id=%s category=%s",
        callback.from_user.id,
        category_name,
    )
    await state.update_data(category=category_name)
    await callback.message.edit_reply_markup(reply_markup=None)  # убираем кнопки
    await callback.message.answer(f"✅ Категория выбрана: *{category_name}*")
    await callback.answer()

    await callback.message.answer("✏️ Введите *название* объявления:")
    await state.set_state(Post.name)


@router.message(
    Post.categories,
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
async def process_categories(message: Message, state: FSMContext):
    await message.answer(
        "❗ Пожалуйста, выберите категорию из предложенных вариантов, используя кнопки ниже 👇"
    )


@router.message(
    Post.name,
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
async def process_name(message: Message, state: FSMContext):
    # if contains_profanity(message.text):
    #     logger.warning("Profanity detected in name by user_id=%s", message.from_user.id)
    #     await message.answer(
    #         "🚫 В названии обнаружены запрещённые слова. Пожалуйста, перепишите без мата."
    #     )
    #     return

    await state.update_data(name=message.text)
    await message.answer("📝 Теперь введите *описание* вашего объявления:")
    await state.set_state(Post.description)


@router.message(
    Post.description,
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
async def process_description(message: Message, state: FSMContext):
    # if contains_profanity(message.text):
    #     logger.warning(
    #         "Profanity detected in description by user_id=%s", message.from_user.id
    #     )
    #     await message.answer(
    #         "🚫 В описании обнаружены запрещённые слова. Пожалуйста, перепишите без мата."
    #     )
    #     return

    await state.update_data(description=message.text)
    await message.answer(
        "📸 Пришлите *до 10 фотографий* для вашего объявления.\n\n"
        "📌 Вы можете отправлять фото как по одному, так и сразу в виде альбома.\n\n"
        "⚠️ *Важно:* запрещён любой контент 18+, насилие, агрессия, оскорбления и другие неприемлемые материалы — такие фото будут удаляться, а аккаунт может быть заблокирован.\n\n"
        "📍 Пожалуйста, отправляйте только качественные и релевантные вашему объявлению фотографии.\n\n"
        "✅ Когда закончите, нажмите кнопку «Подтвердить»"
    )
    await state.update_data(photos=[])
    await state.set_state(Post.photo)


@router.message(
    Post.photo,
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
async def process_photo(
    message: Message,
    state: FSMContext,
    album_messages: list[Message] | None = None,  # middleware передаст сюда список фото
):
    data = await state.get_data()
    photos = data.get("photos", [])

    messages = album_messages if album_messages else [message]

    for msg in messages:
        if len(photos) >= 10:
            await message.answer("📸 Вы уже добавили 10 фото. Нажмите «Подтвердить» ⬇️")
            break

        photo_id = msg.photo[-1].file_id
        photos.append(photo_id)

    await state.update_data(photos=photos)
    logger.info(
        "Photos added for user_id=%s count_now=%s", message.from_user.id, len(photos)
    )

    await message.answer(
        f"✅ Фото добавлено ({len(photos)}/10). Можно отправить ещё или нажмите 'Подтвердить'",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Подтвердить", callback_data="photos_done"
                    )
                ]
            ]
        ),
    )


@router.message(
    Post.photo,
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
async def photo_other_messages(message: Message):
    await message.answer(
        "📷 Пожалуйста, отправляйте фото *по одному* сообщению.\n\nКогда закончите, нажмите кнопку «Подтвердить» ✅:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Подтвердить", callback_data="photos_done"
                    )
                ]
            ]
        ),
    )


@router.callback_query(lambda c: c.data == "photos_done")
async def photos_done_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    if not photos:
        await callback.answer("Вы не отправили ни одного фото", show_alert=True)
        return
    await callback.message.edit_reply_markup()
    await callback.message.answer(
        "💰 Укажите *цену* в рублях для вашего объявления (только цифры)\n💡 Если хотите указать *договорную* цену, нажмите кнопку ниже ⬇️",
        reply_markup=contractual,
    )
    await state.set_state(Post.price)
    await callback.answer()


@router.message(
    Post.price,
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
async def process_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        logger.warning(
            "Invalid price entered by user_id=%s value=%s", message.from_user.id, message.text
        )
        await message.answer("🚫 Цена должна быть числом. Попробуйте снова 💡")
        return

    await state.update_data(price=int(message.text))

    await message.answer(
        "**📞 Пожалуйста, отправьте ваши контактные данные:**\n\n"
        "— Номер телефона (начиная с `+7`, `+380` или `+8`)\n"
        "— Email (например, `example@mail.com`)\n"
        "— Telegram username (начиная с `@`, например `@username`)\n\n"
        "Чтобы быстро поделиться номером, нажмите кнопку «📱 Отправить номер телефона» ниже 👇",
        reply_markup=contact,
    )
    await state.set_state(Post.contact)


@router.callback_query(lambda c: c.data == "price_negotiable")
async def price_negotiable_callback(callback: CallbackQuery, state: FSMContext):
    await state.update_data(price="Договорная цена")
    await callback.message.edit_reply_markup()
    await callback.message.answer(
        "**🤝 Цена установлена как *договорная*.**\n\n"
        "Теперь укажите, как с вами можно связаться:\n"
        "— Телефон (`+7`, `+380`, `+8`)\n"
        "— Email (`example@mail.com`)\n"
        "— Telegram (`@username`)\n\n"
        "Или нажмите кнопку «📱 Отправить номер телефона» ниже 👇",
        reply_markup=contact,
    )
    await state.set_state(Post.contact)
    await callback.answer()


@router.message(
    Post.contact,
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
async def process_contact(message: Message, state: FSMContext):
    # ✅ Если номер получен через кнопку — сохраняем без проверки
    if message.contact:
        await state.update_data(contact=message.contact.phone_number)

    # ✍️ Если введено вручную — очищаем и проверяем
    elif message.text:
        raw = message.text.strip()
        cleaned = await clean_phone(raw) if raw.startswith("+") else raw

        if not re.match(CONTACT_REGEX, cleaned):
            logger.warning(
                "Invalid contact by user_id=%s value=%s", message.from_user.id, raw
            )
            await message.answer(
                "❌ *Неверный формат контактных данных.*\n\n"
                "Пожалуйста, отправьте один из следующих вариантов:\n"
                "• Телефон (начиная с `+7`, `+380` или `+8`, например `+79591166234`)\n"
                "• Email (например, `example@mail.com`)\n"
                "• Telegram username (начиная с `@`, например `@yourname`)"
            )
            return

        await state.update_data(contact=cleaned)

    else:
        await message.answer(
            "❌ Не удалось получить контактные данные. Попробуйте снова."
        )
        return

    # Геолокация — следующий шаг
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить геолокацию", request_location=True)],
            [KeyboardButton(text="Пропустить геолокацию")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await message.answer(
        "📍 Отправьте свою *геолокацию* или нажмите кнопку «Пропустить геолокацию» 👇",
        reply_markup=keyboard,
    )
    await state.set_state(Post.geo)


@router.message(
    Post.geo,
    F.content_type == ContentType.LOCATION,
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
async def process_geo_location(message: Message, state: FSMContext):
    location = message.location
    await state.update_data(
        geo={"latitude": location.latitude, "longitude": location.longitude}
    )
    logger.info(
        "Geo set for user_id=%s lat=%s lon=%s",
        message.from_user.id,
        location.latitude,
        location.longitude,
    )
    await finalize_post(message, state)


@router.message(
    Post.geo,
    F.text.lower() == "пропустить геолокацию",
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
async def skip_geo(message: Message, state: FSMContext):
    await state.update_data(geo=None)
    await message.answer("⏭ Геолокация пропущена.")
    logger.info("Geo skipped by user_id=%s", message.from_user.id)
    await finalize_post(message, state)


@router.message(
    Post.geo,
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
async def process_geo_text(message: Message, state: FSMContext):
    # Если пользователь прислал текст вместо локации или кнопки,
    # выводим ошибку и предлагаем воспользоваться кнопкой.
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить геолокацию", request_location=True)],
            [KeyboardButton(text="Пропустить геолокацию")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(
        "⚠️ Пожалуйста, используйте кнопки ниже, чтобы отправить геолокацию или пропустить этот шаг ⬇️",
        reply_markup=keyboard,
    )


async def finalize_post(message: Message, state: FSMContext):
    data = await state.get_data()
    async with db_helper.session_factory() as session:
        try:
            product = await create_product(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                data=data,
                session=session,
            )
            logger.info(
                "Product created id=%s by user_id=%s", product.id, message.from_user.id
            )
            # Проверяем режим модерации — уведомляем админов только если модерация включена
            settings_row = await get_or_create_bot_settings(session)
            if bool(settings_row.moderation):
                admins = await get_admin_users(session)
                notify_text = (
                    "🔔 Новое объявление ожидает проверки\n\n"
                    f"ID: {product.id}\n"
                    f"Название: {product.name}\n"
                    f"Цена: {('Договорная' if product.price is None else product.price)}\n\n"
                    "Перейдите в админ-панель для модерации."
                )
                for admin in admins:
                    try:
                        await message.bot.send_message(
                            chat_id=admin.telegram_id, text=notify_text
                        )
                    except Exception:
                        # Игнорируем ошибки доставки отдельным администраторам
                        logger.warning(
                            "Failed to notify admin telegram_id=%s about new product id=%s",
                            admin.telegram_id,
                            product.id,
                        )
        except ValueError as e:
            logger.exception(
                "Error creating product for user_id=%s: %s", message.from_user.id, e
            )
            await message.answer(
                f"❌ Произошла ошибка при создании объявления: {e}",
                reply_markup=menu_start,
            )
            return

    await message.answer(
        "🎉 ✅ Объявление создано!\n\nОно появится в ленте в течение 5 минут.",
        reply_markup=menu_start,
    )

    await state.clear()
