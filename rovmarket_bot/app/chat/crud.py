from sqlalchemy import and_

from rovmarket_bot.core.models import (
    db_helper,
    Chat,
    ChatMessage,
    User,
    Product,
    ChatPhoto,
    ChatVideo,
    ChatSticker,
)
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from rovmarket_bot.core.models.chat_audio import ChatAudio
from rovmarket_bot.core.models.chat_document import ChatDocument
from rovmarket_bot.core.models.chat_voice import ChatVoice


async def create_or_get_chat(session, product_id, buyer_id, seller_id):
    chat = await session.execute(
        select(Chat).where(
            Chat.product_id == product_id,
            Chat.buyer_id == buyer_id,
            Chat.seller_id == seller_id,
        )
    )
    print(chat)
    print(chat.id)
    # chat = chat.scalar_one_or_none()
    # if not chat:
    #     chat = Chat(product_id=product_id, buyer_id=buyer_id, seller_id=seller_id)
    #     session.add(chat)
    #     try:
    #         await session.commit()
    #     except Exception as e:
    #         await session.rollback()
    #         print("Ошибка при коммите:", e)
    #         raise
    return chat


async def get_chat_by_id(session: AsyncSession, chat_id: int) -> Optional[Chat]:
    stmt = select(Chat).where(Chat.id == chat_id)
    result = await session.execute(stmt)
    return result.scalars().first()


