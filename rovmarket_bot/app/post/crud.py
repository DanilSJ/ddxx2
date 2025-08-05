from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from rovmarket_bot.core.models import Product, ProductPhoto, User, Categories


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
        raise ValueError("Категория не найдена")

    # Подготовка геоданных в формате JSON
    geo_data = None
    if isinstance(data.get("geo"), dict):
        lat = data["geo"].get("latitude")
        lon = data["geo"].get("longitude")
        if lat is not None and lon is not None:
            geo_data = {"latitude": lat, "longitude": lon}

    # Создание продукта
    product = Product(
        name=data["name"],
        description=data["description"],
        user_id=user.id,
        category_id=category.id,
        price=None if data["price"] == "Договорная цена" else int(data["price"]),
        contact=data["contact"],
        geo=geo_data,
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)

    # Добавление фотографий
    for file_id in data.get("photos", []):
        session.add(ProductPhoto(product_id=product.id, photo_url=file_id))

    await session.commit()
    return product


async def get_categories_page(session: AsyncSession, page: int = 1, limit: int = 10):
    offset = (page - 1) * limit
    stmt = select(Categories).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()
