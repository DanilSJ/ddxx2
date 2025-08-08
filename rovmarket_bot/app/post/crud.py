from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis.asyncio import Redis
from rovmarket_bot.core.models import Product, ProductPhoto, User, Categories
from rovmarket_bot.core.cache import invalidate_all_ads_cache
from rovmarket_bot.app.settings.crud import get_or_create_bot_settings
from rovmarket_bot.core.logger import get_component_logger

redis = Redis.from_url("redis://localhost:6379", decode_responses=True)
logger = get_component_logger("post")


async def index_product_to_redis(product: Product):
    redis_key = f"product:{product.id}"

    data = {
        "name": product.name,
        "description": product.description or "",
        "price": product.price if product.price is not None else 0,
    }

    await redis.hset(redis_key, mapping=data)


async def create_product(
    telegram_id: int,
    username: str | None,
    data: dict,
    session: AsyncSession,
) -> Product:
    # Найти или создать пользователя
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalars().first()
    if not user:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    # Найти категорию
    result = await session.execute(
        select(Categories).where(Categories.name == data["category"])
    )
    category = result.scalars().first()
    if not category:
        logger.error(
            "Category not found while creating product (telegram_id=%s, category=%s)",
            telegram_id,
            data.get("category"),
        )
        raise ValueError("Категория не найдена")

    # Подготовка геоданных в формате JSON
    geo_data = None
    if isinstance(data.get("geo"), dict):
        lat = data["geo"].get("latitude")
        lon = data["geo"].get("longitude")
        if lat is not None and lon is not None:
            geo_data = {"latitude": lat, "longitude": lon}

    # Определяем режим модерации
    settings_row = await get_or_create_bot_settings(session)
    publication_value = True if not bool(settings_row.moderation) else None

    # Создание продукта
    product = Product(
        name=data["name"],
        description=data["description"],
        user_id=user.id,
        category_id=category.id,
        price=None if data["price"] == "Договорная цена" else int(data["price"]),
        contact=data["contact"],
        geo=geo_data,
        publication=publication_value,
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    await index_product_to_redis(product)
    logger.info("Product persisted id=%s for user_id=%s", product.id, user.id)

    # Добавление фотографий
    for file_id in data.get("photos", []):
        session.add(ProductPhoto(product_id=product.id, photo_url=file_id))

    await session.commit()
    await invalidate_all_ads_cache()
    return product


async def get_categories_page(session: AsyncSession, page: int = 1, limit: int = 10):
    offset = (page - 1) * limit
    stmt = select(Categories).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()
