import asyncio
import time
from aiogram import Router, Bot, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandObject
from aiogram.enums import ParseMode

import database.db as db
from config import OWNER_IDS, BOT_NAME, PLAN_PRICES
from functions.emojis import EMOJI

router = Router()

async def is_authorized(uid: int) -> bool:
    return uid in OWNER_IDS or await db.is_admin(uid)

@router.message(Command("stats", prefix="/."))
async def cmd_stats(msg: Message):
    if not await is_authorized(msg.from_user.id):
        return

    stats = await db.get_global_stats()
    text = (
        f"「 {EMOJI['stats']} GLOBAL STATS 」\n\n"
        f"Total Users: <code>{stats['users']}</code>\n"
        f"Total Checks: <code>{stats['checks']}</code>\n"
        f"Charged Hits: <code>{stats['charged']}</code>\n"
        f"Live Hits: <code>{stats['live']}</code>\n"
        f"Banned Users: <code>{stats['banned']}</code>\n"
        f"Active Codes: <code>{stats['active_codes']}</code>"
    )
    await msg.answer(text, parse_mode=ParseMode.HTML)

@router.message(Command("genkey", prefix="/."))
async def cmd_genkey(msg: Message, command: CommandObject):
    if not await is_authorized(msg.from_user.id):
        return

    args = (command.args or "").strip().split()
    if len(args) < 3:
        await msg.answer(
            f"Usage: <code>/genkey &lt;plan&gt; &lt;days&gt; &lt;hpd&gt; [max_uses]</code>\n\n"
            f"Example: <code>/genkey PREMIUM 30 100 1</code>",
            parse_mode=ParseMode.HTML
        )
        return

    plan_type = args[0]
    try:
        days = int(args[1])
        hpd = int(args[2])
        max_uses = int(args[3]) if len(args) > 3 else 1
    except ValueError:
        await msg.answer("Days, HPD and Max Uses must be numbers.")
        return

    code = await db.create_redeem_code(plan_type, days, hpd, max_uses, msg.from_user.id)
    await msg.answer(
        f"「 {EMOJI['charged']} CODE GENERATED 」\n\n"
        f"Code: <code>{code}</code>\n"
        f"Plan: <b>{plan_type}</b>\n"
        f"Days: <code>{days}</code>\n"
        f"HPD: <code>{hpd}</code>\n"
        f"Max Uses: <code>{max_uses}</code>",
        parse_mode=ParseMode.HTML
    )

@router.message(Command("codes", prefix="/."))
async def cmd_codes(msg: Message):
    if not await is_authorized(msg.from_user.id):
        return

    codes = await db.get_active_codes()
    if not codes:
        await msg.answer("No active codes.")
        return

    lines = []
    for c in codes:
        lines.append(f"<code>{c['code']}</code> | {c['plan_type']} | {c['days']}d | {c['used_count']}/{c['max_uses']}")
    
    text = "「 ACTIVE CODES 」\n\n" + "\n".join(lines)
    await msg.answer(text, parse_mode=ParseMode.HTML)

@router.message(Command("revoke", prefix="/."))
async def cmd_revoke(msg: Message, command: CommandObject):
    if not await is_authorized(msg.from_user.id):
        return

    code = (command.args or "").strip()
    if not code:
        await msg.answer("Usage: <code>/revoke CODE-HERE</code>", parse_mode=ParseMode.HTML)
        return

    ok = await db.revoke_code(code)
    if ok:
        await msg.answer(f"{EMOJI['charged']} Code <code>{code}</code> revoked.", parse_mode=ParseMode.HTML)
    else:
        await msg.answer(f"{EMOJI['declined']} Code not found.", parse_mode=ParseMode.HTML)

@router.message(Command("users", prefix="/."))
async def cmd_users(msg: Message):
    if not await is_authorized(msg.from_user.id):
        return

    users = await db.get_all_users()
    if not users:
        await msg.answer("No users found.")
        return

    header = f"「 {EMOJI['welcome']} RECENT USERS 」\n\n"
    lines = []
    for u in users[:20]:
        uname = f"@{u['username']}" if u['username'] else u['first_name'] or "User"
        lines.append(f"<code>{u['user_id']}</code> | {uname} | {u['plan_type']}")
    
    await msg.answer(header + "\n".join(lines), parse_mode=ParseMode.HTML)

@router.message(Command("ban", prefix="/."))
async def cmd_ban(msg: Message, command: CommandObject):
    if not await is_authorized(msg.from_user.id):
        return

    uid_str = (command.args or "").strip()
    if not uid_str or not uid_str.isdigit():
        await msg.answer("Usage: <code>/ban &lt;user_id&gt;</code>", parse_mode=ParseMode.HTML)
        return

    target_uid = int(uid_str)
    await db.ban_user(target_uid)
    await msg.answer(f"{EMOJI['ban']} User <code>{target_uid}</code> banned.", parse_mode=ParseMode.HTML)

