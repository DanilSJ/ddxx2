from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)

from rovmarket_bot.app.chat.keyboard import menu_chat
from rovmarket_bot.app.start.keyboard import menu_start
from rovmarket_bot.core.logger import get_component_logger
from rovmarket_bot.app.chat.crud import (
    create_or_get_chat,
    add_message,
    get_chat_by_id,
    get_active_chat_by_user_id,
    get_user_chats, add_photo_to_message,
)
from rovmarket_bot.core.models import db_helper, Product, User

router = Router()
logger = get_component_logger("chat")


class ChatState(StatesGroup):
    chatting = State()  # пользователь находится в чате


# Ожидается, что chat_id будет в state, когда пользователь пишет в анонимный чат


@router.message(ChatState.chatting)
async def chat(
    message: Message, state: FSMContext, album_messages: list[Message] | None = None
):
    data = await state.get_data()
    chat_id = data.get("chat_id")
    if not chat_id:
        await message.answer(
            "❌ Чат не найден в состоянии. Попробуйте начать диалог через объявление."
        )
        return

    # Лимит сообщений
    import time

    last_sent = data.get("last_message_time")
    now = time.time()
    if last_sent and now - last_sent < 3:
        await message.answer(
            "❌ Подождите немного перед отправкой следующего сообщения."
        )
        return
    await state.update_data(last_message_time=now)

    # Используем только текущее сообщение или альбом
    messages = album_messages if album_messages else [message]

    async with db_helper.session_factory() as session:
        chat = await get_chat_by_id(session, chat_id)
        if not chat or not chat.is_active:
            await message.answer("❌ Чат неактивен или не найден.")
            return

        if message.from_user.id == chat.buyer_id:
            sender_type = "покупателя"
            recipient_id = chat.seller_id
        elif message.from_user.id == chat.seller_id:
            sender_type = "продавца"
            recipient_id = chat.buyer_id
        else:
            await message.answer("❌ Вы не участник этого чата.")
            return

        # Собираем все фото и текст
        photos = []
        full_text = None
        for msg in messages:
            if msg.text and not full_text:
                full_text = msg.text
            if msg.photo:
                largest_photo = msg.photo[-1]  # выбираем самое большое
                photos.append(largest_photo.file_id)
                # Сохраняем в базе
                chat_message = await add_message(
                    session, chat_id, msg.from_user.id, msg.text or ""
                )
                await add_photo_to_message(
                    session, chat_message.id, largest_photo.file_id
                )

        # Отправляем медиагруппу
        try:
            if photos:
                full_text = f"💬 Новое сообщение от {sender_type} по объявлению #{chat.product_id}"
                media_group = [InputMediaPhoto(media=photos[0], caption=full_text)]
                media_group += [InputMediaPhoto(media=p) for p in photos[1:]]
                await message.bot.send_media_group(int(recipient_id), media_group)

            else:
                await message.bot.send_message(
                    int(recipient_id),
                    f"💬 Новое сообщение от {sender_type} по объявлению #{chat.product_id}:\n\n{full_text}",
                )
        except Exception as e:
            logger.warning(
                f"Не удалось отправить сообщение пользователю {recipient_id}: {e}"
            )

        await message.answer(
            "✅ Сообщение отправлено анонимно.", reply_markup=menu_chat
        )


@router.callback_query(F.data.startswith("start_chat:"))
async def start_anonymous_chat(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    product_id = int(callback.data.split(":")[1])

    async with db_helper.session_factory() as session:
        # Проверяем существование объявления
        product = await session.get(Product, product_id)
        if not product:
            await callback.message.answer("❌ Объявление не найдено.")
            return

        seller_id = product.user_id
        buyer_id = callback.from_user.id

        if seller_id == buyer_id:
            await callback.message.answer("❌ Нельзя начать чат с самим собой.")
            return

        # Достаём модель продавца
        seller: User = await session.get(User, product.user_id)
        seller_telegram_id = seller.telegram_id
        buyer_telegram_id = callback.from_user.id

        # Создаём или получаем чат
        chat = await create_or_get_chat(
            session, product_id, buyer_telegram_id, seller_telegram_id
        )

        # Сохраняем chat_id в state
        await state.update_data(chat_id=chat.id)

        # Здесь устанавливаем состояние ChatState.chatting
        await state.set_state(ChatState.chatting)

    # Подтверждаем пользователю
    await callback.message.answer(
        f"💬 Анонимный чат по объявлению #{product_id} начат.\n"
        f"Пишите сообщение прямо сюда, и оно будет отправлено продавцу."
    )

    await callback.answer()


@router.callback_query(F.data == "exit_for_chat")
async def exit_for_chat(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "💬 <b>Вы вышли из чата</b>\n\n"
        "Теперь вы можете продолжить общение, написав команду "
        "/my_chats 📝",
        reply_markup=menu_start,
        parse_mode="HTML",
    )

    await callback.answer()


@router.message(Command("my_chats"))
async def my_chats(message: Message):
    user_id = message.from_user.id

    async with db_helper.session_factory() as session:
        chats = await get_user_chats(session, user_id)

        if not chats:
            await message.answer("❌ У вас пока нет чатов.")
            return

        # формируем список кнопок
        buttons = []
        for chat in chats:
            product = await session.get(Product, chat.product_id)
            product_name = product.name if product else f"Товар #{chat.product_id}"
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=product_name, callback_data=f"chat_{chat.id}"
                    )
                ]
            )
            # каждая кнопка в отдельном списке, чтобы была на своей строке

        # создаём клавиатуру с кнопками
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer("💬 Ваши чаты:", reply_markup=kb)


@router.callback_query(F.data.startswith("chat_"))
async def open_chat(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    async with db_helper.session_factory() as session:
        chat = await get_chat_by_id(session, chat_id)
        if not chat or not chat.is_active:
            await callback.message.answer("❌ Чат не найден или неактивен.")
            return

        if user_id not in [chat.buyer_id, chat.seller_id]:
            await callback.message.answer("❌ Вы не участник этого чата.")
            return

    # Сохраняем chat_id в state и переводим в состояние ChatState.chatting
    await state.update_data(chat_id=chat_id)

    await state.set_state(ChatState.chatting)

    await callback.message.answer(
        "💬 Чат открыт. Теперь вы можете писать сообщения прямо сюда.",
        reply_markup=menu_chat,
    )
    await callback.answer()
