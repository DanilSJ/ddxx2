import json
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .config import settings
from rovmarket_bot.core.models import Categories
from rovmarket_bot.core.models import Product, ProductPhoto

redis_cache = Redis.from_url(settings.REDIS_URL, decode_responses=True)

CACHE_TIMEOUT = 600


async def check_rate_limit(
    user_telegram_id: int,
    action_key: str,
    *,
    limit: int = 3,
    window_seconds: int = 3,
) -> tuple[bool, int]:
    """Rate limiter with fixed cooldown lock.

    - Allows up to `limit` hits within `window_seconds`.
    - When limit exceeded, sets a lock for exactly `window_seconds`.
      During lock, all requests are denied and a remaining TTL is returned.

    Returns (allowed, retry_after_seconds).
    """
    counter_key = f"rl:{user_telegram_id}:{action_key}:cnt"
    lock_key = f"rl:{user_telegram_id}:{action_key}:lock"
    try:
        # If locked – deny with remaining TTL (fixed cooldown)
        ttl = await redis_cache.ttl(lock_key)
        if ttl is not None and ttl > 0:
            return False, int(ttl)

        # Count within window
        current = await redis_cache.incr(counter_key)
        if current == 1:
            await redis_cache.expire(counter_key, window_seconds)

        if current > limit:
            # Set fixed cooldown and reset counter
            await redis_cache.set(lock_key, "1", ex=window_seconds)
            await redis_cache.delete(counter_key)
            return False, window_seconds

        return True, 0
    except Exception:
        # On Redis issues, fail-open
        return True, 0


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

    # Если кэш отсутствует, получаем данные из базы
    stmt = (
        select(Product.id)
        .where(Product.publication == True)
        .order_by(Product.id.desc())
    )
    result = await session.execute(stmt)
    product_ids = [str(row[0]) for row in result.all()]  # ID как строки

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
    ).where(Product.id.in_([int(pid) for pid in product_ids]))
    result = await session.execute(stmt)
    products_data = result.all()

    stmt = select(ProductPhoto).where(
        ProductPhoto.product_id.in_([int(pid) for pid in product_ids])
    )
    result = await session.execute(stmt)
    photos = result.scalars().all()

    photos_map = {}
    for photo in photos:
        photos_map.setdefault(str(photo.product_id), []).append(photo.photo_url)

    display_data = {
        "product_ids": product_ids,
        "products": {},
        "photos": {},
    }

    for product_row in products_data:
        product_id, name, description, price, contact, geo, created_at = product_row
        product_id = str(product_id)

        product_data = {
            "name": name or "Без названия",
            "description": description or "Без описания",
            "price": price or "договорная",
            "contact": contact or "-",
            "geo": geo or None,
            "created_at": created_at.isoformat() if created_at else None,
        }
        display_data["products"][product_id] = product_data

    for pid in product_ids:
        display_data["photos"][pid] = photos_map.get(pid, [])

    # Сохраняем заново в кэш (восстанавливаем)
    try:
        json_data = json.dumps(display_data)
        await redis_cache.set(
            cache_key, json_data, ex=CACHE_TIMEOUT
        )  # или без ex, если не хочешь TTL
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
