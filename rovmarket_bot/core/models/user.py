from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from .base import Base
from sqlalchemy import BigInteger


class User(Base):
    __tablename__ = "user"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
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

    # Many-to-many: categories user subscribed to for notifications
    subscribed_categories = relationship(
        "Categories",
        secondary="user_category_notification",
        back_populates="subscribed_users",
        lazy="selectin",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
