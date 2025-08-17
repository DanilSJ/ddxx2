from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from rovmarket_bot.core.models import db_helper
from .keyboard import menu_start
from .crud import add_user
from rovmarket_bot.core.cache import check_rate_limit
from rovmarket_bot.core.logger import get_component_logger

router = Router()
logger = get_component_logger("start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    logger.info(
        "/start from user_id=%s username=%s",
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
    async with db_helper.session_factory() as session:
        await add_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            session=session,
        )
    logger.info("User ensured in DB user_id=%s", message.from_user.id)

    await message.answer(
        """Привет! 👋
Добро пожаловать в РовенМаркет — доску объявлений города Ровеньки прямо в Telegram.

Здесь ты можешь:
📌 Разместить своё объявление за пару кликов
🛒 Купить или продать любой товар
📍 Смотреть предложения именно в своём районе
🔔 Подписаться на уведомления о новых объявлениях
💬 Общаться через бота — твои контакты остаются в безопасности

Полезные команды:
/all_ads — все объявления
/post — добавить своё объявление

Готов начать?
Выбирай действие в меню ниже или напиши /help для справки.
    """,
        parse_mode="HTML",
        reply_markup=menu_start,
    )

    logger.info("Start menu sent to user_id=%s", message.from_user.id)
