from datetime import datetime, timezone

from sqlalchemy import DateTime, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BotSettings(Base):
    __tablename__ = "bot_settings"

    # Enforce single row via unique constant key and a CHECK
    singleton_key: Mapped[int] = mapped_column(
        default=1,
        server_default="1",
        unique=True,
        nullable=False,
    )

    # Only two toggles requested: moderation and logging
    moderation: Mapped[bool] = mapped_column(default=True, nullable=False)
    logging: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("singleton_key = 1", name="bot_settings_singleton_check"),
    )


