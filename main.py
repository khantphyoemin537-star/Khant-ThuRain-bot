# ============================================================
# 🏛️  SUPER MANAGEMENT BOT  —  main.py (standalone)
# ============================================================
# Features:
#   🗑️  Auto-delete member photo/video (inline-bot results KEPT)
#   🔇  "မြုလိုက်" / "mutethatgay" mute — 5 times / day / admin
#   🔊  "ပြန်ဖွင့်" unmute
#   📌  Pin / Unpin
#   👥  Admin mention (/admins, /report)
#   🤖  Bot-to-Bot: "/del" or "ဖျက်မယ်" → track & auto-clean
#   ⚠️  Warn / Unwarn / Warns / Reset
#   👢  Kick / Ban / Unban
#   🧹  Purge messages
#   🎉  Welcome new members (toggle)
#   📖  Rules (set / show / clear)
#   📊  Stats & Clean UI (Burmese + English)
# ============================================================

import os
import re
import asyncio
import traceback
import unicodedata
import time as _tm
from datetime import datetime, timezone

from telethon import TelegramClient, events, functions
from telethon.tl.functions.channels import (
    EditBannedRequest, GetParticipantsRequest, GetFullChannelRequest,
)
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
from telethon.tl.types import ChatBannedRights, ChannelParticipantsAdmins
from motor.motor_asyncio import AsyncIOMotorClient


# ============================================================
# ⚙️  CONFIG
# ============================================================
APP_ID   = 39584681
APP_HASH = 'c8c0685d6dd5b9e546093ea90d27733b'
MONGO_URI = "mongodb+srv://kkt:h1BdaMt7nxW9jTXa@cluster0.kb5fzfl.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"
BOT_TOKEN = '8896446636:AAHqX8rCX4-cXVqhYkJyBn2DkMddeYeP_qs'

OWNER_ID          = 6015356597
OFFICIAL_GROUP_ID = -1004478099253

MUTE_DAILY_LIMIT   = 5
KICK_BAN_SECONDS   = 60
ADMIN_CACHE_TTL    = 120
WELCOME_DEFAULT    = False
DEFAULT_WARN_LIMIT = 3


# ============================================================
# 🗄️  DATABASE
# ============================================================
_mongo = AsyncIOMotorClient(MONGO_URI)
db = _mongo["group_manager"]

tracked_bots_col = db["tracked_bots"]
mute_daily_col   = db["mute_daily"]
warns_col        = db["warns"]
settings_col     = db["group_settings"]


# ============================================================
# 🤖  BOT CLIENT
# ============================================================
bot = TelegramClient('manager_bot_session', APP_ID, APP_HASH)

_my_id = None
_my_username = None

async def _ensure_me():
    global _my_id, _my_username
    if _my_id is None:
        me = await bot.get_me()
        _my_id = me.id
        _my_username = me.username
    return _my_id


# ============================================================
# 🛡️  HELPERS
# ============================================================
def safe_handler(ctx: str):
    def deco(fn):
        async def wrapper(event, *a, **k):
            try:
                return await fn(event, *a, **k)
            except Exception as e:
                print(f"❌ [{ctx}] {type(e).__name__}: {e}")
                try:
                    print(f"   ℹ️ chat={event.chat_id} sender={event.sender_id}")
                except Exception:
                    pass
                traceback.print_exc()
        wrapper.__name__ = fn.__name__
        return wrapper
    return deco


def make_mention(name: str, user_id: int) -> str:
    safe = (name or "User").replace("<", "").replace(">", "").replace("&", "&amp;")
    return f"<a href='tg://user?id={user_id}'>{safe}</a>"


def code(text) -> str:
    s = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<code>{s}</code>"


def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def clean_invisible(text: str) -> str:
    if not text:
        return ""
    try:
        return "".join(c for c in text if unicodedata.category(c) != "Cf")
    except Exception:
        return text


def get_text(event) -> str:
    return event.text or ""


def get_cmd_and_args(text: str):
    if not text:
        return "", ""
    t = text.strip()
    parts = t.split(maxsplit=1)
    cmd = parts[0]
    args = parts[1].strip() if len(parts) > 1 else ""
    if "@" in cmd:
        cmd = cmd.split("@", 1)[0]
    return cmd, args


# ---------------- ADMIN CACHE ----------------
_admin_cache: dict[int, dict] = {}

async def get_admin_ids(chat_id: int) -> set[int]:
    now = _tm.time()
    cached = _admin_cache.get(chat_id)
    if cached and now < cached["expiry"]:
        return cached["ids"]
    try:
        result = await bot(GetParticipantsRequest(
            channel=chat_id,
            filter=ChannelParticipantsAdmins(),
            offset=0, limit=200, hash=0,
        ))
        ids = {u.id for u in result.users}
        _admin_cache[chat_id] = {"ids": ids, "expiry": now + ADMIN_CACHE_TTL}
        return ids
    except Exception as e:
        print(f"⚠️ get_admin_ids error: {e}")
        _admin_cache[chat_id] = {"ids": set(), "expiry": now + 10}
        return set()


