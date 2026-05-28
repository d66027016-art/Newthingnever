"""Home screen, settings, help, credits, redeem, myhits, ping"""
import time
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject

import database.db as db
from config import (
    OWNER_IDS, FREE_DAILY_LIMIT, BOT_NAME, BOT_USERNAME,
    PLAN_PRICES, SUPPORT_USERNAME, OWNER_USERNAME
)
from functions.emojis import EMOJI, EMOJI_PLAIN

_bot_start_time = time.time()

router = Router()

NO_PREVIEW = {"is_disabled": True}

def _kb(*rows):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d) for t, d in row] for row in rows])


async def _home_screen(target, user, edit=False):
    uid = user.id
    plan = await db.get_user_plan(uid)

    if plan["unlimited"]:
        hpd = plan.get("hits_per_day", 0)
        hpd_str = f"{hpd}/day" if hpd > 0 else "Unlimited ♾"
        plan_text = f"💎 <b>{plan['label'].upper()}</b> (<i>{hpd_str}</i>)"
        exp_text = f"📅 <b>Expiry:</b> <code>{plan['expiry']}</code>"
    else:
        hits = await db.get_daily_hits(uid)
        remaining = max(0, FREE_DAILY_LIMIT - hits)
        plan_text = f"🆓 <b>FREE PLAN</b>"
        exp_text = f"⚡ <b>Hits Used:</b> <code>{hits}/{FREE_DAILY_LIMIT}</code> (<i>{remaining} remaining</i>)"

    fname = user.first_name or "User"
    
    text = (
        f"✦ ━━━━━━━ ⚡ ━━━━━━━ ✦\n"
        f"✨ <b>Welcome to {BOT_NAME}</b>\n"
        f"✦ ━━━━━━━ ⚡ ━━━━━━━ ✦\n\n"
        f"👋 Hey, <b>{fname}</b>!\n\n"
        f"┌─ 👤 <b>USER DASHBOARD</b>\n"
        f"├─ 🆔 <b>User ID:</b> <code>{uid}</code>\n"
        f"├─ 👑 <b>Plan:</b> {plan_text}\n"
        f"└─ {exp_text}\n\n"
        f"💡 <i>Send <code>/hit</code> to start checking cards.</i>"
    )

    rows = [
        [("🚀 Hit Commands", "home_help"), ("🛠️ Utility Tools", "home_tools")],
        [("💳 Credits", "home_credits"), ("📊 My Hits", "home_myhits")],
        [("⚙️ Settings", "home_settings"), ("📁 Saved BINs", "home_bins")],
        [("🏆 Ranking", "home_ranking"), ("📞 Contact Support", "home_contact")],
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=d) for t, d in row] for row in rows
    ])

    if edit:
        await target.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await target.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)


@router.message(Command("start", prefix="/."))
async def cmd_start(msg: Message):
    uid = msg.from_user.id
    await db.upsert_user(uid, msg.from_user.username, msg.from_user.first_name)
    if await db.is_banned(uid):
        await msg.answer(f"{EMOJI['ban']} <b>You are banned.</b>", parse_mode=ParseMode.HTML)
        return
    await _home_screen(msg, msg.from_user)


@router.callback_query(F.data == "home_main")
async def cb_home_main(query: CallbackQuery):
    await _home_screen(query.message, query.from_user, edit=True)
    await query.answer()


@router.callback_query(F.data == "home_help")
async def cb_home_help(query: CallbackQuery):
    text = (
        f"✦ ━━━━━━━ 🚀 ━━━━━━━ ✦\n"
        f"⚡ <b>HIT COMMANDS</b>\n"
        f"✦ ━━━━━━━ 🚀 ━━━━━━━ ✦\n\n"
        f"🔹 <b>Single Card Check:</b>\n"
        f"<code>/hit &lt;url&gt; cc|mm|yy|cvv</code>\n\n"
        f"🔹 <b>Bulk Card Check:</b>\n"
        f"<code>/hit &lt;url&gt;</code>\n"
        f"<code>cc1|mm|yy|cvv</code>\n"
        f"<code>cc2|mm|yy|cvv</code>\n\n"
        f"🔹 <b>Auto-Gen Check from BIN:</b>\n"
        f"<code>/hit &lt;url&gt; bin6+</code>\n\n"
        f"🔹 <b>File Check:</b>\n"
        f"Reply to any <code>.txt</code> card list file with:\n"
        f"<code>/hit &lt;url&gt;</code>\n"
    )
    kb = _kb([("⬅️ Back to Menu", "home_main")])
    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await query.answer()


