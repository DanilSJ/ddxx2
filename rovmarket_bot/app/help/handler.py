from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from rovmarket_bot.app.start.keyboard import menu_start
from rovmarket_bot.core.cache import check_rate_limit
from rovmarket_bot.core.logger import get_component_logger

router = Router()
logger = get_component_logger("help")


@router.message(Command("help"))
async def cmd_start(message: Message, state: FSMContext):
    logger.info(
        "/help from user_id=%s username=%s",
        message.from_user.id,
        message.from_user.username,
    )
    allowed, retry_after = await check_rate_limit(message.from_user.id, "search_cmd")
    if not allowed:
        await message.answer(
            f"Слишком часто. Подождите {retry_after} сек и попробуйте снова."
        )
        return
    await state.clear()
    await message.answer(
        "**👋 Привет!**\n"
        "Ты в боте *РовенМаркет* — здесь легко продавать и покупать товары в **Ровеньках** 🏙\n\n"
        "✨ *Что ты можешь делать:*\n"
        "- 📢 **Разместить объявление** — опиши товар, добавь фото и цену\n"
        "- 🔍 **Посмотреть свежие предложения** — найди то, что ищешь\n\n"
        "🛠 Всё просто — выбирай нужную кнопку в меню и действуй!",
        reply_markup=menu_start,
    )

    logger.info("help menu sent to user_id=%s", message.from_user.id)
