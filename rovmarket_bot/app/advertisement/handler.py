from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo

from rovmarket_bot.core.models import db_helper
from .crud import create_advertisement, add_ad_media
from .keyboard import ad_type_keyboard, duration_keyboard, confirm_media_keyboard
from rovmarket_bot.app.admin.crud import get_all_users

router = Router()


class AdState(StatesGroup):
    choose_type = State()
    text = State()
    media = State()
    duration = State()


@router.callback_query(F.data == "ads")
async def ads_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(media=[])
    await callback.message.answer(
        "📢 Выберите формат рекламы:", reply_markup=ad_type_keyboard
    )
    await state.set_state(AdState.choose_type)


@router.callback_query(F.data.startswith("ad_type:"))
async def choose_ad_type(callback: CallbackQuery, state: FSMContext):
    _, ad_type = callback.data.split(":", 1)
    pinned = ad_type == "broadcast_pinned"
    await state.update_data(ad_type=ad_type, pinned=pinned)

    # Подсказка по содержимому
    if ad_type in ("broadcast", "broadcast_pinned"):
        hint = (
            "✍️ Отправьте текст рассылки. Он будет отправлен всем пользователям.\n\n"
            "Вы можете также добавить до 10 фото или видео, если нужно."
        )
    elif ad_type == "menu":
        hint = (
            "✍️ Отправьте текст рекламы для меню.\n\n"
            "Он будет показываться в разделе меню. При желании можно прикрепить до 10 фото или видео."
        )
    else:  # listings
        hint = (
            "✍️ Отправьте текст рекламы для показа среди объявлений.\n\n"
            "Можно прикрепить до 10 фото или видео."
        )

    await callback.message.edit_reply_markup()
    await callback.message.answer(hint)
    await state.set_state(AdState.text)
    await callback.answer()


