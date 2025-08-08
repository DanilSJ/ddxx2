from sqlalchemy import ForeignKey, String, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from .base import Base


class Advertisement(Base):
    __tablename__ = "advertisement"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Частота показа (неделя, 2 недели, месяц)
    week: Mapped[bool] = mapped_column(Boolean, default=False)
    two_weeks: Mapped[bool] = mapped_column(Boolean, default=False)
    month: Mapped[bool] = mapped_column(Boolean, default=False)
    periodicity: Mapped[int] = mapped_column(Integer, default=1)  # как часто показывать

    # Связь с фотками (1 ко многим)
    photos = relationship(
        "AdPhoto", back_populates="advertisement", cascade="all, delete-orphan"
    )


class AdPhoto(Base):
    __tablename__ = "ad_photo"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    advertisement_id: Mapped[int] = mapped_column(
        ForeignKey("advertisement.id", ondelete="CASCADE")
    )
    file_id: Mapped[str] = mapped_column(String)

    advertisement = relationship("Advertisement", back_populates="photos")
