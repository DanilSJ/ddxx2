from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class ChatAudio(Base):
    __tablename__ = "chat_audio"

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chat_message.id", ondelete="CASCADE"), nullable=False
    )
    audio_url: Mapped[str] = mapped_column(String)

    chat = relationship("ChatMessage", back_populates="audios")
