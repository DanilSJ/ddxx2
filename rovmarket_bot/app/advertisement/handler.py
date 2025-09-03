from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

from rovmarket_bot.core.models import db_helper
from .crud import create_advertisement, add_ad_photos
from .keyboard import ad_type_keyboard, duration_keyboard, confirm_photos_keyboard
from rovmarket_bot.app.admin.crud import get_all_users

router = Router()


class AdState(StatesGroup):
    choose_type = State()
    text = State()
    photos = State()
    duration = State()


@router.callback_query(F.data == "ads")
async def ads_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(photos=[])
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
            "Вы можете также добавить до 10 фото, если нужно."
        )
    elif ad_type == "menu":
        hint = (
            "✍️ Отправьте текст рекламы для меню.\n\n"
            "Он будет показываться в разделе меню. При желании можно прикрепить до 10 фото."
        )
    else:  # listings
        hint = (
            "✍️ Отправьте текст рекламы для показа среди объявлений.\n\n"
            "Можно прикрепить до 10 фото."
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
    await state.update_data(text=message.text.strip(), photos=[])
    await message.answer(
        "📸 Пришлите до 10 фотографий для рекламы (по одному сообщению или альбомом).\n\n"
        "Когда закончите, нажмите «Подтвердить».",
        reply_markup=confirm_photos_keyboard,
    )
    await state.set_state(AdState.photos)


@router.message(AdState.photos, F.photo)
async def receive_ad_photo(
    message: Message,
    state: FSMContext,
    album_messages: list[Message] | None = None,
):
    data = await state.get_data()
    photos: list[str] = data.get("photos", [])

    messages = album_messages if album_messages else [message]
    for msg in messages:
        if len(photos) >= 10:
            await message.answer("📸 Уже добавлено 10 фото. Нажмите «Подтвердить».")
            break
        photos.append(msg.photo[-1].file_id)

    await state.update_data(photos=photos)
    await message.answer(
        f"✅ Фото добавлено ({len(photos)}/10). Можно отправить ещё или нажмите 'Подтвердить'",
        reply_markup=confirm_photos_keyboard,
    )


@router.message(AdState.photos)
async def photos_other_messages(message: Message):
    await message.answer(
        "📷 Пожалуйста, отправляйте фото. Когда закончите, нажмите «Подтвердить».",
        reply_markup=confirm_photos_keyboard,
    )


@router.callback_query(F.data == "ad_photos_done")
async def ad_photos_done(callback: CallbackQuery, state: FSMContext):
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
    photos: list[str] = data.get("photos", [])

    async with db_helper.session_factory() as session:
        ad = await create_advertisement(
            session,
            text=text,
            ad_type=ad_type,
            duration=duration,
            pinned=pinned,
        )
        if photos:
            await add_ad_photos(session, advertisement_id=ad.id, file_ids=photos)
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
                if photos:
                    media = [InputMediaPhoto(media=photos[0], caption=text)]
                    for fid in photos[1:10]:
                        media.append(InputMediaPhoto(media=fid))
                    msgs = await callback.bot.send_media_group(chat_id=user.telegram_id, media=media)
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
