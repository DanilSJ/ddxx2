from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class ProductVideo(Base):
    __tablename__ = "product_video"

    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE")
    )
    video_file_id: Mapped[str] = mapped_column(String)

    product = relationship("Product", back_populates="videos")


