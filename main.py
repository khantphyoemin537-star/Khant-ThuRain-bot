# ============================================================
# 🏛️  BOD MANAGER  —  main.py (standalone)
# ============================================================
# Python 3.14+ compatible
# ✅ Premium Emoji — all handlers verified
# ✅ AFK reply parse_mode fixed
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
BOT_TOKEN = '8642627689:AAHSD4_Y9AeisF43xu7vpziMDamXkiV3NVg'

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


# ============================================================
# ✨  PREMIUM EMOJI
# ============================================================
PREMIUM_EMOJI = {
    "bot":       None,
    "shield":    None,
    "crown":     None,
    "star":      None,
    "sparkle":   None,
    "mute":      6039505337151655702,
    "unmute":    6039454987250044861,
    "warn":      5461098492216752942,
    "ban":       5368562433981947135,
    "kick":      6177127866115822461,
    "lock":      6037249452824072506,
    "unlock":    6037496202990194718,
    "check":     5305670334513427489,
    "cross":     5447544503143504937,
    "clock":     5215327832040811010,
    "alert":     5212969852045634932,
    "pin":       5422357698228290320,
    "delete":    6039522349517115015,
    "fire":      5402406965252989103,
    "eyes":      5350732341109081597,
    "target":    6032949275732742941,
    "stats":     5231200819986047254,
    "info":      5456309534962234647,
    "id":        5465465194056525619,
    "admin":     5373110220232870002,
    "book":      6181489083282363892,
    "link":      6240200624793720535,
    "afk":       5449875850046481967,
    "online":    5217449524410199951,
    "offline":   5444965061749644170,
    "sleep":     5462990652943904884,
    "party":     None,
    "heart":     None,
    "wave":      None,
    "trophy":    None,
    "key":       None,
    "gear":      None,
    "rocket":    None,
    "ghost":     None,
}


def pe(key: str, fallback: str = "✨") -> str:
    """Return premium emoji tag if configured, else fallback."""
    eid = PREMIUM_EMOJI.get(key)
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'
    return fallback


# ============================================================
# 🚫  BADWORDS
# ============================================================
BADWORDS = [
    "ဖာသယ်မ", "ဖာသည်မ",
    "ဖာသယ်မသား", "ဖာသည်မသား",
    "လီး", "မှန်းထု", "မှန်း", "လိုး",
    "မအေလိုး", "ငါလိုးမသား",
]

BADWORD_SAFE_CONTEXTS = [
    "ရည်မှန်းချက်", "ရည်မှန်း",
    "ခန့်မှန်းချက်", "ခန့်မှန်း", "ခန့်မှန်းတွက်", "ခန့်မှန်းပြ",
    "မှန်းဆချက်", "မှန်းဆ", "မှန်းဆတွက်",
    "လီးလာ", "တစ်လီး", "နှစ်လီး", "သုံးလီး",
    "စာရင်းလီး", "လီးစား",
]

_BADWORD_SAFE_SORTED = sorted(BADWORD_SAFE_CONTEXTS, key=len, reverse=True)

BADWORD_WINDOW_SECONDS = 5 * 60
BADWORD_MUTE_DURATION  = 60 * 60


# ============================================================
# 🔧  PYTHON 3.14+ EVENT LOOP
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


def fmt_secs(seconds: int) -> str:
    seconds = int(seconds)
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    parts = []
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s: parts.append(f"{s}s")
    return " ".join(parts) if parts else "0s"


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


