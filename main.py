# ============================================================
# 🏛️  BOD MANAGER  —  main.py (standalone)
# ============================================================
# Python 3.14+ compatible | Telethon 1.28+ required
# ✅ Telethon <tg-emoji> patch included
# ✅ Strict Emoji Rule: NO fallback emojis, only premium IDs
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
    ChannelParticipantCreator, MessageEntityCustomEmoji,
)
from motor.motor_asyncio import AsyncIOMotorClient


# ============================================================
# 🛠️  TELETHON HTML PATCH FOR PREMIUM EMOJI (<tg-emoji>)
# ============================================================
from telethon.extensions import html
TG_EMOJI_RE = re.compile(r'<tg-emoji\s+emoji-id="(\d+)">(.*?)</tg-emoji>', re.DOTALL)
_original_parse = html.parse

def _custom_parse(text):
    emojis = []
    def repl(m):
        idx = len(emojis)
        emojis.append((int(m.group(1)), m.group(2)))
        return f"\uE000{idx}\uE001"
        
    temp_text = TG_EMOJI_RE.sub(repl, text)
    parsed_text, entities = _original_parse(temp_text)
    
    matches = list(re.finditer(r'\uE000(\d+)\uE001', parsed_text))
    
    for m in reversed(matches):
        start, end = m.span()
        emoji_idx = int(m.group(1))
        emoji_id, fallback = emojis[emoji_idx]
        
        utf16_start = len(parsed_text[:start].encode('utf-16-le')) // 2
        utf16_len = len(fallback.encode('utf-16-le')) // 2
        
        entities.append(MessageEntityCustomEmoji(
            offset=utf16_start,
            length=utf16_len,
            document_id=emoji_id
        ))
        
        parsed_text = parsed_text[:start] + fallback + parsed_text[end:]
        shift = (end - start) - utf16_len
        
        for ent in entities:
            if ent.offset >= (utf16_start + (end - start)):
                ent.offset -= shift
                
    entities.sort(key=lambda e: e.offset)
    return parsed_text, entities

# Apply the patch
html.parse = _custom_parse


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


# ============================================================
# ✨  PREMIUM EMOJI IDs & STRICT FUNCTION
# ============================================================
PREMIUM_EMOJI = {
    # ID မထည့်ထားတဲ့ Key တွေကို လုံးဝ Emoji မပြပါဘူး
    "bot":       None, "shield":    None, "crown":     None, 
    "star":      None, "sparkle":   None, "party":     None, 
    "heart":     None, "wave":      None, "trophy":    None,
    "key":       None, "gear":      None, "rocket":    None, 
    "ghost":     None,
    
    # အသုံးပြုမယ့် Premium ID များ
    "mute":      6039505337151655702, "unmute":    6039454987250044861, 
    "warn":      5461098492216752942, "ban":       5368562433981947135, 
    "kick":      6177127866115822461, "lock":      6037249452824072506,
    "unlock":    6037496202990194718, "check":     5305670334513427489, 
    "cross":     5447544503143504937, "clock":     5215327832040811010, 
    "alert":     5212969852045634932, "pin":       5422357698228290320,
    "delete":    6039522349517115015, "fire":      5402406965252989103, 
    "eyes":      5350732341109081597, "target":    6032949275732742941, 
    "stats":     5231200819986047254, "info":      5456309534962234647,
    "id":        5465465194056525619, "admin":     5373110220232870002, 
    "book":      6181489083282363892, "link":      6240200624793720535, 
    "afk":       5449875850046481967, "online":    5217449524410199951,
    "offline":   5444965061749644170, "sleep":     5462990652943904884,
}

def pe(key: str, fallback: str = "") -> str:
    """Strict Premium Emoji: Returns empty string if ID is missing."""
    eid = PREMIUM_EMOJI.get(key)
    if eid:
        # Telegram က tag အတွင်းမှာ fallback စာသား လိုအပ်တာမို့ fallback ကို သုံးထားပါတယ်
        return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'
    return "" # ID မရှိရင် ဘာ Emoji မှ မပြပါ


# ============================================================
# 🚫  BADWORDS
# ============================================================
BADWORDS = [
    "ဖာသယ်မ", "ဖာသည်မ", "ဖာသယ်မသား", "ဖာသည်မသား",
    "လီး", "မှန်းထု", "မှန်း", "လိုး", "မအေလိုး", "ငါလိုးမသား",
]

BADWORD_SAFE_CONTEXTS = [
    "ရည်မှန်းချက်", "ရည်မှန်း", "ခန့်မှန်းချက်", "ခန့်မှန်း", "ခန့်မှန်းတွက်", "ခန့်မှန်းပြ",
    "မှန်းဆချက်", "မှန်းဆ", "မှန်းဆတွက်", "လီးလာ", "တစ်လီး", "နှစ်လီး", "သုံးလီး",
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
# 🗄️  DATABASE & BOT CLIENT
# ============================================================
_mongo = AsyncIOMotorClient(MONGO_URI, io_loop=_loop)
db = _mongo["group_manager"]

tracked_bots_col    = db["tracked_bots"]
mute_daily_col      = db["mute_daily"]
warns_col           = db["warns"]
settings_col        = db["group_settings"]
report_cooldown_col = db["report_cooldown"]

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
# 📴  AFK STATE & HELPERS
# ============================================================
afk_state = {"enabled": False, "since": None, "reply_cooldown": {}}
badword_tracker: dict[tuple, list] = {}

def safe_handler(ctx: str):
    def deco(fn):
        async def wrapper(event, *a, **k):
            try:
                return await fn(event, *a, **k)
            except Exception as e:
                print(f"❌ [{ctx}] {type(e).__name__}: {e}")
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
    if not text: return ""
    try: return "".join(c for c in text if unicodedata.category(c) != "Cf")
    except Exception: return text

def get_text(event) -> str: return event.text or ""

def get_cmd_and_args(text: str):
    if not text: return "", ""
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0]
    args = parts[1].strip() if len(parts) > 1 else ""
    if "@" in cmd: cmd = cmd.split("@", 1)[0]
    return cmd, args

def strip_bot_suffix(text: str) -> str:
    t = (text or "").strip()
    if "@" in t:
        first = t.split()[0]
        if "@" in first: return t.replace(first, first.split("@", 1)[0], 1).strip()
    return t

def fmt_secs(seconds: int) -> str:
    seconds = int(seconds)
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    parts = []
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s: parts.append(f"{s}s")
    return " ".join(parts) if parts else "0s"

LINK_REGEX = re.compile(r"(?:https?://|ftp://|www\.|t\.me/|telegram\.me/|tg://)", re.IGNORECASE)

async def _has_link(message) -> bool:
    if not message: return False
    text = message.text or message.message or ""
    if LINK_REGEX.search(text): return True
    try:
        for ent in (getattr(message, "entities", None) or []):
            if isinstance(ent, (MessageEntityUrl, MessageEntityTextUrl)): return True
    except Exception: pass
    return False

