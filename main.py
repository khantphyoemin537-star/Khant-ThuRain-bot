# ============================================================
# 🏛️  BOD MANAGER  —  main.py (standalone)
# ============================================================
# Python 3.14+ compatible
# NEW: 🚫 Badword filter — warn + auto-mute (5min window)
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
    EditAdminRequest, GetParticipantRequest,
)
from telethon.tl.functions.messages import (
    UpdatePinnedMessageRequest, EditChatDefaultBannedRightsRequest,
)
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import (
    ChatBannedRights, ChannelParticipantsAdmins, ChatAdminRights,
    MessageEntityUrl, MessageEntityTextUrl, MessageEntityMention,
    ChannelParticipantAdmin, ChannelParticipantBanned,
    ChannelParticipantCreator,
)
from motor.motor_asyncio import AsyncIOMotorClient


# ============================================================
# ⚙️  CONFIG
# ============================================================
APP_ID   = 39584681
APP_HASH = 'c8c0685d6dd5b9e546093ea90d27733b'
MONGO_URI = "mongodb+srv://kkt:h1BdaMt7nxW9jTXa@cluster0.kb5fzfl.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"
BOT_TOKEN = '8738081667:AAHADgcDISntnOBwT3uj2yYw7n3XJUN2uZI'

OWNER_ID          = 6015356597
OWNER_USERNAME    = "Hello_Im_DexterMorgan"
OFFICIAL_GROUP_ID = -1004478099253

MUTE_DAILY_LIMIT        = 5
KICK_BAN_SECONDS        = 60
ADMIN_CACHE_TTL         = 120
WELCOME_DEFAULT         = False
DEFAULT_WARN_LIMIT      = 3
REPORT_COOLDOWN_SECONDS = 3 * 60 * 60
REPORT_REMINDER_SECONDS = 3 * 60 * 60
AFK_REPLY_COOLDOWN      = 60

# 🚫 Badword filter
BADWORDS = [
    "ဖာသယ်မ", "ဖာသည်မ",
    "ဖာသယ်မသား", "ဖာသည်မသား",
    "လီး", "မှန်းထု", "မှန်း", "လိုး",
    "မအေလိုး", "ငါလိုးမသား",
]
BADWORD_WINDOW_SECONDS = 5 * 60      # 5 minutes
BADWORD_MUTE_DURATION  = 60 * 60     # 1 hour


# ============================================================
# 🔧  PYTHON 3.14+ EVENT LOOP FIX
# ============================================================
try:
    _loop = asyncio.get_running_loop()
except RuntimeError:
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)


# ============================================================
# 🗄️  DATABASE
# ============================================================
_mongo = AsyncIOMotorClient(MONGO_URI, io_loop=_loop)
db = _mongo["group_manager"]

tracked_bots_col    = db["tracked_bots"]
mute_daily_col      = db["mute_daily"]
warns_col           = db["warns"]
settings_col        = db["group_settings"]
report_cooldown_col = db["report_cooldown"]


# ============================================================
# 🤖  BOT CLIENT
# ============================================================
bot = TelegramClient('manager_bot_session', APP_ID, APP_HASH, loop=_loop)

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
# 📴  AFK STATE
# ============================================================
afk_state = {"enabled": False, "since": None, "reply_cooldown": {}}

# 🚫 Badword tracking
badword_tracker: dict[tuple, list] = {}


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


def strip_bot_suffix(text: str) -> str:
    t = (text or "").strip()
    if "@" in t:
        first = t.split()[0]
        if "@" in first:
            return t.replace(first, first.split("@", 1)[0], 1).strip()
    return t


# ---------------- LINK DETECTION ----------------
LINK_REGEX = re.compile(
    r"(?:https?://|ftp://|www\.|t\.me/|telegram\.me/|tg://)",
    re.IGNORECASE,
)


async def _has_link(message) -> bool:
    if not message:
        return False
    text = message.text or message.message or ""
    if LINK_REGEX.search(text):
        return True
    try:
        entities = getattr(message, "entities", None) or []
        for ent in entities:
            if isinstance(ent, (MessageEntityUrl, MessageEntityTextUrl)):
                return True
    except Exception:
        pass
    return False


# ---------------- BADWORD DETECTION ----------------
def _contains_badword(text: str) -> str | None:
    """Return the matching badword if found, else None."""
    if not text:
        return None
    t = clean_invisible(text)
    for bw in BADWORDS:
        if bw in t:
            return bw
    return None


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
        out, seen = [], set()
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


async def _resolve_target(event):
    if event.is_reply:
        r = await event.get_reply_message()
        if r and r.sender_id:
            return r.sender_id
    _, args = get_cmd_and_args(get_text(event))
    if not args:
        return None
    tok = args.split()[0]
    try:
        if tok.startswith("@"):
            u = await bot.get_entity(tok)
            return u.id
        return int(tok)
    except Exception:
        return None


