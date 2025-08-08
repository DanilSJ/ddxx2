from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from .base import Base


class Categories(Base):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)

    products = relationship(
        "Product",
        back_populates="category",
    )

    # Users subscribed to notifications for this category
    subscribed_users = relationship(
        "User",
        secondary="user_category_notification",
        back_populates="subscribed_categories",
        lazy="selectin",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
