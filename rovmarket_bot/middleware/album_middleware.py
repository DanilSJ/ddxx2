# album_middleware.py
import asyncio
from collections import defaultdict
from typing import Callable, Awaitable, Any

from aiogram import BaseMiddleware, types

AlbumMessages = list[types.Message]
DataType = dict[str, Any]


class AlbumMiddleware(BaseMiddleware):
    def __init__(self, timeout: float = 0.3):
        self.timeout = timeout
        self.album_messages = defaultdict(list)

    def store_album_message(self, message: types.Message) -> int:
        self.album_messages[message.media_group_id].append(message)
        return len(self.album_messages[message.media_group_id])

    def get_result_album(self, message: types.Message) -> AlbumMessages:
        album = self.album_messages.pop(message.media_group_id)
        album.sort(key=lambda m: m.message_id)
        return album

    async def __call__(
        self,
        handler: Callable[[types.Message, DataType], Awaitable[Any]],
        event: types.Message,
        data: DataType,
    ) -> Any | None:
        if event.media_group_id is None:
            return await handler(event, data)

        count = self.store_album_message(event)
        await asyncio.sleep(self.timeout)

        new_count = len(self.album_messages[event.media_group_id])
        if new_count != count:
            return None

        data["album_messages"] = self.get_result_album(event)
        return await handler(event, data)
