from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from rovmarket_bot.core.models import (
    User,
    Categories,
    UserCategoryNotification,
    BotSettings,
)
from rovmarket_bot.core.logger import apply_logging_configuration


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


# ----- Bot settings (singleton) -----


async def get_or_create_bot_settings(session: AsyncSession) -> BotSettings:
    result = await session.execute(
        select(BotSettings).where(BotSettings.singleton_key == 1)
    )
    settings_row = result.scalars().first()
    if settings_row is None:
        settings_row = BotSettings()  # defaults apply
        session.add(settings_row)
        await session.commit()
        await session.refresh(settings_row)
    return settings_row


async def update_bot_settings(
    session: AsyncSession,
    moderation: bool | None = None,
    logging: bool | None = None,
    notifications_all: bool | None = None,
) -> BotSettings:
    settings_row = await get_or_create_bot_settings(session)

    values: dict = {}
    if moderation is not None:
        values["moderation"] = moderation
    if logging is not None:
        values["logging"] = logging
    if notifications_all is not None:
        values["notifications_all"] = notifications_all  # ✅ добавили

    if values:
        await session.execute(
            update(BotSettings)
            .where(BotSettings.id == settings_row.id)
            .values(**values)
        )
        await session.commit()
        await session.refresh(settings_row)

        # Apply logging changes immediately without restart
        if "logging" in values:
            try:
                apply_logging_configuration(bool(settings_row.logging))
            except Exception:
                # Do not break settings update flow if logger reconfig fails
                pass

    return settings_row
