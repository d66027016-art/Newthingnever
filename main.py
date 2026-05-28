import asyncio
import logging
import traceback
import os
import json
import random
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, BOT_NAME, SYSTEM_PROXIES
import database.db as db
from functions.bin_lookup import lookup_bin
from functions.card_utils import parse_card
from functions.stripe_tls import get_checkout_info, charge_card

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


# ─── API & CORS Helper ────────────────────────────────────────────────────────

def cors_response(status_code: int, data: dict):
    return web.Response(
        status=status_code,
        content_type="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, X-API-Key",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
        },
        body=json.dumps(data)
    )


def get_proxy_url(proxy_str: str) -> str:
    if not proxy_str:
        return None
    try:
        if "@" in proxy_str:
            auth, hostport = proxy_str.rsplit("@", 1)
            user, password = auth.split(":", 1)
            host, port = hostport.rsplit(":", 1)
            return f"http://{user}:{password}@{host}:{port}"
        parts = proxy_str.split(":")
        if len(parts) == 4:
            return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
        if len(parts) == 2:
            return f"http://{parts[0]}:{parts[1]}"
    except Exception:
        pass
    return None


async def _pick_proxy(user_id: int = None) -> str:
    if user_id:
        mode = await db.get_user_proxy_mode(user_id)
        if mode == "own":
            user_proxies = await db.get_proxies(user_id)
            if user_proxies:
                return get_proxy_url(random.choice(user_proxies))
    system_proxy = await db.get_setting("system_proxy", "")
    if system_proxy:
        return get_proxy_url(system_proxy)
    if SYSTEM_PROXIES:
        return get_proxy_url(random.choice(SYSTEM_PROXIES))
    return None


# ─── HTTP Route Handlers ──────────────────────────────────────────────────────

async def serve_index(request):
    return web.FileResponse("index.html")


async def serve_style(request):
    return web.FileResponse("style.css")


async def serve_js(request):
    return web.FileResponse("app.js")


async def api_options_handler(request):
    return cors_response(200, {"status": "ok"})


async def api_bin_handler(request):
    bin_num = request.match_info.get("bin", "")
    if not bin_num.isdigit() or len(bin_num) < 6:
        return cors_response(400, {"error": "Invalid BIN. Expected 6+ digits."})
    bin_num = bin_num[:6]
    try:
        bin_info = await lookup_bin(bin_num)
        return cors_response(200, bin_info)
    except Exception as e:
        return cors_response(500, {"error": str(e)})


async def api_stats_handler(request):
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return cors_response(401, {"error": "API key required (X-API-Key header)."})

    key_info = await db.get_api_key_info(api_key)
    if not key_info or not key_info.get("is_active"):
        return cors_response(401, {"error": "Invalid or inactive API key."})

    return cors_response(200, {
        "success": True,
        "plan_type": key_info.get("plan_type"),
        "hits_per_day": key_info.get("hits_per_day"),
        "daily_count": key_info.get("daily_count"),
        "total_count": key_info.get("total_count"),
        "created_at": key_info.get("created_at")
    })


async def api_check_handler(request):
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return cors_response(401, {"error": "API key required (X-API-Key header)."})

    key_info = await db.get_api_key_info(api_key)
    if not key_info or not key_info.get("is_active"):
        return cors_response(401, {"error": "Invalid or inactive API key."})

    hits_per_day = key_info.get("hits_per_day", 0)
    daily_count = key_info.get("daily_count", 0)
    if hits_per_day > 0 and daily_count >= hits_per_day:
        return cors_response(429, {"error": "Daily limit reached for this API key."})

    try:
        body = await request.json()
    except Exception:
        return cors_response(400, {"error": "Invalid JSON body."})

    url = body.get("url")
    card_str = body.get("card")
    if not url or not card_str:
        return cors_response(400, {"error": "Missing parameters. 'url' and 'card' are required."})

    card = parse_card(card_str)
    if not card:
        return cors_response(400, {"error": "Invalid card format. Expected cc|mm|yy|cvv"})

    proxy = await _pick_proxy(user_id=key_info.get("user_id"))
    checkout = await get_checkout_info(url, proxy)
    if checkout.get("error"):
        return cors_response(400, {"error": f"Failed to load checkout page: {checkout['error']}"})

    try:
        result = await asyncio.wait_for(charge_card(card, checkout, proxy), timeout=45)
    except asyncio.TimeoutError:
        result = {"card": card_str, "status": "FAILED", "response": "Timeout", "decline_code": "", "time": 45.0}
    except Exception as e:
        result = {"card": card_str, "status": "FAILED", "response": str(e)[:50], "decline_code": "", "time": 0.0}

    amount_display = f"{checkout.get('price', 0.0):.2f} {(checkout.get('currency') or '').upper()}".strip()
    await db.log_check(
        user_id=key_info.get("user_id"),
        card=result["card"],
        url=url,
        merchant=checkout.get("merchant", "Unknown"),
        amount=amount_display,
        status=result["status"],
        response=result.get("response", ""),
        time_taken=result["time"]
    )
    await db.increment_api_key_hits(api_key)

    return cors_response(200, {
        "success": True,
        "result": {
            "card": result["card"],
            "status": result["status"],
            "decline_code": result.get("decline_code", ""),
            "response": result.get("response", ""),
            "time": result["time"]
        },
        "merchant": checkout.get("merchant", "Unknown"),
        "price": checkout.get("price", 0.0),
        "currency": (checkout.get("currency") or "").upper()
    })


# ─── Server Setup ─────────────────────────────────────────────────────────────

async def start_web_server():
    app = web.Application()
    
    # Static files routing
    app.router.add_get("/", serve_index)
    app.router.add_get("/style.css", serve_style)
    app.router.add_get("/app.js", serve_js)
    
    # API endpoints routing
    app.router.add_options("/api/stats", api_options_handler)
    app.router.add_options("/api/check", api_options_handler)
    app.router.add_get("/api/bin/{bin}", api_bin_handler)
    app.router.add_get("/api/stats", api_stats_handler)
    app.router.add_post("/api/check", api_check_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 5000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    logger.info(f"Starting local server on http://localhost:{port}...")
    await site.start()


async def run_bot():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set!")

    logger.info("Initialising database...")
    await db.get_db()
    logger.info("Database ready.")

    await start_web_server()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    from commands import router as main_router
    dp.include_router(main_router)

    @dp.error()
    async def error_handler(update, exception):
        logger.error(f"Handler error: {exception}", exc_info=True)

    logger.info(f"Starting {BOT_NAME} bot...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await db.close()
        await bot.session.close()


async def main():
    retries = 0
    while True:
        try:
            retries = 0
            await run_bot()
            break
        except KeyboardInterrupt:
            break
        except Exception as e:
            retries += 1
            logger.error(f"Bot crashed (attempt {retries}): {e}")
            if retries >= 10:
                break
            await asyncio.sleep(min(5 * retries, 60))


if __name__ == "__main__":
    asyncio.run(main())
