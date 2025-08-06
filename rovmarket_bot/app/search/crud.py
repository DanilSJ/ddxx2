from rovmarket_bot.core.models import ProductPhoto, db_helper, Product, Categories
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

async def get_photos_for_products(product_ids: list[int], session: AsyncSession) -> dict[int, list[str]]:
    if not product_ids:
        return {}
    stmt = select(ProductPhoto).where(ProductPhoto.product_id.in_(product_ids))
    result = await session.execute(stmt)
    photos = result.scalars().all()
    photo_map = {}
    for photo in photos:
        photo_map.setdefault(photo.product_id, []).append(photo.photo_url)
    return photo_map

async def get_fields_for_products(product_ids: list[int], session: AsyncSession) -> dict[int, dict]:
    if not product_ids:
        return {}
    stmt = select(Product).where(Product.id.in_(product_ids))
    result = await session.execute(stmt)
    products = result.unique().scalars().all()
    fields_map = {}
    for product in products:
        fields_map[product.id] = {
            'name': product.name,
            'description': product.description,
            'price': product.price,
            'contact': product.contact,
            'geo': product.geo,
            'created_at': product.created_at,
        }
    return fields_map

async def get_product_by_id(product_id: int, session: AsyncSession) -> dict | None:
    stmt = select(Product).where(Product.id == product_id)
    result = await session.execute(stmt)
    product = result.unique().scalar_one_or_none()
    if not product:
        return None
    return {
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'contact': product.contact,
        'geo': product.geo,
        'created_at': product.created_at,
        'photos': [photo.photo_url for photo in product.photos],
    }

async def get_all_product_ids(session: AsyncSession) -> list[int]:
    stmt = select(Product.id).order_by(Product.id.desc())
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]

async def get_categories_page(session: AsyncSession, page: int = 1, limit: int = 10):
    """Получить страницу категорий"""
    offset = (page - 1) * limit
    stmt = select(Categories).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()

async def get_products_by_category(session: AsyncSession, category_name: str, page: int = 1, limit: int = 10) -> list[int]:
    """Получить ID товаров по категории с пагинацией"""
    offset = (page - 1) * limit
    stmt = (
        select(Product.id)
        .join(Categories, Product.category_id == Categories.id)
        .where(Categories.name == category_name)
        .order_by(Product.id.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]

async def get_total_products_by_category(session: AsyncSession, category_name: str) -> int:
    """Получить общее количество товаров в категории"""
    from sqlalchemy import func
    stmt = (
        select(func.count(Product.id))
        .join(Categories, Product.category_id == Categories.id)
        .where(Categories.name == category_name)
    )
    result = await session.execute(stmt)
    return result.scalar()
