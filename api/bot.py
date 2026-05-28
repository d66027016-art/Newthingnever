import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

# Resolve local imports (config, database, commands)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self):
        # Health check
        self.send_json(200, {"status": "healthy", "message": "Bot endpoint is ready"})

    def do_POST(self):
        headers_dict = {k.lower(): v for k, v in self.headers.items()}
        content_length = int(headers_dict.get("content-length", 0))
        body_content = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""

        if not body_content:
            self.send_json(400, {"error": "Empty body"})
            return

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(process_update(body_content))
            self.send_json(200, {"status": "ok"})
        except Exception as e:
            self.send_json(500, {"error": str(e)})
        finally:
            loop.close()
