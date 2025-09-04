from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Sequence
from rovmarket_bot.core.models.advertisement import Advertisement, AdMedia
from datetime import datetime, timedelta
from rovmarket_bot.core.models.settings import BotSettings


def _calc_ends_at(starts_at: datetime, duration: str) -> datetime:
    if duration == "day":
        return starts_at + timedelta(days=1)
    if duration == "week":
        return starts_at + timedelta(weeks=1)
    if duration == "month":
        # простая эвристика в 30 дней
        return starts_at + timedelta(days=30)
    return starts_at + timedelta(days=1)


async def create_advertisement(
    session: AsyncSession,
    *,
    text: str,
    ad_type: str,
    duration: str,
    pinned: bool = False,
    periodicity: int = 1,
    starts_at: datetime | None = None,
) -> Advertisement:
    now = starts_at or datetime.utcnow()
    ad = Advertisement(
        text=text,
        ad_type=ad_type,
        duration=duration,
        pinned=pinned,
        periodicity=periodicity,
        starts_at=now,
        ends_at=_calc_ends_at(now, duration),
        active=True,
    )
    session.add(ad)
    await session.flush()
    return ad


async def add_ad_photos(
    session: AsyncSession, *, advertisement_id: int, file_ids: Sequence[str]
) -> list[AdMedia]:
    rows: list[AdMedia] = []
    for fid in file_ids:
        row = AdMedia(advertisement_id=advertisement_id, file_id=fid, media_type="photo")
        session.add(row)
        rows.append(row)
    await session.flush()
    return rows


async def add_ad_media(
    session: AsyncSession, *, advertisement_id: int, media_items: list[tuple[str, str]]
) -> list[AdMedia]:
    """Add media files (photos and videos) to advertisement"""
    rows: list[AdMedia] = []
    for file_id, media_type in media_items:
        row = AdMedia(
            advertisement_id=advertisement_id, 
            file_id=file_id,
            media_type=media_type  # 'photo' or 'video'
        )
        session.add(row)
        rows.append(row)
    await session.flush()
    return rows


async def get_active_ads_by_type(
    session: AsyncSession,
    *,
    ad_type: str,
    now: datetime | None = None,
    oldest_first: bool = False,
) -> list[Advertisement]:
    now = now or datetime.utcnow()
    order_col = Advertisement.created_at.asc() if oldest_first else Advertisement.created_at.desc()
    stmt = (
        select(Advertisement)
        .where(Advertisement.ad_type == ad_type)
        .where(Advertisement.active == True)
        .where(Advertisement.starts_at <= now)
        .where((Advertisement.ends_at.is_(None)) | (Advertisement.ends_at >= now))
        .options(selectinload(Advertisement.media))
        .order_by(order_col)
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def deactivate_ad(session: AsyncSession, *, ad_id: int) -> None:
    ad = await session.get(Advertisement, ad_id)
    if not ad:
        return
    ad.active = False
    await session.flush()


async def get_next_menu_ad(session: AsyncSession) -> Advertisement | None:
    """Return next active 'menu' ad in a circular order, advancing pointer in BotSettings."""
    # Newest first
    ads = await get_active_ads_by_type(session, ad_type="menu", oldest_first=False)
    if not ads:
        return None
    settings = await session.get(BotSettings, 1)
    if not settings:
        settings = BotSettings()
        session.add(settings)
        await session.flush()
    idx = settings.menu_ad_index % len(ads)
    ad = ads[idx]
    # advance and reset pointer explicitly when full cycle completes
    if settings.menu_ad_index + 1 >= len(ads):
        settings.menu_ad_index = 0
    else:
        settings.menu_ad_index = settings.menu_ad_index + 1
    await session.flush()
    return ad


async def get_active_broadcast_ads(session: AsyncSession) -> list[Advertisement]:
    # Newest first across both kinds
    return await get_active_ads_by_type(
        session, ad_type="broadcast", oldest_first=False
    ) + await get_active_ads_by_type(session, ad_type="broadcast_pinned", oldest_first=False)


async def get_next_broadcast_ad(session: AsyncSession) -> Advertisement | None:
    """Return next active broadcast ad (including pinned) in a circular order."""
    ads = await get_active_broadcast_ads(session)
    if not ads:
        return None
    settings = await session.get(BotSettings, 1)
    if not settings:
        settings = BotSettings()
        session.add(settings)
        await session.flush()
    idx = (settings.broadcast_ad_index or 0) % len(ads)
    ad = ads[idx]
    if (settings.broadcast_ad_index or 0) + 1 >= len(ads):
        settings.broadcast_ad_index = 0
    else:
        settings.broadcast_ad_index = (settings.broadcast_ad_index or 0) + 1
    await session.flush()
    return ad


async def get_next_listings_ad(session: AsyncSession) -> Advertisement | None:
    """Return next active 'listings' ad in circular order and advance pointer."""
    # Newest first
    ads = await get_active_ads_by_type(session, ad_type="listings", oldest_first=False)
    if not ads:
        return None
    settings = await session.get(BotSettings, 1)
    if not settings:
        settings = BotSettings()
        session.add(settings)
        await session.flush()
    idx = (settings.listings_ad_index or 0) % len(ads)
    ad = ads[idx]
    if (settings.listings_ad_index or 0) + 1 >= len(ads):
        settings.listings_ad_index = 0
    else:
        settings.listings_ad_index = (settings.listings_ad_index or 0) + 1
    await session.flush()
    return ad

