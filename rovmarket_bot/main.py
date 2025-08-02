import asyncio
from aiogram import Dispatcher
from app.start.handler import router as start
from core.config import bot

dp = Dispatcher()

async def main():
    dp.include_router(start)

    await asyncio.gather(
        dp.start_polling(bot),
    )

if __name__ == "__main__":
    print("Starting...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")
