from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from rovmarket_bot.core.models import Product, ProductPhoto, User, Categories


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
) -> bool:
    """Опубликовать объявление: установить publication=NULL только для владельца.

    Возвращает True, если статус был обновлён, иначе False (не найдено или уже опубликовано).
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
        return False

    if product.publication is None:
        return False

    product.publication = None
    await session.commit()
    return True


async def get_user_product_with_photos(
    product_id: int, telegram_id: int, session: AsyncSession
) -> Product | None:
    """Получить объявление пользователя по id с фотографиями."""
    stmt = (
        select(Product)
        .options(selectinload(Product.photos))
        .join(User)
        .where(Product.id == product_id, User.telegram_id == telegram_id)
        .limit(1)
    )

    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()
