from sqlalchemy import ForeignKey, String, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from .base import Base


class Advertisement(Base):
    __tablename__ = "advertisement"

    text: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Тип рекламы: broadcast | broadcast_pinned | menu | listings
    ad_type: Mapped[str] = mapped_column(String, default="listings")
    # Период показа: day | week | month (для удобства фильтра)
    duration: Mapped[str] = mapped_column(String, default="day")
    # Временные границы показа
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Флаг закрепления (актуален для рассылки)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    # Частота показа в ленте (для listings), например каждые N показов
    periodicity: Mapped[int] = mapped_column(Integer, default=1)

    # Связь с медиа (1 ко многим)
    media = relationship(
        "AdMedia", back_populates="advertisement", cascade="all, delete-orphan"
    )


class AdMedia(Base):
    __tablename__ = "ad_media"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    advertisement_id: Mapped[int] = mapped_column(
        ForeignKey("advertisement.id", ondelete="CASCADE")
    )
    file_id: Mapped[str] = mapped_column(String)
    # Тип медиа: photo | video
    media_type: Mapped[str] = mapped_column(String, default="photo")

    advertisement = relationship("Advertisement", back_populates="media")
