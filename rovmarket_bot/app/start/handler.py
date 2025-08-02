from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from rovmarket_bot.core.models import db_helper
from .keyboard import menu_start
from .crud import add_user

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    async with db_helper.session_factory() as session:
        await add_user(telegram_id=message.from_user.id, session=session)

    await message.answer("Добро пожаловать в РовенМаркет! Что вы хотите сделать?", reply_markup=menu_start)
