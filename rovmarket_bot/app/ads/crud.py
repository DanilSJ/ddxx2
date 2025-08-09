from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from rovmarket_bot.core.models import Product, User
from rovmarket_bot.app.settings.crud import get_or_create_bot_settings


async def get_user_products(telegram_id: int, session: AsyncSession):
    """Получить все объявления пользователя с фотографиями и категориями"""
    stmt = (
        select(Product)
        .options(
            selectinload(Product.photos),
            selectinload(Product.category),
            selectinload(Product.user),
        )
        .join(User)
        .where(User.telegram_id == telegram_id)
        .order_by(Product.created_at.desc())
    )

    result = await session.execute(stmt)
    return result.scalars().all()


async def get_user_products_paginated(
    telegram_id: int, session: AsyncSession, page: int = 1, limit: int = 5
):
    """Получить объявления пользователя с пагинацией"""
    offset = (page - 1) * limit

    stmt = (
        select(Product)
        .options(
            selectinload(Product.photos),
            selectinload(Product.category),
            selectinload(Product.user),
            selectinload(Product.views),
        )
        .join(User)
        .where(User.telegram_id == telegram_id)
        .order_by(Product.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(stmt)
    return result.scalars().all()


async def get_user_products_count(telegram_id: int, session: AsyncSession):
    """Получить количество объявлений пользователя"""
    from sqlalchemy import func

    stmt = (
        select(func.count(Product.id)).join(User).where(User.telegram_id == telegram_id)
    )

    result = await session.execute(stmt)
    return result.scalar()


async def unpublish_user_product(
    product_id: int, telegram_id: int, session: AsyncSession
) -> bool:
    """Снять объявление с публикации (publication=False) только для владельца.

    Возвращает True, если статус был обновлён, иначе False (не найдено или уже снято).
    """
    # Находим продукт по id, принадлежащий пользователю с данным telegram_id
    stmt = (
        select(Product)
        .options(selectinload(Product.photos))
        .join(User)
        .where(Product.id == product_id, User.telegram_id == telegram_id)
        .limit(1)
    )

    result = await session.execute(stmt)
    product: Product | None = result.unique().scalar_one_or_none()

    if product is None:
        return False

    if product.publication is False:
        return False

    product.publication = False
    await session.commit()
    return True


async def publish_user_product(
    product_id: int, telegram_id: int, session: AsyncSession
) -> Product | None:
    """Опубликовать объявление для владельца.

    Если moderation=False → publication=True (без модерации).
    Если moderation=True → publication=NULL (на модерацию).
    Возвращает обновлённый продукт или None (если не найден/не принадлежит).
    """
    stmt = (
        select(Product)
        .options(selectinload(Product.photos))
        .join(User)
        .where(Product.id == product_id, User.telegram_id == telegram_id)
        .limit(1)
    )

    result = await session.execute(stmt)
    product: Product | None = result.unique().scalar_one_or_none()

    if product is None:
        return None

    # Если уже находится в состоянии ожидания (None) и модерация включена,
    # то нет смысла менять
    settings_row = await get_or_create_bot_settings(session)
    moderation_on = bool(settings_row.moderation)

    if moderation_on:
        # переводим на модерацию (NULL), если ещё не NULL
        if product.publication is None:
            return product
        product.publication = None
    else:
        # публикуем сразу
        if product.publication is True:
            return product
        product.publication = True

    await session.commit()
    await session.refresh(product)
    return product


async def get_user_product_with_photos(
    product_id: int, telegram_id: int, session: AsyncSession
) -> Product | None:
    """Получить объявление пользователя по id с фотографиями."""
    stmt = (
        select(Product)
        .options(
            selectinload(Product.photos),
            selectinload(Product.category),
            selectinload(Product.user),
            selectinload(Product.views),
        )
        .join(User)
        .where(Product.id == product_id, User.telegram_id == telegram_id)
        .limit(1)
    )

    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()
