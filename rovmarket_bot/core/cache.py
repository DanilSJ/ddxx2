import json
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .config import settings
from rovmarket_bot.core.models import Categories

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

    # Кэшируем только если есть данные
    if categories:
        # сериализация
        to_cache = [dict(id=c.id, name=c.name) for c in categories]
        await redis_cache.set(cache_key, json.dumps(to_cache), ex=CACHE_TIMEOUT)

    return categories
