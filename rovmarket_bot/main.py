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

from aiogram.fsm.storage.redis import RedisStorage
from rovmarket_bot.core.config import bot, settings
from rovmarket_bot.core.logger import set_logging_enabled
from rovmarket_bot.core.models import db_helper
from rovmarket_bot.app.settings.crud import get_or_create_bot_settings
from rovmarket_bot.middleware.album_middleware import AlbumMiddleware
from rovmarket_bot.middleware.user_check_middleware import UserCheckMiddleware
from rovmarket_bot.app.search.redis_search import ensure_redis_index
from rovmarket_bot.app.start.handler import router as start
from rovmarket_bot.app.post.handler import router as post
from rovmarket_bot.app.search.handler import router as search
from rovmarket_bot.app.ads.handler import router as ads
from rovmarket_bot.app.admin.handler import router as admin
from rovmarket_bot.app.settings.handler import router as settings_router
from rovmarket_bot.app.help.handler import router as help_router


storage = RedisStorage.from_url(settings.REDIS_URL)
dp = Dispatcher(storage=storage)


async def main():
    # Initialize logging flag from DB (CRUD-style)
    try:
        async with db_helper.session_factory() as session:
            bot_settings = await get_or_create_bot_settings(session)
            set_logging_enabled(bool(bot_settings.logging))
    except Exception:
        # Fall back silently to env-based setting if DB is unavailable at startup
        pass

    # Import routers only after logging flag is set to avoid early logger init

    dp.message.middleware(UserCheckMiddleware())
    dp.message.middleware(AlbumMiddleware())
    dp.include_router(start)
    dp.include_router(post)
    dp.include_router(search)
    dp.include_router(ads)
    dp.include_router(admin)
    dp.include_router(help_router)
    dp.include_router(settings_router)

    await ensure_redis_index()
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