@router.callback_query(F.data == "home_tools")
async def cb_home_tools(query: CallbackQuery):
    text = (
        f"✦ ━━━━━━━ 🛠️ ━━━━━━━ ✦\n"
        f"⚙️ <b>UTILITY TOOLS</b>\n"
        f"✦ ━━━━━━━ 🛠️ ━━━━━━━ ✦\n\n"
        f"🔸 <code>/gen &lt;bin&gt; [qty]</code> ➔ Generate cards\n"
        f"🔸 <code>/bin &lt;bin6&gt;</code> ➔ BIN Details lookup\n"
        f"🔸 <code>/myhits</code> ➔ View your personal hits\n"
        f"🔸 <code>/redeem &lt;code&gt;</code> ➔ Activate premium plan\n"
    )
    kb = _kb([("⬅️ Back to Menu", "home_main")])
    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await query.answer()


@router.callback_query(F.data == "home_credits")
async def cb_home_credits(query: CallbackQuery):
    uid = query.from_user.id
    plan = await db.get_user_plan(uid)
    fname = query.from_user.first_name or "User"
    if plan["unlimited"]:
        hpd = plan.get("hits_per_day", 0)
        hpd_str = f"{hpd}/day" if hpd > 0 else "Unlimited ♾"
        text = (
            f"✦ ━━━━━━━ 💳 ━━━━━━━ ✦\n"
            f"💰 <b>ACCOUNT & PLAN DETAILS</b>\n"
            f"✦ ━━━━━━━ 💳 ━━━━━━━ ✦\n\n"
            f"👤 <b>User:</b> {fname} (<code>{uid}</code>)\n"
            f"👑 <b>Current Plan:</b> 💎 <b>{plan['label'].upper()}</b>\n"
            f"⚡ <b>Hit Limit:</b> <code>{hpd_str}</code>\n"
            f"📅 <b>Expiry Date:</b> <code>{plan['expiry']}</code>\n"
        )
    else:
        hits = await db.get_daily_hits(uid)
        remaining = max(0, FREE_DAILY_LIMIT - hits)
        text = (
            f"✦ ━━━━━━━ 💳 ━━━━━━━ ✦\n"
            f"💰 <b>ACCOUNT & PLAN DETAILS</b>\n"
            f"✦ ━━━━━━━ 💳 ━━━━━━━ ✦\n\n"
            f"👤 <b>User:</b> {fname} (<code>{uid}</code>)\n"
            f"👑 <b>Current Plan:</b> 🆓 <b>FREE PLAN</b>\n"
            f"⚡ <b>Hits Used:</b> <code>{hits}/{FREE_DAILY_LIMIT}</code> (<i>{remaining} remaining today</i>)\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💬 <i>Want more limits? Message {OWNER_USERNAME} to upgrade to premium!</i>"
        )
    kb = _kb([("⬅️ Back to Menu", "home_main")])
    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await query.answer()


@router.message(Command("myhits", prefix="/."))
async def cmd_myhits(msg: Message):
    await _show_myhits(msg, msg.from_user.id)


@router.callback_query(F.data == "home_myhits")
async def cb_home_myhits(query: CallbackQuery):
    await _show_myhits(query.message, query.from_user.id, edit=True)
    await query.answer()


async def _show_myhits(target, uid, edit=False):
    logs = await db.get_user_logs(uid, limit=20)
    stats = await db.get_user_hit_stats(uid)
    text = (
        f"✦ ━━━━━━━ 📊 ━━━━━━━ ✦\n"
        f"📈 <b>YOUR CHECK STATISTICS</b>\n"
        f"✦ ━━━━━━━ 📊 ━━━━━━━ ✦\n\n"
        f"📊 <b>Total Checks:</b> <code>{stats['total']}</code>\n"
        f"💰 <b>Charged Hits:</b> <code>{stats['charged']}</code>\n"
        f"🔥 <b>Live Hits:</b> <code>{stats['live']}</code>\n"
        f"❌ <b>Declined:</b> <code>{stats['declined']}</code>\n\n"
        f"📝 <b>Recent Charged/Live Hits:</b>\n"
    )
    if logs:
        lines = []
        for h in logs[:10]:
            amt = h.get('amount', '?')
            merchant = h.get('merchant', '?')
            status_icon = "💰" if h.get('status') == 'CHARGED' else "🔥"
            lines.append(f"{status_icon} <code>{merchant}</code> ➔ <b>{amt}</b>")
        text += "\n".join(lines)
    else:
        text += "<i>No charged or live hits logged yet.</i>"
    if len(text) > 4000:
        text = text[:3990] + "\n..."
    kb = _kb([("⬅️ Back to Menu", "home_main")])
    if edit:
        await target.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await target.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "home_settings")
