from sqlalchemy import DateTime, Table, ForeignKey, Column, Integer, String
from sqlalchemy.orm import Mapped, relationship, mapped_column
from datetime import datetime
from .base import Base


class User(Base):
    __tablename__ = "user"

    telegram_id: Mapped[str]