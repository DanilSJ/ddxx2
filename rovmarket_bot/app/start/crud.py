from sqlalchemy.ext.asyncio import AsyncSession
from rovmarket_bot.core.models.user import User

async def add_user(telegram_id: int, session: AsyncSession) -> User:
    user = User(telegram_id=telegram_id)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user