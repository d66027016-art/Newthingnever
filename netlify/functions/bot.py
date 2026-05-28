import asyncio
import json
import logging
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def process_update(event_body: str):
    # Initialize bot and dispatcher inside the request context to bind to the current event loop
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(main_router)

    try:
        # Establish DB connection
        await db.get_db()
        
        # Parse and feed the update
        update_data = json.loads(event_body)
        update = Update.model_validate(update_data)
        await dp.feed_update(bot, update)
    finally:
        # Clean up database and bot sessions to prevent event loop mismatch across executions
        await db.close()
        await bot.session.close()


def handler(event, context):
    http_method = event.get("httpMethod", "GET")
    
    if http_method == "POST":
        body = event.get("body", "")
        if body:
            try:
                # Run the async process_update function
                asyncio.run(process_update(body))
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"status": "ok"})
                }
            except Exception as e:
                logger.error(f"Error handling update: {e}", exc_info=True)
                return {
                    "statusCode": 500,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": str(e)})
                }
                
    # Health check for GET requests
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "healthy", "message": "Bot endpoint is ready"})
    }
