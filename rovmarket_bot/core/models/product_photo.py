from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class ProductPhoto(Base):
    __tablename__ = "product_photo"

    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE")
    )
    photo_url: Mapped[str] = mapped_column(String)

    product = relationship("Product", back_populates="photos")
