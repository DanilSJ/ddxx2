from sqlalchemy.ext.asyncio import AsyncSession
from rovmarket_bot.core.models.user import User
from sqlalchemy.future import select


async def add_user(telegram_id: int, username: str | None, session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalars().first()

    if user:
        return user

    user = User(telegram_id=telegram_id, username=username)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