def _contains_badword(text: str) -> str | None:
    if not text:
        return None
    t = clean_invisible(text)
    masked = t
    for safe in _BADWORD_SAFE_SORTED:
        if safe in masked:
            masked = masked.replace(safe, "▢" * len(safe))
    for bw in BADWORDS:
        if bw in masked:
            return bw
    return None


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
# 🚫  BADWORD FILTER
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("badword_filter_handler")
async def badword_filter_handler(event):
    if not event.text:
        return
    sender_id = event.sender_id
    chat_id = event.chat_id

    try:
        if await is_admin(chat_id, sender_id):
            return
    except Exception:
        pass
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

    key = (chat_id, sender_id)
    now = _tm.time()
    history = [t for t in badword_tracker.get(key, []) if now - t < BADWORD_WINDOW_SECONDS]
    history.append(now)
    badword_tracker[key] = history

    if len(history) >= 2:
        try:
            until = int(now + BADWORD_MUTE_DURATION)
            await bot(EditBannedRequest(
                channel=chat_id, participant=sender_id,
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
                f"{pe('mute', '🔇')} <b>Language Restriction Activated</b>\n\n"
                f"{mention} — your recent message contained prohibited language that violates our community standards.\n\n"
                f"<b>Restriction:</b> Muted for 1 hour\n"
                f"<b>Expires:</b> {code(expiry)}\n"
                f"<b>Reason:</b> Second violation within a 5-minute window\n\n"
                f"<i>Respect is the foundation of every healthy community. We hope to see you engage positively once this restriction lifts.</i>",
                parse_mode="html", reply_to=event.id,
            )
            badword_tracker.pop(key, None)
        except Exception as e:
            await event.reply(
                f"{pe('cross', '❌')} <b>Moderation Action Failed</b>\n\n"
                f"Please verify that I have the <b>Ban Users</b> admin right enabled.\n\n"
                f"<b>Error:</b> {code(str(e))}",
                parse_mode="html",
            )
        return

    try:
        await event.reply(
            f"{pe('warn', '⚠️')} <b>A Gentle Reminder</b> {mention}\n\n"
            f"The message you just sent contains language that isn't welcome here in <b>The BODgram</b>. "
            f"We're all here to enjoy a comfortable, friendly space together.\n\n"
            f"Please be mindful going forward — a second occurrence within the next <b>5 minutes</b> will result in a <b>1-hour mute</b>.\n\n"
            f"<i>Thank you for helping us keep this community welcoming for everyone.</i>",
            parse_mode="html", reply_to=event.id,
        )
    except Exception as e:
        print(f"❌ Badword warning failed: {e}")


# ============================================================
# 🗑️  AUTO-DELETE MEDIA + LINKS
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
    except Exception as e:
        print(f"❌ auto-delete failed: {e}")

    if delete_link:
        try:
            name = await get_user_name(sender_id)
            await bot.send_message(
                chat_id,
                f"{pe('cross', '❌')} <b>Link Sharing Restricted</b>\n\n"
                f"{make_mention(name, sender_id)} — links are not permitted in this group for members. "
                f"Your message has been removed automatically by the moderation system.\n\n"
                f"<i>If you believe this was an error, please contact an admin via /report.</i>",
                parse_mode="html",
            )
        except Exception as e:
            print(f"❌ link warning failed: {e}")


# ============================================================
# 📴  AFK MENTION AUTO-REPLY  ⭐ FIXED: parse_mode="html"
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

    # ⭐ FIXED: added parse_mode="html"
    try:
        await event.reply(
            f"{pe('afk', '📴')} <b>AFK Auto-Reply</b>\n\n"
            f"{AFK_EN_MSG}\n\n"
            f"{AFK_MM_MSG}",
            parse_mode="html",
        )
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
                f"{pe('alert', '🚨')} <b>Report a Message</b>\n\n"
                f"To report inappropriate content:\n\n"
                f"• <b>Step 1:</b> Reply directly to the offending message\n"
                f"• <b>Step 2:</b> Send <code>/report</code>\n\n"
                f"All group admins will receive an alert with the reported content "
                f"and be able to take action immediately.\n\n"
                f"<i>Note: Each member may report once every 3 hours.</i>",
                parse_mode="html",
            )
        return

    replied = await event.get_reply_message()
    if not replied:
        await event.reply("⚠️ Unable to locate the message you replied to. Please try again.")
        return

    user_id, chat_id, now = event.sender_id, event.chat_id, _tm.time()

    doc = await report_cooldown_col.find_one({"chat_id": chat_id, "user_id": user_id})
    if doc:
        last = float(doc.get("last_report", 0))
        elapsed = now - last
        if elapsed < REPORT_COOLDOWN_SECONDS:
            remaining = int(REPORT_COOLDOWN_SECONDS - elapsed)
            await event.reply(
                f"{pe('clock', '⏳')} <b>Report Cooldown Active</b>\n\n"
                f"You've recently submitted a report. To prevent spam, each member may report once every 3 hours.\n\n"
                f"<b>Time remaining:</b> {code(fmt_secs(remaining))}\n\n"
                f"<i>If this is an urgent matter, please contact an admin directly.</i>",
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
            f"{pe('alert', '🚨')} <b>Report Received</b>\n\n"
            f"<b>Reporter:</b> {make_mention(reporter_name, user_id)}\n"
            f"<b>Reported User:</b> {target_mention}\n"
            f"<b>Message ID:</b> {code(replied.id)}\n\n"
            f"<b>Alerting Admins:</b>\n{admin_mentions}\n\n"
            f"<b>Recommended Action:</b>\n"
            f"If the reported content contains inappropriate language or violates our rules, "
            f"reply directly to the offender's message with <code>မြုလိုက်</code> to apply a mute restriction.\n\n"
            f"<i>The reported message is displayed below for context.</i>",
            parse_mode="html", reply_to=replied.id,
        )
    except Exception as e:
        print(f"⚠️ report alert failed: {e}")

    try:
        await event.reply(
            f"{pe('check', '✅')} <b>Report Submitted Successfully</b>\n\n"
            f"Thank you for helping keep our community safe. All admins have been notified "
            f"and will review the reported content shortly.\n\n"
            f"<b>Next available report:</b> in 3 hours\n\n"
            f"<i>For urgent matters, please reach out to an admin directly.</i>",
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
                f"{pe('alert', '🚨')} <b>Community Safety Reminder</b>\n\n"
                f"If you encounter content that violates our community guidelines — "
                f"whether it's spam, inappropriate language, or anything else that feels off — "
                f"please report it using these steps:\n\n"
                f"<b>1.</b> Reply to the offending message\n"
                f"<b>2.</b> Send <code>/report</code>\n\n"
                f"All admins will be alerted immediately and can take action.\n\n"
                f"<i>Each member may submit one report every 3 hours to keep this feature running smoothly.</i>",
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
            f"{pe('delete', '🗑️')} <b>Bot Tracking System</b>\n\n"
            f"To automatically delete all future messages from a bot, reply directly to that bot's message with either:\n\n"
            f"• <code>/del</code>\n"
            f"• <code>ဖျက်မယ်</code>\n\n"
            f"The bot will then be tracked, and every message it sends will be removed automatically.",
            parse_mode="html",
        )
        return

    replied = await event.get_reply_message()
    if not replied or not replied.sender_id:
        await event.reply("⚠️ Unable to identify the message sender. Please reply directly to a bot's message and try again.")
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
        await event.reply(f"⚠️ Failed to save tracking data: {code(e)}", parse_mode="html")
        return

    try:
        await replied.delete()
    except Exception:
        pass

    kind = "🤖 Bot" if is_bot else "👤 User"
    uname_str = f" (<code>@{username}</code>)" if username else ""
    await event.reply(
        f"{pe('check', '✅')} <b>Auto-Delete Activated</b>\n\n"
        f"The following entity has been added to the tracked list. All future messages from them will be automatically removed.\n\n"
        f"<b>Type:</b> {kind}\n"
        f"<b>Name:</b> {make_mention(display, target_id)}{uname_str}\n"
        f"<b>ID:</b> {code(target_id)}\n\n"
        f"To stop tracking this entity, send <code>/untrack {target_id}</code>.",
        parse_mode="html",
    )


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/untrack(\s|$)"))
@safe_handler("untrack_handler")
async def untrack_handler(event):
    if event.sender_id != OWNER_ID:
        return
    _, args = get_cmd_and_args(get_text(event))
    if not args or not args.split()[0].isdigit():
        await event.reply(f"⚠️ <b>Usage:</b> <code>/untrack [user_or_bot_id]</code>", parse_mode="html")
        return
    tid = int(args.split()[0])
    try:
        res = await tracked_bots_col.delete_one({"bot_id": tid, "chat_id": event.chat_id})
        tracked_bots_cache.pop(tid, None)
        if res.deleted_count:
            await event.reply(
                f"{pe('check', '✅')} <b>Auto-Delete Deactivated</b>\n\n"
                f"Entity {code(tid)} has been removed from the tracked list.",
                parse_mode="html",
            )
        else:
            await event.reply(f"ℹ️ <b>Not Found</b>\n\nThe entity {code(tid)} was not in the tracked list.", parse_mode="html")
    except Exception as e:
        await event.reply(f"⚠️ Failed to remove tracking: {code(e)}", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/tracked(\s|$)"))
@safe_handler("tracked_list_handler")
async def tracked_list_handler(event):
    if event.sender_id != OWNER_ID:
        return
    if not tracked_bots_cache:
        await event.reply(
            f"📭 <b>No Tracked Entities</b>\n\n"
            f"<i>To track a bot, reply to one of its messages with <code>/del</code>.</i>",
            parse_mode="html",
        )
        return
    lines = [f"👻 <b>Tracked Entities ({len(tracked_bots_cache)})</b>\n"]
    for i, bid in enumerate(tracked_bots_cache.keys(), 1):
        name = await get_user_name(bid)
        lines.append(f"{i}. {make_mention(name, bid)} — {code(bid)}")
    lines.append(f"\n<i>To stop tracking any entity, use <code>/untrack [id]</code>.</i>")
    await event.reply("\n".join(lines), parse_mode="html")


# ============================================================
# 🔇  MUTE / 🔊 UNMUTE
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
        await event.reply(
            f"{pe('lock', '🔒')} <b>Admin Permission Required</b>\n\n"
            f"This action is restricted to group administrators.",
            parse_mode="html",
        )
        return

    if not event.is_reply:
        word = "မြုလိုက်" if is_mute else "ပြန်ဖွင့်"
        await event.reply(
            f"{pe('warn', '⚠️')} <b>Reply Required</b>\n\n"
            f"Reply directly to a member's message and send <code>{word}</code>.",
            parse_mode="html",
        )
        return

    replied = await event.get_reply_message()
    if not replied or not replied.sender_id:
        await event.reply("⚠️ Unable to identify the reply target.")
        return

    target_id = replied.sender_id
    if target_id == event.sender_id:
        await event.reply("⚠️ You cannot apply this action to yourself.")
        return
    if target_id == OWNER_ID:
        await event.reply("🛡️ The group owner is protected from this action.")
        return
    if target_id < 0:
        await event.reply("⚠️ Channel posts cannot be muted or unmuted.")
        return
    try:
        target_user = await bot.get_entity(target_id)
        if target_user and getattr(target_user, "bot", False):
            await event.reply("⚠️ Bots cannot be muted via this command.")
            return
    except Exception:
        pass
    if await is_admin(event.chat_id, target_id):
        await event.reply(
            f"🛡️ <b>Protected Member</b>\n\n"
            f"The target is an admin and cannot be muted.",
            parse_mode="html",
        )
        return

    target_name = await get_user_name(target_id)

    if is_mute:
        used = await get_mute_count(event.sender_id, event.chat_id)
        if used >= MUTE_DAILY_LIMIT:
            await event.reply(
                f"{pe('clock', '⏳')} <b>Daily Mute Quota Reached</b>\n\n"
                f"You've used all {code(MUTE_DAILY_LIMIT)} of your daily mute actions.\n\n"
                f"<b>Used today:</b> {code(used)} / {code(MUTE_DAILY_LIMIT)}\n"
                f"<b>Quota resets:</b> UTC 00:00\n\n"
                f"<i>For urgent moderation needs, please contact the group owner.</i>",
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
                f"{pe('mute', '🔇')} <b>Member Muted</b>\n\n"
                f"<b>Target:</b> {make_mention(target_name, target_id)}\n"
                f"<b>Restriction:</b> All message types blocked\n\n"
                f"<b>Blocked:</b> Text · Media · Stickers · GIFs · Voice · Inline · Links · Polls\n"
                f"<b>Duration:</b> Indefinite (until unmuted by admin)\n\n"
                f"<b>Your Daily Quota:</b>\n"
                f"Used: {code(used_after)} / {code(MUTE_DAILY_LIMIT)}\n"
                f"Remaining: {code(remaining)}\n\n"
                f"<i>To lift this restriction, reply with <code>ပြန်ဖွင့်</code>.</i>",
                parse_mode="html",
            )
        else:
            await bot(EditBannedRequest(
                channel=event.chat_id, participant=target_id,
                banned_rights=_unmute_rights(),
            ))
            await event.reply(
                f"{pe('unmute', '🔊')} <b>Member Unmuted</b>\n\n"
                f"<b>Target:</b> {make_mention(target_name, target_id)}\n"
                f"<b>Status:</b> Full access restored\n\n"
                f"<i>We hope they'll continue to engage respectfully going forward.</i>",
                parse_mode="html",
            )
    except Exception as e:
        err = str(e)
        if any(k in err.lower() for k in ("admin", "right", "permission", "chat_admin_required")):
            await event.reply(
                f"{pe('cross', '❌')} <b>Insufficient Permissions</b>\n\n"
                f"I don't have the required <b>Ban Users</b> admin right.",
                parse_mode="html",
            )
        else:
            await event.reply(f"⚠️ <b>Action Failed</b>\n\n<b>Error:</b> {code(err)}", parse_mode="html")


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
            f"{pe('lock', '🔒')} <b>Group Locked</b>\n\n"
            f"The group is now in read-only mode. Only admins can send messages.\n\n"
            f"<b>Effect:</b> All member messages, media, stickers, and links are blocked\n\n"
            f"<i>To unlock the group, send <code>စာဖွင့်</code>.</i>",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"⚠️ <b>Lock Failed</b>\n\n<b>Error:</b> {code(e)}", parse_mode="html")


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
        await event.reply(
            f"{pe('unlock', '🔓')} <b>Group Unlocked</b>\n\n"
            f"The group is now open for everyone to participate again.\n\n"
            f"<i>We appreciate your patience during the temporary restriction.</i>",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"⚠️ <b>Unlock Failed</b>\n\n<b>Error:</b> {code(e)}", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("owner_ban_handler")
async def owner_ban_handler(event):
    if event.sender_id != OWNER_ID:
        return
    if strip_bot_suffix(event.text or "") not in ("ဘန်း", "ဘန်း "):
        return
    tid = await _resolve_target(event)
    if not tid:
        await event.reply(
            f"{pe('warn', '⚠️')} <b>Reply Required</b>\n\n"
            f"Reply to a message and send <code>ဘန်း</code>.",
            parse_mode="html",
        )
        return
    if tid == OWNER_ID or await is_admin(event.chat_id, tid):
        await event.reply("🛡️ Admins and the owner are protected from ban actions.")
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
        await event.reply(
            f"{pe('ban', '🚫')} <b>Member Banned</b>\n\n"
            f"<b>Target:</b> {make_mention(name, tid)}\n"
            f"<b>Action:</b> Permanent removal\n\n"
            f"The member has been removed and blocked from rejoining this group.",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"⚠️ <b>Ban Failed</b>\n\n<b>Error:</b> {code(e)}", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("owner_kick_handler")
async def owner_kick_handler(event):
    if event.sender_id != OWNER_ID:
        return
    if strip_bot_suffix(event.text or "") not in ("ကစ်", "ကစ် "):
        return
    tid = await _resolve_target(event)
    if not tid:
        await event.reply(
            f"{pe('warn', '⚠️')} <b>Reply Required</b>\n\n"
            f"Reply to a message and send <code>ကစ်</code>.",
            parse_mode="html",
        )
        return
    if tid == OWNER_ID or await is_admin(event.chat_id, tid):
        await event.reply("🛡️ Admins and the owner are protected from kick actions.")
        return
    try:
        until = int(_tm.time() + KICK_BAN_SECONDS)
        await bot(EditBannedRequest(
            channel=event.chat_id, participant=tid,
            banned_rights=ChatBannedRights(until_date=until, view_messages=True),
        ))
        name = await get_user_name(tid)
        await event.reply(
            f"{pe('kick', '👢')} <b>Member Kicked</b>\n\n"
            f"<b>Target:</b> {make_mention(name, tid)}\n"
            f"<b>Duration:</b> {code(KICK_BAN_SECONDS)} seconds\n\n"
            f"The member will be able to rejoin once the cooldown expires.",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"⚠️ <b>Kick Failed</b>\n\n<b>Error:</b> {code(e)}", parse_mode="html")


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
            f"🛡️ <b>Grant Limited Admin</b>\n\n"
            f"Reply to a member's message and send <code>adm</code>.\n\n"
            f"<b>Granted:</b> Delete · Invite · Pin\n"
            f"<b>Restricted:</b> Ban · Change info · Add admins",
            parse_mode="html",
        )
        return
    try:
        await bot(EditAdminRequest(
            channel=event.chat_id, user_id=tid,
            admin_rights=ChatAdminRights(
                change_info=False, post_messages=False, edit_messages=False,
                delete_messages=True, ban_users=False, invite_users=True,
                pin_messages=True, add_admins=False, anonymous=False,
                manage_call=False, other=False, manage_topics=False,
            ),
            rank="Moderator",
        ))
        name = await get_user_name(tid)
        await event.reply(
            f"🛡️ <b>Limited Admin Granted</b>\n\n"
            f"<b>Member:</b> {make_mention(name, tid)}\n"
            f"<b>Rank:</b> Moderator\n\n"
            f"<b>Permissions Granted:</b>\n"
            f"{pe('check', '✅')} Delete messages\n"
            f"{pe('check', '✅')} Invite users\n"
            f"{pe('check', '✅')} Pin messages\n\n"
            f"<b>Permissions Withheld:</b>\n"
            f"{pe('ban', '🚫')} Ban users\n"
            f"{pe('ban', '🚫')} Change group info\n"
            f"{pe('ban', '🚫')} Add administrators",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"⚠️ <b>Grant Failed</b>\n\n<b>Error:</b> {code(e)}", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^\?(\s|$)"))
@safe_handler("owner_info_handler")
async def owner_info_handler(event):
    if event.sender_id != OWNER_ID:
        return
    tid = await _resolve_target(event)
    if not tid:
        await event.reply(
            f"❓ <b>User Information Lookup</b>\n\n"
            f"<b>Usage:</b>\n"
            f"• Reply to a message with <code>?</code>\n"
            f"• Or use <code>? @username</code>\n"
            f"• Or use <code>? 123456789</code>",
            parse_mode="html",
        )
        return

    await event.reply(f"{pe('clock', '⏳')} <b>Fetching user data...</b>", parse_mode="html")

    try:
        user = await bot.get_entity(tid)
    except Exception as e:
        await event.reply(f"⚠️ <b>Lookup Failed</b>\n\n{code(e)}", parse_mode="html")
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
                last_seen = f"{pe('online', '🟢')} Online now"
            elif cls == "UserStatusOffline":
                dt = getattr(status, "was_online", None)
                last_seen = f"{pe('offline', '⚪')} {dt.strftime('%Y-%m-%d %H:%M')} UTC" if dt else f"{pe('offline', '⚪')} Offline"
            elif cls == "UserStatusRecently":
                last_seen = "🟡 Recently active"
            elif cls == "UserStatusLastWeek":
                last_seen = "🟠 Within last week"
            elif cls == "UserStatusLastMonth":
                last_seen = "🔴 Within last month"
    except Exception:
        pass

    flags = []
    if getattr(user, "bot", False): flags.append("🤖 Bot")
    if getattr(user, "premium", False): flags.append("⭐ Premium")
    if getattr(user, "verified", False): flags.append("☑️ Verified")
    if getattr(user, "scam", False): flags.append(f"{pe('warn', '⚠️')} Scam")
    if getattr(user, "fake", False): flags.append("🎭 Fake")
    if getattr(user, "restricted", False): flags.append(f"{pe('ban', '🚫')} Restricted")
    if getattr(user, "deleted", False): flags.append(f"{pe('delete', '🗑️')} Deleted")
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
        f"❓ <b>User Information Report</b>\n",
        f"<b>Identity</b>\n"
        f"Name: {make_mention(full_name, uid)}\n"
        f"User ID: {pe('id', '🆔')} {code(uid)}\n"
        f"Username: {pe('link', '🔗')} {('@' + username) if username else '<i>not set</i>'}\n"
        f"Phone: {code(phone) if phone else '<i>hidden</i>'}\n"
        f"Language: {code(lang) if lang else '<i>unknown</i>'}",
        f"\n<b>Activity & Status</b>\n"
        f"Last seen: {last_seen}\n"
        f"Account flags: {', '.join(flags) if flags else 'None — normal account'}",
    ]
    if restrict_reason:
        lines.append(f"Restriction reason: {code(restrict_reason)}")

    lines.append(f"\n<b>Profile</b>\nBio:")
    if about:
        bio = about[:500] + ("…" if len(about) > 500 else "")
        lines.append(f"<i>{bio}</i>")
    else:
        lines.append("<i>No bio set</i>")
    lines.append(f"Common chats: {code(common_chats if common_chats is not None else 'N/A')}")

    lines.append(f"\n<b>Membership in This Group</b>")
    lines.append(f"Member: {pe('check', '✅') if is_member else pe('cross', '❌')}")
    if join_date:
        try:
            lines.append(f"Joined: {code(join_date.strftime('%Y-%m-%d %H:%M UTC'))}")
        except Exception:
            pass
    if admin_rights:
        lines.append(f"Admin status: {code(str(admin_rights))}")
    if banned_rights:
        try:
            is_banned = any([banned_rights.view_messages, banned_rights.send_messages, banned_rights.send_media])
            if is_banned:
                perm_until = getattr(banned_rights, "until_date", None)
                if perm_until:
                    lines.append(f"{pe('ban', '🚫')} Restricted until: {code(perm_until.strftime('%Y-%m-%d %H:%M UTC'))}")
                else:
                    lines.append(f"{pe('ban', '🚫')} Restricted: permanent")
        except Exception:
            pass

    lines.append(f"\n<b>Moderation History</b>")
    lines.append(f"{pe('warn', '⚠️')} Active warnings: {code(warn_count)} / {code(DEFAULT_WARN_LIMIT)}")
    if warn_reasons:
        lines.append("Recent reasons:")
        for r in warn_reasons:
            lines.append(f"  • {code(r)}")

    lines.append(f"\n<i>Report generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</i>")

    try:
        await event.reply("\n".join(lines), parse_mode="html")
    except Exception as e:
        await event.reply(f"⚠️ <b>Send Failed</b>\n\n{code(e)}", parse_mode="html")


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
            f"{pe('afk', '📴')} <b>AFK Mode Activated</b>\n\n"
            f"I'll automatically respond to anyone who mentions "
            f"<code>@{OWNER_USERNAME}</code>.\n\n"
            f"<b>Reply cooldown:</b> 60 seconds per user\n\n"
            f"<i>To disable, send <code>afk off</code>.</i>",
            parse_mode="html",
        )
    elif txt == "afk off":
        afk_state["enabled"] = False
        afk_state["since"] = None
        await event.reply(
            f"{pe('online', '🟢')} <b>AFK Mode Deactivated</b>\n\n"
            f"You're back online. Mention auto-replies are disabled.\n\n"
            f"<i>Welcome back!</i>",
            parse_mode="html",
        )
    elif txt == "afk":
        status = f"{pe('afk', '📴')} Active" if afk_state["enabled"] else f"{pe('online', '🟢')} Inactive"
        since_str = ""
        if afk_state["since"]:
            since_str = f"\n<b>Active since:</b> {code(afk_state['since'].strftime('%Y-%m-%d %H:%M UTC'))}"
        await event.reply(
            f"{pe('stats', '📊')} <b>AFK Status</b>\n\n"
            f"<b>Current state:</b> {status}{since_str}",
            parse_mode="html",
        )