def _contains_badword(text: str) -> str | None:
    if not text: return None
    t = clean_invisible(text)
    masked = t
    for safe in _BADWORD_SAFE_SORTED:
        if safe in masked: masked = masked.replace(safe, "▢" * len(safe))
    for bw in BADWORDS:
        if bw in masked: return bw
    return None

_admin_cache: dict[int, dict] = {}

async def get_admin_ids(chat_id: int) -> set[int]:
    now = _tm.time()
    cached = _admin_cache.get(chat_id)
    if cached and now < cached["expiry"]: return cached["ids"]
    try:
        result = await bot(GetParticipantsRequest(chat_id, ChannelParticipantsAdmins(), 0, 200, 0))
        ids = {u.id for u in result.users}
        _admin_cache[chat_id] = {"ids": ids, "expiry": now + ADMIN_CACHE_TTL}
        return ids
    except Exception:
        _admin_cache[chat_id] = {"ids": set(), "expiry": now + 10}
        return set()

async def is_admin(chat_id: int, user_id: int) -> bool:
    if user_id == OWNER_ID: return True
    return user_id in await get_admin_ids(chat_id)

async def get_admin_list(chat_id: int) -> list[tuple[int, str]]:
    try:
        result = await bot(GetParticipantsRequest(chat_id, ChannelParticipantsAdmins(), 0, 200, 0))
        out, seen = [], set()
        for u in result.users:
            if u.id in seen: continue
            seen.add(u.id)
            name = f"{u.first_name or ''} {u.last_name or ''}".strip() or "Admin"
            out.append((u.id, name))
        if OWNER_ID not in seen: out.append((OWNER_ID, "Owner"))
        return out
    except Exception: return [(OWNER_ID, "Owner")]

async def get_user_name(user_id: int) -> str:
    try:
        u = await bot.get_entity(user_id)
        return f"{u.first_name or ''} {u.last_name or ''}".strip() or str(user_id)
    except Exception: return str(user_id)

async def get_group_title(chat_id: int) -> str:
    try:
        ent = await bot.get_entity(chat_id)
        return getattr(ent, "title", str(chat_id)) or str(chat_id)
    except Exception: return str(chat_id)

async def _resolve_target(event):
    if event.is_reply:
        r = await event.get_reply_message()
        if r and r.sender_id: return r.sender_id
    _, args = get_cmd_and_args(get_text(event))
    if not args: return None
    tok = args.split()[0]
    try:
        if tok.startswith("@"): return (await bot.get_entity(tok)).id
        return int(tok)
    except Exception: return None


