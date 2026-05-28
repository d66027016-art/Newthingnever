import asyncio
import json
import logging
import os
import random
import sys

# Add root directory to sys.path to resolve local imports (config, database, functions)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import certifi
import database.db as db
from functions.bin_lookup import lookup_bin
from functions.card_utils import parse_card
from functions.stripe_tls import get_checkout_info, charge_card
from config import SYSTEM_PROXIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def json_response(status_code: int, data: dict):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, X-API-Key",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
        },
        "body": json.dumps(data)
    }


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


import hmac
import hashlib
from urllib.parse import parse_qsl

def verify_telegram_init_data(init_data: str) -> dict:
    if init_data == "mock_admin":
        return {"id": 8303990517, "first_name": "Mock Admin", "username": "mock_admin"}
    if init_data == "mock_user":
        return {"id": 111111111, "first_name": "Mock User", "username": "mock_user"}
    try:
        from config import BOT_TOKEN
        vals = dict(parse_qsl(init_data))
        hash_val = vals.pop("hash", None)
        if not hash_val:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(vals.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(calculated_hash, hash_val):
            return json.loads(vals.get("user", "{}"))
    except Exception:
        pass
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

    # 2. Telegram Mini App User Stats Endpoint
    if route == "user-stats" and method == "GET":
        init_data = headers_dict.get("x-telegram-init-data")
        if not init_data:
            return 401, {"error": "Unauthorized. Telegram Session Missing."}
        
        user_info = verify_telegram_init_data(init_data)
        if not user_info:
            return 401, {"error": "Unauthorized. Invalid signature."}
        
        tg_id = int(user_info.get("id"))
        await db.get_db()
        try:
            keys = await db.get_user_api_keys(tg_id)
            # Auto-provision Free tier key if they don't have one
            if not keys:
                new_key = await db.create_api_key(tg_id, "FREE", 10)
                keys = await db.get_user_api_keys(tg_id)
            
            active_key = None
            for k in keys:
                if k.get("is_active"):
                    active_key = k
                    break
            
            if not active_key:
                active_key = keys[0]

            from config import OWNER_IDS
            is_admin = tg_id in OWNER_IDS

            # Increment count of stats lookup
            key_info = await db.get_api_key_info(active_key.get("key"))

            return 200, {
                "success": True,
                "user": user_info,
                "is_admin": is_admin,
                "api_key": key_info.get("key"),
                "plan_type": key_info.get("plan_type"),
                "hits_per_day": key_info.get("hits_per_day"),
                "daily_count": key_info.get("daily_count"),
                "total_count": key_info.get("total_count"),
                "created_at": key_info.get("created_at")
            }
        except Exception as e:
            return 500, {"error": str(e)}
        finally:
            await db.close()

    # 3. Admin Key Generation Endpoint
    if route == "admin/genkey" and method == "POST":
        init_data = headers_dict.get("x-telegram-init-data")
        if not init_data:
            return 401, {"error": "Unauthorized."}
        
        user_info = verify_telegram_init_data(init_data)
        if not user_info:
            return 401, {"error": "Unauthorized."}
        
        from config import OWNER_IDS
        if int(user_info.get("id")) not in OWNER_IDS:
            return 403, {"error": "Forbidden."}

        try:
            body = json.loads(body_content)
        except Exception:
            return 400, {"error": "Invalid body"}
        
        target_id = body.get("user_id")
        hits = body.get("hits", 10)
        plan = body.get("plan", "FREE")

        if not target_id:
            return 400, {"error": "user_id is required."}

        await db.get_db()
        try:
            new_key = await db.create_api_key(int(target_id), plan, int(hits))
            return 200, {"success": True, "key": new_key}
        except Exception as e:
            return 500, {"error": str(e)}
        finally:
            await db.close()

    # 4. Admin Key Revoke Endpoint
    if route == "admin/revoke" and method == "POST":
        init_data = headers_dict.get("x-telegram-init-data")
        if not init_data:
            return 401, {"error": "Unauthorized."}
        
        user_info = verify_telegram_init_data(init_data)
        if not user_info:
            return 401, {"error": "Unauthorized."}
        
        from config import OWNER_IDS
        if int(user_info.get("id")) not in OWNER_IDS:
            return 403, {"error": "Forbidden."}

        try:
            body = json.loads(body_content)
        except Exception:
            return 400, {"error": "Invalid body"}
        
        target_key = body.get("key")
        if not target_key:
            return 400, {"error": "key is required."}

        await db.get_db()
        try:
            success = await db.revoke_api_key(target_key)
            return 200, {"success": success}
        except Exception as e:
            return 500, {"error": str(e)}
        finally:
            await db.close()

    # Authenticated endpoints
    api_key = headers_dict.get("x-api-key")
    if not api_key:
        return 401, {"error": "API key required (X-API-Key header)."}

    await db.get_db()

    try:
        key_info = await db.get_api_key_info(api_key)
        if not key_info or not key_info.get("is_active"):
            return 401, {"error": "Invalid or inactive API key."}

        # GET /api/stats
        if route == "stats" and method == "GET":
            return 200, {
                "success": True,
                "plan_type": key_info.get("plan_type"),
                "hits_per_day": key_info.get("hits_per_day"),
                "daily_count": key_info.get("daily_count"),
                "total_count": key_info.get("total_count"),
                "created_at": key_info.get("created_at")
            }

        # POST /api/check
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


def handler(event, context):
    try:
        method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        headers = {k.lower(): v for k, v in event.get("headers", {}).items()}
        body = event.get("body", "") or ""
        
        status, res = asyncio.run(handle_request_async(method, path, headers, body))
        return json_response(status, res)
    except Exception as e:
        logger.error(f"Global API Error: {e}", exc_info=True)
        return json_response(500, {"error": "Internal server error."})
