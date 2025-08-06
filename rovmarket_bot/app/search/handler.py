from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InputMediaPhoto
from .crud import *
from .keyboard import menu_search
from .redis_search import search_in_redis
import datetime

router = Router()


class Search(StatesGroup):
    text = State()


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    await button_search(message, state)


@router.message(F.text == "🔍 Найти объявление")
async def button_search(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Search.text)

    await message.answer(
        "Напишите текст для поиска. Или выберите кнопки", reply_markup=menu_search
    )


@router.message(Search.text)
async def search_ads(message: Message, state: FSMContext):
    query = message.text
    async with db_helper.session_factory() as session:
        results = await search_in_redis(query, session)
    if not results:
        await message.answer("Ничего не найдено 😔")
        return
    for item in results:
        name = item.get("name", "Без названия")
        desc = item.get("description", "Без описания")
        price = item.get("price", "Цена не указана")
        contact = item.get("contact", "-")
        geo = item.get("geo")
        created_at = item.get("created_at")
        # Форматируем дату
        if created_at:
            if isinstance(created_at, str):
                try:
                    created_at = datetime.datetime.fromisoformat(created_at)
                except Exception:
                    created_at = None
            if isinstance(created_at, datetime.datetime):
                created_str = created_at.strftime("%d.%m.%Y %H:%M")
            else:
                created_str = "-"
        else:
            created_str = "-"
        geo_str = "-"
        if geo and isinstance(geo, dict):
            lat = geo.get("latitude")
            lon = geo.get("longitude")
            if lat is not None and lon is not None:
                geo_str = f"{lat}, {lon}"
        text = (
            f"📌 {name}\n"
            f"💬 {desc}\n"
            f"💰 {price}\n"
            f"📞 Контакт: {contact}\n"
            f"📍 Геолокация: {geo_str}\n"
            f"🕒 Дата создания: {created_str}"
        )
        photos = item.get("photos", [])
        if photos:
            media = []
            for idx, photo_url in enumerate(photos):
                if idx == 0:
                    media.append(InputMediaPhoto(media=photo_url, caption=text))
                else:
                    media.append(InputMediaPhoto(media=photo_url))
            await message.answer_media_group(media)
        else:
            await message.answer(text)
