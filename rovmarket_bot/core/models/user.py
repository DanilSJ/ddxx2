from sqlalchemy import DateTime, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from .base import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String, nullable=True)

    products = relationship(
        "Product", back_populates="user", cascade="all, delete-orphan"
    )

    viewed_products = relationship(
        "ProductView", back_populates="user", cascade="all, delete-orphan"
    )

    complaints = relationship(
        "Complaint", back_populates="user", cascade="all, delete-orphan"
    )

    admin: Mapped[bool] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