# ============================================================
# 🚫  BADWORD FILTER
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("badword_filter_handler")
async def badword_filter_handler(event):
    if not event.text: return
    sender_id, chat_id = event.sender_id, event.chat_id

    try:
        if await is_admin(chat_id, sender_id): return
        sender = await event.get_sender()
        if getattr(sender, "bot", False): return
    except Exception: pass

    badword = _contains_badword(event.text)
    if not badword: return

    name = await get_user_name(sender_id)
    mention = make_mention(name, sender_id)
    key, now = (chat_id, sender_id), _tm.time()
    history = [t for t in badword_tracker.get(key, []) if now - t < BADWORD_WINDOW_SECONDS]
    history.append(now)
    badword_tracker[key] = history

    if len(history) >= 2:
        try:
            until = int(now + BADWORD_MUTE_DURATION)
            await bot(EditBannedRequest(chat_id, sender_id, ChatBannedRights(
                until_date=until, view_messages=False, send_messages=True,
                send_media=True, send_stickers=True, send_gifs=True,
                send_games=True, send_inline=True, embed_links=True, send_polls=True
            )))
            expiry = datetime.fromtimestamp(until, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            await event.reply(
                f"{pe('mute', '🔇')} <b>Language Restriction Activated</b>\n\n"
                f"{mention} — your message contained prohibited language.\n\n"
                f"<b>Restriction:</b> Muted for 1 hour\n"
                f"<b>Expires:</b> {code(expiry)}\n"
                f"<b>Reason:</b> Second violation within a 5-minute window\n\n"
                f"<i>Respect is the foundation of every healthy community.</i>",
                parse_mode="html", reply_to=event.id,
            )
            badword_tracker.pop(key, None)
        except Exception as e:
            await event.reply(f"{pe('cross', '❌')} <b>Action Failed</b>\n\n{code(str(e))}", parse_mode="html")
        return

    try:
        await event.reply(
            f"{pe('warn', '⚠️')} <b>A Gentle Reminder</b> {mention}\n\n"
            f"The message you just sent contains language that isn't welcome here.\n\n"
            f"Please be mindful — a second occurrence within the next <b>5 minutes</b> will result in a <b>1-hour mute</b>.\n\n"
            f"<i>Thank you for helping us keep this community welcoming.</i>",
            parse_mode="html", reply_to=event.id,
        )
    except Exception: pass


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
    except Exception: pass

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("media_moderation_handler")
async def media_moderation_handler(event):
    msg, sender_id, chat_id = event.message, event.sender_id, event.chat_id
    my_id = await _ensure_me()

    if sender_id in tracked_bots_cache:
        try: await event.delete()
        except Exception: pass
        return

    if sender_id == my_id: return
    try:
        sender = await event.get_sender()
        if getattr(sender, "bot", False): return
    except Exception: pass
    try:
        if await is_admin(chat_id, sender_id): return
    except Exception: pass

    if getattr(msg, "sticker", None) or getattr(msg, "gif", False): return
    try:
        if msg.document:
            for attr in (msg.document.attributes or []):
                if attr.__class__.__name__ == "DocumentAttributeAnimated": return
    except Exception: pass

    via_bot = getattr(event, "via_bot_id", None) or getattr(msg, "via_bot_id", None)
    is_media = bool(msg.photo or msg.video)
    delete_media = is_media and not via_bot
    delete_link = False
    if not via_bot:
        try: delete_link = await _has_link(msg)
        except Exception: pass

    if not (delete_media or delete_link): return

    try: await event.delete()
    except Exception: pass

    if delete_link:
        try:
            name = await get_user_name(sender_id)
            await bot.send_message(
                chat_id,
                f"{pe('cross', '❌')} <b>Link Sharing Restricted</b>\n\n"
                f"{make_mention(name, sender_id)} — links are not permitted here for members. "
                f"Your message has been removed automatically.\n\n"
                f"<i>If this was an error, please contact an admin via /report.</i>",
                parse_mode="html",
            )
        except Exception: pass


# ============================================================
# 📴  AFK MENTION AUTO-REPLY
# ============================================================
AFK_EN_MSG = "Owner Morgan is currently AFK.\n\nHe might be busy, resting, studying, watching a movie, or gaming. Please leave your message, and he'll reply when he's back online."
AFK_MM_MSG = "Owner Morgan လောလောဆယ် AFK ဖြစ်နေပါတယ်။\n\nအလုပ်များနေတာ၊ အနားယူနေတာ၊ စာလေ့လာနေတာ၊ Movie ကြည့်နေတာ ဒါမှမဟုတ် Game ဆော့နေတာ ဖြစ်နိုင်ပါတယ်။ ပြောစရာရှိတာတွေ တစ်ခါတည်း ရေးထားပေးပါ။ Online ပြန်တက်လာရင် Reply ပြန်ပေးပါလိမ့်မယ်။"

def _mentions_owner(message) -> bool:
    text = (message.text or message.message or "").lower()
    target = OWNER_USERNAME.lower()
    if f"@{target}" in text: return True
    try:
        for ent in (message.entities or []):
            if isinstance(ent, MessageEntityMention):
                mentioned = text[ent.offset:ent.offset + ent.length].lstrip("@").lower()
                if mentioned == target: return True
    except Exception: pass
    return False

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("afk_mention_handler")
async def afk_mention_handler(event):
    if not afk_state["enabled"]: return
    sender_id = event.sender_id
    if sender_id in (OWNER_ID, await _ensure_me()): return

    msg = event.message
    triggered = _mentions_owner(msg)
    if not triggered and event.is_reply:
        try:
            replied = await event.get_reply_message()
            if replied and replied.sender_id == OWNER_ID: triggered = True
        except Exception: pass
    if not triggered: return

    now, cooldowns = _tm.time(), afk_state["reply_cooldown"]
    last = cooldowns.get(sender_id, 0)
    if now - last < AFK_REPLY_COOLDOWN: return
    cooldowns[sender_id] = now

    try:
        await event.reply(
            f"{pe('afk', '📴')} <b>AFK Auto-Reply</b>\n\n"
            f"{AFK_EN_MSG}\n\n"
            f"{AFK_MM_MSG}",
            parse_mode="html",
        )
    except Exception: pass


# ============================================================
# 🚨  REPORT & REMINDER
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^(?:/report|report)(?:@\w+)?(?:\s|$)"))
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
                f"All group admins will receive an alert immediately.\n\n"
                f"<i>Note: Each member may report once every 3 hours.</i>",
                parse_mode="html",
            )
        return

    replied = await event.get_reply_message()
    if not replied:
        await event.reply("⚠️ Unable to locate the message you replied to.")
        return

    user_id, chat_id, now = event.sender_id, event.chat_id, _tm.time()
    doc = await report_cooldown_col.find_one({"chat_id": chat_id, "user_id": user_id})
    if doc:
        last = float(doc.get("last_report", 0))
        if now - last < REPORT_COOLDOWN_SECONDS:
            remaining = int(REPORT_COOLDOWN_SECONDS - (now - last))
            await event.reply(
                f"{pe('clock', '⏳')} <b>Report Cooldown Active</b>\n\n"
                f"You've recently submitted a report. To prevent spam, each member may report once every 3 hours.\n\n"
                f"<b>Time remaining:</b> {code(fmt_secs(remaining))}",
                parse_mode="html",
            )
            return

    try:
        await report_cooldown_col.update_one({"chat_id": chat_id, "user_id": user_id}, {"$set": {"last_report": now}}, upsert=True)
    except Exception: pass

    admins = await get_admin_list(chat_id)
    admin_mentions = " ".join(make_mention(name, uid) for uid, name in admins)
    reporter = await event.get_sender()
    reporter_name = f"{getattr(reporter, 'first_name', '') or ''} {getattr(reporter, 'last_name', '') or ''}".strip() or "User"
    target_id = replied.sender_id
    target_name = await get_user_name(target_id) if target_id else "Unknown"
    target_mention = make_mention(target_name, target_id) if target_id else "Unknown"

    try: await bot.forward_messages(OWNER_ID, replied.id, chat_id)
    except Exception: pass

    try:
        await bot.send_message(
            chat_id,
            f"{pe('alert', '🚨')} <b>Report Received</b>\n\n"
            f"<b>Reporter:</b> {make_mention(reporter_name, user_id)}\n"
            f"<b>Reported User:</b> {target_mention}\n"
            f"<b>Message ID:</b> {code(replied.id)}\n\n"
            f"<b>Alerting Admins:</b>\n{admin_mentions}\n\n"
            f"<b>Recommended Action:</b>\n"
            f"If the content violates our rules, reply to the offender with <code>မြုလိုက်</code> to apply a mute.\n\n"
            f"<i>The reported message is displayed below.</i>",
            parse_mode="html", reply_to=replied.id,
        )
    except Exception: pass

    try:
        await event.reply(
            f"{pe('check', '✅')} <b>Report Submitted</b>\n\n"
            f"Thank you for helping keep our community safe. Admins have been notified.\n\n"
            f"<b>Next available report:</b> in 3 hours",
            parse_mode="html",
        )
    except Exception: pass

async def report_reminder_loop():
    await asyncio.sleep(60)
    while True:
        try:
            await bot.send_message(
                OFFICIAL_GROUP_ID,
                f"{pe('alert', '🚨')} <b>Community Safety Reminder</b>\n\n"
                f"If you encounter content that violates our community guidelines — whether it's spam, inappropriate language, or anything else that feels off — please report it using these steps:\n\n"
                f"<b>1.</b> Reply to the offending message\n"
                f"<b>2.</b> Send <code>/report</code>\n\n"
                f"All admins will be alerted immediately.\n\n"
                f"<i>Each member may submit one report every 3 hours.</i>",
                parse_mode="html",
            )
        except Exception: pass
        await asyncio.sleep(REPORT_REMINDER_SECONDS)


