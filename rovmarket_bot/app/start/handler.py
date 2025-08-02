from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from .keyboard import menu_start

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Добро пожаловать в РовенМаркет! Что вы хотите сделать?", reply_markup=menu_start)
