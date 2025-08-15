import time

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    InputMediaVideo,
)

from rovmarket_bot.app.chat.keyboard import menu_chat
from rovmarket_bot.app.start.keyboard import menu_start
from rovmarket_bot.core.logger import get_component_logger
from rovmarket_bot.app.chat.crud import (
    create_or_get_chat,
    add_message,
    get_chat_by_id,
    get_user_chats,
    add_video_to_message,
    add_audio_to_message,
    add_voice_to_message,
    add_document_to_message,
    add_photo_to_message,
    get_last_messages,
    add_sticker_to_message,
    mark_chat_as_inactive,
    get_product_name,
)
from rovmarket_bot.core.models import db_helper, Product, User

router = Router()
logger = get_component_logger("chat")


class ChatState(StatesGroup):
    chatting = State()  # пользователь находится в чате


# Ожидается, что chat_id будет в state, когда пользователь пишет в анонимный чат


@router.message(
    ChatState.chatting,
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

    last_sent = data.get("last_message_time")
    now = time.time()
    if last_sent and now - last_sent < 3:
        await message.answer(
            "❌ Подождите немного перед отправкой следующего сообщения."
        )
        return
    await state.update_data(last_message_time=now)

    messages = album_messages if album_messages else [message]

    async with db_helper.session_factory() as session:
        chat = await get_chat_by_id(session, chat_id)
        if not chat or not chat.is_active:
            await message.answer("❌ Чат неактивен или не найден.")
            return

        if message.from_user.id == chat.buyer_id:
            sender_type = "покупателя"
            recipient_id = int(chat.seller_id)
        elif message.from_user.id == chat.seller_id:
            sender_type = "продавца"
            recipient_id = int(chat.buyer_id)
        else:
            await message.answer("❌ Вы не участник этого чата.")
            return

        photos, videos, stickers, audios, voices, documents = [], [], [], [], [], []
        full_text = None
        for msg in messages:
            if msg.sticker:
                stickers.append(msg.sticker.file_id)
                chat_message = await add_message(
                    session, chat_id, msg.from_user.id, msg.text or ""
                )
                await add_sticker_to_message(
                    session, chat_message.id, msg.sticker.file_id
                )
            if msg.audio:
                audios.append(msg.audio.file_id)
                chat_message = await add_message(
                    session, chat_id, msg.from_user.id, msg.text or ""
                )
                await add_audio_to_message(session, chat_message.id, msg.audio.file_id)
            if msg.voice:
                voices.append(msg.voice.file_id)
                chat_message = await add_message(
                    session, chat_id, msg.from_user.id, msg.text or ""
                )
                await add_voice_to_message(session, chat_message.id, msg.voice.file_id)
            if msg.document:
                documents.append(msg.document.file_id)
                chat_message = await add_message(
                    session, chat_id, msg.from_user.id, msg.text or ""
                )
                await add_document_to_message(
                    session, chat_message.id, msg.document.file_id
                )
            if msg.text:
                full_text = msg.text
                await add_message(session, chat_id, msg.from_user.id, msg.text)
            if msg.photo:
                largest_photo = msg.photo[-1]
                photos.append(largest_photo.file_id)
                chat_message = await add_message(
                    session, chat_id, msg.from_user.id, msg.text or ""
                )
                await add_photo_to_message(
                    session, chat_message.id, largest_photo.file_id
                )
            if msg.video:
                videos.append(msg.video.file_id)
                chat_message = await add_message(
                    session, chat_id, msg.from_user.id, msg.text or ""
                )
                await add_video_to_message(session, chat_message.id, msg.video.file_id)

        try:
            product_name = await get_product_name(session, int(chat.product_id))
            media_group = []
            if full_text:
                full_text = f"💬 Новое сообщение от {sender_type} по объявлению {product_name}:\n\n{full_text}"

            if photos:
                media_group.append(InputMediaPhoto(media=photos[0], caption=full_text))
                media_group += [InputMediaPhoto(media=p) for p in photos[1:]]
            if videos:
                media_group.append(InputMediaVideo(media=videos[0], caption=full_text))
                media_group += [InputMediaVideo(media=v) for v in videos[1:]]

            if stickers:
                await message.bot.send_message(
                    int(recipient_id),
                    f"💬 Новое сообщение от {sender_type} по объявлению {product_name} (стикеры)",
                )
                for st in stickers:
                    await message.bot.send_sticker(int(recipient_id), st)

            for au in audios:
                await message.bot.send_audio(
                    int(recipient_id),
                    au,
                    caption=f"💬 Новое сообщение от {sender_type} по объявлению {product_name} (аудио)",
                )

            for vc in voices:
                await message.bot.send_voice(
                    int(recipient_id),
                    vc,
                    caption=f"💬 Новое сообщение от {sender_type} по объявлению {product_name} (голосовое)",
                )

            for doc in documents:
                await message.bot.send_document(
                    int(recipient_id),
                    doc,
                    caption=f"💬 Новое сообщение от {sender_type} по объявлению {product_name} (файлы)",
                )

            if media_group:
                await message.bot.send_media_group(int(recipient_id), media_group)
            else:
                await message.bot.send_message(int(recipient_id), full_text)

        except TelegramForbiddenError:
            logger.warning(
                f"Пользователь {recipient_id} заблокировал бота или удалил аккаунт."
            )
            await mark_chat_as_inactive(
                session, chat_id
            )  # Функция пометит чат как закрытый
            await message.answer(
                "❌ Пользователь недоступен (возможно, заблокировал бота). Чат закрыт."
            )
        except TelegramBadRequest as e:
            logger.error(f"Ошибка при отправке сообщения {recipient_id}: {e}")
        except Exception as e:
            logger.error(
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
    product_name = await get_product_name(session, int(product_id))

    # Подтверждаем пользователю
    await callback.message.answer(
        f"💬 Анонимный чат по объявлению {product_name} начат.\n"
        f"Пишите сообщение прямо сюда, и оно будет отправлено продавцу."
    )

    await callback.answer()


@router.callback_query(F.data == "exit_for_chat")
async def exit_for_chat(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chat_messages = data.get("chat_messages", [])  # Список ID сообщений чата

    # Удаляем все сообщения чата
    for msg_id in chat_messages:
        try:
            await callback.message.bot.delete_message(
                chat_id=callback.from_user.id, message_id=msg_id
            )
        except Exception:
            pass  # Игнорируем ошибки удаления

    # Очищаем состояние
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
        await message.answer("xxxx")
        chats = await get_user_chats(session, user_id)
        await message.answer(chats)
        await message.answer("zzzz")
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

        messages = await get_last_messages(session, chat_id, limit=15)

    await state.update_data(chat_id=chat_id)
    await state.set_state(ChatState.chatting)

    await state.update_data(chat_id=chat_id, chat_messages=[])  # Список сообщений

    for msg in messages:
        sender = "Покупатель" if msg["sender_id"] == chat.buyer_id else "Продавец"
        text = msg["text"]
        media_group = []
        msg_ids = []

        # Фото
        for photo in msg.get("photos", []):
            if photo:
                if text:
                    media_group.append(
                        InputMediaPhoto(media=photo, caption=f"💬 {sender}:\n{text}")
                    )
                    text = None
                else:
                    media_group.append(InputMediaPhoto(media=photo))

        # Видео
        for video in msg.get("videos", []):
            if video:
                if text:
                    media_group.append(
                        InputMediaVideo(media=video, caption=f"💬 {sender}:\n{text}")
                    )
                    text = None
                else:
                    media_group.append(InputMediaVideo(media=video))

        if media_group:
            sent = await callback.message.answer_media_group(media_group)
            msg_ids.extend([m.message_id for m in sent])

        # Если остался текст без медиа
        if text:
            sent_msg = await callback.message.answer(f"💬 {sender}:\n{text}")
            msg_ids.append(sent_msg.message_id)

        # Стикеры
        for st in msg.get("stickers", []):
            if st:
                sent_msg = await callback.message.answer_sticker(st)
                msg_ids.append(sent_msg.message_id)

        # Аудио
        for au in msg.get("audios", []):
            if au:
                sent_msg = await callback.message.answer_audio(
                    au, caption=f"💬 {sender}:"
                )
                msg_ids.append(sent_msg.message_id)

        # Голосовые
        for vc in msg.get("voices", []):
            if vc:
                sent_msg = await callback.message.answer_voice(
                    vc, caption=f"💬 {sender}:"
                )
                msg_ids.append(sent_msg.message_id)

        # Документы
        for doc in msg.get("documents", []):
            if doc:
                sent_msg = await callback.message.answer_document(
                    doc, caption=f"💬 {sender}:"
                )
                msg_ids.append(sent_msg.message_id)

        # Сохраняем ID сообщений
        chat_data = await state.get_data()
        chat_messages = chat_data.get("chat_messages", [])
        chat_messages.extend(msg_ids)
        await state.update_data(chat_messages=chat_messages)

    sent_msg = await callback.message.answer(
        "💬 Чат открыт. Теперь вы можете писать сообщения прямо сюда.",
        reply_markup=menu_chat,
    )
    chat_messages = (await state.get_data()).get("chat_messages", [])
    chat_messages.append(sent_msg.message_id)
    await state.update_data(chat_messages=chat_messages)


@router.message(F.text == "👥 Мои чаты")
async def button_my_chats(message: Message, state: FSMContext):
    await state.clear()
    await my_chats(message)