@router.message(AdState.text)
async def receive_ad_text(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("⚠️ Пожалуйста, отправьте текст объявления.")
        return
    await state.update_data(text=message.text.strip(), media=[])
    await message.answer(
        "📸 Пришлите до 10 фотографий или видео для рекламы (по одному сообщению или альбомом).\n\n"
        "Когда закончите, нажмите «Подтвердить».",
        reply_markup=confirm_media_keyboard,
    )
    await state.set_state(AdState.media)


@router.message(AdState.media, F.photo)
async def receive_ad_photo(
    message: Message,
    state: FSMContext,
    album_messages: list[Message] | None = None,
):
    data = await state.get_data()
    media: list[tuple[str, str]] = data.get("media", [])

    messages = album_messages if album_messages else [message]
    added_count = 0
    
    for msg in messages:
        if len(media) >= 10:
            await message.answer("📸 Уже добавлено 10 медиа файлов. Нажмите «Подтвердить».")
            break
        
        # Добавляем фото, если есть
        if msg.photo and len(msg.photo) > 0:
            media.append((msg.photo[-1].file_id, "photo"))
            added_count += 1
            continue
        # Добавляем видео, если есть (для смешанных альбомов)
        if getattr(msg, "video", None):
            media.append((msg.video.file_id, "video"))
            added_count += 1

    await state.update_data(media=media)
    
    if added_count > 0:
        await message.answer(
            f"✅ Медиа добавлено ({len(media)}/10). Можно отправить ещё или нажмите 'Подтвердить'",
            reply_markup=confirm_media_keyboard,
        )
    else:
        await message.answer(
            "⚠️ Не удалось обработать медиа. Попробуйте отправить заново.",
            reply_markup=confirm_media_keyboard,
        )


@router.message(AdState.media, F.video)
async def receive_ad_video(
    message: Message,
    state: FSMContext,
    album_messages: list[Message] | None = None,
):
    data = await state.get_data()
    media: list[tuple[str, str]] = data.get("media", [])

    messages = album_messages if album_messages else [message]
    added_count = 0
    
    for msg in messages:
        if len(media) >= 10:
            await message.answer("📹 Уже добавлено 10 медиа файлов. Нажмите «Подтвердить».")
            break
        
        # Добавляем видео, если есть
        if getattr(msg, "video", None):
            media.append((msg.video.file_id, "video"))
            added_count += 1
            continue
        # Добавляем фото, если есть (для смешанных альбомов)
        if msg.photo and len(msg.photo) > 0:
            media.append((msg.photo[-1].file_id, "photo"))
            added_count += 1

    await state.update_data(media=media)
    
    if added_count > 0:
        await message.answer(
            f"✅ Медиа добавлено ({len(media)}/10). Можно отправить ещё или нажмите 'Подтвердить'",
            reply_markup=confirm_media_keyboard,
        )
    else:
        await message.answer(
            "⚠️ Не удалось обработать медиа. Попробуйте отправить заново.",
            reply_markup=confirm_media_keyboard,
        )


@router.message(AdState.media)
async def media_other_messages(message: Message):
    await message.answer(
        "📷 Пожалуйста, отправляйте фото или видео. Когда закончите, нажмите «Подтвердить».",
        reply_markup=confirm_media_keyboard,
    )


@router.callback_query(F.data == "ad_photos_done")
async def ad_media_done(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await callback.message.answer("⏳ Выберите срок размещения:", reply_markup=duration_keyboard)
    await state.set_state(AdState.duration)
    await callback.answer()


@router.callback_query(F.data.startswith("ad_duration:"))
async def choose_duration(callback: CallbackQuery, state: FSMContext):
    _, duration = callback.data.split(":", 1)
    data = await state.get_data()
    text: str = data.get("text")
    ad_type: str = data.get("ad_type")
    pinned: bool = bool(data.get("pinned"))
    media: list[tuple[str, str]] = data.get("media", [])

    async with db_helper.session_factory() as session:
        ad = await create_advertisement(
            session,
            text=text,
            ad_type=ad_type,
            duration=duration,
            pinned=pinned,
        )
        if media:
            await add_ad_media(session, advertisement_id=ad.id, media_items=media)
        await session.commit()

    # If it's a broadcast type, send to all users
    if ad_type in ("broadcast", "broadcast_pinned"):
        async with db_helper.session_factory() as session:
            users = await get_all_users(session)
        sent = 0
        failed = 0
        for user in users:
            try:
                pinned_required = ad_type == "broadcast_pinned"
                if media:
                    # Создаем медиа группу с поддержкой фото и видео
                    media_group = []
                    for file_id, media_type in media[:10]:  # Ограничиваем до 10 файлов
                        if media_type == "photo":
                            media_group.append(InputMediaPhoto(media=file_id))
                        elif media_type == "video":
                            media_group.append(InputMediaVideo(media=file_id))
                    
                    if media_group:
                        # Добавляем caption к первому элементу
                        if media_group:
                            media_group[0].caption = text
                        
                        msgs = await callback.bot.send_media_group(chat_id=user.telegram_id, media=media_group)
                        if pinned_required and msgs:
                            try:
                                await callback.bot.pin_chat_message(chat_id=user.telegram_id, message_id=msgs[0].message_id)
                            except Exception:
                                pass
                else:
                    msg = await callback.bot.send_message(chat_id=user.telegram_id, text=text)
                    if pinned_required:
                        try:
                            await callback.bot.pin_chat_message(chat_id=user.telegram_id, message_id=msg.message_id)
                        except Exception:
                            pass
                sent += 1
            except Exception:
                failed += 1

        await callback.message.answer(
            f"📬 Рассылка завершена. Успешно: {sent}, ошибок: {failed}."
        )

    await callback.message.edit_reply_markup()
    await callback.message.answer(
        "🎉 Реклама создана и будет активной согласно выбранному сроку."
    )
    await state.clear()
    await callback.answer()
