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
from rovmarket_bot.app.chat.handler import router as chat
from rovmarket_bot.app.settings.handler import router as settings_router
from rovmarket_bot.app.help.handler import router as help_router
from rovmarket_bot.app.advertisement.handler import router as advertisement_router
from rovmarket_bot.app.advertisement.crud import get_next_broadcast_ad
from rovmarket_bot.app.admin.crud import get_all_users


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
    dp.include_router(chat)
    dp.include_router(advertisement_router)

    await ensure_redis_index()

    async def broadcast_scheduler():
        while True:
            try:
                async with db_helper.session_factory() as session:
                    ad = await get_next_broadcast_ad(session)
                    if ad:
                        users = await get_all_users(session)
                        # commit pointer advance even if sending fails later
                        await session.commit()

                        # prepare media/text
                        text = ad.text
                        photos = [p.file_id for p in (ad.photos or [])]
                        sent = 0
                        for user in users:
                            try:
                                if photos:
                                    from aiogram.types import InputMediaPhoto

                                    media = [InputMediaPhoto(media=photos[0], caption=text)]
                                    for fid in photos[1:10]:
                                        media.append(InputMediaPhoto(media=fid))
                                    msgs = await bot.send_media_group(chat_id=user.telegram_id, media=media)
                                    if ad.pinned and msgs:
                                        try:
                                            await bot.pin_chat_message(chat_id=user.telegram_id, message_id=msgs[0].message_id)
                                        except Exception:
                                            pass
                                else:
                                    msg = await bot.send_message(chat_id=user.telegram_id, text=text)
                                    if ad.pinned:
                                        try:
                                            await bot.pin_chat_message(chat_id=user.telegram_id, message_id=msg.message_id)
                                        except Exception:
                                            pass
                                sent += 1
                            except Exception:
                                # ignore per-user failures
                                pass
            except Exception:
                # swallow scheduler errors; continue next tick
                pass
            # wait one hour
            await asyncio.sleep(60 * 60)

    await asyncio.gather(
        dp.start_polling(bot),
        broadcast_scheduler(),
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
