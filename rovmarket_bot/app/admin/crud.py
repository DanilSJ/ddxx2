from datetime import datetime

from sqlalchemy import func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from rovmarket_bot.core.models import UserCategoryNotification
from rovmarket_bot.core.models.user import User
from rovmarket_bot.core.models.product_view import ProductView
from rovmarket_bot.core.models.complaint import Complaint
from rovmarket_bot.core.models.product import Product
from rovmarket_bot.core.models.advertisement import Advertisement, AdPhoto
from rovmarket_bot.core.models.categories import Categories
from sqlalchemy.future import select

USERS_PER_PAGE = 50
COMPLAINTS_PER_PAGE = 3


async def is_admin(telegram_id: int, session: AsyncSession) -> bool:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id, User.admin == True)
    )
    user = result.scalars().first()
    return user is not None


async def get_admin_users(session: AsyncSession) -> list[User]:
    """Возвращает всех пользователей с правами администратора."""
    result = await session.execute(select(User).where(User.admin == True))
    return list(result.scalars().all())


async def get_all_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User))
    return list(result.scalars().all())


async def get_users_count(session) -> int:
    total = await session.scalar(select(func.count()).select_from(User))
    return total


async def get_users_page(session, page: int):
    offset = (page - 1) * USERS_PER_PAGE
    result = await session.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(USERS_PER_PAGE)
    )
    users = result.scalars().all()
    return users


async def get_users_view_counts(session) -> dict[int, int]:
    result = await session.execute(
        select(ProductView.user_id, func.count()).group_by(ProductView.user_id)
    )
    counts = dict(result.all())
    return counts


# Получить все жалобы с пользователями (связь через user)
async def get_all_complaints(session: AsyncSession):
    result = await session.execute(
        select(Complaint)
        .options(selectinload(Complaint.user))  # <- здесь ключевой момент
        .order_by(Complaint.created_at.desc())
    )
    return result.scalars().all()


# Удалить жалобу по id
async def delete_complaint(session: AsyncSession, complaint_id: int):
    await session.execute(delete(Complaint).where(Complaint.id == complaint_id))
    await session.commit()


async def get_stats_for_period(session: AsyncSession, period_start: datetime):
    # Кол-во пользователей, зарегистрированных с period_start
    users_count = await session.scalar(
        select(func.count()).select_from(User).where(User.created_at >= period_start)
    )

    # Кол-во объявлений, созданных с period_start
    products_count = await session.scalar(
        select(func.count())
        .select_from(Product)
        .where(Product.created_at >= period_start)
    )

    # Пользователь, создавший больше всего объявлений за период
    result = await session.execute(
        select(Product.user_id, func.count(Product.id).label("count"))
        .where(Product.created_at >= period_start)
        .group_by(Product.user_id)
        .order_by(func.count(Product.id).desc())
        .limit(1)
    )
    top_user = result.first()

    return {
        "users_count": users_count or 0,
        "products_count": products_count or 0,
        "top_user_id": top_user.user_id if top_user else None,
        "top_user_products_count": top_user.count if top_user else 0,
    }


async def create_advertisement(
    session,
    text: str,
    photos_file_ids: list[str],
    week=False,
    two_weeks=False,
    month=False,
    periodicity=1,
):
    ad = Advertisement(
        text=text,
        active=True,
        week=week,
        two_weeks=two_weeks,
        month=month,
        periodicity=periodicity,
    )
    session.add(ad)
    await session.flush()  # чтобы получить id

    for file_id in photos_file_ids:
        photo = AdPhoto(advertisement_id=ad.id, file_id=file_id)
        session.add(photo)

    await session.commit()
    return ad


# Получить все неопубликованные объявления (publication IS NULL)
async def get_unpublished_products(session: AsyncSession) -> list[Product]:
    result = await session.execute(
        select(Product)
        .where(Product.publication == None)
        .options(selectinload(Product.photos), selectinload(Product.user))
    )
    return list(result.scalars().all())


# Принять объявление (publication = True)
async def approve_product(session: AsyncSession, product_id: int):
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.unique().scalar_one_or_none()

    if product:
        product.publication = True
        await session.commit()


# Отклонить объявление (publication = False)
async def decline_product(session: AsyncSession, product_id: int) -> Product | None:
    result = await session.execute(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.user))
    )
    product = result.unique().scalar_one_or_none()
    if product:
        product.publication = False
        await session.commit()
    return product


async def get_product_with_photos(
    session: AsyncSession, product_id: int
) -> Product | None:
    result = await session.execute(
        select(Product)
        .where(Product.id == product_id)
        .options(
            selectinload(Product.photos),
            selectinload(Product.user),  # ✅ загружаем user заранее
        )
    )
    return result.unique().scalar_one_or_none()


# Получить объявление по ID с фото и пользователем
async def get_product_with_photos_and_user(
    session: AsyncSession, product_id: int
) -> Product | None:
    result = await session.execute(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.photos), selectinload(Product.user))
    )
    return result.scalar_one_or_none()


async def create_category(
    session: AsyncSession, name: str, description: str
) -> Categories:
    category = Categories(name=name, description=description)
    session.add(category)
    await session.commit()
    return category


async def get_all_categories(session: AsyncSession) -> list[Categories]:
    result = await session.execute(
        select(Categories).order_by(Categories.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_category(session: AsyncSession, category_id: int):
    await session.execute(delete(Categories).where(Categories.id == category_id))
    await session.commit()


async def get_subscriber_telegram_ids_for_category(
    session: AsyncSession, category_id: int, exclude_user_id: int | None = None
) -> list[int]:
    stmt = (
        select(User.telegram_id)
        .join(UserCategoryNotification, User.id == UserCategoryNotification.user_id)
        .where(UserCategoryNotification.category_id == category_id)
        .distinct()
    )
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    result = await session.execute(stmt)
    tg_ids = [row[0] for row in result.all()]
    # Ensure uniqueness at Python level as well
    return list({tg_id for tg_id in tg_ids if tg_id is not None})
