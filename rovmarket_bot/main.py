import asyncio
from aiogram import Dispatcher
from aiogram.exceptions import (
    TelegramNetworkError,
    TelegramAPIError,
    TelegramServerError,
    TelegramUnauthorizedError,
    TelegramNotFound,
    TelegramBadRequest,
)

from rovmarket_bot.app.start.handler import router as start
from rovmarket_bot.app.post.handler import router as post
from rovmarket_bot.app.search.handler import router as search
from rovmarket_bot.app.ads.handler import router as ads
from rovmarket_bot.core.config import bot, settings
from aiogram.fsm.storage.redis import RedisStorage


storage = RedisStorage.from_url(settings.REDIS_URL)
dp = Dispatcher(storage=storage)


async def main():
    dp.include_router(start)
    dp.include_router(post)
    dp.include_router(search)
    dp.include_router(ads)

    await asyncio.gather(
        dp.start_polling(bot),
    )


if __name__ == "__main__":
    print("Starting...")
    try:
        asyncio.run(main())
    except TelegramNetworkError:
        print("No internet connection")
    except TelegramUnauthorizedError:
        print("No authorization token")
    except TelegramNotFound:
        print("No bot token")
    except TelegramServerError:
        print("No server connection")
    except TelegramBadRequest:
        print("Bad request")
    except TelegramAPIError:
        print("No API connection")
    except KeyboardInterrupt:
        print("Exit")
