from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from .crud import create_product
from rovmarket_bot.core.cache import get_categories_page_cached as get_categories_page
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

router = Router()


class Post(StatesGroup):
    categories = State()
    name = State()
    description = State()
    photo = State()
    price = State()
    contact = State()
    geo = State()


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
    await button_post(message=message, state=state)


@router.message(F.text == "📢 Разместить объявление")
async def button_post(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Post.categories)
    await send_category_page(message, state, page=1)


@router.callback_query(F.data.startswith("page:"))
async def paginate_categories(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    await send_category_page(callback, state, page=page)
    await callback.answer()


@router.callback_query(F.data.startswith("select_category:"))
async def category_selected(callback: CallbackQuery, state: FSMContext):
    category_name = callback.data.split(":")[1]
    await state.update_data(category=category_name)
    await callback.message.edit_reply_markup(reply_markup=None)  # убираем кнопки
    await callback.message.answer(f"✅ Категория выбрана: *{category_name}*")
    await callback.answer()

    await callback.message.answer("✏️ Введите *название* объявления:")
    await state.set_state(Post.name)


@router.message(Post.categories)
async def process_categories(message: Message, state: FSMContext):
    await message.answer(
        "❗ Пожалуйста, выберите категорию из предложенных вариантов, используя кнопки ниже 👇"
    )


@router.message(Post.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📝 Теперь введите *описание* вашего объявления:")
    await state.set_state(Post.description)


@router.message(Post.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer(
        "📸 Пришлите *до 3 фотографий* для вашего объявления.\n\nКогда закончите, нажмите кнопку «Подтвердить» ✅"
    )
    await state.update_data(photos=[])
    await state.set_state(Post.photo)


@router.message(Post.photo, F.content_type == ContentType.PHOTO)
async def process_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    if len(photos) >= 3:
        await message.answer(
            f"✅ Фото {len(photos)} принято.\nМожете отправить ещё или нажмите «Подтвердить» ⬇️",
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
        return
    photo_id = message.photo[-1].file_id

    photos.append(photo_id)
    await state.update_data(photos=photos)
    await message.answer(
        f"Фото {len(photos)} принято. Можно отправить еще или нажмите 'Подтвердить'",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Подтвердить", callback_data="photos_done")]
            ]
        ),
    )


@router.message(Post.photo)
async def photo_other_messages(message: Message):
    await message.answer(
        "📷 Пожалуйста, отправьте фото или нажмите кнопку «Подтвердить» ✅",
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
        "💰 Укажите *цену* для вашего объявления (только цифры):"
    )
    await state.set_state(Post.price)
    await callback.answer()


@router.message(Post.price)
async def process_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("🚫 Цена должна быть числом. Попробуйте снова 💡")
        return

    await state.update_data(price=int(message.text))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Договорная", callback_data="price_negotiable")]
        ]
    )

    await message.answer(
        "💡 Если хотите указать *договорную* цену, нажмите кнопку ниже ⬇️\n\nИли просто отправьте контактные данные 📞:",
        reply_markup=keyboard,
    )
    await state.set_state(Post.contact)


@router.callback_query(lambda c: c.data == "price_negotiable")
async def price_negotiable_callback(callback: CallbackQuery, state: FSMContext):
    await state.update_data(price="Договорная цена")
    await callback.message.edit_reply_markup()  # убираем inline кнопки
    await callback.message.answer(
        "🤝 Цена установлена как *договорная*.\nТеперь введите контактные данные (телефон, email и т.п.) 📱:"
    )
    await state.set_state(Post.contact)
    await callback.answer()  # чтобы убрать "часики" у кнопки


@router.message(Post.contact)
async def process_contact(message: Message, state: FSMContext):
    await state.update_data(contact=message.text)
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


@router.message(Post.geo, F.content_type == ContentType.LOCATION)
async def process_geo_location(message: Message, state: FSMContext):
    location = message.location
    await state.update_data(
        geo={"latitude": location.latitude, "longitude": location.longitude}
    )
    await finalize_post(message, state)


@router.message(Post.geo, F.text.lower() == "пропустить геолокацию")
async def skip_geo(message: Message, state: FSMContext):
    await state.update_data(geo=None)
    await message.answer("⏭ Геолокация пропущена.")
    await finalize_post(message, state)


@router.message(Post.geo)
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
        except ValueError as e:
            await message.answer(f"❌ Произошла ошибка при создании объявления: {e}")
            return

    await message.answer("🎉 Ваше объявление успешно создано!")

    await state.clear()
