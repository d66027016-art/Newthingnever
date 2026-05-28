import asyncio
import json
import os
import sys
import random
from http.server import BaseHTTPRequestHandler

# Resolve local imports (config, database, functions)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import certifi
import database.db as db
from functions.bin_lookup import lookup_bin
from functions.card_utils import parse_card
from functions.stripe_tls import get_checkout_info, charge_card
from config import SYSTEM_PROXIES

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

async def handle_request_async(method: str, path: str, headers_dict: dict, body_content: str):
    # Route parsing
    route = path.replace("/api", "").strip("/")

    if method == "OPTIONS":
        return 200, {"status": "ok"}

    # 1. GET /api/bin/<bin>
    if route.startswith("bin/"):
        parts = route.split("/", 1)
        if len(parts) < 2 or not parts[1].isdigit() or len(parts[1]) < 6:
            return 400, {"error": "Invalid BIN. Expected 6+ digits."}
        bin_num = parts[1][:6]
        try:
            bin_info = await lookup_bin(bin_num)
            return 200, bin_info
        except Exception as e:
            return 500, {"error": str(e)}

    # Authenticated endpoints
    api_key = headers_dict.get("x-api-key")
    if not api_key:
        return 401, {"error": "API key required (X-API-Key header)."}

    await db.get_db()

    try:
        key_info = await db.get_api_key_info(api_key)
        if not key_info or not key_info.get("is_active"):
            return 401, {"error": "Invalid or inactive API key."}

        # 2. GET /api/stats
        if route == "stats" and method == "GET":
            return 200, {
                "success": True,
                "plan_type": key_info.get("plan_type"),
                "hits_per_day": key_info.get("hits_per_day"),
                "daily_count": key_info.get("daily_count"),
                "total_count": key_info.get("total_count"),
                "created_at": key_info.get("created_at")
            }

        # 3. POST /api/check
        if route == "check" and method == "POST":
            hits_per_day = key_info.get("hits_per_day", 0)
            daily_count = key_info.get("daily_count", 0)
            if hits_per_day > 0 and daily_count >= hits_per_day:
                return 429, {"error": "Daily limit reached for this API key."}

            try:
                body = json.loads(body_content)
            except Exception:
                return 400, {"error": "Invalid JSON body."}

            url = body.get("url")
            card_str = body.get("card")
            if not url or not card_str:
                return 400, {"error": "Missing parameters. 'url' and 'card' are required."}

            card = parse_card(card_str)
            if not card:
                return 400, {"error": "Invalid card format. Expected cc|mm|yy|cvv"}

            proxy = await _pick_proxy(user_id=key_info.get("user_id"))
            checkout = await get_checkout_info(url, proxy)
            if checkout.get("error"):
                return 400, {"error": f"Failed to load checkout page: {checkout['error']}"}

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

            return 200, {
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
            }

        return 404, {"error": "Endpoint not found."}
    finally:
        await db.close()


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_json(200, {"status": "ok"})

    def do_GET(self):
        headers_dict = {k.lower(): v for k, v in self.headers.items()}
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            status, res = loop.run_until_complete(
                handle_request_async("GET", self.path, headers_dict, "")
            )
            self.send_json(status, res)
        except Exception as e:
            self.send_json(500, {"error": str(e)})
        finally:
            loop.close()

    def do_POST(self):
        headers_dict = {k.lower(): v for k, v in self.headers.items()}
        content_length = int(headers_dict.get("content-length", 0))
        body_content = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            status, res = loop.run_until_complete(
                handle_request_async("POST", self.path, headers_dict, body_content)
            )
            self.send_json(status, res)
        except Exception as e:
            self.send_json(500, {"error": str(e)})
        finally:
            loop.close()
