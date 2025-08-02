from sqlalchemy import DateTime, String, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from .base import Base


class Categories(Base):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)

    product_id = mapped_column(
        Integer,
        ForeignKey("product.id"),
        unique=True,
    )
    product = relationship(
        "Product",
        back_populates="categories",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
