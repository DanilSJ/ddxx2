from sqlalchemy import DateTime, ForeignKey, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from .base import Base


class Chat(Base):
    __tablename__ = "chat"

    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=False)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    messages = relationship(
        "ChatMessage", back_populates="chat", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_message"

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chat.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)

    photos = relationship(
        "ChatPhoto",
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    videos = relationship(
        "ChatVideo",
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    stickers = relationship(
        "ChatSticker",
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    documents = relationship(
        "ChatDocument",
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    audios = relationship(
        "ChatAudio",
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    voices = relationship(
        "ChatVoice",
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    chat = relationship("Chat", back_populates="messages")
