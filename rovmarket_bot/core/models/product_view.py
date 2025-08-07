from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from .base import Base


class ProductView(Base):
    __tablename__ = "product_view"

    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships (опциональны, для удобства)
    product = relationship("Product", back_populates="views")
    user = relationship("User", back_populates="viewed_products")

    # Гарантирует, что один пользователь может быть только один раз в просмотрах одного товара
    __table_args__ = (
        UniqueConstraint("product_id", "user_id", name="unique_product_user_view"),
    )