# ============================================================
# 🤖  BOT TRACKING
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^(?:/del|ဖျက်မယ်)(?:@\w+)?(?:\s|$)"))
@safe_handler("del_track_handler")
async def del_track_handler(event):
    if event.sender_id != OWNER_ID: return
    if not event.is_reply:
        await event.reply(f"{pe('delete', '🗑️')} <b>Bot Tracking System</b>\n\nReply directly to a bot's message with <code>/del</code> or <code>ဖျက်မယ်</code>.", parse_mode="html")
        return

    replied = await event.get_reply_message()
    if not replied or not replied.sender_id:
        await event.reply("⚠️ Unable to identify the message sender.")
        return

    target_id = replied.sender_id
    try: sender = await bot.get_entity(target_id)
    except Exception: sender = None

    is_bot = bool(sender and getattr(sender, "bot", False))
    username = getattr(sender, "username", None) if sender else None
    display = f"{getattr(sender, 'first_name', '') or ''} {getattr(sender, 'last_name', '') or ''}".strip() if sender else str(target_id)

    try:
        await tracked_bots_col.update_one({"bot_id": target_id, "chat_id": event.chat_id}, {"$set": {"bot_id": target_id, "chat_id": event.chat_id, "username": username, "display_name": display, "is_bot": is_bot, "added_by": event.sender_id, "added_at": datetime.now(timezone.utc)}}, upsert=True)
        tracked_bots_cache[target_id] = event.chat_id
    except Exception as e:
        await event.reply(f"⚠️ Failed to save: {code(e)}", parse_mode="html"); return

    try: await replied.delete()
    except Exception: pass

    kind = "🤖 Bot" if is_bot else "👤 User"
    uname_str = f" (<code>@{username}</code>)" if username else ""
    await event.reply(
        f"{pe('check', '✅')} <b>Auto-Delete Activated</b>\n\n"
        f"<b>Type:</b> {kind}\n"
        f"<b>Name:</b> {make_mention(display, target_id)}{uname_str}\n"
        f"<b>ID:</b> {code(target_id)}\n\n"
        f"To stop: <code>/untrack {target_id}</code>.",
        parse_mode="html",
    )

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/untrack(\s|$)"))
@safe_handler("untrack_handler")
async def untrack_handler(event):
    if event.sender_id != OWNER_ID: return
    _, args = get_cmd_and_args(get_text(event))
    if not args or not args.split()[0].isdigit():
        await event.reply(f"⚠️ <b>Usage:</b> <code>/untrack [id]</code>", parse_mode="html"); return
    
    tid = int(args.split()[0])
    try:
        res = await tracked_bots_col.delete_one({"bot_id": tid, "chat_id": event.chat_id})
        tracked_bots_cache.pop(tid, None)
        if res.deleted_count: await event.reply(f"{pe('check', '✅')} <b>Deactivated</b>\n\nEntity {code(tid)} removed.", parse_mode="html")
        else: await event.reply(f"ℹ️ <b>Not Found</b>", parse_mode="html")
    except Exception as e: await event.reply(f"⚠️ {code(e)}", parse_mode="html")


# ============================================================
# 🔇  MUTE / 🔊 UNMUTE
# ============================================================
MUTE_COMMANDS   = {"မြုလိုက်", "မြုလိုက်ပါ", "mute", "mutethatgay", "/mute"}
UNMUTE_COMMANDS = {"ပြန်ဖွင့်", "ပြန်ဖွင့်", "ပြန်ဖွင့်ပါ", "ပြန်ဖွင့်ပါ", "unmute", "/unmute"}

def _mute_rights() -> ChatBannedRights:
    return ChatBannedRights(until_date=0, view_messages=False, send_messages=True, send_media=True, send_stickers=True, send_gifs=True, send_games=True, send_inline=True, embed_links=True, send_polls=True)

def _unmute_rights() -> ChatBannedRights: return ChatBannedRights(until_date=0)

async def get_mute_count(admin_id: int, chat_id: int) -> int:
    doc = await mute_daily_col.find_one({"admin_id": admin_id, "chat_id": chat_id, "date": today_str()})
    return int(doc["count"]) if doc else 0

async def increment_mute_count(admin_id: int, chat_id: int):
    await mute_daily_col.update_one({"admin_id": admin_id, "chat_id": chat_id, "date": today_str()}, {"$inc": {"count": 1}}, upsert=True)

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("mute_handler")
async def mute_handler(event):
    if not event.text: return
    trigger = event.text.strip()
    if "@" in trigger: trigger = trigger.split("@", 1)[0].strip()
    trigger_lower = trigger.lower()
    is_mute = trigger_lower in MUTE_COMMANDS
    is_unmute = trigger_lower in UNMUTE_COMMANDS
    if not (is_mute or is_unmute): return

    if not await is_admin(event.chat_id, event.sender_id):
        await event.reply(f"{pe('lock', '🔒')} <b>Admin Permission Required</b>", parse_mode="html"); return

    if not event.is_reply:
        word = "မြုလိုက်" if is_mute else "ပြန်ဖွင့်"
        await event.reply(f"{pe('warn', '⚠️')} <b>Reply Required</b>\n\nReply and send <code>{word}</code>.", parse_mode="html"); return

    replied = await event.get_reply_message()
    if not replied or not replied.sender_id:
        await event.reply("⚠️ Unable to identify target."); return

    target_id = replied.sender_id
    if target_id == event.sender_id: await event.reply("⚠️ Cannot target yourself."); return
    if target_id == OWNER_ID: await event.reply("🛡️ Owner is protected."); return
    if target_id < 0: await event.reply("⚠️ Cannot target channel posts."); return
    try:
        target_user = await bot.get_entity(target_id)
        if target_user and getattr(target_user, "bot", False): await event.reply("⚠️ Bots cannot be muted."); return
    except Exception: pass
    if await is_admin(event.chat_id, target_id):
        await event.reply(f"🛡️ <b>Protected Member</b>", parse_mode="html"); return

    target_name = await get_user_name(target_id)
    if is_mute:
        used = await get_mute_count(event.sender_id, event.chat_id)
        if used >= MUTE_DAILY_LIMIT:
            await event.reply(f"{pe('clock', '⏳')} <b>Daily Mute Quota Reached</b>\n\nUsed: {code(used)} / {code(MUTE_DAILY_LIMIT)}", parse_mode="html"); return

    try:
        if is_mute:
            await bot(EditBannedRequest(event.chat_id, target_id, _mute_rights()))
            await increment_mute_count(event.sender_id, event.chat_id)
            used_after = await get_mute_count(event.sender_id, event.chat_id)
            remaining = max(0, MUTE_DAILY_LIMIT - used_after)
            await event.reply(
                f"{pe('mute', '🔇')} <b>Member Muted</b>\n\n"
                f"<b>Target:</b> {make_mention(target_name, target_id)}\n"
                f"<b>Quota Used:</b> {code(used_after)} / {code(MUTE_DAILY_LIMIT)}\n"
                f"<b>Remaining:</b> {code(remaining)}",
                parse_mode="html",
            )
        else:
            await bot(EditBannedRequest(event.chat_id, target_id, _unmute_rights()))
            await event.reply(f"{pe('unmute', '🔊')} <b>Member Unmuted</b>\n\n<b>Target:</b> {make_mention(target_name, target_id)}", parse_mode="html")
    except Exception as e:
        err = str(e)
        if any(k in err.lower() for k in ("admin", "right", "permission")):
            await event.reply(f"{pe('cross', '❌')} <b>Insufficient Permissions</b>\n\nEnable <b>Ban Users</b>.", parse_mode="html")
        else:
            await event.reply(f"⚠️ <b>Failed</b>\n\n{code(err)}", parse_mode="html")


