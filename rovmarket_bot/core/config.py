from pydantic import BaseModel
from pydantic_settings import BaseSettings
from pathlib import Path
from aiogram import Bot, types
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    db_url: str = "sqlite+aiosqlite:///./db.sqlite3"
    db_echo: bool = False

    TOKEN: str = os.environ["TELEGRAM_TOKEN"]
    BOT_USERNAME: str = os.environ["BOT_USERNAME"]

settings = Settings()

bot = Bot(token=settings.TOKEN)
