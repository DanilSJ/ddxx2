from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class ChatVideo(Base):
    __tablename__ = "chat_video"

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chat_message.id", ondelete="CASCADE"), nullable=False
    )
    video_url: Mapped[str] = mapped_column(String)

    chat = relationship("ChatMessage", back_populates="videos")
