from rovmarket_bot.core.models import ProductPhoto, db_helper, Product
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
            'contact': product.contact,
            'geo': product.geo,
            'created_at': product.created_at,
        }
    return fields_map
