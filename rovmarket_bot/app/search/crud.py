from sqlalchemy import func

from rovmarket_bot.core.models import (
    ProductView,
    ProductPhoto,
    db_helper,
    Product,
    Categories,
    User,
)
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from rovmarket_bot.core.cache import get_categories_page_cached, get_all_ads_cached


async def get_photos_for_products(
    product_ids: list[int], session: AsyncSession
) -> dict[int, list[str]]:
    if not product_ids:
        return {}
    stmt = select(ProductPhoto).where(ProductPhoto.product_id.in_(product_ids))
    result = await session.execute(stmt)
    photos = result.scalars().all()
    photo_map = {}
    for photo in photos:
        photo_map.setdefault(photo.product_id, []).append(photo.photo_url)
    return photo_map


async def get_fields_for_products(
    product_ids: list[int], session: AsyncSession
) -> dict[int, dict]:
    if not product_ids:
        return {}
    stmt = select(
        Product.id,
        Product.name,
        Product.description,
        Product.price,
        Product.contact,
        Product.geo,
        Product.created_at,
    ).where(Product.id.in_(product_ids))
    result = await session.execute(stmt)
    products_data = result.all()
    fields_map = {}
    for product_row in products_data:
        product_id, name, description, price, contact, geo, created_at = product_row
        fields_map[product_id] = {
            "name": name,
            "description": description,
            "price": price,
            "contact": contact,
            "geo": geo,
            "created_at": created_at,
        }
    return fields_map


async def get_product_by_id(product_id: int, session: AsyncSession) -> dict | None:
    stmt = select(
        Product.id,
        Product.name,
        Product.description,
        Product.price,
        Product.contact,
        Product.geo,
        Product.created_at,
    ).where(Product.id == product_id, Product.publication.is_(True))
    result = await session.execute(stmt)
    product_row = result.first()
    if not product_row:
        return None

    product_id, name, description, price, contact, geo, created_at = product_row

    stmt = select(ProductPhoto.photo_url).where(ProductPhoto.product_id == product_id)
    result = await session.execute(stmt)
    photos = [row[0] for row in result.all()]

    return {
        "id": product_id,
        "name": name,
        "description": description,
        "price": price,
        "contact": contact,
        "geo": geo,
        "created_at": created_at,
        "photos": photos,
    }


async def get_all_product_ids(session: AsyncSession) -> list[int]:
    stmt = select(Product.id).order_by(Product.id.desc())
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def get_categories_page(session: AsyncSession, page: int = 1, limit: int = 10):
    """Получить страницу категорий (использует кэш)"""
    return await get_categories_page_cached(session, page, limit)


async def get_products_by_category(
    session: AsyncSession, category_name: str, page: int = 1, limit: int = 10
) -> list[int]:
    offset = (page - 1) * limit
    stmt = (
        select(Product.id)
        .join(Categories, Product.category_id == Categories.id)
        .where(
            Categories.name == category_name,
            Product.publication.is_(True),
        )
        .order_by(Product.id.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def get_total_products_by_category(
    session: AsyncSession, category_name: str
) -> int:

    stmt = (
        select(func.count(Product.id))
        .join(Categories, Product.category_id == Categories.id)
        .where(Categories.name == category_name)
    )
    result = await session.execute(stmt)
    return result.scalar()


async def get_all_ads_data(session: AsyncSession) -> dict:
    return await get_all_ads_cached(session)


async def get_publication_for_products(
    product_ids: list[int], session: AsyncSession
) -> dict[int, bool]:
    """Получить словарь product_id -> publication (bool)"""
    if not product_ids:
        return {}
    stmt = select(Product.id, Product.publication).where(Product.id.in_(product_ids))
    result = await session.execute(stmt)

    return {pid: pub for pid, pub in result.all()}


async def get_products_by_category_filtered(
    session: AsyncSession,
    category_name: str,
    *,
    page: int = 1,
    limit: int = 10,
    sort: str | None = None,  # 'new' | 'old'
    price_min: int | None = None,
    price_max: int | None = None,
) -> list[int]:
    offset = (page - 1) * limit
    stmt = (
        select(Product.id)
        .join(Categories, Product.category_id == Categories.id)
        .where(
            Categories.name == category_name,
            Product.publication.is_(True),
        )
    )
    if price_min is not None:
        stmt = stmt.where(Product.price.is_(None) | (Product.price >= price_min))
    if price_max is not None:
        stmt = stmt.where(Product.price.is_(None) | (Product.price <= price_max))

    if sort == "old":
        stmt = stmt.order_by(Product.id.asc())
    else:
        stmt = stmt.order_by(Product.id.desc())

    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def get_total_products_by_category_filtered(
    session: AsyncSession,
    category_name: str,
    *,
    price_min: int | None = None,
    price_max: int | None = None,
) -> int:
    stmt = (
        select(func.count(Product.id))
        .join(Categories, Product.category_id == Categories.id)
        .where(
            Categories.name == category_name,
            Product.publication.is_(True),
        )
    )
    if price_min is not None:
        stmt = stmt.where(Product.price.is_(None) | (Product.price >= price_min))
    if price_max is not None:
        stmt = stmt.where(Product.price.is_(None) | (Product.price <= price_max))

    result = await session.execute(stmt)
    return result.scalar()


async def get_user_id_by_telegram_id(
    telegram_id: int, session: AsyncSession
) -> int | None:
    stmt = select(User.id).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    row = result.first()
    return row[0] if row else None


async def add_product_view(product_id: int, user_id: int, session: AsyncSession):
    stmt = select(Product).where(Product.id == product_id)
    result = await session.execute(stmt)
    product = result.scalars().unique().one_or_none()

    if not product:
        return  # товара нет

    if product.user_id == user_id:
        return  # владелец товара — не добавляем просмотр

    # Проверка: уже есть просмотр?
    stmt = select(ProductView).where(
        ProductView.product_id == product_id,
        ProductView.user_id == user_id,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        return  # уже просмотрено

    # Создаем просмотр
    view = ProductView(product_id=product_id, user_id=user_id)
    session.add(view)
    await session.commit()
