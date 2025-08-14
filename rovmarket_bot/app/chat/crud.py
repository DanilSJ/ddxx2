from rovmarket_bot.core.models import (
    db_helper,
    Chat,
    ChatMessage,
    User,
    Product,
    ChatPhoto,
)
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List


async def create_or_get_chat(
    session: AsyncSession, product_id: int, buyer_id: int, seller_id: int
) -> Chat:
    stmt = select(Chat).where(
        Chat.product_id == product_id,
        Chat.buyer_id == buyer_id,
        Chat.seller_id == seller_id,
        Chat.is_active.is_(True),
    )
    result = await session.execute(stmt)
    chat = result.scalars().first()
    if chat:
        return chat
    chat = Chat(product_id=product_id, buyer_id=buyer_id, seller_id=seller_id)
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
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
