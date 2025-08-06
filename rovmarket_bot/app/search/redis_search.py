from redis.asyncio import Redis
from redis.commands.search.query import Query
from .crud import get_photos_for_products, get_fields_for_products
from sqlalchemy.ext.asyncio import AsyncSession

REDIS_INDEX = "products"  # имя индекса

redis = Redis.from_url("redis://localhost:6379", decode_responses=True)


async def search_in_redis(text: str, session: AsyncSession, limit: int = 10):
    try:
        query = Query(f"@name:{text} | @description:{text}").paging(0, limit)
        result = await redis.ft(REDIS_INDEX).search(query)
        docs = [doc.__dict__ for doc in result.docs]
        # Получаем product_ids из Redis
        product_ids = []
        for doc in docs:
            # id может быть в виде 'product:123', нужно извлечь число
            redis_id = doc.get('id')
            if redis_id and ':' in redis_id:
                try:
                    product_ids.append(int(redis_id.split(':')[1]))
                except Exception:
                    continue
        # Получаем фото из базы
        photos_map = await get_photos_for_products(product_ids, session)
        # Получаем contact, geo, created_at из базы
        fields_map = await get_fields_for_products(product_ids, session)
        # Добавляем фото и поля к результатам
        for doc in docs:
            redis_id = doc.get('id')
            pid = None
            if redis_id and ':' in redis_id:
                try:
                    pid = int(redis_id.split(':')[1])
                except Exception:
                    continue
            doc['photos'] = photos_map.get(pid, [])
            fields = fields_map.get(pid, {})
            doc['contact'] = fields.get('contact')
            doc['geo'] = fields.get('geo')
            doc['created_at'] = fields.get('created_at')
        return docs
    except Exception as e:
        print("RedisSearch error:", e)
        return []
