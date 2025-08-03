import asyncio
from aiogram import Dispatcher
from rovmarket_bot.app.start.handler import router as start
from rovmarket_bot.core.config import bot, settings
from aiogram.fsm.storage.redis import RedisStorage


storage = RedisStorage.from_url(settings.REDIS_URL)
dp = Dispatcher(storage=storage)


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