async def cb_home_settings(query: CallbackQuery):
    await _show_settings(query)


async def _show_settings(query: CallbackQuery):
    uid = query.from_user.id
    proxy_mode = await db.get_user_proxy_mode(uid)
    user_proxies = await db.get_proxies(uid)
    sys_proxy = await db.get_setting("system_proxy", None)

    if proxy_mode == "own":
        mode_text = "🟢 <b>Using Personal Proxy</b>"
        toggle_btn = ("🌐 Switch to System Proxy", "settings_proxy_system")
    else:
        mode_text = "🔵 <b>Using System Shared Proxy</b>"
        toggle_btn = ("🔑 Switch to Personal Proxy", "settings_proxy_own")

    sys_status = f"<code>{sys_proxy[:25]}...</code>" if sys_proxy else "Hosting IP"
    proxy_list = "\n".join(f"🔸 <code>{p}</code>" for p in user_proxies[:3]) if user_proxies else "<i>No personal proxies added yet.</i>"

    text = (
        f"✦ ━━━━━━━ ⚙️ ━━━━━━━ ✦\n"
        f"⚙️ <b>PROXY CONFIGURATION</b>\n"
        f"✦ ━━━━━━━ ⚙️ ━━━━━━━ ✦\n\n"
        f"🌐 <b>Current Mode:</b> {mode_text}\n"
        f"🖥️ <b>System Default:</b> {sys_status}\n\n"
        f"📂 <b>Your Proxies (showing top 3):</b>\n{proxy_list}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"➕ <b>Add Proxy:</b> <code>/proxy add host:port:user:pass</code>\n"
        f"🧪 <b>Test Speed:</b> <code>/proxy test</code>"
    )
    kb = _kb([toggle_btn], [("⬅️ Back to Menu", "home_main")])
    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await query.answer()


@router.callback_query(F.data == "settings_proxy_own")
async def cb_settings_proxy_own(query: CallbackQuery):
    uid = query.from_user.id
    user_proxies = await db.get_proxies(uid)
    if not user_proxies:
        await query.answer("Add a proxy first with /proxy add", show_alert=True)
        return
    await db.set_user_proxy_mode(uid, "own")
    await _show_settings(query)


@router.callback_query(F.data == "settings_proxy_system")
async def cb_settings_proxy_system(query: CallbackQuery):
    await db.set_user_proxy_mode(query.from_user.id, "system")
    await _show_settings(query)


@router.callback_query(F.data == "home_contact")
async def cb_home_contact(query: CallbackQuery):
    text = (
        f"✦ ━━━━━━━ 💬 ━━━━━━━ ✦\n"
        f"📞 <b>SUPPORT & CONTACT</b>\n"
        f"✦ ━━━━━━━ 💬 ━━━━━━━ ✦\n\n"
        f"👤 <b>Owner/Developer:</b> {OWNER_USERNAME}\n\n"
        f"💡 <i>If you face any issues, need to buy custom plans, or want to report bugs, contact support below.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Message Owner", url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="home_main")],
    ])
    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await query.answer()


