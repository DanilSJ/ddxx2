from pydantic_settings import BaseSettings
from pathlib import Path
from aiogram import Bot
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    db_url: str = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./db.sqlite3")
    db_echo: bool = False

    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379")

    TOKEN: str = os.environ["TELEGRAM_TOKEN"]
    BOT_USERNAME: str = os.environ["BOT_USERNAME"]


settings = Settings()

bot = Bot(token=settings.TOKEN)