# ============================================================
# 🚫  BADWORD FILTER HANDLER (NEW)
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("badword_filter_handler")
async def badword_filter_handler(event):
    if not event.text:
        return

    sender_id = event.sender_id
    chat_id = event.chat_id

    # Skip admins (they're trusted)
    try:
        if await is_admin(chat_id, sender_id):
            return
    except Exception:
        pass

    # Skip bots
    try:
        sender = await event.get_sender()
        if getattr(sender, "bot", False):
            return
    except Exception:
        pass

    badword = _contains_badword(event.text)
    if not badword:
        return

    name = await get_user_name(sender_id)
    mention = make_mention(name, sender_id)

    # Track violations within 5-min window
    key = (chat_id, sender_id)
    now = _tm.time()
    history = [t for t in badword_tracker.get(key, []) if now - t < BADWORD_WINDOW_SECONDS]
    history.append(now)
    badword_tracker[key] = history

    # ---- 2nd+ violation within 5 min → 1h mute ----
    if len(history) >= 2:
        try:
            until = int(now + BADWORD_MUTE_DURATION)
            await bot(EditBannedRequest(
                channel=chat_id,
                participant=sender_id,
                banned_rights=ChatBannedRights(
                    until_date=until, view_messages=False,
                    send_messages=True, send_media=True,
                    send_stickers=True, send_gifs=True,
                    send_games=True, send_inline=True,
                    embed_links=True, send_polls=True,
                ),
            ))
            expiry = datetime.fromtimestamp(until, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            await event.reply(
                f"🔇 <b>Muted — 1 Hour</b>\n\n"
                f"👤 {mention}\n\n"
                f"🚫 <b>Reason:</b> Repeated use of inappropriate language "
                f"(within 5 minutes of first warning).\n\n"
                f"⏱️ <b>Duration:</b> 1 hour\n"
                f"🕒 <b>Expires:</b> {code(expiry)}\n\n"
                f"<i>Use this time to review the group rules: /rules</i>\n"
                f"<i>Respect is mutual — treat others the way you want to be treated.</i>",
                parse_mode="html",
                reply_to=event.id,
            )
            badword_tracker.pop(key, None)
            print(f"🔇 Badword mute: {sender_id} (matched: {badword})")
        except Exception as e:
            await event.reply(
                f"❌ Mute failed: {code(str(e))}",
                parse_mode="html",
            )
            print(f"❌ Badword mute failed: {e}")
        return

    # ---- 1st violation → warning only (no delete) ----
    try:
        await event.reply(
            f"⚠️ <b>Don't be rude, kid.</b> {mention}\n\n"
            f"Bad words aren't allowed in <b>The BODgram</b> group. "
            f"The owner and admins will treat you with respect as long as "
            f"you behave respectfully too.\n\n"
            f"<i>⚠️ Note: Using bad words again within 5 minutes will result in a 1-hour mute.</i>",
            parse_mode="html",
            reply_to=event.id,
        )
        print(f"⚠️ Badword warning: {sender_id} (matched: {badword})")
    except Exception as e:
        print(f"❌ Badword warning failed: {e}")


# ============================================================
# 🗑️  AUTO-DELETE MEDIA + LINKS + TRACKED-BOT CLEANER
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

    if sender_id in tracked_bots_cache:
        try:
            await event.delete()
        except Exception as e:
            print(f"❌ tracked-bot delete failed: {e}")
        return

    if sender_id == my_id:
        return

    try:
        sender = await event.get_sender()
        if getattr(sender, "bot", False):
            return
    except Exception:
        pass

    try:
        if await is_admin(chat_id, sender_id):
            return
    except Exception as e:
        print(f"⚠️ admin check failed: {e}")

    if getattr(msg, "sticker", None):
        return

    if getattr(msg, "gif", False):
        return
    try:
        if msg.document:
            for attr in (msg.document.attributes or []):
                if attr.__class__.__name__ == "DocumentAttributeAnimated":
                    return
    except Exception:
        pass

    via_bot = getattr(event, "via_bot_id", None) or getattr(msg, "via_bot_id", None)
    is_media     = bool(msg.photo or msg.video)
    delete_media = is_media and not via_bot
    delete_link  = False
    if not via_bot:
        try:
            delete_link = await _has_link(msg)
        except Exception:
            pass

    if not (delete_media or delete_link):
        return

    try:
        await event.delete()
        print(f"🗑️ Auto-deleted msg={msg.id} sender={sender_id} media={delete_media} link={delete_link}")
    except Exception as e:
        print(f"❌ auto-delete failed: {e}")

    if delete_link:
        try:
            name = await get_user_name(sender_id)
            await bot.send_message(
                chat_id,
                f"🚫 Don't send link Son {make_mention(name, sender_id)}",
                parse_mode="html",
            )
        except Exception as e:
            print(f"❌ link warning failed: {e}")


# ============================================================
# 📴  AFK MENTION AUTO-REPLY
# ============================================================
AFK_EN_MSG = (
    "Owner Morgan is currently AFK.\n\n"
    "He might be busy, resting, studying, watching a movie, or gaming. "
    "Please leave your message, and he'll reply when he's back online."
)
AFK_MM_MSG = (
    "Owner Morgan လောလောဆယ် AFK ဖြစ်နေပါတယ်။\n\n"
    "အလုပ်များနေတာ၊ အနားယူနေတာ၊ စာလေ့လာနေတာ၊ Movie ကြည့်နေတာ "
    "ဒါမှမဟုတ် Game ဆော့နေတာ ဖြစ်နိုင်ပါတယ်။ ပြောစရာရှိတာတွေ တစ်ခါတည်း ရေးထားပေးပါ။ "
    "Online ပြန်တက်လာရင် Reply ပြန်ပေးပါလိမ့်မယ်။"
)


def _mentions_owner(message) -> bool:
    text = (message.text or message.message or "").lower()
    target = OWNER_USERNAME.lower()
    if f"@{target}" in text:
        return True
    try:
        for ent in (message.entities or []):
            if isinstance(ent, MessageEntityMention):
                mentioned = text[ent.offset:ent.offset + ent.length].lstrip("@").lower()
                if mentioned == target:
                    return True
    except Exception:
        pass
    return False


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("afk_mention_handler")
async def afk_mention_handler(event):
    if not afk_state["enabled"]:
        return
    if not event.text and not event.message:
        return

    sender_id = event.sender_id
    if sender_id in (OWNER_ID, await _ensure_me()):
        return

    msg = event.message
    triggered = _mentions_owner(msg)
    if not triggered and event.is_reply:
        try:
            replied = await event.get_reply_message()
            if replied and replied.sender_id == OWNER_ID:
                triggered = True
        except Exception:
            pass

    if not triggered:
        return

    now = _tm.time()
    cooldowns = afk_state["reply_cooldown"]
    last = cooldowns.get(sender_id, 0)
    if now - last < AFK_REPLY_COOLDOWN:
        return
    cooldowns[sender_id] = now

    try:
        await event.reply(
            f"📴 {AFK_EN_MSG}\n\n━━━━━━━━━━━━━━━━━━\n\n{AFK_MM_MSG}",
        )
        print(f"📴 AFK reply sent to {sender_id}")
    except Exception as e:
        print(f"❌ AFK reply failed: {e}")


# ============================================================
# 🚨  REPORT
# ============================================================
@bot.on(events.NewMessage(
    chats=[OFFICIAL_GROUP_ID],
    pattern=r"^(?:/report|report)(?:@\w+)?(?:\s|$)",
))
@safe_handler("report_handler")
async def report_handler(event):
    text = (event.text or "").strip()
    is_slash = text.startswith("/")

    if not event.is_reply:
        if is_slash:
            await event.reply(
                "⚠️ <b>Report a message</b>\n\n"
                "🚨 Reply to a message and send <code>/report</code>.\n"
                "📣 All admins will be alerted.\n"
                "🕛 Each user can report once every 3 hours.",
                parse_mode="html",
            )
        return

    replied = await event.get_reply_message()
    if not replied:
        await event.reply("❌ Cannot find the replied message.")
        return

    user_id, chat_id, now = event.sender_id, event.chat_id, _tm.time()

    doc = await report_cooldown_col.find_one({"chat_id": chat_id, "user_id": user_id})
    if doc:
        last = float(doc.get("last_report", 0))
        elapsed = now - last
        if elapsed < REPORT_COOLDOWN_SECONDS:
            remaining = REPORT_COOLDOWN_SECONDS - elapsed
            hrs, mins, secs = int(remaining // 3600), int((remaining % 3600) // 60), int(remaining % 60)
            await event.reply(
                f"⏳ <b>Report Cooldown</b>\n\n"
                f"🕛 You can report again in {code(f'{hrs}h {mins}m {secs}s')}.",
                parse_mode="html",
            )
            return

    try:
        await report_cooldown_col.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"last_report": now}},
            upsert=True,
        )
    except Exception as e:
        print(f"⚠️ report cooldown save failed: {e}")

    admins = await get_admin_list(chat_id)
    admin_mentions = " ".join(make_mention(name, uid) for uid, name in admins)

    reporter = await event.get_sender()
    reporter_name = (
        f"{getattr(reporter, 'first_name', '') or ''} "
        f"{getattr(reporter, 'last_name', '') or ''}"
    ).strip() or "User"

    target_id = replied.sender_id
    target_name = await get_user_name(target_id) if target_id else "Unknown"
    target_mention = make_mention(target_name, target_id) if target_id else "Unknown"

    try:
        await bot.forward_messages(OWNER_ID, replied.id, chat_id)
    except Exception as e:
        print(f"⚠️ report forward failed: {e}")

    try:
        await bot.send_message(
            chat_id,
            f"🚨 <b>REPORT RECEIVED</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>Reporter:</b> {make_mention(reporter_name, user_id)}\n"
            f"🎯 <b>Reported user:</b> {target_mention}\n"
            f"🆔 <b>Message ID:</b> {code(replied.id)}\n\n"
            f"🔔 <b>Alerting Admins:</b>\n{admin_mentions}\n\n"
            f"⚡ <b>Action:</b> Reply + <code>မြုလိုက်</code> to mute if inappropriate.",
            parse_mode="html",
            reply_to=replied.id,
        )
    except Exception as e:
        print(f"⚠️ report alert failed: {e}")

    try:
        await event.reply(
            f"✅ <b>Report submitted</b>\n📣 Admins alerted.\n🕛 Next report after 3h.",
            parse_mode="html",
        )
    except Exception:
        pass