async def is_admin(chat_id: int, user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    return user_id in await get_admin_ids(chat_id)


async def get_admin_list(chat_id: int) -> list[tuple[int, str]]:
    try:
        result = await bot(GetParticipantsRequest(
            channel=chat_id,
            filter=ChannelParticipantsAdmins(),
            offset=0, limit=200, hash=0,
        ))
        out = []
        seen = set()
        for u in result.users:
            if u.id in seen:
                continue
            seen.add(u.id)
            name = f"{u.first_name or ''} {u.last_name or ''}".strip() or "Admin"
            out.append((u.id, name))
        if OWNER_ID not in seen:
            out.append((OWNER_ID, "Owner"))
        return out
    except Exception as e:
        print(f"⚠️ get_admin_list error: {e}")
        return [(OWNER_ID, "Owner")]


async def get_user_name(user_id: int) -> str:
    try:
        u = await bot.get_entity(user_id)
        name = f"{u.first_name or ''} {u.last_name or ''}".strip()
        return name or str(user_id)
    except Exception:
        return str(user_id)


async def get_group_title(chat_id: int) -> str:
    try:
        ent = await bot.get_entity(chat_id)
        return getattr(ent, "title", str(chat_id)) or str(chat_id)
    except Exception:
        return str(chat_id)


# ============================================================
# 🗑️  AUTO-DELETE MEDIA + TRACKED-BOT CLEANER
# ============================================================
tracked_bots_cache: dict[int, int] = {}

async def load_tracked_bots():
    global tracked_bots_cache
    tracked_bots_cache = {}
    try:
        async for doc in tracked_bots_col.find({"chat_id": OFFICIAL_GROUP_ID}):
            tracked_bots_cache[doc["bot_id"]] = doc["chat_id"]
        print(f"🤖 Loaded {len(tracked_bots_cache)} tracked bot(s).")
    except Exception as e:
        print(f"⚠️ load_tracked_bots error: {e}")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("media_moderation_handler")
async def media_moderation_handler(event):
    msg = event.message
    sender_id = event.sender_id
    chat_id = event.chat_id
    my_id = await _ensure_me()

    # 1) Tracked bot → delete everything
    if sender_id in tracked_bots_cache:
        try:
            await event.delete()
            print(f"🧹 Deleted tracked-bot msg: bot={sender_id} msg={msg.id}")
        except Exception as e:
            print(f"❌ tracked-bot delete failed: {e}")
        return

    # 2) Only photo/video
    if not (msg.photo or msg.video):
        return

    # 3) Keep inline-bot results (@gif, @pic, etc.)
    via_bot = getattr(event, "via_bot_id", None) or getattr(msg, "via_bot_id", None)
    if via_bot:
        return

    # 4) Keep bot's own messages
    if sender_id == my_id:
        return

    # 5) Keep other bot messages
    try:
        sender = await event.get_sender()
        if getattr(sender, "bot", False):
            return
    except Exception:
        pass

    # 6) Keep admin messages
    try:
        if await is_admin(chat_id, sender_id):
            return
    except Exception as e:
        print(f"⚠️ admin check failed (defaulting to delete): {e}")

    # 7) Delete
    try:
        await event.delete()
        print(f"🗑️ Auto-deleted media msg={msg.id} sender={sender_id}")
    except Exception as e:
        print(f"❌ auto-delete failed: {e}")


# ============================================================
# 🤖  BOT-TO-BOT:  /del  or  ဖျက်မယ်  → track & clean
# ============================================================
@bot.on(events.NewMessage(
    chats=[OFFICIAL_GROUP_ID],
    pattern=r"^(?:/del|ဖျက်မယ်)(?:@\w+)?(?:\s|$)",
))
@safe_handler("del_track_handler")
async def del_track_handler(event):
    if event.sender_id != OWNER_ID:
        return

    if not event.is_reply:
        await event.reply(
            "⚠️ <b>Usage</b>\n\n"
            "📌 Bot တစ်ခုရဲ့ message ကို <b>reply</b> လုပ်ပြီး အောက်ပါတစ်ခုခု ရိုက်ပါ:\n"
            "• <code>/del</code>\n"
            "• <code>ဖျက်မယ်</code>\n\n"
            "🤖 ထို bot ရဲ့ နောက်လာမယ့် message တွေ အားလုံး auto-delete ဖြစ်ပါမယ်။",
            parse_mode="html",
        )
        return

    replied = await event.get_reply_message()
    if not replied or not replied.sender_id:
        await event.reply("❌ Reply ခံရသူကို ရှာမတွေ့ပါ။")
        return

    target_id = replied.sender_id

    try:
        sender = await bot.get_entity(target_id)
    except Exception:
        sender = None

    is_bot = bool(sender and getattr(sender, "bot", False))
    username = getattr(sender, "username", None) if sender else None
    display = (
        f"{getattr(sender, 'first_name', '') or ''} {getattr(sender, 'last_name', '') or ''}".strip()
        if sender else str(target_id)
    ) or str(target_id)

    try:
        await tracked_bots_col.update_one(
            {"bot_id": target_id, "chat_id": event.chat_id},
            {"$set": {
                "bot_id": target_id,
                "chat_id": event.chat_id,
                "username": username,
                "display_name": display,
                "is_bot": is_bot,
                "added_by": event.sender_id,
                "added_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )
        tracked_bots_cache[target_id] = event.chat_id
    except Exception as e:
        await event.reply(f"❌ DB save failed: {e}")
        return

    try:
        await replied.delete()
    except Exception:
        pass

    kind = "🤖 Bot" if is_bot else "👤 User"
    uname_str = f" (@{username})" if username else ""
    await event.reply(
        f"✅ <b>Tracked & Auto-Delete ON</b>\n\n"
        f"{kind}: {make_mention(display, target_id)}{uname_str}\n"
        f"🆔 {code(target_id)}\n"
        f"📍 Chat: {code(event.chat_id)}\n\n"
        f"<i>ဒီပုဂ္ဂိုလ်/bot ရဲ့ message တွေ နောက်ပိုင်း auto-delete ဖြစ်ပါမယ်။</i>\n"
        f"🛑 ဖျက်ချင်မှ ရပ်ရန်: <code>/untrack {target_id}</code>",
        parse_mode="html",
    )


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/untrack(\s|$)"))
@safe_handler("untrack_handler")
async def untrack_handler(event):
    if event.sender_id != OWNER_ID:
        return
    _, args = get_cmd_and_args(get_text(event))
    if not args or not args.split()[0].isdigit():
        await event.reply("⚠️ <b>Usage:</b> <code>/untrack [user_or_bot_id]</code>", parse_mode="html")
        return
    tid = int(args.split()[0])
    try:
        res = await tracked_bots_col.delete_one({"bot_id": tid, "chat_id": event.chat_id})
        tracked_bots_cache.pop(tid, None)
        if res.deleted_count:
            await event.reply(f"✅ Untracked {code(tid)}")
        else:
            await event.reply(f"ℹ️ {code(tid)} was not tracked.")
    except Exception as e:
        await event.reply(f"❌ Failed: {e}")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/tracked(\s|$)"))
@safe_handler("tracked_list_handler")
async def tracked_list_handler(event):
    if event.sender_id != OWNER_ID:
        return
    if not tracked_bots_cache:
        await event.reply("📭 <b>No tracked bots.</b>", parse_mode="html")
        return
    lines = [f"🤖 <b>Tracked Entities ({len(tracked_bots_cache)})</b>\n"]
    for i, bid in enumerate(tracked_bots_cache.keys(), 1):
        name = await get_user_name(bid)
        lines.append(f"{i}. {make_mention(name, bid)} — {code(bid)}")
    await event.reply("\n".join(lines), parse_mode="html")


# ============================================================
# 🔇  MUTE (5/day per admin)  ·  🔊  UNMUTE
# ============================================================
# 🔥 Aliases — both Burmese + English (case-insensitive via .lower())
MUTE_COMMANDS   = {"မြုလိုက်", "မြုလိုက်ပါ", "mute", "mutethatgay"}
UNMUTE_COMMANDS = {"ပြန်ဖွင့်", "ပြန်ဖွင့်", "ပြန်ဖွင့်ပါ", "ပြန်ဖွင့်ပါ", "unmute"}


def _mute_rights() -> ChatBannedRights:
    return ChatBannedRights(
        until_date=0,
        view_messages=False,
        send_messages=True,
        send_media=True,
        send_stickers=True,
        send_gifs=True,
        send_games=True,
        send_inline=True,
        embed_links=True,
        send_polls=True,
    )


def _unmute_rights() -> ChatBannedRights:
    return ChatBannedRights(until_date=0)


async def get_mute_count(admin_id: int, chat_id: int) -> int:
    doc = await mute_daily_col.find_one({
        "admin_id": admin_id, "chat_id": chat_id, "date": today_str(),
    })
    return int(doc["count"]) if doc else 0


async def increment_mute_count(admin_id: int, chat_id: int):
    await mute_daily_col.update_one(
        {"admin_id": admin_id, "chat_id": chat_id, "date": today_str()},
        {"$inc": {"count": 1}},
        upsert=True,
    )


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("mute_handler")
async def mute_handler(event):
    if not event.text:
        return

    trigger = event.text.strip()
    # ✂️ Strip @botname suffix (mutethatgay@MyBot → mutethatgay)
    if "@" in trigger:
        trigger = trigger.split("@", 1)[0].strip()
    trigger_lower = trigger.lower()

    is_mute = trigger_lower in MUTE_COMMANDS
    is_unmute = trigger_lower in UNMUTE_COMMANDS
    if not (is_mute or is_unmute):
        return

    # ---- Admin-only ----
    if not await is_admin(event.chat_id, event.sender_id):
        await event.reply(
            "❌ <b>Admin only</b>\nဒီ command ကို admin တွေပဲ သုံးနိုင်ပါတယ်။",
            parse_mode="html",
        )
        return

    # ---- Must be reply ----
    if not event.is_reply:
        word = "မြုလိုက်" if is_mute else "ပြန်ဖွင့်"
        await event.reply(
            f"⚠️ <b>Reply required</b>\n\n"
            f"📌 Reply ခံရသူကို <code>{word}</code> လုပ်ရန် သက်ဆိုင်ရာ message ကို reply ပြီး ရိုက်ပါ။",
            parse_mode="html",
        )
        return

    replied = await event.get_reply_message()
    if not replied or not replied.sender_id:
        await event.reply("❌ Reply ခံရသူကို ရှာမတွေ့ပါ။")
        return

    target_id = replied.sender_id

    # ---- Safety checks ----
    if target_id == event.sender_id:
        await event.reply("❌ ကိုယ့်ကိုယ်ကို မလုပ်နိုင်ပါ။")
        return
    if target_id == OWNER_ID:
        await event.reply("❌ Owner ကို mute မလုပ်နိုင်ပါ။")
        return
    if target_id < 0:
        await event.reply("❌ Channel post ကို mute မလုပ်နိုင်ပါ။")
        return

    try:
        target_user = await bot.get_entity(target_id)
        if target_user and getattr(target_user, "bot", False):
            await event.reply("❌ Bot ကို mute မလုပ်နိုင်ပါ။")
            return
    except Exception:
        target_user = None

    if await is_admin(event.chat_id, target_id):
        await event.reply("❌ Admin ကို mute မလုပ်နိုင်ပါ။")
        return

    target_name = await get_user_name(target_id)

    # ---- MUTE: check daily quota ----
    if is_mute:
        used = await get_mute_count(event.sender_id, event.chat_id)
        remaining = MUTE_DAILY_LIMIT - used
        if remaining <= 0:
            await event.reply(
                f"⏳ <b>Daily Mute Limit Reached</b>\n\n"
                f"📊 Daily quota: {code(MUTE_DAILY_LIMIT)} / day\n"
                f"✅ Used today: {code(used)}\n"
                f"🕛 Resets: <b>UTC 00:00</b> (မနက်ဖန်)\n\n"
                f"<i>Quota ပြန်ပြည့်တဲ့အထိ စောင့်ပါ။</i>",
                parse_mode="html",
            )
            return

    # ---- Execute ----
    try:
        if is_mute:
            await bot(EditBannedRequest(
                channel=event.chat_id,
                participant=target_id,
                banned_rights=_mute_rights(),
            ))
            await increment_mute_count(event.sender_id, event.chat_id)
            used_after = await get_mute_count(event.sender_id, event.chat_id)
            remaining_after = max(0, MUTE_DAILY_LIMIT - used_after)

            await event.reply(
                f"🔇 <b>Muted Successfully</b>\n\n"
                f"👤 {make_mention(target_name, target_id)}\n"
                f"🚫 Text · Photo/Video · Sticker · GIF · Voice · Inline · Links · Polls\n\n"
                f"📊 <b>Your daily quota:</b> {code(used_after)} / {code(MUTE_DAILY_LIMIT)}\n"
                f"🎫 <b>Remaining today:</b> {code(remaining_after)}",
                parse_mode="html",
            )
            print(f"🔇 Muted {target_id} in {event.chat_id} by {event.sender_id} "
                  f"(used {used_after}/{MUTE_DAILY_LIMIT})")
        else:
            await bot(EditBannedRequest(
                channel=event.chat_id,
                participant=target_id,
                banned_rights=_unmute_rights(),
            ))
            await event.reply(
                f"🔊 <b>Unmuted</b>\n\n"
                f"👤 {make_mention(target_name, target_id)}\n"
                f"✅ User can send messages again.",
                parse_mode="html",
            )
            print(f"🔊 Unmuted {target_id} in {event.chat_id} by {event.sender_id}")
    except Exception as e:
        err = str(e)
        if any(k in err.lower() for k in ("admin", "right", "permission", "chat_admin_required")):
            await event.reply(
                "❌ <b>Bot has insufficient permissions</b>\n\n"
                "🤖 Bot ကို admin ပေးပြီး <b>Ban Users</b> right ဖွင့်ထားပါ။",
                parse_mode="html",
            )
        else:
            await event.reply(f"❌ မအောင်မြင်ပါ:\n<code>{err}</code>", parse_mode="html")
        print(f"❌ mute/unmute error: {e}")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/mutecount(\s|$)"))
@safe_handler("mutecount_handler")
async def mutecount_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    used = await get_mute_count(event.sender_id, event.chat_id)
    remaining = max(0, MUTE_DAILY_LIMIT - used)
    bar_total = MUTE_DAILY_LIMIT
    filled = min(used, bar_total)
    bar = "🟩" * filled + "⬜" * (bar_total - filled)

    await event.reply(
        f"📊 <b>Your Mute Quota Today</b>\n\n"
        f"{bar}\n"
        f"✅ Used: {code(used)} / {code(MUTE_DAILY_LIMIT)}\n"
        f"🎫 Remaining: {code(remaining)}\n"
        f"🕛 Resets: <b>UTC 00:00</b>",
        parse_mode="html",
    )


# ============================================================
# 📌  PIN / UNPIN
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/pin(\s|$)"))
@safe_handler("pin_handler")
async def pin_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.reply("❌ Admin only.")
        return
    if not event.is_reply:
        await event.reply(
            "⚠️ <b>Usage</b>\n\n"
            "📌 Pin လုပ်ချင်တဲ့ message ကို <b>reply</b> ပြီး <code>/pin</code> ရိုက်ပါ။",
            parse_mode="html",
        )
        return
    replied = await event.get_reply_message()
    try:
        await bot(UpdatePinnedMessageRequest(
            peer=event.chat_id, id=replied.id, silent=False,
        ))
        await event.reply(
            f"📌 <b>Pinned</b>\n\n🆔 Message: {code(replied.id)}",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"❌ Pin failed: <code>{e}</code>", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/unpin(\s|$)"))
@safe_handler("unpin_handler")
async def unpin_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.reply("❌ Admin only.")
        return
    if not event.is_reply:
        await event.reply(
            "⚠️ <b>Usage</b>\n\n"
            "📌 Unpin လုပ်ချင်တဲ့ message ကို <b>reply</b> ပြီး <code>/unpin</code> ရိုက်ပါ။",
            parse_mode="html",
        )
        return
    replied = await event.get_reply_message()
    try:
        await bot(UpdatePinnedMessageRequest(
            peer=event.chat_id, id=replied.id, unpin=True,
        ))
        await event.reply(
            f"📌 <b>Unpinned</b>\n\n🆔 Message: {code(replied.id)}",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"❌ Unpin failed: <code>{e}</code>", parse_mode="html")


# ============================================================
# 👥  ADMIN MENTION
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/admins(\s|$)"))
@safe_handler("admins_handler")
async def admins_handler(event):
    admins = await get_admin_list(event.chat_id)
    title = await get_group_title(event.chat_id)
    if not admins:
        await event.reply("📭 <b>No admin data found.</b>", parse_mode="html")
        return
    lines = [f"👥 <b>{title}</b>\n📊 <b>Admins ({len(admins)}):</b>\n"]
    for i, (uid, name) in enumerate(admins, 1):
        lines.append(f"{i}. {make_mention(name, uid)} — {code(uid)}")
    await event.reply("\n".join(lines), parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/report(\s|$)"))
@safe_handler("report_handler")
async def report_handler(event):
    if not event.is_reply:
        await event.reply(
            "⚠️ <b>Report a message</b>\n\n"
            "🚨 Report လုပ်ချင်တဲ့ message ကို <b>reply</b> ပြီး <code>/report</code> ရိုက်ပါ။\n"
            "📣 Admin အားလုံးကို alert ဖြစ်ပါမယ်။",
            parse_mode="html",
        )
        return
    replied = await event.get_reply_message()
    admins = await get_admin_list(event.chat_id)
    admin_mentions = " ".join(make_mention(name, uid) for uid, name in admins)
    reporter = await event.get_sender()
    reporter_name = (
        f"{getattr(reporter, 'first_name', '') or ''} "
        f"{getattr(reporter, 'last_name', '') or ''}"
    ).strip() or "User"

    await event.reply(
        f"🚨 <b>REPORT RECEIVED</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Reporter:</b> {make_mention(reporter_name, event.sender_id)}\n"
        f"🆔 <b>Message ID:</b> {code(replied.id)}\n\n"
        f"🔔 <b>Alerting Admins:</b>\n{admin_mentions}\n\n"
        f"<i>Admin တစ်ယောက်ယောက်က စစ်ဆေးပေးပါ။</i>",
        parse_mode="html",
        reply_to=replied.id,
    )


# ============================================================
# ⚠️  WARN SYSTEM
# ============================================================
async def _resolve_target(event):
    if event.is_reply:
        r = await event.get_reply_message()
        if r and r.sender_id:
            return r.sender_id, None
    _, args = get_cmd_and_args(get_text(event))
    if not args:
        return None, "No target"
    tok = args.split()[0]
    try:
        if tok.startswith("@"):
            u = await bot.get_entity(tok)
            return u.id, args[len(tok):].strip()
        return int(tok), args[len(tok):].strip()
    except Exception:
        return None, "Invalid target"


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/warn(\s|$)"))
@safe_handler("warn_handler")
async def warn_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    tid, reason = await _resolve_target(event)
    if not tid:
        await event.reply(
            "⚠️ <b>Usage</b>\n\n"
            "<code>/warn @user reason</code>\n"
            "or reply to a message: <code>/warn reason</code>",
            parse_mode="html",
        )
        return
    if await is_admin(event.chat_id, tid):
        await event.reply("❌ Admin ကို warn မလုပ်နိုင်ပါ။")
        return
    if tid < 0:
        await event.reply("❌ Channel post ကို warn မလုပ်နိုင်ပါ။")
        return

    reason = (reason or "no reason").strip()[:200]
    doc = await warns_col.find_one_and_update(
        {"chat_id": event.chat_id, "user_id": tid},
        {
            "$inc": {"count": 1},
            "$push": {"reasons": {"$each": [reason], "$slice": -20}},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
        upsert=True,
        return_document=True,
    )
    count = int(doc.get("count", 1)) if doc else 1
    target_name = await get_user_name(tid)

    action_note = ""
    if count >= DEFAULT_WARN_LIMIT:
        try:
            until = int(_tm.time() + 3600)
            await bot(EditBannedRequest(
                channel=event.chat_id,
                participant=tid,
                banned_rights=ChatBannedRights(
                    until_date=until, view_messages=False,
                    send_messages=True, send_media=True,
                    send_stickers=True, send_gifs=True,
                    send_games=True, send_inline=True,
                    embed_links=True, send_polls=True,
                ),
            ))
            action_note = f"\n\n🔇 <b>Auto-muted for 1h</b> ({DEFAULT_WARN_LIMIT} warns reached)"
        except Exception as e:
            action_note = f"\n\n⚠️ Auto-mute failed: {code(e)}"

    await event.reply(
        f"⚠️ <b>Warning Issued</b>\n\n"
        f"👤 {make_mention(target_name, tid)}\n"
        f"📝 Reason: {code(reason)}\n"
        f"📊 Total warns: {code(count)} / {code(DEFAULT_WARN_LIMIT)}{action_note}",
        parse_mode="html",
    )


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/unwarn(\s|$)"))
@safe_handler("unwarn_handler")
async def unwarn_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    tid, _ = await _resolve_target(event)
    if not tid:
        await event.reply("⚠️ <b>Usage:</b> <code>/unwarn @user</code>", parse_mode="html")
        return
    doc = await warns_col.find_one({"chat_id": event.chat_id, "user_id": tid})
    if not doc or not doc.get("count"):
        await event.reply("ℹ️ ဒီ user မှာ warns မရှိပါ။")
        return
    new_count = int(doc["count"]) - 1
    if new_count <= 0:
        await warns_col.delete_one({"chat_id": event.chat_id, "user_id": tid})
        new_count = 0
    else:
        await warns_col.update_one(
            {"chat_id": event.chat_id, "user_id": tid},
            {"$set": {"count": new_count}, "$pop": {"reasons": 1}},
        )
    target_name = await get_user_name(tid)
    await event.reply(
        f"✅ <b>Warn Removed</b>\n\n"
        f"👤 {make_mention(target_name, tid)}\n"
        f"📊 Total warns: {code(new_count)}",
        parse_mode="html",
    )


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/warns(\s|$)"))
@safe_handler("warns_handler")
async def warns_handler(event):
    tid, _ = await _resolve_target(event)
    if not tid:
        await event.reply("⚠️ <b>Usage:</b> <code>/warns @user</code>", parse_mode="html")
        return
    doc = await warns_col.find_one({"chat_id": event.chat_id, "user_id": tid})
    target_name = await get_user_name(tid)
    if not doc or not doc.get("count"):
        await event.reply(
            f"✅ <b>Clean record</b>\n\n👤 {make_mention(target_name, tid)}",
            parse_mode="html",
        )
        return
    reasons = doc.get("reasons", [])[-5:]
    lines = [
        f"⚠️ <b>Warns for</b> {make_mention(target_name, tid)}\n",
        f"📊 <b>Total:</b> {code(doc['count'])} / {code(DEFAULT_WARN_LIMIT)}\n",
        f"📝 <b>Recent reasons:</b>",
    ]
    for r in reasons:
        lines.append(f"   • {code(r)}")
    await event.reply("\n".join(lines), parse_mode="html")


# ============================================================
# 👢  KICK / BAN / UNBAN
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/kick(\s|$)"))
@safe_handler("kick_handler")
async def kick_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    tid, _ = await _resolve_target(event)
    if not tid:
        await event.reply("⚠️ <b>Usage:</b> <code>/kick @user</code>", parse_mode="html")
        return
    if await is_admin(event.chat_id, tid) or tid == OWNER_ID:
        await event.reply("❌ Admin ကို kick မလုပ်နိုင်ပါ။")
        return
    try:
        until = int(_tm.time() + KICK_BAN_SECONDS)
        await bot(EditBannedRequest(
            channel=event.chat_id,
            participant=tid,
            banned_rights=ChatBannedRights(until_date=until, view_messages=True),
        ))
        name = await get_user_name(tid)
        await event.reply(
            f"👢 <b>Kicked</b>\n\n"
            f"👤 {make_mention(name, tid)}\n"
            f"⏱️ Duration: {code(KICK_BAN_SECONDS)}s",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"❌ Kick failed: <code>{e}</code>", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/ban(\s|$)"))
@safe_handler("ban_handler")
async def ban_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    tid, reason = await _resolve_target(event)
    if not tid:
        await event.reply("⚠️ <b>Usage:</b> <code>/ban @user [reason]</code>", parse_mode="html")
        return
    if await is_admin(event.chat_id, tid) or tid == OWNER_ID:
        await event.reply("❌ Admin ကို ban မလုပ်နိုင်ပါ။")
        return
    try:
        await bot(EditBannedRequest(
            channel=event.chat_id,
            participant=tid,
            banned_rights=ChatBannedRights(
                until_date=0, view_messages=True,
                send_messages=True, send_media=True,
                send_stickers=True, send_gifs=True,
                send_games=True, send_inline=True,
                embed_links=True, send_polls=True,
            ),
        ))
        name = await get_user_name(tid)
        await event.reply(
            f"🚫 <b>Banned</b>\n\n"
            f"👤 {make_mention(name, tid)}\n"
            f"📝 Reason: {code(reason or 'no reason')}",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"❌ Ban failed: <code>{e}</code>", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/unban(\s|$)"))
@safe_handler("unban_handler")
async def unban_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    tid, _ = await _resolve_target(event)
    if not tid:
        await event.reply("⚠️ <b>Usage:</b> <code>/unban @user</code>", parse_mode="html")
        return
    try:
        await bot(EditBannedRequest(
            channel=event.chat_id, participant=tid,
            banned_rights=ChatBannedRights(until_date=0),
        ))
        name = await get_user_name(tid)
        await event.reply(
            f"✅ <b>Unbanned</b>\n\n👤 {make_mention(name, tid)}",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"❌ Unban failed: <code>{e}</code>", parse_mode="html")


# ============================================================
# 🧹  PURGE
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/purge(\s|$)"))
@safe_handler("purge_handler")
async def purge_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    if not event.is_reply:
        await event.reply(
            "⚠️ <b>Usage</b>\n\n"
            "🧹 ဖျက်ချင်တဲ့ message ကို <b>reply</b> ပြီး <code>/purge</code> ရိုက်ပါ။\n"
            "📌 Reply ခံရတဲ့ message ကနေ လက်ရှိ message အထိ ဖျက်ပါမယ်။",
            parse_mode="html",
        )
        return
    replied = await event.get_reply_message()
    start_id = replied.id
    end_id = event.id
    ids = list(range(start_id, end_id + 1))

    deleted = 0
    for i in range(0, len(ids), 100):
        batch = ids[i:i + 100]
        try:
            await bot.delete_messages(event.chat_id, batch)
            deleted += len(batch)
        except Exception as e:
            print(f"⚠️ purge batch error: {e}")

    try:
        await event.reply(
            f"🧹 <b>Purge Complete</b>\n\n"
            f"🗑️ Deleted: {code(deleted)} messages",
            parse_mode="html",
        )
    except Exception:
        pass


# ============================================================
# 📖  RULES
# ============================================================
async def get_settings(chat_id: int) -> dict:
    doc = await settings_col.find_one({"chat_id": chat_id})
    if not doc:
        return {"chat_id": chat_id, "welcome": WELCOME_DEFAULT, "rules": ""}
    return doc


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/setrules(\s|$)"))
@safe_handler("setrules_handler")
async def setrules_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    _, args = get_cmd_and_args(get_text(event))
    if not args:
        await event.reply(
            "⚠️ <b>Usage:</b> <code>/setrules [text]</code>",
            parse_mode="html",
        )
        return
    await settings_col.update_one(
        {"chat_id": event.chat_id},
        {"$set": {"rules": args, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    await event.reply("✅ <b>Rules saved.</b>", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/rules(\s|$)"))
@safe_handler("rules_handler")
async def rules_handler(event):
    s = await get_settings(event.chat_id)
    rules = s.get("rules") or ""
    if not rules:
        await event.reply(
            "📭 <b>No rules set yet.</b>\n\n"
            "ℹ️ Admin: <code>/setrules [text]</code>",
            parse_mode="html",
        )
        return
    await event.reply(
        f"📖 <b>GROUP RULES</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{rules}",
        parse_mode="html",
    )


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/clearrules(\s|$)"))
@safe_handler("clearrules_handler")
async def clearrules_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    await settings_col.update_one(
        {"chat_id": event.chat_id},
        {"$set": {"rules": ""}},
        upsert=True,
    )
    await event.reply("🗑️ <b>Rules cleared.</b>", parse_mode="html")


# ============================================================
# 🎉  WELCOME (toggle)
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/welcome(\s|$)"))
@safe_handler("welcome_toggle_handler")
async def welcome_toggle_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    _, args = get_cmd_and_args(get_text(event))
    s = await get_settings(event.chat_id)
    current = bool(s.get("welcome", WELCOME_DEFAULT))

    if args.lower() in ("on", "enable", "yes"):
        new_val = True
    elif args.lower() in ("off", "disable", "no"):
        new_val = False
    elif not args:
        new_val = not current
    else:
        await event.reply("⚠️ <b>Usage:</b> <code>/welcome on</code> or <code>/welcome off</code>", parse_mode="html")
        return

    await settings_col.update_one(
        {"chat_id": event.chat_id},
        {"$set": {"welcome": new_val}},
        upsert=True,
    )
    icon = "🟢" if new_val else "🔴"
    await event.reply(
        f"{icon} <b>Welcome message: {'ON' if new_val else 'OFF'}</b>",
        parse_mode="html",
    )


@bot.on(events.ChatAction(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("welcome_new_member_handler")
async def welcome_new_member_handler(event):
    if not (event.user_joined or event.user_added):
        return
    s = await get_settings(event.chat_id)
    if not s.get("welcome", False):
        return

    user_id = None
    try:
        user_id = event.user_id
    except Exception:
        pass
    if not user_id:
        return

    name = await get_user_name(user_id)

    count_str = "—"
    try:
        full = await bot(GetFullChannelRequest(event.chat_id))
        count_str = f"{full.full_chat.participants_count}"
    except Exception:
        pass

    await bot.send_message(
        event.chat_id,
        f"🎉 <b>Welcome!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 {make_mention(name, user_id)}\n"
        f"🏛️ မှ ကြိုဆိုပါတယ်။\n\n"
        f"📖 <b>Rules:</b> /rules\n"
        f"👥 <b>Members:</b> {code(count_str)}\n"
        f"🆔 <b>Your ID:</b> {code(user_id)}\n\n"
        f"<i>ပျော်ရွှင်စွာ ပါဝင်ဆွေးနွေးပါ။</i>",
        parse_mode="html",
    )


# ============================================================
# 📊  STATS & INFO
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/stats(\s|$)"))
@safe_handler("stats_handler")
async def stats_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    title = await get_group_title(event.chat_id)
    admins = await get_admin_list(event.chat_id)
    tracked = len(tracked_bots_cache)

    count_str = "—"
    try:
        full = await bot(GetFullChannelRequest(event.chat_id))
        count_str = f"{full.full_chat.participants_count}"
    except Exception:
        pass

    today = today_str()
    total_mutes = 0
    try:
        async for d in mute_daily_col.find({"chat_id": event.chat_id, "date": today}):
            total_mutes += int(d.get("count", 0))
    except Exception:
        pass

    await event.reply(
        f"📊 <b>GROUP STATS</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🏛️ <b>Title:</b> {code(title)}\n"
        f"🆔 <b>Chat ID:</b> {code(event.chat_id)}\n"
        f"👥 <b>Members:</b> {code(count_str)}\n"
        f"🛡️ <b>Admins:</b> {code(len(admins))}\n"
        f"🤖 <b>Tracked bots:</b> {code(tracked)}\n"
        f"🔇 <b>Mutes today:</b> {code(total_mutes)} / {code(len(admins) * MUTE_DAILY_LIMIT)}\n"
        f"🕛 <b>Date (UTC):</b> {code(today)}",
        parse_mode="html",
    )


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/id(\s|$)"))
@safe_handler("id_handler")
async def id_handler(event):
    if event.is_reply:
        r = await event.get_reply_message()
        if r and r.sender_id:
            name = await get_user_name(r.sender_id)
            await event.reply(
                f"🆔 <b>User ID</b>\n\n"
                f"👤 {make_mention(name, r.sender_id)}\n"
                f"🔢 {code(r.sender_id)}",
                parse_mode="html",
            )
            return
    sender = await event.get_sender()
    name = (
        f"{getattr(sender, 'first_name', '') or ''} "
        f"{getattr(sender, 'last_name', '') or ''}"
    ).strip() or "User"
    await event.reply(
        f"🆔 <b>Chat Info</b>\n\n"
        f"👤 <b>You:</b> {make_mention(name, event.sender_id)}\n"
        f"🔢 <b>Your ID:</b> {code(event.sender_id)}\n"
        f"🏛️ <b>Chat ID:</b> {code(event.chat_id)}\n"
        f"📝 <b>Message ID:</b> {code(event.message.id)}",
        parse_mode="html",
    )


# ============================================================
# 📖  /start  &  /help
# ============================================================
@bot.on(events.NewMessage(pattern=r"^/start(\s|$)"))
@safe_handler("start_handler")
async def start_handler(event):
    if event.chat_id != OWNER_ID and event.chat_id != OFFICIAL_GROUP_ID:
        return
    await event.reply(
        "🏛️ <b>SUPER MANAGEMENT BOT</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "✅ System Online\n"
        "🛡️ Moderation ready\n"
        "📌 Pin system ready\n"
        "🤖 Bot-tracking active\n"
        "🔇 Mute quota: " + code(MUTE_DAILY_LIMIT) + " / day / admin\n\n"
        "📖 Commands အားလုံးကြည့်ရန်: /help",
        parse_mode="html",
    )


@bot.on(events.NewMessage(pattern=r"^/help(\s|$)"))
@safe_handler("help_handler")
async def help_handler(event):
    if event.chat_id != OWNER_ID and event.chat_id != OFFICIAL_GROUP_ID:
        return
    text = (
        "📖 <b>COMMAND LIST</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🛡️ <b>Moderation</b>\n"
        "• Reply + <code>မြုလိုက်</code> — mute (5/day)\n"
        "• Reply + <code>mutethatgay</code> — same as မြုလိုက်\n"
        "• Reply + <code>ပြန်ဖွင့်</code> — unmute\n"
        "• <code>/warn @user reason</code>\n"
        "• <code>/unwarn @user</code>\n"
        "• <code>/warns @user</code>\n"
        "• <code>/kick @user</code>\n"
        "• <code>/ban @user reason</code>\n"
        "• <code>/unban @user</code>\n"
        "• Reply + <code>/purge</code> — delete range\n\n"
        "📌 <b>Pinning</b>\n"
        "• Reply + <code>/pin</code>\n"
        "• Reply + <code>/unpin</code>\n\n"
        "👥 <b>Admin & Info</b>\n"
        "• <code>/admins</code> — list admins\n"
        "• Reply + <code>/report</code> — alert admins\n"
        "• <code>/id</code> — chat/user IDs\n"
        "• <code>/stats</code> — group stats\n"
        "• <code>/mutecount</code> — your quota\n\n"
        "🤖 <b>Bot Tracking (Owner)</b>\n"
        "• Reply + <code>/del</code> or <code>ဖျက်မယ်</code> — track & auto-delete\n"
        "• <code>/untrack [id]</code>\n"
        "• <code>/tracked</code> — list tracked\n\n"
        "📖 <b>Rules & Welcome</b>\n"
        "• <code>/setrules [text]</code>\n"
        "• <code>/rules</code>\n"
        "• <code>/clearrules</code>\n"
        "• <code>/welcome on/off</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔇 Mute quota: {code(MUTE_DAILY_LIMIT)} / day / admin\n"
        f"🕛 Resets UTC 00:00\n"
        f"ℹ️ Alias အားလုံး <code>@botname</code> ပါလည်း အလုပ်လုပ်ပါတယ်။"
    )
    await event.reply(text, parse_mode="html")


# ============================================================
# 🌍  RENDER HEALTH CHECK
# ============================================================
async def _health(reader, writer):
    await reader.read(100)
    writer.write(
        b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nOK"
    )
    await writer.drain()
    writer.close()

async def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        srv = await asyncio.start_server(_health, "0.0.0.0", port)
        async with srv:
            await srv.serve_forever()
    except Exception:
        pass


# ============================================================
# 🚀  STARTUP
# ============================================================
async def startup():
    print("⏳ Super Management Bot starting...")
    asyncio.create_task(start_health_server())

    try:
        await bot.start(bot_token=BOT_TOKEN)
        me = await _ensure_me()
        print(f"🤖 Bot connected: @{_my_username} (id={me})")
    except Exception as e:
        print(f"❌ Bot start failed: {e}")
        return

    await load_tracked_bots()

    try:
        await bot.send_message(
            OWNER_ID,
            "🟢 <b>Super Management Bot ONLINE</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"🏛️ Target group: {code(OFFICIAL_GROUP_ID)}\n"
            f"🗑️ Auto-delete: {code('ON')} (photo/video, keeps inline-bot)\n"
            f"🔇 Mute quota: {code(MUTE_DAILY_LIMIT)} / day / admin\n"
            f"📌 Pin system: {code('ON')}\n"
            f"🤖 Tracked bots loaded: {code(len(tracked_bots_cache))}\n"
            f"👥 Admin cache TTL: {code(ADMIN_CACHE_TTL)}s\n\n"
            "💡 /help — full command list\n"
            "🔤 Aliases: <code>မြုလိုက်</code> · <code>mutethatgay</code> · <code>ဖျက်မယ်</code>",
            parse_mode="html",
        )
    except Exception:
        pass

    print("🚀 Ready. Listening...")
    await bot.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(startup())
