import json
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .config import settings
from rovmarket_bot.core.models import Categories
from rovmarket_bot.core.models import Product, ProductPhoto

redis_cache = Redis.from_url(settings.REDIS_URL, decode_responses=True)

CACHE_TIMEOUT = 60 * 60  # 1 час


async def get_categories_page_cached(
    session: AsyncSession, page: int = 1, limit: int = 10
):
    cache_key = f"categories_page:{page}:{limit}"
    cached_data = await redis_cache.get(cache_key)

    if cached_data:
        return [Categories(**item) for item in json.loads(cached_data)]

    offset = (page - 1) * limit
    stmt = select(Categories).offset(offset).limit(limit)
    result = await session.execute(stmt)
    categories = result.scalars().all()

    if categories:
        to_cache = [dict(id=c.id, name=c.name) for c in categories]
        await redis_cache.set(cache_key, json.dumps(to_cache), ex=CACHE_TIMEOUT)
    return categories


async def get_all_ads_cached(session: AsyncSession) -> dict:
    cache_key = "all_ads_display_data"
    cached_data = await redis_cache.get(cache_key)

    if cached_data:
        return json.loads(cached_data)

    stmt = select(Product.id).order_by(Product.id.desc())
    result = await session.execute(stmt)
    product_ids = [row[0] for row in result.all()]

    if not product_ids:
        return {"product_ids": [], "products": {}, "photos": {}}

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

    # Получаем фотографии для всех продуктов
    stmt = select(ProductPhoto).where(ProductPhoto.product_id.in_(product_ids))
    result = await session.execute(stmt)
    photos = result.scalars().all()

    # Группируем фотографии по продуктам
    photos_map = {}
    for photo in photos:
        photos_map.setdefault(photo.product_id, []).append(photo.photo_url)

    display_data = {
        "product_ids": [str(pid) for pid in product_ids],
        "products": {},
        "photos": {},
    }

    for product_row in products_data:
        product_id, name, description, price, contact, geo, created_at = product_row

        # Проверяем, что данные не None
        product_data = {
            "name": name or "Без названия",
            "description": description or "Без описания",
            "price": price or "договорная",
            "contact": contact or "-",
            "geo": geo or None,
            "created_at": created_at.isoformat() if created_at else None,
        }
        display_data["products"][product_id] = product_data

    # Проверяем данные перед сохранением
    if display_data["products"]:
        first_product_id = list(display_data["products"].keys())[0]
        first_product = display_data["products"][first_product_id]

    # Кэшируем данные
    try:
        json_data = json.dumps(display_data)
        await redis_cache.set(cache_key, json_data, ex=CACHE_TIMEOUT)
    except Exception as e:
        print(f"❌ Ошибка при сохранении в кэш: {e}")

    return display_data


async def invalidate_all_ads_cache():
    """Инвалидация кэша всех объявлений"""
    await redis_cache.delete("all_ads_display_data")


async def invalidate_categories_cache():
    """Инвалидация кэша категорий"""
    keys = await redis_cache.keys("categories_page:*")
    if keys:
        await redis_cache.delete(*keys)


async def invalidate_cache_on_new_ad():
    """Инвалидация кэша при добавлении нового объявления"""
    await invalidate_all_ads_cache()
    await invalidate_categories_cache()


async def clear_all_cache():
    """Полная очистка всего кэша"""
    try:
        all_keys = await redis_cache.keys("*")
        if all_keys:
            await redis_cache.delete(*all_keys)

    except Exception as e:
        print(f"❌ Ошибка при полной очистке кэша: {e}")


async def show_cache_stats():
    """Показать статистику кэша"""
    try:
        all_keys = await redis_cache.keys("*")
        ads_keys = await redis_cache.keys("all_ads_display_data")
        categories_keys = await redis_cache.keys("categories_page:*")
        search_keys = await redis_cache.keys("search_results:*")

        return {
            "total": len(all_keys),
            "ads": len(ads_keys),
            "categories": len(categories_keys),
            "search": len(search_keys),
        }
    except Exception as e:
        print(f"❌ Ошибка при получении статистики кэша: {e}")
        return None
