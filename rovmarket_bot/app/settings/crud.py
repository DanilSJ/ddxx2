from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from rovmarket_bot.core.models import User, Categories, UserCategoryNotification


async def get_user_with_subscriptions(
    telegram_id: int, session: AsyncSession
) -> User | None:
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    return result.scalars().first()


async def get_categories_page(session: AsyncSession, page: int = 1, limit: int = 10):
    offset = (page - 1) * limit
    stmt = select(Categories).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


async def is_user_subscribed_to_category(
    telegram_id: int, category_id: int, session: AsyncSession
) -> bool:
    stmt = (
        select(UserCategoryNotification)
        .join(User, User.id == UserCategoryNotification.user_id)
        .where(
            User.telegram_id == telegram_id,
            UserCategoryNotification.category_id == category_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalars().first() is not None


async def toggle_category_subscription(
    telegram_id: int, category_id: int, session: AsyncSession
) -> bool:
    """Toggle subscription. Returns True if now subscribed, False if unsubscribed."""
    # fetch user id
    stmt_user = select(User).where(User.telegram_id == telegram_id)
    result_user = await session.execute(stmt_user)
    user = result_user.scalars().first()
    if user is None:
        user = User(telegram_id=telegram_id, username=None)
        session.add(user)
        await session.flush()

    # check current
    stmt = select(UserCategoryNotification).where(
        UserCategoryNotification.user_id == user.id,
        UserCategoryNotification.category_id == category_id,
    )
    result = await session.execute(stmt)
    existing = result.scalars().first()
    if existing:
        await session.delete(existing)
        await session.commit()
        return False
    else:
        link = UserCategoryNotification(user_id=user.id, category_id=category_id)
        session.add(link)
        await session.commit()
        return True
