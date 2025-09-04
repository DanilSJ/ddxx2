from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from rovmarket_bot.core.models import db_helper
from .keyboard import menu_start, menu_start_inline
from .crud import add_user
from rovmarket_bot.core.cache import check_rate_limit
from rovmarket_bot.core.logger import get_component_logger
from rovmarket_bot.app.advertisement.crud import get_next_menu_ad
from aiogram.types import InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import InputMediaVideo

router = Router()
logger = get_component_logger("start")


def escape_markdown(text: str) -> str:
    """Escape Telegram Markdown special characters.
    This targets classic Markdown (not V2): _, *, `, [, ] and parentheses.
    """
    if not text:
        return text
    # Backslash first
    text = text.replace("\\", "\\\\")
    for ch in ("_", "*", "`", "[", "]", "(", ")"):
        text = text.replace(ch, f"\\{ch}")
    return text


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
Добро пожаловать в РовенМаркет — доску объявлений ЛНР прямо в Telegram.

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
        parse_mode="Markdown",
        reply_markup=menu_start,
    )
    await message.answer("👇 Выберите действие:", reply_markup=menu_start_inline)
    
    logger.info("Start menu sent to user_id=%s", message.from_user.id)

    # Show exactly one rotating menu advertisement (if exists)
    async with db_helper.session_factory() as session:
        ad = await get_next_menu_ad(session)
        if ad:
            # Try to send media (photos/videos) if present, else just text
            if getattr(ad, "media", None):
                media_group = []
                for idx, m in enumerate(ad.media[:10]):
                    if m.media_type == "photo":
                        item = InputMediaPhoto(media=m.file_id)
                    else:
                        item = InputMediaVideo(media=m.file_id)
                    if idx == 0:
                        item.caption = escape_markdown(ad.text)
                        item.parse_mode = "Markdown"
                    media_group.append(item)
                try:
                    await message.answer_media_group(media_group)
                except Exception:
                    await message.answer(escape_markdown(ad.text), parse_mode="Markdown")
            else:
                await message.answer(escape_markdown(ad.text), parse_mode="Markdown")
        # persist pointer changes
        await session.commit()