async def get_chat_by_product_and_buyer(
    session: AsyncSession, product_id: int, buyer_id: int
) -> Optional[Chat]:
    stmt = select(Chat).where(
        Chat.product_id == product_id,
        Chat.buyer_id == buyer_id,
        Chat.is_active.is_(True),
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def add_message(
    session: AsyncSession, chat_id: int, sender_id: int, text: str
) -> ChatMessage:
    message = ChatMessage(chat_id=chat_id, sender_id=sender_id, text=text)
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def get_messages(
    session: AsyncSession, chat_id: int, limit: int = 50
) -> List[ChatMessage]:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_active_chat_by_user_id(
    session: AsyncSession, user_id: int
) -> Optional[Chat]:
    """
    Возвращает активный чат для пользователя (покупателя) по его user_id.
    Если пользователь не участвует в активных чатах, возвращает None.
    """
    stmt = (
        select(Chat)
        .where(Chat.buyer_id == user_id, Chat.is_active.is_(True))
        .order_by(Chat.id.desc())
    )  # Берем последний созданный чат

    result = await session.execute(stmt)
    return result.scalars().first()


async def get_user_chats(session: AsyncSession, user_id: int):
    """
    Получает все активные чаты для пользователя (покупатель или продавец)
    """
    stmt = (
        select(Chat)
        .where(
            ((Chat.buyer_id == user_id) | (Chat.seller_id == user_id))
            & (Chat.is_active.is_(True))
        )
        .order_by(Chat.id.desc())
    )
    result = await session.execute(stmt)
    chats = result.scalars().all()
    return chats


async def get_product_name(session: AsyncSession, product_id: int) -> str:
    """
    Получает название товара по его ID
    """
    product = await session.get(Product, product_id)
    return product.name if product else f"Товар #{product_id}"


async def add_photo_to_message(
    session: AsyncSession, message_id: int, file_id: str
) -> ChatPhoto:
    """
    Сохраняет фото для сообщения чата.

    :param session: AsyncSession SQLAlchemy
    :param message_id: ID сообщения (ChatMessage.id)
    :param file_id: Telegram file_id фотографии
    :return: созданный объект ChatPhoto
    """
    photo = ChatPhoto(chat_id=message_id, photo_url=file_id)
    session.add(photo)
    await session.commit()
    await session.refresh(photo)
    return photo


async def add_video_to_message(
    session: AsyncSession, message_id: int, file_id: str
) -> "ChatVideo":
    """
    Сохраняет видео для сообщения чата.

    :param session: AsyncSession SQLAlchemy
    :param message_id: ID сообщения (ChatMessage.id)
    :param file_id: Telegram file_id видео
    :return: созданный объект ChatVideo
    """
    video = ChatVideo(chat_id=message_id, video_url=file_id)
    session.add(video)
    await session.commit()
    await session.refresh(video)
    return video


async def add_sticker_to_message(
    session: AsyncSession, message_id: int, file_id: str
) -> "ChatSticker":
    """
    Сохраняет стикеров для сообщения чата.

    :param session: AsyncSession SQLAlchemy
    :param message_id: ID сообщения (ChatMessage.id)
    :param file_id: Telegram file_id стикера
    :return: созданный объект ChatSticker
    """
    sticker = ChatSticker(chat_id=message_id, sticker_url=file_id)
    session.add(sticker)
    await session.commit()
    await session.refresh(sticker)
    return sticker


async def add_audio_to_message(
    session: AsyncSession, message_id: int, file_id: str
) -> "ChatAudio":
    """
    Сохраняет аудио для сообщения чата.

    :param session: AsyncSession SQLAlchemy
    :param message_id: ID сообщения (ChatMessage.id)
    :param file_id: Telegram file_id аудио
    :return: созданный объект ChatAudio
    """
    audio = ChatAudio(chat_id=message_id, audio_url=file_id)
    session.add(audio)
    await session.commit()
    await session.refresh(audio)
    return audio


async def add_voice_to_message(
    session: AsyncSession, message_id: int, file_id: str
) -> "ChatVoice":
    """
    Сохраняет голосовых для сообщения чата.

    :param session: AsyncSession SQLAlchemy
    :param message_id: ID сообщения (ChatMessage.id)
    :param file_id: Telegram file_id голосовых
    :return: созданный объект ChatVoice
    """
    voice = ChatVoice(chat_id=message_id, voice_url=file_id)
    session.add(voice)
    await session.commit()
    await session.refresh(voice)
    return voice


async def add_document_to_message(
    session: AsyncSession, message_id: int, file_id: str
) -> "ChatDocument":
    """
    Сохраняет документа для сообщения чата.

    :param session: AsyncSession SQLAlchemy
    :param message_id: ID сообщения (ChatMessage.id)
    :param file_id: Telegram file_id документа
    :return: созданный объект ChatDocument
    """
    document = ChatDocument(chat_id=message_id, document_url=file_id)
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


async def get_last_messages(session: AsyncSession, chat_id: int, limit: int = 15):
    """
    Возвращает последние сообщения чата с фото, видео, стикерами, аудио, голосовыми и документами.
    """
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    messages = result.unique().scalars().all()

    messages_list = []
    for msg in reversed(messages):  # от старых к новым
        # Фото
        photos_result = await session.execute(
            select(ChatPhoto.photo_url).where(ChatPhoto.chat_id == msg.id)
        )
        photos = [p[0] for p in photos_result.all()]

        # Видео
        videos_result = await session.execute(
            select(ChatVideo.video_url).where(ChatVideo.chat_id == msg.id)
        )
        videos = [v[0] for v in videos_result.all()]

        # Стикеры
        stickers_result = await session.execute(
            select(ChatSticker.sticker_url).where(ChatSticker.chat_id == msg.id)
        )
        stickers = [s[0] for s in stickers_result.all()]

        # Аудио
        audios_result = await session.execute(
            select(ChatAudio.audio_url).where(ChatAudio.chat_id == msg.id)
        )
        audios = [a[0] for a in audios_result.all()]

        # Голосовые
        voices_result = await session.execute(
            select(ChatVoice.voice_url).where(ChatVoice.chat_id == msg.id)
        )
        voices = [v[0] for v in voices_result.all()]

        # Документы
        documents_result = await session.execute(
            select(ChatDocument.document_url).where(ChatDocument.chat_id == msg.id)
        )
        documents = [d[0] for d in documents_result.all()]

        messages_list.append(
            {
                "text": msg.text,
                "sender_id": msg.sender_id,
                "photos": photos,
                "videos": videos,
                "stickers": stickers,
                "audios": audios,
                "voices": voices,
                "documents": documents,
            }
        )

    return messages_list


async def mark_chat_as_inactive(
    session: AsyncSession,
    chat_id: int,
) -> Chat | None:
    """
    Помечает чат как неактивный.
    Возвращает обновленный объект Chat или None, если чат не найден.
    """
    chat = await session.get(Chat, chat_id)  # Получаем объект Chat по ID
    if not chat:
        return None

    chat.is_active = False
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    return chat