# ============================================================
# 📢  PERIODIC REPORT REMINDER
# ============================================================
async def report_reminder_loop():
    await asyncio.sleep(60)
    while True:
        try:
            await bot.send_message(
                OFFICIAL_GROUP_ID,
                "📢 <b>Reminder</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "🚨 Spotted inappropriate content?\n"
                "👉 Reply to it and send <code>/report</code>\n\n"
                "ℹ️ Once every 3 hours per user.\n"
                "🛡️ All admins will be alerted.",
                parse_mode="html",
            )
        except Exception as e:
            print(f"⚠️ report reminder failed: {e}")
        await asyncio.sleep(REPORT_REMINDER_SECONDS)


# ============================================================
# 🤖  BOT-TO-BOT: /del or ဖျက်မယ်
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
            "⚠️ <b>Usage</b>\n\n📌 Reply to a bot's message and send:\n• <code>/del</code>\n• <code>ဖျက်မယ်</code>",
            parse_mode="html",
        )
        return

    replied = await event.get_reply_message()
    if not replied or not replied.sender_id:
        await event.reply("❌ Reply target not found.")
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
                "bot_id": target_id, "chat_id": event.chat_id,
                "username": username, "display_name": display, "is_bot": is_bot,
                "added_by": event.sender_id, "added_at": datetime.now(timezone.utc),
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
        f"🆔 {code(target_id)}\n\n"
        f"🛑 To stop: <code>/untrack {target_id}</code>",
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
# 🔇  MUTE (5/day)  ·  🔊  UNMUTE
# ============================================================
MUTE_COMMANDS   = {"မြုလိုက်", "မြုလိုက်ပါ", "mute", "mutethatgay", "/mute"}
UNMUTE_COMMANDS = {"ပြန်ဖွင့်", "ပြန်ဖွင့်", "ပြန်ဖွင့်ပါ", "ပြန်ဖွင့်ပါ", "unmute", "/unmute"}


