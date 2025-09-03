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
        "👋 **Привет!**\n"
        "Добро пожаловать в *РовенМаркет* — место, где легко продавать и покупать товары в **ЛНР** 🏙\n\n"
        "✨ *Что здесь можно:*\n"
        "• 📢 **Разместить объявление** — добавь фото, опиши товар и укажи цену\n"
        "• 🔍 **Найти нужное** — просматривай свежие предложения и выбирай лучшее\n\n"
        "💬 По всем вопросам пиши: **@DanilRov**\n"
        "🛠 Просто выбери нужную кнопку в меню и начинай!",
        reply_markup=menu_start,
    )

    logger.info("help menu sent to user_id=%s", message.from_user.id)