@router.message(Command("help", prefix="/."))
async def cmd_help(msg: Message):
    text = (
        f"✦ ━━━━━━━ 🚀 ━━━━━━━ ✦\n"
        f"⚡ <b>AVAILABLE COMMANDS</b>\n"
        f"✦ ━━━━━━━ 🚀 ━━━━━━━ ✦\n\n"
        f"🔹 <b>Single Card Check:</b>\n"
        f"<code>/hit &lt;url&gt; cc|mm|yy|cvv</code>\n\n"
        f"🔹 <b>Bulk Card Check:</b>\n"
        f"<code>/hit &lt;url&gt;</code>\n"
        f"<code>cc1|mm|yy|cvv</code>\n"
        f"<code>cc2|mm|yy|cvv</code>\n\n"
        f"🔹 <b>Auto-Gen Check from BIN:</b>\n"
        f"<code>/hit &lt;url&gt; bin6+</code>\n\n"
        f"🔹 <b>File Check:</b>\n"
        f"Reply to any <code>.txt</code> card list file with:\n"
        f"<code>/hit &lt;url&gt;</code>\n\n"
        f"✦ ━━━━━━━ 🛠️ ━━━━━━━ ✦\n"
        f"⚙️ <b>UTILITY TOOLS:</b>\n"
        f"✦ ━━━━━━━ 🛠️ ━━━━━━━ ✦\n\n"
        f"🔸 <code>/gen &lt;bin&gt; [qty]</code> ➔ Generate cards\n"
        f"🔸 <code>/bin &lt;bin6&gt;</code> ➔ BIN Details lookup\n"
        f"🔸 <code>/myhits</code> ➔ View your personal hits\n"
        f"🔸 <code>/redeem &lt;code&gt;</code> ➔ Activate premium plan\n"
    )
    await msg.answer(text, parse_mode=ParseMode.HTML)


@router.message(Command("redeem", prefix="/."))
async def cmd_redeem(msg: Message, command: CommandObject):
    uid = msg.from_user.id
    code = (command.args or "").strip()
    if not code:
        await msg.answer(f"Usage: <code>/redeem YOUR-CODE-HERE</code>", parse_mode=ParseMode.HTML)
        return
    result = await db.use_redeem_code(uid, code)
    if result["success"]:
        hpd = result.get("hits_per_day", 0)
        hpd_str = f"{hpd}/day" if hpd > 0 else "Unlimited"
        await msg.answer(
            f"{EMOJI['charged']} <b>Code Redeemed!</b>\nPlan: <b>{result['plan_type']}</b>\nHits: {hpd_str}\nDuration: {result['days']} days",
            parse_mode=ParseMode.HTML
        )
    else:
        await msg.answer(f"{EMOJI['declined']} {result['error']}", parse_mode=ParseMode.HTML)


@router.message(Command("credits", prefix="/."))
async def cmd_credits(msg: Message):
    uid = msg.from_user.id
    plan = await db.get_user_plan(uid)
    if plan["unlimited"]:
        hpd = plan.get("hits_per_day", 0)
        hpd_str = f"{hpd}/day" if hpd > 0 else f"Unlimited"
        text = f"Plan: <b>{plan['label']}</b> | Hits: {hpd_str} | Exp: {plan['expiry']}"
    else:
        hits = await db.get_daily_hits(uid)
        remaining = max(0, FREE_DAILY_LIMIT - hits)
        text = f"Plan: Free | Hits: {hits}/{FREE_DAILY_LIMIT} ({remaining} left)"
    await msg.answer(text, parse_mode=ParseMode.HTML)


@router.message(Command("ping", prefix="/."))
async def cmd_ping(msg: Message):
    start = time.time()
    sent = await msg.answer(f"⚡ Pinging...", parse_mode=ParseMode.HTML)
    latency_ms = round((time.time() - start) * 1000)
    uptime_sec = int(time.time() - _bot_start_time)
    hours, rem = divmod(uptime_sec, 3600)
    mins, secs = divmod(rem, 60)
    uptime_str = f"{hours}h {mins}m {secs}s"
    await sent.edit_text(f"🚀 <b>Pong!</b>\n\n📡 <b>Latency:</b> <code>{latency_ms}ms</code>\n⏰ <b>Uptime:</b> <code>{uptime_str}</code>", parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "home_ranking")
async def cb_home_ranking(query: CallbackQuery):
    ranking = await db.get_charged_ranking(10)
    text = (
        f"✦ ━━━━━━━ 🏆 ━━━━━━━ ✦\n"
        f"🏆 <b>TOP HITTERS LEADERBOARD</b>\n"
        f"✦ ━━━━━━━ 🏆 ━━━━━━━ ✦\n\n"
    )
    if not ranking:
        text += "<i>No charged hits recorded yet. Be the first!</i>"
    else:
        lines = []
        medals = ["🥇 <b>1st</b>", "🥈 <b>2nd</b>", "🥉 <b>3rd</b>"]
        for idx, r in enumerate(ranking):
            name = r.get("first_name") or r.get("username") or "Anonymous"
            count = r["charged_count"]
            pos = medals[idx] if idx < 3 else f"✨ <b>{idx+1}th</b>"
            lines.append(f"{pos} ➔ {name} (<code>{count}</code> charged)")
        text += "\n".join(lines)
    kb = _kb([("⬅️ Back to Menu", "home_main")])
    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await query.answer()


