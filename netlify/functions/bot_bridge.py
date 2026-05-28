import asyncio
import json
import os
import sys

# Add root directory to sys.path to resolve local imports (config, database, commands)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import certifi
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update

from config import BOT_TOKEN
import database.db as db
from commands import router as main_router

async def process_update(event_body: str):
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(main_router)

    try:
        await db.get_db()
        update_data = json.loads(event_body)
        update = Update.model_validate(update_data)
        await dp.feed_update(bot, update)
    finally:
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    try:
        # Read update JSON from stdin
        body = sys.stdin.read()
        if body:
            asyncio.run(process_update(body))
            print(json.dumps({"status": "ok"}))
        else:
            print(json.dumps({"error": "Empty body"}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