@router.message(Command("unban", prefix="/."))
async def cmd_unban(msg: Message, command: CommandObject):
    if not await is_authorized(msg.from_user.id):
        return

    uid_str = (command.args or "").strip()
    if not uid_str or not uid_str.isdigit():
        await msg.answer("Usage: <code>/unban &lt;user_id&gt;</code>", parse_mode=ParseMode.HTML)
        return

    target_uid = int(uid_str)
    await db.unban_user(target_uid)
    await msg.answer(f"{EMOJI['welcome']} User <code>{target_uid}</code> unbanned.", parse_mode=ParseMode.HTML)

@router.message(Command("promote", prefix="/."))
async def cmd_promote(msg: Message, command: CommandObject):
    if msg.from_user.id not in OWNER_IDS:
        return

    uid_str = (command.args or "").strip()
    if not uid_str or not uid_str.isdigit():
        await msg.answer("Usage: <code>/promote &lt;user_id&gt;</code>", parse_mode=ParseMode.HTML)
        return

    target_uid = int(uid_str)
    await db.add_admin(target_uid)
    await msg.answer(f"{EMOJI['charged']} User <code>{target_uid}</code> promoted to Admin.", parse_mode=ParseMode.HTML)

@router.message(Command("demote", prefix="/."))
async def cmd_demote(msg: Message, command: CommandObject):
    if msg.from_user.id not in OWNER_IDS:
        return

    uid_str = (command.args or "").strip()
    if not uid_str or not uid_str.isdigit():
        await msg.answer("Usage: <code>/demote &lt;user_id&gt;</code>", parse_mode=ParseMode.HTML)
        return

    target_uid = int(uid_str)
    await db.remove_admin(target_uid)
    await msg.answer(f"{EMOJI['declined']} User <code>{target_uid}</code> demoted from Admin.", parse_mode=ParseMode.HTML)

@router.message(Command("broadcast", prefix="/."))
async def cmd_broadcast(msg: Message, bot: Bot):
    if not await is_authorized(msg.from_user.id):
        return

    text = ""
    if msg.reply_to_message:
        text = msg.reply_to_message.text or msg.reply_to_message.caption or ""
    else:
        # Extract text after command
        parts = msg.text.split(None, 1)
        if len(parts) > 1:
            text = parts[1]

    if not text:
        await msg.answer("Usage: <code>/broadcast &lt;message&gt;</code> or reply to a message with <code>/broadcast</code>", parse_mode=ParseMode.HTML)
        return

    uids = await db.get_all_user_ids()
    sent = 0
    failed = 0
    
    status_msg = await msg.answer(f"Starting broadcast to {len(uids)} users...")
    
    for uid in uids:
        try:
            await bot.send_message(uid, text, parse_mode=ParseMode.HTML)
            sent += 1
            await asyncio.sleep(0.05) # Small sleep to avoid flood
        except Exception:
            failed += 1
    
    await status_msg.edit_text(f"「 BROADCAST COMPLETE 」\n\nSent: <code>{sent}</code>\nFailed: <code>{failed}</code>", parse_mode=ParseMode.HTML)


@router.message(Command("genapikey", prefix="/."))
async def cmd_genapikey(msg: Message, command: CommandObject):
    if not await is_authorized(msg.from_user.id):
        return

    args = (command.args or "").strip().split()
    if len(args) < 3:
        await msg.answer(
            f"Usage: <code>/genapikey &lt;user_id&gt; &lt;hits_per_day&gt; &lt;plan_type&gt;</code>\n\n"
            f"Example: <code>/genapikey 8303990517 5000 BUSINESS</code>",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        target_uid = int(args[0])
        hits_per_day = int(args[1])
    except ValueError:
        await msg.answer("User ID and Hits Per Day must be numbers.")
        return

    plan_type = args[2].upper()
    key = await db.create_api_key(target_uid, plan_type, hits_per_day)
    
    await msg.answer(
        f"「 🔑 <b>API KEY GENERATED</b> 」\n\n"
        f"👤 <b>For User ID:</b> <code>{target_uid}</code>\n"
        f"✨ <b>Plan:</b> <code>{plan_type}</code>\n"
        f"📊 <b>Daily Quota:</b> <code>{hits_per_day}</code> hits\n"
        f"🗝️ <b>Key:</b> <code>{key}</code>\n\n"
        f"⚠️ <i>Keep this key secret. Never expose it in client-side code!</i>",
        parse_mode=ParseMode.HTML
    )


@router.message(Command("revokeapikey", prefix="/."))
async def cmd_revokeapikey(msg: Message, command: CommandObject):
    if not await is_authorized(msg.from_user.id):
        return

    key = (command.args or "").strip()
    if not key:
        await msg.answer("Usage: <code>/revokeapikey &lt;api_key&gt;</code>", parse_mode=ParseMode.HTML)
        return

    ok = await db.revoke_api_key(key)
    if ok:
        await msg.answer(f"✅ API Key revoked and disabled successfully.", parse_mode=ParseMode.HTML)
    else:
        await msg.answer(f"❌ API Key not found or already inactive.", parse_mode=ParseMode.HTML)