@router.callback_query(F.data == "home_bins")
async def cb_home_bins(query: CallbackQuery):
    uid = query.from_user.id
    bins = await db.get_saved_bins(uid)
    text = (
        f"✦ ━━━━━━━ 📁 ━━━━━━━ ✦\n"
        f"📁 <b>SAVED BIN CONFIGURATIONS</b>\n"
        f"✦ ━━━━━━━ 📁 ━━━━━━━ ✦\n\n"
    )
    if not bins:
        text += "<i>No saved BINs found.</i>\n\n💡 <b>Save BIN command:</b>\n<code>/savebin &lt;name&gt; &lt;bin&gt;</code>"
    else:
        lines = [f"📁 <b>{b['name'].upper()}</b> ➔ <code>{b['bin_value']}</code>" for b in bins]
        text += "\n".join(lines) + f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n❌ <b>Delete:</b> <code>/delbin &lt;name&gt;</code>"
    kb = _kb([("⬅️ Back to Menu", "home_main")])
    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await query.answer()


@router.message(Command("savebin", prefix="/."))
async def cmd_savebin(msg: Message, command: CommandObject):
    uid = msg.from_user.id
    args = (command.args or "").strip().split(None, 1)
    if len(args) < 2:
        await msg.answer(f"Usage: <code>/savebin &lt;name&gt; &lt;bin&gt;</code>", parse_mode=ParseMode.HTML)
        return
    ok = await db.save_bin(uid, args[0], args[1])
    if ok:
        await msg.answer(f"{EMOJI['charged']} BIN saved as <b>{args[0]}</b>.", parse_mode=ParseMode.HTML)
    else:
        await msg.answer(f"{EMOJI['declined']} Failed.", parse_mode=ParseMode.HTML)


@router.message(Command("mybins", prefix="/."))
async def cmd_mybins(msg: Message):
    uid = msg.from_user.id
    bins = await db.get_saved_bins(uid)
    if not bins:
        await msg.answer(f"<i>No saved BINs. Use /savebin.</i>", parse_mode=ParseMode.HTML)
        return
    lines = [f"<code>{b['name']}</code> -> <code>{b['bin_value']}</code>" for b in bins]
    await msg.answer(f"「 SAVED BINS 」\n\n" + "\n".join(lines), parse_mode=ParseMode.HTML)


@router.message(Command("delbin", prefix="/."))
async def cmd_delbin(msg: Message, command: CommandObject):
    name = (command.args or "").strip()
    if not name:
        await msg.answer(f"Usage: <code>/delbin &lt;name&gt;</code>", parse_mode=ParseMode.HTML)
        return
    await db.delete_saved_bin(msg.from_user.id, name)
    await msg.answer(f"{EMOJI['charged']} BIN <b>{name}</b> removed.", parse_mode=ParseMode.HTML)


@router.message(Command("myapi", prefix="/."))
async def cmd_myapi(msg: Message):
    uid = msg.from_user.id
    keys = await db.get_user_api_keys(uid)
    if not keys:
        await msg.answer(
            f"❌ <b>No API Keys found.</b>\n\n"
            f"💡 <i>Contact support/admins to purchase or generate a Business API key.</i>",
            parse_mode=ParseMode.HTML
        )
        return

    text = f"🔑 <b>YOUR BUSINESS API KEYS:</b>\n\n"
    for i, k in enumerate(keys):
        status_label = "🟢 Active" if k["is_active"] else "🔴 Revoked"
        limit_label = f"<code>{k['hits_per_day']}</code>" if k["hits_per_day"] > 0 else "Unlimited"
        text += (
            f"<b>Key {i+1}:</b> <code>{k['key']}</code>\n"
            f"├─ <b>Status:</b> {status_label}\n"
            f"├─ <b>Plan:</b> <code>{k['plan_type']}</code>\n"
            f"└─ <b>Quota:</b> <code>{k['daily_count']}</code> / {limit_label} hits today\n\n"
        )
    await msg.answer(text, parse_mode=ParseMode.HTML)

