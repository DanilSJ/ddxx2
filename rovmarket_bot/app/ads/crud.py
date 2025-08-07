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
            selectinload(Product.user)
        )
        .join(User)
        .where(User.telegram_id == telegram_id)
        .order_by(Product.created_at.desc())
    )
    
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_user_products_paginated(
    telegram_id: int, 
    session: AsyncSession, 
    page: int = 1, 
    limit: int = 5
):
    """Получить объявления пользователя с пагинацией"""
    offset = (page - 1) * limit
    
    stmt = (
        select(Product)
        .options(
            selectinload(Product.photos),
            selectinload(Product.category),
            selectinload(Product.user)
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
        select(func.count(Product.id))
        .join(User)
        .where(User.telegram_id == telegram_id)
    )
    
    result = await session.execute(stmt)
    return result.scalar()
