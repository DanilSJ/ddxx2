import asyncio
from aiogram import Dispatcher
from app.start.handler import router as start

dp = Dispatcher()

async def main():
    dp.include_router(start)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")
