from redis.asyncio import Redis
from redis.commands.search.query import Query
from sqlalchemy import select

from .crud import (
    get_photos_for_products,
    get_fields_for_products,
    get_publication_for_products,
)
from sqlalchemy.ext.asyncio import AsyncSession
from rovmarket_bot.core.config import settings
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.field import TextField, NumericField

from ...core.models import Product

REDIS_INDEX = "products"  # имя индекса

redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def search_in_redis(text: str, session: AsyncSession, limit: int = 10):
    """Поиск в Redis"""
    return await search_in_redis_original(text, session, limit)


from re import findall


async def search_in_redis_original(text: str, session: AsyncSession, limit: int = 10):
    try:
        print(f"\n🔍 Поисковый текст: {text}")

        # Ищем все числа в тексте для поиска по цене
        numbers = findall(r"\d+", text)
        print(f"🔢 Найденные числа в тексте: {numbers}")

        # Формируем часть запроса для price, если есть числа
        price_query = ""
        if numbers:
            price_ranges = " | ".join([f"@price:[{num} {num}]" for num in numbers])
            price_query = f" | {price_ranges}"
        print(f"💰 Price query: {price_query}")

        # Основной запрос по name и description + price
        query_str = f"@name:{text} | @description:{text}{price_query}"
        print(f"🔧 Итоговый RedisSearch запрос: {query_str}")

        query = Query(query_str).paging(0, limit)
        result = await redis.ft(REDIS_INDEX).search(query)

        print(f"📄 Найдено документов в Redis: {len(result.docs)}")

        docs = [doc.__dict__ for doc in result.docs]

        # Получение product_ids из redis id
        product_ids = []
        for doc in docs:
            redis_id = doc.get("id")
            if redis_id and ":" in redis_id:
                try:
                    product_ids.append(int(redis_id.split(":")[1]))
                except Exception as e:
                    print(f"⚠️ Ошибка извлечения ID из {redis_id}: {e}")
                    continue

        print(f"🆔 Полученные product_ids из Redis: {product_ids}")
        if not product_ids:
            print("🚫 Нет product_ids — ничего не возвращаем.")
            await restore_redis_data(session)
            return []

        publication_map = await get_publication_for_products(product_ids, session)
        filtered_product_ids = [pid for pid in product_ids if publication_map.get(pid)]
        print(f"✅ Отфильтрованные опубликованные product_ids: {filtered_product_ids}")

        if not filtered_product_ids:
            print("🚫 Нет опубликованных объявлений.")
            return []

        photos_map = await get_photos_for_products(filtered_product_ids, session)
        fields_map = await get_fields_for_products(filtered_product_ids, session)

        filtered_docs = []
        for doc in docs:
            redis_id = doc.get("id")
            pid = None
            if redis_id and ":" in redis_id:
                try:
                    pid = int(redis_id.split(":")[1])
                except Exception:
                    continue

            if pid not in filtered_product_ids:
                continue

            doc["photos"] = photos_map.get(pid, [])
            fields = fields_map.get(pid, {})
            doc["contact"] = fields.get("contact")
            doc["geo"] = fields.get("geo")
            doc["created_at"] = fields.get("created_at")

            filtered_docs.append(doc)

        print(f"📦 Возвращаем {len(filtered_docs)} документов.")
        return filtered_docs

    except Exception as e:
        print("❌ RedisSearch error:", e)
        return []


async def index_product_in_redis(product):
    # Примерная структура, зависит от того, как у тебя устроен индекс
    # Redisearch document ID: "product:<id>"
    doc_id = f"product:{product.id}"
    await redis.hset(
        doc_id,
        mapping={
            "name": product.name or "",
            "description": product.description or "",
            "price": str(product.price) if product.price else "0",
            # Добавь другие поля, если нужно
        },
    )


async def restore_redis_data(session: AsyncSession):
    # Получаем все опубликованные продукты из БД
    stmt = select(Product).where(Product.publication == True)
    result = await session.execute(stmt)
    products = result.unique().scalars().all()

    for product in products:
        key = f"product:{product.id}"
        # Записываем в Redis Hash
        await redis.hset(
            key,
            mapping={
                "name": product.name or "",
                "description": product.description or "",
                "price": str(product.price) if product.price else "0",
            },
        )
    # После этого RedisSearch должен индексировать эти хеши автоматически


async def ensure_redis_index():
    try:
        await redis.ft("products").info()
    except Exception:
        await redis.ft("products").create_index(
            [
                TextField("name"),
                TextField("description"),
                NumericField("price"),
            ],
            definition=IndexDefinition(prefix=["product:"], index_type=IndexType.HASH),
        )
