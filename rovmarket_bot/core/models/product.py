from sqlalchemy import DateTime, String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from .base import Base


class Product(Base):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(String)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"),
        nullable=False,
    )
    user = relationship(
        "User",
        back_populates="products",
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"),
        nullable=False,
    )

    category = relationship(
        "Categories",
        back_populates="products",
    )

    photos = relationship(
        "ProductPhoto",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    description: Mapped[str] = mapped_column(String)
    price: Mapped[int | None] = mapped_column(nullable=True)
    contact: Mapped[str] = mapped_column(String)

    geo: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
