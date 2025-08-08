from aiogram.types import TelegramObject
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from typing import Callable, Awaitable, Dict, Any
from rovmarket_bot.core.models import db_helper
from rovmarket_bot.app.start.crud import add_user
from rovmarket_bot.core.models.user import User


class UserCheckMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        async with db_helper.session_factory() as session:
            user: User = await add_user(
                telegram_id=tg_user.id, username=tg_user.username, session=session
            )
            data["user"] = user

        return await handler(event, data)