# ============================================================
# 👑  OWNER COMMANDS (Burmese)
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("lock_chat_handler")
async def lock_chat_handler(event):
    if event.sender_id != OWNER_ID or strip_bot_suffix(event.text or "") != "စာပိတ်": return
    try:
        await bot(EditChatDefaultBannedRightsRequest(event.chat_id, ChatBannedRights(until_date=0, view_messages=False, send_messages=True, send_media=True, send_stickers=True, send_gifs=True, send_games=True, send_inline=True, embed_links=True, send_polls=True)))
        await event.reply(f"{pe('lock', '🔒')} <b>Group Locked</b>\n\nOnly admins can send messages now.", parse_mode="html")
    except Exception as e: await event.reply(f"⚠️ {code(e)}", parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("unlock_chat_handler")
async def unlock_chat_handler(event):
    if event.sender_id != OWNER_ID or strip_bot_suffix(event.text or "") != "စာဖွင့်": return
    try:
        await bot(EditChatDefaultBannedRightsRequest(event.chat_id, ChatBannedRights(until_date=0)))
        await event.reply(f"{pe('unlock', '🔓')} <b>Group Unlocked</b>\n\nAll members can send again.", parse_mode="html")
    except Exception as e: await event.reply(f"⚠️ {code(e)}", parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("owner_ban_handler")
async def owner_ban_handler(event):
    if event.sender_id != OWNER_ID or strip_bot_suffix(event.text or "") not in ("ဘန်း", "ဘန်း "): return
    tid = await _resolve_target(event)
    if not tid: await event.reply(f"{pe('warn', '⚠️')} Reply to a message and send <code>ဘန်း</code>.", parse_mode="html"); return
    if tid == OWNER_ID or await is_admin(event.chat_id, tid): await event.reply("🛡️ Protected."); return
    try:
        await bot(EditBannedRequest(event.chat_id, tid, ChatBannedRights(until_date=0, view_messages=True, send_messages=True, send_media=True, send_stickers=True, send_gifs=True, send_games=True, send_inline=True, embed_links=True, send_polls=True)))
        name = await get_user_name(tid)
        await event.reply(f"{pe('ban', '🚫')} <b>Member Banned</b>\n\n<b>Target:</b> {make_mention(name, tid)}", parse_mode="html")
    except Exception as e: await event.reply(f"⚠️ {code(e)}", parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("owner_kick_handler")
async def owner_kick_handler(event):
    if event.sender_id != OWNER_ID or strip_bot_suffix(event.text or "") not in ("ကစ်", "ကစ် "): return
    tid = await _resolve_target(event)
    if not tid: await event.reply(f"{pe('warn', '⚠️')} Reply to a message and send <code>ကစ်</code>.", parse_mode="html"); return
    if tid == OWNER_ID or await is_admin(event.chat_id, tid): await event.reply("🛡️ Protected."); return
    try:
        until = int(_tm.time() + KICK_BAN_SECONDS)
        await bot(EditBannedRequest(event.chat_id, tid, ChatBannedRights(until_date=until, view_messages=True)))
        name = await get_user_name(tid)
        await event.reply(f"{pe('kick', '👢')} <b>Member Kicked</b>\n\n<b>Target:</b> {make_mention(name, tid)}\n<b>Duration:</b> {code(KICK_BAN_SECONDS)}s", parse_mode="html")
    except Exception as e: await event.reply(f"⚠️ {code(e)}", parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("owner_adm_handler")
async def owner_adm_handler(event):
    if event.sender_id != OWNER_ID or strip_bot_suffix(event.text or "") != "adm": return
    tid = await _resolve_target(event)
    if not tid: await event.reply(f"🛡️ Reply and send <code>adm</code>.", parse_mode="html"); return
    try:
        await bot(EditAdminRequest(event.chat_id, tid, ChatAdminRights(change_info=False, post_messages=False, edit_messages=False, delete_messages=True, ban_users=False, invite_users=True, pin_messages=True, add_admins=False, anonymous=False, manage_call=False, other=False, manage_topics=False), rank="Moderator"))
        name = await get_user_name(tid)
        await event.reply(f"🛡️ <b>Moderator Granted</b>\n\n<b>Member:</b> {make_mention(name, tid)}\n\n{pe('check', '✅')} Delete · Invite · Pin\n{pe('ban', '🚫')} Ban · Change info · Add admins", parse_mode="html")
    except Exception as e: await event.reply(f"⚠️ {code(e)}", parse_mode="html")


# ============================================================
# 📴  AFK TOGGLE
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("afk_toggle_handler")
async def afk_toggle_handler(event):
    if event.sender_id != OWNER_ID: return
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
            f"I'll automatically respond to anyone who mentions <code>@{OWNER_USERNAME}</code>.\n\n"
            f"<b>Reply cooldown:</b> 60 seconds per user\n\n"
            f"<i>To disable, send <code>afk off</code>.</i>",
            parse_mode="html",
        )
    elif txt == "afk off":
        afk_state["enabled"] = False
        afk_state["since"] = None
        await event.reply(
            f"{pe('online', '🟢')} <b>AFK Mode Deactivated</b>\n\n"
            f"You're back online. Mention auto-replies are disabled.",
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
# 📌  PIN / UNPIN / ADMINS / WARN / KICK / BAN / PURGE
# ============================================================
@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/pin(\s|$)"))
@safe_handler("pin_handler")
async def pin_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.reply(f"{pe('lock', '🔒')} <b>Admin Only</b>", parse_mode="html"); return
    if not event.is_reply:
        await event.reply(f"{pe('pin', '📌')} <b>Reply to a message to pin it.</b>", parse_mode="html"); return
    replied = await event.get_reply_message()
    try:
        await bot(UpdatePinnedMessageRequest(event.chat_id, replied.id, silent=False))
        await event.reply(f"{pe('pin', '📌')} <b>Message Pinned</b>", parse_mode="html")
    except Exception as e: await event.reply(f"⚠️ {code(e)}", parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/unpin(\s|$)"))
@safe_handler("unpin_handler")
async def unpin_handler(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.reply(f"{pe('lock', '🔒')} <b>Admin Only</b>", parse_mode="html"); return
    if not event.is_reply:
        await event.reply(f"{pe('pin', '📌')} <b>Reply to a message to unpin it.</b>", parse_mode="html"); return
    replied = await event.get_reply_message()
    try:
        await bot(UpdatePinnedMessageRequest(event.chat_id, replied.id, unpin=True))
        await event.reply(f"{pe('pin', '📌')} <b>Message Unpinned</b>", parse_mode="html")
    except Exception as e: await event.reply(f"⚠️ {code(e)}", parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/admins(\s|$)"))
@safe_handler("admins_handler")
async def admins_handler(event):
    admins = await get_admin_list(event.chat_id)
    title = await get_group_title(event.chat_id)
    if not admins: await event.reply("📭 <b>No Admin Data</b>", parse_mode="html"); return
    lines = [f"{pe('admin', '👥')} <b>Group Administration</b>\n", f"<b>Group:</b> {code(title)}\n<b>Admins:</b> {code(len(admins))}\n"]
    for i, (uid, name) in enumerate(admins, 1): lines.append(f"{i}. {make_mention(name, uid)} — {code(uid)}")
    await event.reply("\n".join(lines), parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/warn(\s|$)"))
@safe_handler("warn_handler")
async def warn_handler(event):
    if not await is_admin(event.chat_id, event.sender_id): return
    tid = await _resolve_target(event)
    if not tid: await event.reply(f"{pe('warn', '⚠️')} <b>Reply or @user to warn.</b>", parse_mode="html"); return
    if await is_admin(event.chat_id, tid): await event.reply("🛡️ Admins cannot be warned."); return

    _, args = get_cmd_and_args(get_text(event))
    reason = (args or "no reason").strip()[:200] if event.is_reply else (args.split(maxsplit=1)[1].strip()[:200] if len(args.split(maxsplit=1)) > 1 else "no reason")

    doc = await warns_col.find_one_and_update({"chat_id": event.chat_id, "user_id": tid}, {"$inc": {"count": 1}, "$push": {"reasons": {"$each": [reason], "$slice": -20}}, "$set": {"updated_at": datetime.now(timezone.utc)}}, upsert=True, return_document=True)
    count = int(doc.get("count", 1)) if doc else 1
    target_name = await get_user_name(tid)

    action_note = ""
    if count >= DEFAULT_WARN_LIMIT:
        try:
            until = int(_tm.time() + 3600)
            await bot(EditBannedRequest(event.chat_id, tid, ChatBannedRights(until_date=until, view_messages=False, send_messages=True, send_media=True, send_stickers=True, send_gifs=True, send_games=True, send_inline=True, embed_links=True, send_polls=True)))
            action_note = f"\n\n{pe('mute', '🔇')} <b>Auto-Mute Activated</b> (1h)"
        except Exception as e: action_note = f"\n\n⚠️ <b>Auto-mute failed:</b> {code(e)}"

    await event.reply(f"{pe('warn', '⚠️')} <b>Warning Issued</b>\n\n<b>Member:</b> {make_mention(target_name, tid)}\n<b>Reason:</b> {code(reason)}\n<b>Count:</b> {code(count)} / {code(DEFAULT_WARN_LIMIT)}{action_note}", parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/unwarn(\s|$)"))
@safe_handler("unwarn_handler")
async def unwarn_handler(event):
    if not await is_admin(event.chat_id, event.sender_id): return
    tid = await _resolve_target(event)
    if not tid: return
    doc = await warns_col.find_one({"chat_id": event.chat_id, "user_id": tid})
    if not doc or not doc.get("count"): await event.reply("ℹ️ <b>No Warnings Found</b>", parse_mode="html"); return
    
    new_count = int(doc["count"]) - 1
    if new_count <= 0: await warns_col.delete_one({"chat_id": event.chat_id, "user_id": tid}); new_count = 0
    else: await warns_col.update_one({"chat_id": event.chat_id, "user_id": tid}, {"$set": {"count": new_count}, "$pop": {"reasons": 1}})
    
    target_name = await get_user_name(tid)
    await event.reply(f"{pe('check', '✅')} <b>Warning Removed</b>\n\n<b>Member:</b> {make_mention(target_name, tid)}\n<b>Updated Count:</b> {code(new_count)}", parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/warns(\s|$)"))
@safe_handler("warns_handler")
async def warns_handler(event):
    tid = await _resolve_target(event)
    if not tid: return
    doc = await warns_col.find_one({"chat_id": event.chat_id, "user_id": tid})
    target_name = await get_user_name(tid)
    if not doc or not doc.get("count"): await event.reply(f"{pe('check', '✅')} <b>Clean Record</b>\n\n{make_mention(target_name, tid)}", parse_mode="html"); return
    
    reasons = doc.get("reasons", [])[-5:]
    lines = [f"{pe('warn', '⚠️')} <b>Warnings for</b> {make_mention(target_name, tid)}\n", f"<b>Total:</b> {code(doc['count'])}\n"]
    for r in reasons: lines.append(f"• {code(r)}")
    await event.reply("\n".join(lines), parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/kick(\s|$)"))
@safe_handler("kick_handler")
async def kick_handler(event):
    if not await is_admin(event.chat_id, event.sender_id): return
    tid = await _resolve_target(event)
    if not tid: return
    if await is_admin(event.chat_id, tid) or tid == OWNER_ID: await event.reply("🛡️ Protected."); return
    try:
        until = int(_tm.time() + KICK_BAN_SECONDS)
        await bot(EditBannedRequest(event.chat_id, tid, ChatBannedRights(until_date=until, view_messages=True)))
        name = await get_user_name(tid)
        await event.reply(f"{pe('kick', '👢')} <b>Member Kicked</b>\n\n<b>Target:</b> {make_mention(name, tid)}\n<b>Duration:</b> {code(KICK_BAN_SECONDS)}s", parse_mode="html")
    except Exception as e: await event.reply(f"⚠️ {code(e)}", parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/ban(\s|$)"))
@safe_handler("ban_handler")
async def ban_handler(event):
    if not await is_admin(event.chat_id, event.sender_id): return
    tid = await _resolve_target(event)
    if not tid: return
    if await is_admin(event.chat_id, tid) or tid == OWNER_ID: await event.reply("🛡️ Protected."); return
    try:
        await bot(EditBannedRequest(event.chat_id, tid, ChatBannedRights(until_date=0, view_messages=True, send_messages=True, send_media=True, send_stickers=True, send_gifs=True, send_games=True, send_inline=True, embed_links=True, send_polls=True)))
        name = await get_user_name(tid)
        await event.reply(f"{pe('ban', '🚫')} <b>Member Banned</b>\n\n<b>Target:</b> {make_mention(name, tid)}", parse_mode="html")
    except Exception as e: await event.reply(f"⚠️ {code(e)}", parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/unban(\s|$)"))
@safe_handler("unban_handler")
async def unban_handler(event):
    if not await is_admin(event.chat_id, event.sender_id): return
    tid = await _resolve_target(event)
    if not tid: return
    try:
        await bot(EditBannedRequest(event.chat_id, tid, ChatBannedRights(until_date=0)))
        name = await get_user_name(tid)
        await event.reply(f"{pe('check', '✅')} <b>Member Unbanned</b>\n\n<b>Target:</b> {make_mention(name, tid)}", parse_mode="html")
    except Exception as e: await event.reply(f"⚠️ {code(e)}", parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/purge(\s|$)"))
@safe_handler("purge_handler")
async def purge_handler(event):
    if not await is_admin(event.chat_id, event.sender_id): return
    if not event.is_reply: await event.reply(f"{pe('delete', '🗑️')} <b>Reply to the first message in the range.</b>", parse_mode="html"); return
    
    replied = await event.get_reply_message()
    ids = list(range(replied.id, event.id + 1))
    deleted = 0
    for i in range(0, len(ids), 100):
        try: await bot.delete_messages(event.chat_id, ids[i:i + 100]); deleted += len(ids[i:i + 100])
        except Exception: pass
    try: await event.reply(f"{pe('delete', '🗑️')} <b>Purge Complete</b>\n\n<b>Messages Deleted:</b> {code(deleted)}", parse_mode="html")
    except Exception: pass


# ============================================================
# 📖  RULES / WELCOME / STATS / ID / HELP / START
# ============================================================
async def get_settings(chat_id: int) -> dict:
    doc = await settings_col.find_one({"chat_id": chat_id})
    return doc if doc else {"chat_id": chat_id, "welcome": WELCOME_DEFAULT, "rules": ""}

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/setrules(\s|$)"))
@safe_handler("setrules_handler")
async def setrules_handler(event):
    if not await is_admin(event.chat_id, event.sender_id): return
    _, args = get_cmd_and_args(get_text(event))
    if not args: await event.reply("📝 <b>Usage:</b> <code>/setrules [text]</code>", parse_mode="html"); return
    await settings_col.update_one({"chat_id": event.chat_id}, {"$set": {"rules": args, "updated_at": datetime.now(timezone.utc)}}, upsert=True)
    await event.reply(f"{pe('check', '✅')} <b>Rules Saved</b>", parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/rules(\s|$)"))
@safe_handler("rules_handler")
async def rules_handler(event):
    s = await get_settings(event.chat_id)
    if not s.get("rules"): await event.reply("📭 <b>No Rules Set Yet</b>", parse_mode="html"); return
    await event.reply(f"{pe('book', '📖')} <b>Group Rules</b>\n\n{s['rules']}", parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/clearrules(\s|$)"))
@safe_handler("clearrules_handler")
async def clearrules_handler(event):
    if not await is_admin(event.chat_id, event.sender_id): return
    await settings_col.update_one({"chat_id": event.chat_id}, {"$set": {"rules": ""}}, upsert=True)
    await event.reply(f"{pe('delete', '🗑️')} <b>Rules Cleared</b>", parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/welcome(\s|$)"))
@safe_handler("welcome_toggle_handler")
async def welcome_toggle_handler(event):
    if not await is_admin(event.chat_id, event.sender_id): return
    _, args = get_cmd_and_args(get_text(event))
    s = await get_settings(event.chat_id)
    current = bool(s.get("welcome", WELCOME_DEFAULT))
    
    if args.lower() in ("on", "enable", "yes"): new_val = True
    elif args.lower() in ("off", "disable", "no"): new_val = False
    elif not args: new_val = not current
    else: await event.reply("⚠️ <b>Usage:</b> <code>/welcome on|off</code>", parse_mode="html"); return

    await settings_col.update_one({"chat_id": event.chat_id}, {"$set": {"welcome": new_val}}, upsert=True)
    if new_val: await event.reply(f"{pe('online', '🟢')} <b>Welcome Messages Enabled</b>", parse_mode="html")
    else: await event.reply(f"{pe('offline', '🔴')} <b>Welcome Messages Disabled</b>", parse_mode="html")

@bot.on(events.ChatAction(chats=[OFFICIAL_GROUP_ID]))
@safe_handler("welcome_new_member_handler")
async def welcome_new_member_handler(event):
    if not (event.user_joined or event.user_added): return
    s = await get_settings(event.chat_id)
    if not s.get("welcome", False): return
    user_id = getattr(event, "user_id", None)
    if not user_id: return
    name = await get_user_name(user_id)
    count_str = "—"
    try: count_str = str((await bot(GetFullChannelRequest(event.chat_id))).full_chat.participants_count)
    except Exception: pass

    await bot.send_message(
        event.chat_id,
        f"🎉 <b>A warm welcome to our newest member!</b>\n\n"
        f"{make_mention(name, user_id)}, we're thrilled to have you join us here.\n\n"
        f"<b>Quick Links:</b>\n"
        f"• {pe('book', '📖')} Rules: /rules\n"
        f"• {pe('info', 'ℹ️')} Help: /help\n"
        f"• {pe('admin', '👥')} Admins: /admins\n\n"
        f"<b>Members:</b> {code(count_str)}\n"
        f"<b>Your ID:</b> {code(user_id)}",
        parse_mode="html",
    )

@bot.on(events.ChatAction())
@safe_handler("bot_added_to_group_handler")
async def bot_added_to_group_handler(event):
    my_id = await _ensure_me()
    added = (event.user_added and event.user_id == my_id) or (event.user_joined and event.user_id == my_id)
    if not added: return
    try: title = await get_group_title(event.chat_id)
    except Exception: title = str(event.chat_id)

    await bot.send_message(
        event.chat_id,
        f"🏛️ <b>BOD Manager — Ready to Serve</b>\n\n"
        f"Greetings, <b>{title}</b>! I'm <b>BOD Manager</b>, your dedicated group guardian.\n\n"
        f"🛡️ <b>Automated Moderation</b>\n"
        f"• Auto-delete member photos/videos & links\n"
        f"• Badword filtering\n"
        f"• Mute, warn, kick, ban\n\n"
        f"{pe('pin', '📌')} <b>Utility Features</b>\n"
        f"• Pin/unpin · report system · stats\n\n"
        f"⚙️ <b>Setup:</b>\n"
        f"1. Grant me <b>admin</b> status\n"
        f"2. Enable: <b>Ban Users</b>, <b>Delete Messages</b>, <b>Pin Messages</b>\n"
        f"3. Run <code>/help</code> for all commands",
        parse_mode="html",
    )

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/stats(\s|$)"))
@safe_handler("stats_handler")
async def stats_handler(event):
    if not await is_admin(event.chat_id, event.sender_id): return
    title = await get_group_title(event.chat_id)
    admins = await get_admin_list(event.chat_id)
    count_str = "—"
    try: count_str = str((await bot(GetFullChannelRequest(event.chat_id))).full_chat.participants_count)
    except Exception: pass
    afk_status = f"{pe('afk', '📴')} Active" if afk_state["enabled"] else f"{pe('online', '🟢')} Inactive"
    
    await event.reply(
        f"{pe('stats', '📊')} <b>Group Statistics</b>\n\n"
        f"<b>Group:</b> {code(title)}\n"
        f"<b>ID:</b> {code(event.chat_id)}\n"
        f"<b>Members:</b> {code(count_str)}\n"
        f"<b>Admins:</b> {code(len(admins))}\n"
        f"<b>AFK Mode:</b> {afk_status}",
        parse_mode="html",
    )

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/id(\s|$)"))
@safe_handler("id_handler")
async def id_handler(event):
    if event.is_reply:
        r = await event.get_reply_message()
        if r and r.sender_id:
            name = await get_user_name(r.sender_id)
            await event.reply(f"{pe('id', '🆔')} <b>User ID</b>\n\n<b>Name:</b> {make_mention(name, r.sender_id)}\n<b>ID:</b> {code(r.sender_id)}\n<b>Msg ID:</b> {code(r.id)}", parse_mode="html")
            return
    sender = await event.get_sender()
    name = f"{getattr(sender, 'first_name', '') or ''} {getattr(sender, 'last_name', '') or ''}".strip() or "User"
    await event.reply(f"{pe('id', '🆔')} <b>Chat Identification</b>\n\n<b>You:</b> {make_mention(name, event.sender_id)}\n<b>Your ID:</b> {code(event.sender_id)}\n<b>Chat ID:</b> {code(event.chat_id)}", parse_mode="html")

@bot.on(events.NewMessage(chats=[OFFICIAL_GROUP_ID], pattern=r"^/mutecount(\s|$)"))
@safe_handler("mutecount_handler")
async def mutecount_handler(event):
    if not await is_admin(event.chat_id, event.sender_id): return
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

@bot.on(events.NewMessage(pattern=r"^/start(\s|$)"))
@safe_handler("start_handler")
async def start_handler(event):
    afk_status = f"{pe('afk', '📴')} Active" if afk_state["enabled"] else f"{pe('online', '🟢')} Inactive"
    await event.reply(
        f"🏛️ <b>BOD Manager</b>\n\n"
        f"I'm your dedicated group guardian.\n\n"
        f"<b>System Status:</b> {code('Operational')}\n"
        f"<b>AFK Mode:</b> {afk_status}\n"
        f"<b>Mute Quota:</b> {code(MUTE_DAILY_LIMIT)} / admin / day\n\n"
        f"<b>Quick Access:</b>\n"
        f"• {pe('book', '📖')} <code>/help</code> — Commands\n"
        f"• {pe('book', '📖')} <code>/rules</code> — Group rules\n"
        f"• {pe('admin', '👥')} <code>/admins</code> — Admins\n"
        f"• {pe('alert', '🚨')} <code>/report</code> — Report",
        parse_mode="html",
    )

@bot.on(events.NewMessage(pattern=r"^/help(\s|$)"))
@safe_handler("help_handler")
async def help_handler(event):
    text = (
        f"{pe('book', '📖')} <b>BOD Manager — Command Reference</b>\n\n"
        f"<b>{pe('crown', '👑')} Owner Commands</b>\n"
        f"• <code>စာပိတ်</code> — {pe('lock', '🔒')} Lock the group\n"
        f"• <code>စာဖွင့်</code> — {pe('unlock', '🔓')} Unlock the group\n"
        f"• Reply + <code>ဘန်း</code> — {pe('ban', '🚫')} Permanently ban\n"
        f"• Reply + <code>ကစ်</code> — {pe('kick', '👢')} Kick for 60s\n"
        f"• Reply + <code>adm</code> — {pe('shield', '🛡️')} Grant limited admin\n"
        f"• Reply + <code>?</code> — {pe('info', 'ℹ️')} User info\n"
        f"• <code>afk on/off</code> — {pe('afk', '📴')} AFK mode\n"
        f"• Reply + <code>/del</code> or <code>ဖျက်မယ်</code> — {pe('delete', '🗑️')} Track bot\n\n"
        f"<b>{pe('shield', '🛡️')} Moderation (Admins)</b>\n"
        f"• Reply + <code>မြုလိုက်</code> / <code>/mute</code> — {pe('mute', '🔇')} Mute (5/day)\n"
        f"• Reply + <code>ပြန်ဖွင့်</code> / <code>/unmute</code> — {pe('unmute', '🔊')} Unmute\n"
        f"• <code>/warn</code> · <code>/unwarn</code> · <code>/warns</code> — {pe('warn', '⚠️')} Warnings\n"
        f"• <code>/kick</code> · <code>/ban</code> · <code>/unban</code> — {pe('ban', '🚫')} Manage users\n"
        f"• Reply + <code>/pin</code> · <code>/unpin</code> — {pe('pin', '📌')} Manage pins\n"
        f"• Reply + <code>/purge</code> — {pe('delete', '🗑️')} Bulk delete\n"
        f"• <code>/setrules</code> · <code>/clearrules</code> — {pe('book', '📖')} Manage rules\n"
        f"• <code>/welcome on/off</code> · <code>/mutecount</code> — {pe('stats', '📊')} Settings\n\n"
        f"<b>{pe('admin', '👥')} Member Commands</b>\n"
        f"• <code>/start</code> · <code>/help</code> · <code>/rules</code> · <code>/id</code> — {pe('info', 'ℹ️')} Basic\n"
        f"• Reply + <code>/report</code> — {pe('alert', '🚨')} Report to admins\n\n"
        f"<b>{pe('cross', '❌')} Automated Protection</b>\n"
        f"• Non-admin photos/videos auto-deleted\n"
        f"• Non-admin links auto-deleted\n"
        f"• Badword filter with 5-min window\n"
        f"• Stickers and GIFs always allowed\n"
        f"• Muted users fully blocked"
    )
    await event.reply(text, parse_mode="html")


# ============================================================
# 🌍  RENDER HEALTH CHECK & STARTUP
# ============================================================
async def _health(reader, writer):
    await reader.read(100)
    writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nOK")
    await writer.drain(); writer.close()

async def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        srv = await asyncio.start_server(_health, "0.0.0.0", port)
        async with srv: await srv.serve_forever()
    except Exception: pass

async def startup():
    print("⏳ BOD Manager starting...")
    asyncio.create_task(start_health_server())

    try:
        await bot.start(bot_token=BOT_TOKEN)
        me = await _ensure_me()
        print(f"🤖 Bot connected: @{_my_username} (id={me})")
    except Exception as e:
        print(f"❌ Bot start failed: {e}"); return

    await load_tracked_bots()
    asyncio.create_task(report_reminder_loop())

    try:
        await bot.send_message(
            OWNER_ID,
            f"{pe('online', '🟢')} <b>BOD Manager Online</b>\n\n"
            f"All systems operational.\n\n"
            f"<b>Configuration:</b>\n"
            f"• Group: {code(OFFICIAL_GROUP_ID)}\n"
            f"• Badword filter: {pe('check', '✅')}\n"
            f"• AFK mode: {pe('offline', '🔴')} Inactive\n"
            f"• Tracked bots: {code(len(tracked_bots_cache))}",
            parse_mode="html",
        )
    except Exception: pass
    print("🚀 Ready.")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    if _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    try: _loop.run_until_complete(startup())
    except KeyboardInterrupt: pass
    finally:
        try: _loop.close()
        except Exception: pass