def _mute_rights() -> ChatBannedRights:
    return ChatBannedRights(
        until_date=0, view_messages=False,
        send_messages=True, send_media=True,
        send_stickers=True, send_gifs=True,
        send_games=True, send_inline=True,
        embed_links=True, send_polls=True,
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
    if "@" in trigger:
        trigger = trigger.split("@", 1)[0].strip()
    trigger_lower = trigger.lower()

    is_mute = trigger_lower in MUTE_COMMANDS
    is_unmute = trigger_lower in UNMUTE_COMMANDS
    if not (is_mute or is_unmute):
        return

    if not await is_admin(event.chat_id, event.sender_id):
        await event.reply("❌ <b>Admin only</b>", parse_mode="html")
        return

    if not event.is_reply:
        word = "မြုလိုက်" if is_mute else "ပြန်ဖွင့်"
        await event.reply(
            f"⚠️ <b>Reply required</b>\n📌 Reply and send <code>{word}</code>.",
            parse_mode="html",
        )
        return

    replied = await event.get_reply_message()
    if not replied or not replied.sender_id:
        await event.reply("❌ Reply target not found.")
        return

    target_id = replied.sender_id

    if target_id == event.sender_id:
        await event.reply("❌ You cannot mute yourself.")
        return
    if target_id == OWNER_ID:
        await event.reply("❌ Cannot mute the owner.")
        return
    if target_id < 0:
        await event.reply("❌ Cannot mute channel posts.")
        return

    try:
        target_user = await bot.get_entity(target_id)
        if target_user and getattr(target_user, "bot", False):
            await event.reply("❌ Cannot mute a bot.")
            return
    except Exception:
        pass

    if await is_admin(event.chat_id, target_id):
        await event.reply("❌ Cannot mute an admin.")
        return

    target_name = await get_user_name(target_id)

    if is_mute:
        used = await get_mute_count(event.sender_id, event.chat_id)
        if used >= MUTE_DAILY_LIMIT:
            await event.reply(
                f"⏳ <b>Daily Mute Limit Reached</b>\n"
                f"📊 {code(MUTE_DAILY_LIMIT)} / day · ✅ Used: {code(used)}\n"
                f"🕛 Resets UTC 00:00",
                parse_mode="html",
            )
            return

    try:
        if is_mute:
            await bot(EditBannedRequest(
                channel=event.chat_id, participant=target_id,
                banned_rights=_mute_rights(),
            ))
            await increment_mute_count(event.sender_id, event.chat_id)
            used_after = await get_mute_count(event.sender_id, event.chat_id)
            remaining = max(0, MUTE_DAILY_LIMIT - used_after)
            await event.reply(
                f"🔇 <b>Muted Successfully</b>\n\n"
                f"👤 {make_mention(target_name, target_id)}\n\n"
                f"🚫 Text · Photo/Video · Sticker · GIF · Voice · Inline · Links · Polls\n\n"
                f"📊 Quota: {code(used_after)} / {code(MUTE_DAILY_LIMIT)}\n"
                f"🎫 Remaining: {code(remaining)}",
                parse_mode="html",
            )
        else:
            await bot(EditBannedRequest(
                channel=event.chat_id, participant=target_id,
                banned_rights=_unmute_rights(),
            ))
            await event.reply(
                f"🔊 <b>Unmuted</b>\n\n👤 {make_mention(target_name, target_id)}",
                parse_mode="html",
            )
    except Exception as e:
        err = str(e)
        if any(k in err.lower() for k in ("admin", "right", "permission", "chat_admin_required")):
            await event.reply(
                "❌ <b>Bot has insufficient permissions</b>\n\n"
                "🤖 Enable <b>Ban Users</b> for this bot.",
                parse_mode="html",
            )
        else:
            await event.reply(f"❌ Failed: <code>{err}</code>", parse_mode="html")


# ============================================================
# 👑  OWNER-ONLY BURMESE COMMANDS
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("lock_chat_handler")
async def lock_chat_handler(event):
    if event.sender_id != OWNER_ID:
        return
    if strip_bot_suffix(event.text or "") != "စာပိတ်":
        return
    try:
        await bot(EditChatDefaultBannedRightsRequest(
            peer=event.chat_id,
            banned_rights=ChatBannedRights(
                until_date=0, view_messages=False,
                send_messages=True, send_media=True,
                send_stickers=True, send_gifs=True,
                send_games=True, send_inline=True,
                embed_links=True, send_polls=True,
            ),
        ))
        await event.reply(
            "🔒 <b>Chat Locked</b>\n\n🚫 Only admins can send.\n🔓 Unlock: <code>စာဖွင့်</code>",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"❌ Lock failed: <code>{e}</code>", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("unlock_chat_handler")
async def unlock_chat_handler(event):
    if event.sender_id != OWNER_ID:
        return
    if strip_bot_suffix(event.text or "") != "စာဖွင့်":
        return
    try:
        await bot(EditChatDefaultBannedRightsRequest(
            peer=event.chat_id,
            banned_rights=ChatBannedRights(until_date=0),
        ))
        await event.reply("🔓 <b>Chat Unlocked</b>\n\n✅ All members can send again.", parse_mode="html")
    except Exception as e:
        await event.reply(f"❌ Unlock failed: <code>{e}</code>", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("owner_ban_handler")
async def owner_ban_handler(event):
    if event.sender_id != OWNER_ID:
        return
    if strip_bot_suffix(event.text or "") not in ("ဘန်း", "ဘန်း "):
        return
    tid = await _resolve_target(event)
    if not tid:
        await event.reply("⚠️ <b>Usage:</b> Reply + <code>ဘန်း</code>", parse_mode="html")
        return
    if tid == OWNER_ID or await is_admin(event.chat_id, tid):
        await event.reply("❌ Cannot ban an admin.")
        return
    try:
        await bot(EditBannedRequest(
            channel=event.chat_id, participant=tid,
            banned_rights=ChatBannedRights(
                until_date=0, view_messages=True,
                send_messages=True, send_media=True,
                send_stickers=True, send_gifs=True,
                send_games=True, send_inline=True,
                embed_links=True, send_polls=True,
            ),
        ))
        name = await get_user_name(tid)
        await event.reply(f"🚫 <b>Banned</b>\n\n👤 {make_mention(name, tid)}", parse_mode="html")
    except Exception as e:
        await event.reply(f"❌ Ban failed: <code>{e}</code>", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("owner_kick_handler")
async def owner_kick_handler(event):
    if event.sender_id != OWNER_ID:
        return
    if strip_bot_suffix(event.text or "") not in ("ကစ်", "ကစ် "):
        return
    tid = await _resolve_target(event)
    if not tid:
        await event.reply("⚠️ <b>Usage:</b> Reply + <code>ကစ်</code>", parse_mode="html")
        return
    if tid == OWNER_ID or await is_admin(event.chat_id, tid):
        await event.reply("❌ Cannot kick an admin.")
        return
    try:
        until = int(_tm.time() + KICK_BAN_SECONDS)
        await bot(EditBannedRequest(
            channel=event.chat_id, participant=tid,
            banned_rights=ChatBannedRights(until_date=until, view_messages=True),
        ))
        name = await get_user_name(tid)
        await event.reply(
            f"👢 <b>Kicked</b>\n\n👤 {make_mention(name, tid)}\n⏱️ {code(KICK_BAN_SECONDS)}s",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"❌ Kick failed: <code>{e}</code>", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("owner_adm_handler")
async def owner_adm_handler(event):
    if event.sender_id != OWNER_ID:
        return
    if strip_bot_suffix(event.text or "") != "adm":
        return
    tid = await _resolve_target(event)
    if not tid:
        await event.reply(
            "⚠️ <b>Usage:</b> Reply + <code>adm</code>\n"
            "ℹ️ Limited admin (no ban / no info edit / no add admin).",
            parse_mode="html",
        )
        return
    try:
        await bot(EditAdminRequest(
            channel=event.chat_id,
            user_id=tid,
            admin_rights=ChatAdminRights(
                change_info=False,
                post_messages=False,
                edit_messages=False,
                delete_messages=True,
                ban_users=False,
                invite_users=True,
                pin_messages=True,
                add_admins=False,
                anonymous=False,
                manage_call=False,
                other=False,
                manage_topics=False,
            ),
            rank="Moderator",
        ))
        name = await get_user_name(tid)
        await event.reply(
            f"🛡️ <b>Admin Granted</b>\n\n"
            f"👤 {make_mention(name, tid)}\n"
            f"🏅 Rank: <code>Moderator</code>\n\n"
            f"✅ Delete · Invite · Pin\n"
            f"🚫 Ban · Change info · Add admins",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"❌ Grant failed: <code>{e}</code>", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^\?(\s|$)"))
@safe_handler("owner_info_handler")
async def owner_info_handler(event):
    if event.sender_id != OWNER_ID:
        return
    tid = await _resolve_target(event)
    if not tid:
        await event.reply(
            "⚠️ <b>Usage:</b> Reply + <code>?</code> or <code>? @user</code>",
            parse_mode="html",
        )
        return

    await event.reply("⏳ <b>Fetching user info...</b>", parse_mode="html")

    try:
        user = await bot.get_entity(tid)
    except Exception as e:
        await event.reply(f"❌ Cannot fetch user: <code>{e}</code>", parse_mode="html")
        return

    about, common_chats, lang = None, None, None
    try:
        full = await bot(GetFullUserRequest(tid))
        if full.full_user:
            about = full.full_user.about
            common_chats = full.full_user.common_chats_count
            lang = full.full_user.lang_code
    except Exception:
        pass

    join_date = None
    admin_rights = None
    banned_rights = None
    is_member = False
    try:
        part = await bot(GetParticipantRequest(event.chat_id, tid))
        participant = part.participant
        is_member = True

        if isinstance(participant, ChannelParticipantCreator):
            admin_rights = "👑 Creator"
            join_date = getattr(participant, "date", None)
        elif isinstance(participant, ChannelParticipantAdmin):
            join_date = getattr(participant, "date", None)
            r = participant.admin_rights
            perms = []
            if getattr(r, "change_info", False): perms.append("ChangeInfo")
            if getattr(r, "delete_messages", False): perms.append("Delete")
            if getattr(r, "ban_users", False): perms.append("Ban")
            if getattr(r, "invite_users", False): perms.append("Invite")
            if getattr(r, "pin_messages", False): perms.append("Pin")
            if getattr(r, "add_admins", False): perms.append("AddAdmin")
            if getattr(r, "manage_call", False): perms.append("Call")
            admin_rights = ", ".join(perms) if perms else "admin (no rights)"
        elif isinstance(participant, ChannelParticipantBanned):
            banned_rights = participant.banned_rights
    except Exception:
        pass

    warn_doc = await warns_col.find_one({"chat_id": event.chat_id, "user_id": tid})
    warn_count = int(warn_doc.get("count", 0)) if warn_doc else 0
    warn_reasons = (warn_doc or {}).get("reasons", [])[-3:]

    last_seen = "🔒 Hidden"
    try:
        status = getattr(user, "status", None)
        if status:
            cls = status.__class__.__name__
            if cls == "UserStatusOnline":
                last_seen = "🟢 Online"
            elif cls == "UserStatusOffline":
                dt = getattr(status, "was_online", None)
                last_seen = f"⚪ {dt.strftime('%Y-%m-%d %H:%M')} UTC" if dt else "⚪ Offline"
            elif cls == "UserStatusRecently":
                last_seen = "🟡 Recently"
            elif cls == "UserStatusLastWeek":
                last_seen = "🟠 Last week"
            elif cls == "UserStatusLastMonth":
                last_seen = "🔴 Last month"
    except Exception:
        pass

    flags = []
    if getattr(user, "bot", False): flags.append("🤖 Bot")
    if getattr(user, "premium", False): flags.append("⭐ Premium")
    if getattr(user, "verified", False): flags.append("☑️ Verified")
    if getattr(user, "scam", False): flags.append("⚠️ Scam")
    if getattr(user, "fake", False): flags.append("🎭 Fake")
    if getattr(user, "restricted", False): flags.append("🚫 Restricted")
    if getattr(user, "deleted", False): flags.append("🗑️ Deleted")
    if getattr(user, "support", False): flags.append("🛟 Support")

    restrict_reason = ""
    try:
        if getattr(user, "restricted", False) and getattr(user, "restriction_reason", None):
            reasons = user.restriction_reason
            if reasons:
                restrict_reason = reasons[0].reason or ""
    except Exception:
        pass

    first = getattr(user, "first_name", "") or ""
    last = getattr(user, "last_name", "") or ""
    full_name = f"{first} {last}".strip() or "Unknown"
    username = getattr(user, "username", None)
    phone = getattr(user, "phone", None)
    uid = getattr(user, "id", tid)

    lines = [
        f"❓ <b>USER INFORMATION</b>",
        f"━━━━━━━━━━━━━━━━━━",
        f"",
        f"👤 <b>Name:</b> {make_mention(full_name, uid)}",
        f"🆔 <b>User ID:</b> {code(uid)}",
        f"🔗 <b>Username:</b> {('@' + username) if username else '<i>none</i>'}",
        f"📱 <b>Phone:</b> {code(phone) if phone else '<i>hidden</i>'}",
        f"🗣️ <b>Language:</b> {code(lang) if lang else '<i>unknown</i>'}",
        f"",
        f"<b>── STATUS ──</b>",
        f"👁️ <b>Last seen:</b> {last_seen}",
        f"🏷️ <b>Flags:</b> {', '.join(flags) if flags else '<i>normal</i>'}",
    ]
    if restrict_reason:
        lines.append(f"🚫 <b>Restriction:</b> {code(restrict_reason)}")

    lines += [f"", f"<b>── PROFILE ──</b>", f"📝 <b>Bio:</b>"]
    if about:
        bio = about[:500] + ("…" if len(about) > 500 else "")
        lines.append(f"<i>{bio}</i>")
    else:
        lines.append("<i>empty</i>")

    lines += [
        f"🌐 <b>Common chats:</b> {code(common_chats if common_chats is not None else 'N/A')}",
        f"",
        f"<b>── IN THIS GROUP ──</b>",
        f"✅ <b>Member:</b> {'yes' if is_member else 'no'}",
    ]
    if join_date:
        try:
            lines.append(f"📅 <b>Joined:</b> {code(join_date.strftime('%Y-%m-%d %H:%M UTC'))}")
        except Exception:
            pass
    if admin_rights:
        lines.append(f"🛡️ <b>Admin:</b> {code(str(admin_rights))}")
    if banned_rights:
        try:
            is_banned = any([banned_rights.view_messages, banned_rights.send_messages, banned_rights.send_media])
            if is_banned:
                perm_until = getattr(banned_rights, "until_date", None)
                if perm_until:
                    lines.append(f"🚫 <b>Restricted until:</b> {code(perm_until.strftime('%Y-%m-%d %H:%M UTC'))}")
                else:
                    lines.append(f"🚫 <b>Restricted:</b> permanent")
        except Exception:
            pass

    lines.append(f"⚠️ <b>Warnings:</b> {code(warn_count)} / {code(DEFAULT_WARN_LIMIT)}")
    if warn_reasons:
        lines.append(f"📋 <b>Recent reasons:</b>")
        for r in warn_reasons:
            lines.append(f"   • {code(r)}")

    lines += [f"", f"━━━━━━━━━━━━━━━━━━", f"<i>Fetched by owner</i>"]

    try:
        await event.reply("\n".join(lines), parse_mode="html")
    except Exception as e:
        await event.reply(f"❌ Send failed: <code>{e}</code>", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("afk_toggle_handler")
async def afk_toggle_handler(event):
    if event.sender_id != OWNER_ID:
        return
    txt = (event.text or "").strip().lower()
    if txt and "@" in txt.split()[0]:
        first = txt.split()[0]
        txt = txt.replace(first, first.split("@", 1)[0], 1)

    if txt == "afk on":
        afk_state["enabled"] = True
        afk_state["since"] = datetime.now(timezone.utc)
        afk_state["reply_cooldown"] = {}
        await event.reply(
            "📴 <b>AFK Mode: ON</b>\n\n"
            f"🛡️ Mention replies active for <code>@{OWNER_USERNAME}</code>.\n"
            "🕛 Turn off: <code>afk off</code>",
            parse_mode="html",
        )
    elif txt == "afk off":
        afk_state["enabled"] = False
        afk_state["since"] = None
        await event.reply("🟢 <b>AFK Mode: OFF</b>\n\n✅ Mention auto-replies disabled.", parse_mode="html")
    elif txt == "afk":
        status = "📴 ON" if afk_state["enabled"] else "🟢 OFF"
        since_str = ""
        if afk_state["since"]:
            since_str = f"\n🕒 Since: <code>{afk_state['since'].strftime('%Y-%m-%d %H:%M UTC')}</code>"
        await event.reply(
            f"📊 <b>AFK Status</b>\n\nStatus: <b>{status}</b>{since_str}\n\n"
            f"ℹ️ Use <code>afk on</code> or <code>afk off</code>.",
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
        await event.reply("⚠️ <b>Usage:</b> Reply and send <code>/pin</code>.", parse_mode="html")
        return
    replied = await event.get_reply_message()
    try:
        await bot(UpdatePinnedMessageRequest(peer=event.chat_id, id=replied.id, silent=False))
        await event.reply(f"📌 <b>Pinned</b> — {code(replied.id)}", parse_mode="html")
    except Exception as e:
        await event.reply(f"❌ Pin failed: <code>{e}</code>", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/unpin(\s|$)"))
@safe_handler("unpin_handler")
async def unpin_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.reply("❌ Admin only.")
        return
    if not event.is_reply:
        await event.reply("⚠️ <b>Usage:</b> Reply and send <code>/unpin</code>.", parse_mode="html")
        return
    replied = await event.get_reply_message()
    try:
        await bot(UpdatePinnedMessageRequest(peer=event.chat_id, id=replied.id, unpin=True))
        await event.reply(f"📌 <b>Unpinned</b> — {code(replied.id)}", parse_mode="html")
    except Exception as e:
        await event.reply(f"❌ Unpin failed: <code>{e}</code>", parse_mode="html")


# ============================================================
# 👥  ADMIN LIST
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


# ============================================================
# ⚠️  WARN SYSTEM
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/warn(\s|$)"))
@safe_handler("warn_handler")
async def warn_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    tid = await _resolve_target(event)
    if not tid:
        await event.reply("⚠️ <b>Usage:</b> <code>/warn @user reason</code>", parse_mode="html")
        return
    if await is_admin(event.chat_id, tid):
        await event.reply("❌ Cannot warn an admin.")
        return
    if tid < 0:
        await event.reply("❌ Cannot warn channel posts.")
        return

    _, args = get_cmd_and_args(get_text(event))
    reason = "no reason"
    if event.is_reply:
        reason = (args or "no reason").strip()[:200]
    else:
        parts = args.split(maxsplit=1)
        reason = (parts[1].strip()[:200] if len(parts) > 1 else "no reason")

    doc = await warns_col.find_one_and_update(
        {"chat_id": event.chat_id, "user_id": tid},
        {
            "$inc": {"count": 1},
            "$push": {"reasons": {"$each": [reason], "$slice": -20}},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
        upsert=True, return_document=True,
    )
    count = int(doc.get("count", 1)) if doc else 1
    target_name = await get_user_name(tid)

    action_note = ""
    if count >= DEFAULT_WARN_LIMIT:
        try:
            until = int(_tm.time() + 3600)
            await bot(EditBannedRequest(
                channel=event.chat_id, participant=tid,
                banned_rights=ChatBannedRights(
                    until_date=until, view_messages=False,
                    send_messages=True, send_media=True,
                    send_stickers=True, send_gifs=True,
                    send_games=True, send_inline=True,
                    embed_links=True, send_polls=True,
                ),
            ))
            action_note = f"\n\n🔇 <b>Auto-muted for 1h</b>"
        except Exception as e:
            action_note = f"\n\n⚠️ Auto-mute failed: {code(e)}"

    await event.reply(
        f"⚠️ <b>Warning Issued</b>\n\n"
        f"👤 {make_mention(target_name, tid)}\n"
        f"📝 Reason: {code(reason)}\n"
        f"📊 Total: {code(count)} / {code(DEFAULT_WARN_LIMIT)}{action_note}",
        parse_mode="html",
    )


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/unwarn(\s|$)"))
@safe_handler("unwarn_handler")
async def unwarn_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    tid = await _resolve_target(event)
    if not tid:
        await event.reply("⚠️ <b>Usage:</b> <code>/unwarn @user</code>", parse_mode="html")
        return
    doc = await warns_col.find_one({"chat_id": event.chat_id, "user_id": tid})
    if not doc or not doc.get("count"):
        await event.reply("ℹ️ No warnings for this user.")
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
        f"✅ <b>Warn Removed</b>\n\n👤 {make_mention(target_name, tid)}\n📊 Total: {code(new_count)}",
        parse_mode="html",
    )


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/warns(\s|$)"))
@safe_handler("warns_handler")
async def warns_handler(event):
    tid = await _resolve_target(event)
    if not tid:
        await event.reply("⚠️ <b>Usage:</b> <code>/warns @user</code>", parse_mode="html")
        return
    doc = await warns_col.find_one({"chat_id": event.chat_id, "user_id": tid})
    target_name = await get_user_name(tid)
    if not doc or not doc.get("count"):
        await event.reply(f"✅ <b>Clean record</b>\n\n👤 {make_mention(target_name, tid)}", parse_mode="html")
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
    tid = await _resolve_target(event)
    if not tid:
        await event.reply("⚠️ <b>Usage:</b> <code>/kick @user</code>", parse_mode="html")
        return
    if await is_admin(event.chat_id, tid) or tid == OWNER_ID:
        await event.reply("❌ Cannot kick an admin.")
        return
    try:
        until = int(_tm.time() + KICK_BAN_SECONDS)
        await bot(EditBannedRequest(
            channel=event.chat_id, participant=tid,
            banned_rights=ChatBannedRights(until_date=until, view_messages=True),
        ))
        name = await get_user_name(tid)
        await event.reply(
            f"👢 <b>Kicked</b>\n\n👤 {make_mention(name, tid)}\n⏱️ {code(KICK_BAN_SECONDS)}s",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"❌ Kick failed: <code>{e}</code>", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/ban(\s|$)"))
@safe_handler("ban_handler")
async def ban_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    tid = await _resolve_target(event)
    if not tid:
        await event.reply("⚠️ <b>Usage:</b> <code>/ban @user</code>", parse_mode="html")
        return
    if await is_admin(event.chat_id, tid) or tid == OWNER_ID:
        await event.reply("❌ Cannot ban an admin.")
        return
    try:
        await bot(EditBannedRequest(
            channel=event.chat_id, participant=tid,
            banned_rights=ChatBannedRights(
                until_date=0, view_messages=True,
                send_messages=True, send_media=True,
                send_stickers=True, send_gifs=True,
                send_games=True, send_inline=True,
                embed_links=True, send_polls=True,
            ),
        ))
        name = await get_user_name(tid)
        await event.reply(f"🚫 <b>Banned</b>\n\n👤 {make_mention(name, tid)}", parse_mode="html")
    except Exception as e:
        await event.reply(f"❌ Ban failed: <code>{e}</code>", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/unban(\s|$)"))
@safe_handler("unban_handler")
async def unban_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    tid = await _resolve_target(event)
    if not tid:
        await event.reply("⚠️ <b>Usage:</b> <code>/unban @user</code>", parse_mode="html")
        return
    try:
        await bot(EditBannedRequest(
            channel=event.chat_id, participant=tid,
            banned_rights=ChatBannedRights(until_date=0),
        ))
        name = await get_user_name(tid)
        await event.reply(f"✅ <b>Unbanned</b>\n\n👤 {make_mention(name, tid)}", parse_mode="html")
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
        await event.reply("⚠️ <b>Usage:</b> Reply and send <code>/purge</code>.", parse_mode="html")
        return
    replied = await event.get_reply_message()
    ids = list(range(replied.id, event.id + 1))
    deleted = 0
    for i in range(0, len(ids), 100):
        batch = ids[i:i + 100]
        try:
            await bot.delete_messages(event.chat_id, batch)
            deleted += len(batch)
        except Exception as e:
            print(f"⚠️ purge batch error: {e}")
    try:
        await event.reply(f"🧹 <b>Purge Complete</b>\n\n🗑️ Deleted: {code(deleted)}", parse_mode="html")
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
        await event.reply("⚠️ <b>Usage:</b> <code>/setrules [text]</code>", parse_mode="html")
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
        await event.reply("📭 <b>No rules set yet.</b>", parse_mode="html")
        return
    await event.reply(f"📖 <b>GROUP RULES</b>\n━━━━━━━━━━━━━━━━━━\n\n{rules}", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/clearrules(\s|$)"))
@safe_handler("clearrules_handler")
async def clearrules_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    await settings_col.update_one({"chat_id": event.chat_id}, {"$set": {"rules": ""}}, upsert=True)
    await event.reply("🗑️ <b>Rules cleared.</b>", parse_mode="html")


# ============================================================
# 🎉  WELCOME
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/welcome(\s|$)"))
@safe_handler("welcome_toggle_handler")
async def welcome_toggle_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    _, args = get_cmd_and_args(get_text(event))
    s = await get_settings(event.chat_id)
    current = bool(s.get("welcome", WELCOME_DEFAULT))

    if args.lower() in ("on", "enable", "yes"): new_val = True
    elif args.lower() in ("off", "disable", "no"): new_val = False
    elif not args: new_val = not current
    else:
        await event.reply("⚠️ <b>Usage:</b> <code>/welcome on</code> or <code>/welcome off</code>", parse_mode="html")
        return

    await settings_col.update_one({"chat_id": event.chat_id}, {"$set": {"welcome": new_val}}, upsert=True)
    icon = "🟢" if new_val else "🔴"
    await event.reply(f"{icon} <b>Welcome: {'ON' if new_val else 'OFF'}</b>", parse_mode="html")


@bot.on(events.ChatAction(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("welcome_new_member_handler")
async def welcome_new_member_handler(event):
    if not (event.user_joined or event.user_added):
        return
    s = await get_settings(event.chat_id)
    if not s.get("welcome", False):
        return
    user_id = getattr(event, "user_id", None)
    if not user_id: return
    name = await get_user_name(user_id)
    count_str = "—"
    try:
        full = await bot(GetFullChannelRequest(event.chat_id))
        count_str = f"{full.full_chat.participants_count}"
    except Exception:
        pass

    await bot.send_message(
        event.chat_id,
        f"🎉 <b>Welcome to the group!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 {make_mention(name, user_id)}\n"
        f"🏛️ We're glad to have you join us.\n\n"
        f"📖 <b>Rules:</b> /rules\n"
        f"👥 <b>Members:</b> {code(count_str)}\n"
        f"🆔 <b>Your ID:</b> {code(user_id)}\n\n"
        f"<i>Enjoy your stay and have fun!</i>",
        parse_mode="html",
    )


@bot.on(events.ChatAction())
@safe_handler("bot_added_to_group_handler")
async def bot_added_to_group_handler(event):
    my_id = await _ensure_me()
    added = (event.user_added and event.user_id == my_id) or (event.user_joined and event.user_id == my_id)
    if not added: return
    try:
        title = await get_group_title(event.chat_id)
    except Exception:
        title = str(event.chat_id)

    await bot.send_message(
        event.chat_id,
        f"🏛️ <b>BOD Manager — Ready to Serve</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 Hello <b>{title}</b>!\n\n"
        f"🛡️ Auto-delete · Mute · Warn · Kick · Ban\n"
        f"📌 Pin · /report · /stats · 🚫 Badword filter\n"
        f"👑 Owner: စာပိတ် · စာဖွင့် · ဘန်း · ကစ် · adm · ? · afk\n\n"
        f"⚙️ <b>Setup:</b>\n"
        f"   1. Make me <b>admin</b>\n"
        f"   2. Enable: <b>Ban Users</b>, <b>Delete Messages</b>, <b>Pin Messages</b>\n"
        f"   3. Send <code>/help</code>",
        parse_mode="html",
    )
    print(f"🤖 Bot added to group {event.chat_id} ({title})")


# ============================================================
# 📊  STATS & ID
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

    afk_status = "📴 ON" if afk_state["enabled"] else "🟢 OFF"

    await event.reply(
        f"📊 <b>GROUP STATS</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🏛️ <b>Title:</b> {code(title)}\n"
        f"🆔 <b>Chat ID:</b> {code(event.chat_id)}\n"
        f"👥 <b>Members:</b> {code(count_str)}\n"
        f"🛡️ <b>Admins:</b> {code(len(admins))}\n"
        f"🤖 <b>Tracked bots:</b> {code(tracked)}\n"
        f"🔇 <b>Mutes today:</b> {code(total_mutes)} / {code(len(admins) * MUTE_DAILY_LIMIT)}\n"
        f"📴 <b>AFK mode:</b> {afk_status}\n"
        f"🚫 <b>Badword filter:</b> {code('ON')} ({code(len(BADWORDS))} words)\n"
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
                f"🆔 <b>User ID</b>\n\n👤 {make_mention(name, r.sender_id)}\n🔢 {code(r.sender_id)}",
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


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/mutecount(\s|$)"))
@safe_handler("mutecount_handler")
async def mutecount_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    used = await get_mute_count(event.sender_id, event.chat_id)
    remaining = max(0, MUTE_DAILY_LIMIT - used)
    bar = "🟩" * min(used, MUTE_DAILY_LIMIT) + "⬜" * (MUTE_DAILY_LIMIT - min(used, MUTE_DAILY_LIMIT))
    await event.reply(
        f"📊 <b>Your Mute Quota Today</b>\n\n{bar}\n"
        f"✅ Used: {code(used)} / {code(MUTE_DAILY_LIMIT)}\n"
        f"🎫 Remaining: {code(remaining)}\n"
        f"🕛 Resets: <b>UTC 00:00</b>",
        parse_mode="html",
    )


# ============================================================
# 📖  /start  &  /help
# ============================================================
@bot.on(events.NewMessage(pattern=r"^/start(\s|$)"))
@safe_handler("start_handler")
async def start_handler(event):
    afk_status = "📴 ON" if afk_state["enabled"] else "🟢 OFF"
    await event.reply(
        "🏛️ <b>BOD MANAGER</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "✅ System Online\n"
        "🛡️ Moderation ready\n"
        "📌 Pin system ready\n"
        "🤖 Bot-tracking active\n"
        "🚫 Link auto-delete ON\n"
        "🚫 Badword filter ON\n"
        f"📴 AFK mode: {afk_status}\n"
        f"🔇 Mute quota: {code(MUTE_DAILY_LIMIT)} / day / admin\n\n"
        "📖 See all commands: /help",
        parse_mode="html",
    )


@bot.on(events.NewMessage(pattern=r"^/help(\s|$)"))
@safe_handler("help_handler")
async def help_handler(event):
    text = (
        "📖 <b>COMMAND LIST</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "👑 <b>Owner-Only (Burmese)</b>\n"
        "• <code>စာပိတ်</code> — lock chat\n"
        "• <code>စာဖွင့်</code> — unlock chat\n"
        "• Reply + <code>ဘန်း</code> — ban user\n"
        "• Reply + <code>ကစ်</code> — kick user (60s)\n"
        "• Reply + <code>adm</code> — give limited admin\n"
        "• Reply + <code>?</code> — full user info\n"
        "• <code>afk on</code> / <code>afk off</code> — AFK mode\n\n"
        "🛡️ <b>Moderation</b>\n"
        "• Reply + <code>မြုလိုက်</code> — mute (5/day)\n"
        "• Reply + <code>/mute</code> — same\n"
        "• Reply + <code>ပြန်ဖွင့်</code> / <code>/unmute</code> — unmute\n"
        "• <code>/warn @user reason</code>\n"
        "• <code>/unwarn @user</code> · <code>/warns @user</code>\n"
        "• <code>/kick @user</code> · <code>/ban @user</code> · <code>/unban @user</code>\n"
        "• Reply + <code>/purge</code>\n\n"
        "🚫 <b>Badword Filter</b>\n"
        "• Auto-warn on bad words\n"
        "• 2nd violation within 5 min = 1h mute\n\n"
        "📌 <b>Pinning</b>\n"
        "• Reply + <code>/pin</code> · <code>/unpin</code>\n\n"
        "🚨 <b>Report</b>\n"
        "• Reply + <code>/report</code> — alerts admins (3h cooldown)\n\n"
        "👥 <b>Info</b>\n"
        "• <code>/admins</code> · <code>/id</code> · <code>/stats</code> · <code>/mutecount</code>\n\n"
        "🤖 <b>Bot Tracking (Owner)</b>\n"
        "• Reply + <code>/del</code> or <code>ဖျက်မယ်</code>\n"
        "• <code>/untrack [id]</code> · <code>/tracked</code>\n\n"
        "📖 <b>Rules & Welcome</b>\n"
        "• <code>/setrules [text]</code> · <code>/rules</code> · <code>/clearrules</code>\n"
        "• <code>/welcome on/off</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔇 Mute: {code('5')} / day · 🕛 UTC 00:00\n"
        f"🚫 Non-admin links auto-deleted\n"
        f"✅ Stickers & GIFs NOT auto-deleted\n"
        f"🚫 Muted users cannot send anything"
    )
    await event.reply(text, parse_mode="html")


# ============================================================
# 🌍  RENDER HEALTH CHECK
# ============================================================
async def _health(reader, writer):
    await reader.read(100)
    writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nOK")
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
    print("⏳ BOD Manager starting...")
    asyncio.create_task(start_health_server())

    try:
        await bot.start(bot_token=BOT_TOKEN)
        me = await _ensure_me()
        print(f"🤖 Bot connected: @{_my_username} (id={me})")
    except Exception as e:
        print(f"❌ Bot start failed: {e}")
        return

    await load_tracked_bots()
    asyncio.create_task(report_reminder_loop())

    try:
        await bot.send_message(
            OWNER_ID,
            "🟢 <b>BOD Manager ONLINE</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"🏛️ Target: {code(OFFICIAL_GROUP_ID)}\n"
            f"🗑️ Auto-delete: {code('ON')} (photo/video/links)\n"
            f"✅ Stickers/GIFs: {code('NOT auto-deleted')}\n"
            f"🔇 Mute: {code(MUTE_DAILY_LIMIT)} / day / admin\n"
            f"🚫 Badword filter: {code('ON')} ({code(len(BADWORDS))} words)\n"
            f"📴 AFK mode: {code('OFF')}\n"
            f"🚨 Report cooldown: {code('3h')}\n\n"
            "👑 <b>Owner commands:</b>\n"
            "• <code>စာပိတ်</code> · <code>စာဖွင့်</code>\n"
            "• Reply + <code>ဘန်း</code> · <code>ကစ်</code> · <code>adm</code> · <code>?</code>\n"
            "• <code>afk on</code> · <code>afk off</code>\n\n"
            "💡 /help — full command list",
            parse_mode="html",
        )
    except Exception:
        pass

    print("🚀 Ready. Listening...")
    await bot.run_until_disconnected()


if __name__ == "__main__":
    if _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    try:
        _loop.run_until_complete(startup())
    except KeyboardInterrupt:
        print("⏹️ Interrupted by user.")
    finally:
        try:
            _loop.close()
        except Exception:
            pass