# ============================================================
# 📌  PIN / UNPIN
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/pin(\s|$)"))
@safe_handler("pin_handler")
async def pin_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.reply(f"{pe('lock', '🔒')} <b>Admin Only</b>", parse_mode="html")
        return
    if not event.is_reply:
        await event.reply(
            f"{pe('pin', '📌')} <b>Pin a Message</b>\n\n"
            f"Reply to a message and send <code>/pin</code>.",
            parse_mode="html",
        )
        return
    replied = await event.get_reply_message()
    try:
        await bot(UpdatePinnedMessageRequest(peer=event.chat_id, id=replied.id, silent=False))
        await event.reply(
            f"{pe('pin', '📌')} <b>Message Pinned</b>\n\n"
            f"<b>Message ID:</b> {code(replied.id)}",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"⚠️ <b>Pin Failed</b>\n\n{code(e)}", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/unpin(\s|$)"))
@safe_handler("unpin_handler")
async def unpin_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.reply(f"{pe('lock', '🔒')} <b>Admin Only</b>", parse_mode="html")
        return
    if not event.is_reply:
        await event.reply(
            f"{pe('pin', '📌')} <b>Unpin a Message</b>\n\n"
            f"Reply to a message and send <code>/unpin</code>.",
            parse_mode="html",
        )
        return
    replied = await event.get_reply_message()
    try:
        await bot(UpdatePinnedMessageRequest(peer=event.chat_id, id=replied.id, unpin=True))
        await event.reply(
            f"{pe('pin', '📌')} <b>Message Unpinned</b>\n\n"
            f"<b>Message ID:</b> {code(replied.id)}",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"⚠️ <b>Unpin Failed</b>\n\n{code(e)}", parse_mode="html")


# ============================================================
# 👥  ADMIN LIST
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/admins(\s|$)"))
@safe_handler("admins_handler")
async def admins_handler(event):
    admins = await get_admin_list(event.chat_id)
    title = await get_group_title(event.chat_id)
    if not admins:
        await event.reply("📭 <b>No Admin Data</b>", parse_mode="html")
        return
    lines = [
        f"{pe('admin', '👥')} <b>Group Administration</b>\n",
        f"<b>Group:</b> {code(title)}\n"
        f"<b>Total Administrators:</b> {code(len(admins))}\n",
        f"<b>Current Admins:</b>",
    ]
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
        await event.reply(
            f"{pe('warn', '⚠️')} <b>Warning System</b>\n\n"
            f"<b>Usage:</b>\n"
            f"• Reply + <code>/warn [reason]</code>\n"
            f"• Or <code>/warn @username [reason]</code>",
            parse_mode="html",
        )
        return
    if await is_admin(event.chat_id, tid):
        await event.reply("🛡️ Admins cannot be warned.")
        return
    if tid < 0:
        await event.reply("⚠️ Channel posts cannot receive warnings.")
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
            action_note = (
                f"\n\n{pe('mute', '🔇')} <b>Auto-Mute Activated</b>\n"
                f"Having reached the warning limit, this member has been automatically muted for 1 hour."
            )
        except Exception as e:
            action_note = f"\n\n⚠️ <b>Auto-mute failed:</b> {code(e)}"

    await event.reply(
        f"{pe('warn', '⚠️')} <b>Formal Warning Issued</b>\n\n"
        f"<b>Member:</b> {make_mention(target_name, tid)}\n"
        f"<b>Reason:</b> {code(reason)}\n"
        f"<b>Warning Count:</b> {code(count)} / {code(DEFAULT_WARN_LIMIT)}\n\n"
        f"This is an official warning for conduct that violates our community rules.{action_note}",
        parse_mode="html",
    )


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/unwarn(\s|$)"))
@safe_handler("unwarn_handler")
async def unwarn_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    tid = await _resolve_target(event)
    if not tid:
        await event.reply(f"⚠️ <b>Usage:</b> Reply + <code>/unwarn</code> or <code>/unwarn @user</code>", parse_mode="html")
        return
    doc = await warns_col.find_one({"chat_id": event.chat_id, "user_id": tid})
    if not doc or not doc.get("count"):
        await event.reply("ℹ️ <b>No Warnings Found</b>", parse_mode="html")
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
        f"{pe('check', '✅')} <b>Warning Removed</b>\n\n"
        f"<b>Member:</b> {make_mention(target_name, tid)}\n"
        f"<b>Updated Count:</b> {code(new_count)} / {code(DEFAULT_WARN_LIMIT)}",
        parse_mode="html",
    )


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/warns(\s|$)"))
@safe_handler("warns_handler")
async def warns_handler(event):
    tid = await _resolve_target(event)
    if not tid:
        await event.reply(f"⚠️ <b>Usage:</b> Reply + <code>/warns</code> or <code>/warns @user</code>", parse_mode="html")
        return
    doc = await warns_col.find_one({"chat_id": event.chat_id, "user_id": tid})
    target_name = await get_user_name(tid)
    if not doc or not doc.get("count"):
        await event.reply(
            f"{pe('check', '✅')} <b>Clean Record</b>\n\n"
            f"{make_mention(target_name, tid)} has no active warnings.",
            parse_mode="html",
        )
        return
    reasons = doc.get("reasons", [])[-5:]
    lines = [
        f"{pe('warn', '⚠️')} <b>Warning History</b>\n",
        f"<b>Member:</b> {make_mention(target_name, tid)}\n"
        f"<b>Active Warnings:</b> {code(doc['count'])} / {code(DEFAULT_WARN_LIMIT)}\n",
        f"<b>Recent Warning Reasons:</b>",
    ]
    for r in reasons:
        lines.append(f"• {code(r)}")
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
        await event.reply(f"⚠️ <b>Usage:</b> Reply + <code>/kick</code> or <code>/kick @user</code>", parse_mode="html")
        return
    if await is_admin(event.chat_id, tid) or tid == OWNER_ID:
        await event.reply("🛡️ Admins and owner cannot be kicked.")
        return
    try:
        until = int(_tm.time() + KICK_BAN_SECONDS)
        await bot(EditBannedRequest(
            channel=event.chat_id, participant=tid,
            banned_rights=ChatBannedRights(until_date=until, view_messages=True),
        ))
        name = await get_user_name(tid)
        await event.reply(
            f"{pe('kick', '👢')} <b>Member Kicked</b>\n\n"
            f"<b>Target:</b> {make_mention(name, tid)}\n"
            f"<b>Duration:</b> {code(KICK_BAN_SECONDS)} seconds",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"⚠️ <b>Kick Failed</b>\n\n{code(e)}", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/ban(\s|$)"))
@safe_handler("ban_handler")
async def ban_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    tid = await _resolve_target(event)
    if not tid:
        await event.reply(f"⚠️ <b>Usage:</b> Reply + <code>/ban</code> or <code>/ban @user</code>", parse_mode="html")
        return
    if await is_admin(event.chat_id, tid) or tid == OWNER_ID:
        await event.reply("🛡️ Admins and owner cannot be banned.")
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
        await event.reply(
            f"{pe('ban', '🚫')} <b>Member Banned</b>\n\n"
            f"<b>Target:</b> {make_mention(name, tid)}\n"
            f"<b>Action:</b> Permanent removal",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"⚠️ <b>Ban Failed</b>\n\n{code(e)}", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/unban(\s|$)"))
@safe_handler("unban_handler")
async def unban_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    tid = await _resolve_target(event)
    if not tid:
        await event.reply(f"⚠️ <b>Usage:</b> Reply + <code>/unban</code> or <code>/unban @user</code>", parse_mode="html")
        return
    try:
        await bot(EditBannedRequest(
            channel=event.chat_id, participant=tid,
            banned_rights=ChatBannedRights(until_date=0),
        ))
        name = await get_user_name(tid)
        await event.reply(
            f"{pe('check', '✅')} <b>Member Unbanned</b>\n\n"
            f"<b>Target:</b> {make_mention(name, tid)}",
            parse_mode="html",
        )
    except Exception as e:
        await event.reply(f"⚠️ <b>Unban Failed</b>\n\n{code(e)}", parse_mode="html")


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
            f"{pe('delete', '🗑️')} <b>Bulk Message Deletion</b>\n\n"
            f"Reply to the first message in the range and send <code>/purge</code>.\n\n"
            f"<i>⚠️ This action cannot be undone.</i>",
            parse_mode="html",
        )
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
        await event.reply(
            f"{pe('delete', '🗑️')} <b>Purge Complete</b>\n\n"
            f"<b>Messages Deleted:</b> {code(deleted)}",
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
        await event.reply(f"📝 <b>Usage:</b> <code>/setrules [text]</code>", parse_mode="html")
        return
    await settings_col.update_one(
        {"chat_id": event.chat_id},
        {"$set": {"rules": args, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    await event.reply(
        f"{pe('check', '✅')} <b>Rules Saved</b>\n\n"
        f"Members can view them anytime with <code>/rules</code>.",
        parse_mode="html",
    )


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/rules(\s|$)"))
@safe_handler("rules_handler")
async def rules_handler(event):
    s = await get_settings(event.chat_id)
    rules = s.get("rules") or ""
    if not rules:
        await event.reply(
            f"📭 <b>No Rules Set Yet</b>\n\n"
            f"<i>Admins: use <code>/setrules [text]</code> to add them.</i>",
            parse_mode="html",
        )
        return
    await event.reply(f"{pe('book', '📖')} <b>Group Rules</b>\n\n{rules}", parse_mode="html")


@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/clearrules(\s|$)"))
@safe_handler("clearrules_handler")
async def clearrules_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        return
    await settings_col.update_one({"chat_id": event.chat_id}, {"$set": {"rules": ""}}, upsert=True)
    await event.reply(f"{pe('delete', '🗑️')} <b>Rules Cleared</b>", parse_mode="html")


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
        await event.reply(f"⚠️ <b>Usage:</b> <code>/welcome on</code> or <code>/welcome off</code>", parse_mode="html")
        return

    await settings_col.update_one({"chat_id": event.chat_id}, {"$set": {"welcome": new_val}}, upsert=True)
    if new_val:
        await event.reply(
            f"{pe('online', '🟢')} <b>Welcome Messages Enabled</b>\n\n"
            f"New members will receive a welcome message when joining.",
            parse_mode="html",
        )
    else:
        await event.reply(
            f"{pe('offline', '🔴')} <b>Welcome Messages Disabled</b>",
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
        f"🎉 <b>A warm welcome to our newest member!</b>\n\n"
        f"{make_mention(name, user_id)}, we're thrilled to have you join us here. "
        f"Feel free to introduce yourself and jump into the conversation.\n\n"
        f"<b>Quick Links:</b>\n"
        f"• {pe('book', '📖')} Group Rules: /rules\n"
        f"• {pe('info', 'ℹ️')} Command Help: /help\n"
        f"• {pe('admin', '👥')} Contact Admins: /admins\n\n"
        f"<b>Group Stats:</b>\n"
        f"• Members: {code(count_str)}\n"
        f"• Your ID: {code(user_id)}\n\n"
        f"<i>We hope you enjoy your time with us!</i>",
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
        f"🏛️ <b>BOD Manager — Ready to Serve</b>\n\n"
        f"Greetings, <b>{title}</b>! I'm <b>BOD Manager</b>, your dedicated group guardian.\n\n"
        f"<b>What I bring:</b>\n\n"
        f"🛡️ <b>Automated Moderation</b>\n"
        f"• Auto-delete member photos/videos\n"
        f"• Auto-remove link-sharing from non-admins\n"
        f"• Badword filtering with context detection\n"
        f"• Mute, warn, kick, ban actions\n\n"
        f"{pe('pin', '📌')} <b>Utility Features</b>\n"
        f"• Pin/unpin messages · report system · stats\n\n"
        f"⚙️ <b>Setup:</b>\n"
        f"1. Grant me <b>admin</b> status\n"
        f"2. Enable: <b>Ban Users</b>, <b>Delete Messages</b>, <b>Pin Messages</b>\n"
        f"3. Run <code>/help</code> for all commands\n\n"
        f"<i>Let's work together to make this group a safe and enjoyable space!</i>",
        parse_mode="html",
    )


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

    afk_status = f"{pe('afk', '📴')} Active" if afk_state["enabled"] else f"{pe('online', '🟢')} Inactive"

    await event.reply(
        f"{pe('stats', '📊')} <b>Group Statistics Report</b>\n\n"
        f"<b>Group Info</b>\n"
        f"Title: {code(title)}\n"
        f"Chat ID: {code(event.chat_id)}\n"
        f"Members: {code(count_str)}\n\n"
        f"<b>Administration</b>\n"
        f"Total Admins: {code(len(admins))}\n"
        f"Mutes today: {code(total_mutes)} / {code(len(admins) * MUTE_DAILY_LIMIT)}\n\n"
        f"<b>Bot Systems</b>\n"
        f"Tracked bots: {code(tracked)}\n"
        f"Badword filter: {pe('check', '✅')} ({code(len(BADWORDS))} words)\n"
        f"AFK mode: {afk_status}\n\n"
        f"<b>Report:</b> {code(today)}",
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
                f"{pe('id', '🆔')} <b>User Identification</b>\n\n"
                f"<b>Name:</b> {make_mention(name, r.sender_id)}\n"
                f"<b>User ID:</b> {code(r.sender_id)}\n"
                f"<b>Message ID:</b> {code(r.id)}",
                parse_mode="html",
            )
            return
    sender = await event.get_sender()
    name = (
        f"{getattr(sender, 'first_name', '') or ''} "
        f"{getattr(sender, 'last_name', '') or ''}"
    ).strip() or "User"
    await event.reply(
        f"{pe('id', '🆔')} <b>Chat Identification</b>\n\n"
        f"<b>Your Info</b>\n"
        f"Name: {make_mention(name, event.sender_id)}\n"
        f"User ID: {code(event.sender_id)}\n\n"
        f"<b>Chat Info</b>\n"
        f"Chat ID: {code(event.chat_id)}\n"
        f"Message ID: {code(event.message.id)}",
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
        f"{pe('stats', '📊')} <b>Your Mute Quota Today</b>\n\n"
        f"{bar}\n\n"
        f"<b>Used:</b> {code(used)} / {code(MUTE_DAILY_LIMIT)}\n"
        f"<b>Remaining:</b> {code(remaining)}\n"
        f"<b>Resets:</b> UTC 00:00",
        parse_mode="html",
    )


# ============================================================
# 📖  /start  &  /help
# ============================================================
@bot.on(events.NewMessage(pattern=r"^/start(\s|$)"))
@safe_handler("start_handler")
async def start_handler(event):
    afk_status = f"{pe('afk', '📴')} Active" if afk_state["enabled"] else f"{pe('online', '🟢')} Inactive"
    await event.reply(
        f"🏛️ <b>BOD Manager</b>\n\n"
        f"I'm your group's dedicated moderation and management system.\n\n"
        f"<b>System Status:</b> {code('All systems operational')}\n"
        f"<b>AFK Mode:</b> {afk_status}\n"
        f"<b>Mute Quota:</b> {code(MUTE_DAILY_LIMIT)} per admin per day\n"
        f"<b>Badword Filter:</b> {pe('check', '✅')}\n"
        f"<b>Link Protection:</b> {pe('check', '✅')}\n"
        f"<b>Media Moderation:</b> {pe('check', '✅')}\n\n"
        f"<b>Quick Access:</b>\n"
        f"• {pe('book', '📖')} <code>/help</code> — All commands\n"
        f"• {pe('book', '📖')} <code>/rules</code> — Group rules\n"
        f"• {pe('admin', '👥')} <code>/admins</code> — Contact admins\n"
        f"• {pe('alert', '🚨')} <code>/report</code> — Report content",
        parse_mode="html",
    )


@bot.on(events.NewMessage(pattern=r"^/help(\s|$)"))
@safe_handler("help_handler")
async def help_handler(event):
    text = (
        f"{pe('book', '📖')} <b>BOD Manager — Command Reference</b>\n\n"
        f"<b>👑 Owner Commands</b>\n"
        f"• <code>စာပိတ်</code> — Lock the group\n"
        f"• <code>စာဖွင့်</code> — Unlock the group\n"
        f"• Reply + <code>ဘန်း</code> — Permanently ban\n"
        f"• Reply + <code>ကစ်</code> — Kick for 60 seconds\n"
        f"• Reply + <code>adm</code> — Grant limited admin\n"
        f"• Reply + <code>?</code> — Advanced user info\n"
        f"• <code>afk on</code> / <code>afk off</code> — AFK mode\n"
        f"• Reply + <code>/del</code> or <code>ဖျက်မယ်</code> — Track bot\n"
        f"• <code>/untrack [id]</code> · <code>/tracked</code>\n\n"
        f"<b>🛡️ Moderation (Admins)</b>\n"
        f"• Reply + <code>မြုလိုက်</code> / <code>/mute</code> — Mute (5/day)\n"
        f"• Reply + <code>ပြန်ဖွင့်</code> / <code>/unmute</code> — Unmute\n"
        f"• <code>/warn @user [reason]</code> — Issue warning\n"
        f"• <code>/unwarn @user</code> · <code>/warns @user</code>\n"
        f"• <code>/kick @user</code> · <code>/ban @user</code> · <code>/unban @user</code>\n"
        f"• Reply + <code>/pin</code> · <code>/unpin</code> · <code>/purge</code>\n"
        f"• <code>/setrules [text]</code> · <code>/clearrules</code>\n"
        f"• <code>/welcome on/off</code> · <code>/mutecount</code>\n"
        f"• <code>/stats</code> · <code>/admins</code>\n\n"
        f"<b>👥 Member Commands</b>\n"
        f"• <code>/start</code> · <code>/help</code> · <code>/rules</code> · <code>/id</code>\n"
        f"• Reply + <code>/report</code> — Report to admins (3h cooldown)\n\n"
        f"<b>🚫 Automated Protection</b>\n"
        f"• Non-admin photos/videos auto-deleted\n"
        f"• Non-admin links auto-deleted\n"
        f"• Badword filter with 5-min window\n"
        f"• Stickers and GIFs always allowed\n"
        f"• Muted users fully blocked\n\n"
        f"<b>📊 System Limits</b>\n"
        f"• Mute: {code(MUTE_DAILY_LIMIT)} / day / admin (resets UTC 00:00)\n"
        f"• Badword window: 5 min (2nd offense = 1h mute)\n"
        f"• Report cooldown: 3 hours / user\n"
        f"• AFK cooldown: 60 seconds / user"
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
            f"{pe('online', '🟢')} <b>BOD Manager Online</b>\n\n"
            f"All systems operational.\n\n"
            f"<b>Configuration:</b>\n"
            f"• Target group: {code(OFFICIAL_GROUP_ID)}\n"
            f"• Auto-delete: {pe('check', '✅')} (photos/videos/links)\n"
            f"• Stickers/GIFs: {pe('check', '✅')} (allowed)\n"
            f"• Mute quota: {code(MUTE_DAILY_LIMIT)} / admin / day\n"
            f"• Badword filter: {pe('check', '✅')} ({code(len(BADWORDS))} words)\n"
            f"• AFK mode: {pe('offline', '🔴')} Inactive\n"
            f"• Report cooldown: {code('3 hours')}\n"
            f"• Tracked bots: {code(len(tracked_bots_cache))}\n\n"
            f"<i>Send /help for the full command reference.</i>",
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
