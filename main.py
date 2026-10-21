# ============================================================
# 🏛️  BOD MANAGER v2  —  main.py (standalone)
# ============================================================
# ✅ Multi-group      : works in every group it is added to (per-group settings in MongoDB)
# ✅ Premium emoji    : every message AND every inline button uses the premium-emoji registry
# ✅ Inline buttons   : /settings panel, help menu, action buttons, report buttons
# ✅ Welcome (photo)  : member / bot joins -> profile photo + premium-emoji caption + "Start bot" button
# ✅ DM intro         : /start in DM explains everything in Burmese with inline buttons
# ✅ AFK              : works for EVERY group owner (not only the bot owner), saved in MongoDB
# ✅ Runtime emoji    : /emojiid, /setemoji, /emojis  (no code edits needed to add emoji IDs)
#
# Requires : Python 3.10+  |  telethon  |  motor
# Env vars : API_ID, API_HASH, BOT_TOKEN, MONGO_URI            (required)
#            OWNER_ID, OWNER_USERNAME, OFFICIAL_GROUP_ID, PORT (optional)
#
# Premium emoji / button icons only render when the bot OWNER account has
# Telegram Premium. Without it, the fallback emoji is shown instead.
# ============================================================

import os
import re
import json
import time as _tm
import asyncio
import traceback
import unicodedata
import urllib.request
import urllib.error
from collections import defaultdict, deque
from datetime import datetime, timezone
from html import escape as esc, unescape as _unesc

from telethon import TelegramClient, events
from telethon.tl.functions.channels import (
    EditBannedRequest, GetParticipantsRequest, EditAdminRequest,
)
from telethon.tl.functions.messages import UpdatePinnedMessageRequest, EditChatDefaultBannedRightsRequest
from telethon.tl.types import (
    ChatBannedRights, ChannelParticipantsAdmins, ChatAdminRights,
    MessageEntityUrl, MessageEntityTextUrl, MessageEntityMention,
    ChannelParticipantCreator, ChatParticipantCreator, MessageEntityCustomEmoji,
)
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument


# ============================================================
# ⚙️  CONFIG  (secrets come from environment variables only)
# ============================================================
def _req(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        raise SystemExit(f"❌ Missing required environment variable: {name}")
    return v

API_ID    = int(_req("API_ID"))
API_HASH  = _req("API_HASH")
BOT_TOKEN = _req("BOT_TOKEN")
MONGO_URI = _req("MONGO_URI")

OWNER_ID          = int(os.environ.get("OWNER_ID", "6015356597"))
OWNER_USERNAME    = os.environ.get("OWNER_USERNAME", "Hello_Im_DexterMorgan")
OFFICIAL_GROUP_ID = int(os.environ.get("OFFICIAL_GROUP_ID", "-1004478099253"))

MUTE_DAILY_LIMIT        = 5
KICK_BAN_SECONDS        = 60
ADMIN_CACHE_TTL         = 120
WELCOME_DEFAULT         = True       # welcome is ON in every group by default (/welcome off to disable)
DEFAULT_WARN_LIMIT      = 3
REPORT_COOLDOWN_SECONDS = 3 * 60 * 60
REPORT_REMINDER_SECONDS = 3 * 60 * 60
AFK_REPLY_COOLDOWN      = 60
BADWORD_WINDOW_SECONDS  = 5 * 60
BADWORD_MUTE_DURATION   = 60 * 60
FLOOD_MESSAGES          = 6          # messages ...
FLOOD_WINDOW            = 8          # ... within this many seconds => flood
FLOOD_MUTE_SECONDS      = 10 * 60
WELCOME_CAPTION_MAX     = 1000       # photo captions are limited to 1024 characters
WELCOME_MAX_PER_EVENT   = 10         # welcome at most this many people per join event
OWNER_DISPLAY_NAME      = "Morgan"   # name shown in AFK replies for the bot owner
NOTICE_TTL              = 12         # short notices delete themselves
PURGE_MAX               = 1000
ADMIN_PING_LIMIT        = 25

# False -> a missing premium ID falls back to the normal emoji (recommended).
# True  -> missing premium IDs render nothing (the old "strict" rule).
STRICT_EMOJI = False


# ============================================================
# 🚫  BADWORDS (defaults — each group can add its own with /addword)
# ============================================================
BADWORDS = [
    'ဖာသယ်မ',
    'ဖာသည်မ',
    'ဖာသယ်မသား',
    'ဖာသည်မသား',
    'လီး',
    'မှန်းထု',
    'မှန်း',
    'လိုး',
    'မအေလိုး',
    'ငါလိုးမသား',
]

BADWORD_SAFE_CONTEXTS = [
    'ရည်မှန်းချက်',
    'ရည်မှန်း',
    'ခန့်မှန်းချက်',
    'ခန့်မှန်း',
    'ခန့်မှန်းတွက်',
    'ခန့်မှန်းပြ',
    'မှန်းဆချက်',
    'မှန်းဆ',
    'မှန်းဆတွက်',
    'လီးလာ',
    'တစ်လီး',
    'နှစ်လီး',
    'သုံးလီး',
    'စာရင်းလီး',
    'လီးစား',
]
_BADWORD_SAFE_SORTED = sorted(BADWORD_SAFE_CONTEXTS, key=len, reverse=True)

# Burmese text triggers (copied verbatim from the original file)
MUTE_TRIGGERS   = [
    'မြုလိုက်',
    'မြုလိုက်ပါ',
    'mute',
    'mutethatgay',
]
UNMUTE_TRIGGERS = [
    'ပြန်ဖွင့်',
    'ပြန်ဖွင့်ပါ',
    'ပြန်ဖွင့်',
    'ပြန်ဖွင့်ပါ',
    'unmute',
]
TRG_LOCK   = ('စာပိတ်',)
TRG_UNLOCK = ('စာဖွင့်',)
TRG_BAN    = ('ဘန်း', 'ဘန်း ',)
TRG_KICK   = ('ကစ်', 'ကစ် ',)
TRG_TRACK  = 'ဖျက်မယ်'

AFK_EN_MSG = ("{name} is currently AFK.\n\nThey might be busy, resting, studying, watching a movie, or gaming. "
             "Please leave your message, and they'll reply as soon as they're back online.")
AFK_MM_MSG = '{name} လောလောဆယ် AFK ဖြစ်နေပါတယ်။\n\nအလုပ်များနေတာ၊ အနားယူနေတာ၊ စာလေ့လာနေတာ၊ Movie ကြည့်နေတာ ဒါမှမဟုတ် Game ဆော့နေတာ ဖြစ်နိုင်ပါတယ်။ ပြောစရာရှိတာတွေ တစ်ခါတည်း ရေးထားပေးပါ။ Online ပြန်တက်လာရင် Reply ပြန်ပေးပါလိမ့်မယ်။'


# ============================================================
# 🔧  PYTHON 3.14+ EVENT LOOP
# ============================================================
try:
    _loop = asyncio.get_running_loop()
except RuntimeError:
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)


# ============================================================
# ✨  PREMIUM EMOJI REGISTRY
# ============================================================
# Fallback (normal) emoji for every key. Keys are what the code uses: pe("crown").
EMOJI_FALLBACK = {
    # --- IDs already known ---
    "mute": "🔇", "unmute": "🔊", "warn": "⚠️", "ban": "🚫", "kick": "👢", "lock": "🔒",
    "unlock": "🔓", "check": "✅", "cross": "❌", "clock": "⏳", "alert": "🚨", "pin": "📌",
    "delete": "🗑️", "fire": "🔥", "eyes": "👀", "target": "🎯", "stats": "📊", "info": "ℹ️",
    "id": "🆔", "admin": "👥", "book": "📖", "link": "🔗", "afk": "📴", "online": "🟢",
    "offline": "🔴", "sleep": "😴",
    # --- slots that had no ID in the old file ---
    "bot": "🤖", "shield": "🛡️", "crown": "👑", "star": "⭐", "sparkle": "✨", "party": "🎉",
    "heart": "❤️", "wave": "👋", "trophy": "🏆", "key": "🔑", "gear": "⚙️", "rocket": "🚀",
    "ghost": "👻",
    # --- new slots (fill them with /setemoji) ---
    "home": "🏛️", "user": "👤", "back": "⬅️", "close": "✖️", "plus": "➕", "minus": "➖",
    "bolt": "⚡", "bell": "🔔", "pencil": "📝", "broom": "🧹", "mailbox": "📭", "globe": "🌐",
    "chat": "💬", "refresh": "🔄", "list": "📋", "tools": "🧰", "human": "🧑",
}

# Keys that reuse another key's premium emoji until you give them their own.
EMOJI_ALIAS = {
    "on": "check", "off": "cross", "ok": "check", "rules": "book", "report": "alert",
    "users": "admin", "trash": "delete", "time": "clock", "danger": "alert", "hammer": "ban",
}

# Premium custom-emoji IDs (copied from the original file).
PREMIUM_EMOJI: dict = {k: None for k in EMOJI_FALLBACK}
PREMIUM_EMOJI.update({
    "mute": 6039505337151655702,
    "unmute": 6039454987250044861,
    "warn": 5461098492216752942,
    "ban": 5368562433981947135,
    "kick": 6177127866115822461,
    "lock": 6037249452824072506,
    "unlock": 6037496202990194718,
    "check": 5305670334513427489,
    "cross": 5447544503143504937,
    "clock": 5215327832040811010,
    "alert": 5212969852045634932,
    "pin": 5422357698228290320,
    "delete": 6039522349517115015,
    "fire": 5402406965252989103,
    "eyes": 5350732341109081597,
    "target": 6032949275732742941,
    "stats": 5231200819986047254,
    "info": 5456309534962234647,
    "id": 5465465194056525619,
    "admin": 5373110220232870002,
    "book": 6181489083282363892,
    "link": 6240200624793720535,
    "afk": 5449875850046481967,
    "online": 5217449524410199951,
    "offline": 5444965061749644170,
    "sleep": 5462990652943904884,
})
BUILTIN_EMOJI = dict(PREMIUM_EMOJI)       # used by /resetemoji


def _resolve(key: str):
    k = EMOJI_ALIAS.get(key, key)
    return k, PREMIUM_EMOJI.get(k), EMOJI_FALLBACK.get(k, "")

def pe(key: str, fallback: str = "") -> str:
    """Premium emoji as an HTML <tg-emoji> tag (Bot API HTML)."""
    k, pid, fb = _resolve(key)
    fb = fb or fallback or "▫️"
    if pid:
        return f'<tg-emoji emoji-id="{pid}">{fb}</tg-emoji>'
    return "" if STRICT_EMOJI else fb

def head(key: str, title: str) -> str:
    """Standard message heading: premium emoji + bold title."""
    return f"{pe(key)} <b>{title}</b>".strip()

_TGEMOJI_RE = re.compile(r'<tg-emoji emoji-id="\d+">(.*?)</tg-emoji>', re.S)
def _plain_emoji(text: str) -> str:
    return _TGEMOJI_RE.sub(r"\1", text)

def _to_plain(text: str) -> str:
    return _unesc(re.sub(r"</?[a-zA-Z][^>]*>", "", text))


# ============================================================
# 🌐  BOT API CLIENT  (native <tg-emoji>, button icons & styles)
# ============================================================
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
_bg_tasks: set = set()

def spawn(coro):
    t = asyncio.get_running_loop().create_task(coro)
    _bg_tasks.add(t)
    t.add_done_callback(_bg_tasks.discard)
    return t

def _encode_multipart(fields: dict, file: tuple):
    """Build a multipart/form-data body (needed to upload a photo through the Bot API)."""
    boundary = "----bodmanager" + os.urandom(12).hex()
    field, filename, content, mime = file
    chunks = []
    for k, v in fields.items():
        if isinstance(v, bool):
            v = "true" if v else "false"
        elif isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8"))
    chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
                  f"Content-Type: {mime}\r\n\r\n".encode("utf-8") + content + b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"

def _api_sync(method: str, payload: dict, file: tuple | None = None) -> dict:
    if file:
        data, ctype = _encode_multipart(payload, file)
    else:
        data, ctype = json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json"
    req = urllib.request.Request(API_URL + method, data=data, headers={"Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=40 if file else 25) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"ok": False, "description": f"HTTP {e.code}"}
    except Exception as e:
        return {"ok": False, "description": type(e).__name__}

async def api(method: str, _file: tuple | None = None, **payload) -> dict:
    """Call a Bot API method. _file = (field, filename, bytes, mime) switches to a multipart upload."""
    payload = {k: v for k, v in payload.items() if v is not None}
    res: dict = {}
    for attempt in range(2):
        res = await asyncio.to_thread(_api_sync, method, payload, _file)
        if res.get("ok"):
            return res
        wait = (res.get("parameters") or {}).get("retry_after")
        if wait and attempt == 0:
            await asyncio.sleep(min(int(wait), 30))
            continue
        break
    desc = res.get("description", "")
    if "not modified" not in desc.lower():
        print(f"⚠️ Bot API {method}: {desc}")
    return res


# ---------- inline keyboard helpers ----------
def btn(text: str, data: str | None = None, *, url: str | None = None,
        icon: str | None = None, style: str | None = None) -> dict:
    """One inline button. icon = premium-emoji key, style = primary|success|danger."""
    b: dict = {"text": text}
    if icon:
        _, pid, fb = _resolve(icon)
        if pid:
            b["icon_custom_emoji_id"] = str(pid)
            b["_fb"] = fb
        elif not STRICT_EMOJI and fb:
            b["text"] = f"{fb} {text}"
    if style:
        b["style"] = style
    if url:
        b["url"] = url
    else:
        assert data and len(data.encode()) <= 64, f"bad callback data: {data!r}"
        b["callback_data"] = data
    return b

def _finalize_kb(kb, strip: bool = False):
    out = []
    for row in kb:
        r = []
        for b in row:
            b = dict(b)
            fb = b.pop("_fb", None)
            if strip:
                if b.pop("icon_custom_emoji_id", None) and fb and not STRICT_EMOJI:
                    b["text"] = f"{fb} {b['text']}"
                b.pop("style", None)
            r.append(b)
        out.append(r)
    return out

_FATAL = ("chat not found", "forbidden", "kicked", "blocked", "not enough rights", "no rights",
          "administrator rights", "deactivated", "need to be", "have no rights", "not found")

async def _attempt(method: str, base: dict, text: str, kb, text_key: str = "text", file: tuple | None = None):
    """Try the rich version first, then degrade (no icons -> no custom emoji -> plain text).
    text_key = "text" for sendMessage/editMessageText, "caption" for sendPhoto."""
    first_kb = _finalize_kb(kb) if kb else kb          # kb == [] means "remove buttons"
    variants = [(text, first_kb, "HTML")]
    if kb:
        stripped = _finalize_kb(kb, strip=True)
        if stripped != first_kb:
            variants.append((text, stripped, "HTML"))
    t2 = _plain_emoji(text)
    if t2 != text:
        variants.append((t2, variants[-1][1], "HTML"))
    variants.append((_to_plain(t2), variants[-1][1], None))
    res: dict = {}
    for t, k, pm in variants:
        payload = {**base, text_key: t, "parse_mode": pm}
        if k is not None:
            payload["reply_markup"] = {"inline_keyboard": k}
        res = await api(method, _file=file, **payload)
        if res.get("ok"):
            return res
        d = (res.get("description") or "").lower()
        if "not modified" in d or any(f in d for f in _FATAL):
            break
    return res

async def tg_send(chat_id, text: str, kb=None, reply_to: int | None = None,
                  ttl: int | None = None, silent: bool = False):
    base = {"chat_id": chat_id, "link_preview_options": {"is_disabled": True},
            "disable_notification": True if silent else None}
    if reply_to:
        base["reply_parameters"] = {"message_id": reply_to, "allow_sending_without_reply": True}
    res = await _attempt("sendMessage", base, text[:4096], kb)
    msg = res.get("result") if res.get("ok") else None
    if msg and ttl:
        spawn(_delete_later(chat_id, msg["message_id"], ttl))
    return msg

async def tg_send_photo(chat_id, photo: bytes, caption: str, kb=None, reply_to: int | None = None,
                        ttl: int | None = None):
    """Send a photo (raw bytes) with an HTML caption (premium emoji kept) and optional inline buttons.
    Returns the message dict, or None if it failed (callers then fall back to plain text)."""
    base = {"chat_id": chat_id}
    if reply_to:
        base["reply_parameters"] = {"message_id": reply_to, "allow_sending_without_reply": True}
    res = await _attempt("sendPhoto", base, caption, kb, text_key="caption",
                         file=("photo", "profile.jpg", photo, "image/jpeg"))
    msg = res.get("result") if res.get("ok") else None
    if msg and ttl:
        spawn(_delete_later(chat_id, msg["message_id"], ttl))
    return msg

async def tg_edit(chat_id, message_id: int, text: str, kb=None):
    base = {"chat_id": chat_id, "message_id": message_id, "link_preview_options": {"is_disabled": True}}
    return await _attempt("editMessageText", base, text[:4096], kb if kb is not None else [])

async def tg_delete(chat_id, message_id: int):
    try:
        await api("deleteMessage", chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

async def _delete_later(chat_id, message_id: int, delay: int):
    await asyncio.sleep(delay)
    await tg_delete(chat_id, message_id)

async def reply(event, text: str, kb=None, ttl: int | None = None):
    return await tg_send(event.chat_id, text, kb, reply_to=event.id, ttl=ttl)

async def notice(event, text: str, kb=None):
    """Short message that cleans itself up."""
    return await reply(event, text, kb, ttl=NOTICE_TTL)


# ============================================================
# 🧾  TEXT HELPERS  (+ Telegram entities -> HTML, keeps premium emoji)
# ============================================================
def make_mention(name: str, user_id: int) -> str:
    return f'<a href="tg://user?id={user_id}">{esc(name or "User")}</a>'

def code(text) -> str:
    return f"<code>{esc(str(text))}</code>"

def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def clean_invisible(text: str) -> str:
    if not text:
        return ""
    try:
        return "".join(c for c in text if unicodedata.category(c) != "Cf")
    except Exception:
        return text

def norm_text(text: str) -> str:
    """Normalise for trigger matching: strip invisibles, unify Burmese asat/aukmyit order, collapse spaces."""
    t = clean_invisible(text or "").replace("\u103a\u1037", "\u1037\u103a")
    return " ".join(t.split()).lower()

def fmt_secs(seconds: int) -> str:
    seconds = int(seconds)
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    parts = []
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s: parts.append(f"{s}s")
    return " ".join(parts) if parts else "0s"

_DUR_RE = re.compile(r"^(\d+)\s*([smhdw])$", re.I)
_DUR_MULT = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
def parse_duration(tok: str) -> int | None:
    m = _DUR_RE.match((tok or "").strip())
    if not m:
        return None
    secs = int(m.group(1)) * _DUR_MULT[m.group(2).lower()]
    return max(60, min(secs, 366 * 86400))

_ENT_TAGS = {
    "MessageEntityBold": ("<b>", "</b>"), "MessageEntityItalic": ("<i>", "</i>"),
    "MessageEntityUnderline": ("<u>", "</u>"), "MessageEntityStrike": ("<s>", "</s>"),
    "MessageEntityCode": ("<code>", "</code>"), "MessageEntityPre": ("<pre>", "</pre>"),
    "MessageEntitySpoiler": ("<tg-spoiler>", "</tg-spoiler>"),
    "MessageEntityBlockquote": ("<blockquote>", "</blockquote>"),
}

def _entity_tags(ent):
    name = type(ent).__name__
    if name == "MessageEntityBlockquote" and getattr(ent, "collapsed", False):
        return ("<blockquote expandable>", "</blockquote>")
    if name in _ENT_TAGS:
        return _ENT_TAGS[name]
    if name == "MessageEntityTextUrl":
        return (f'<a href="{esc(ent.url, quote=True)}">', "</a>")
    if name == "MessageEntityMentionName":
        return (f'<a href="tg://user?id={ent.user_id}">', "</a>")
    if name == "MessageEntityCustomEmoji":
        return (f'<tg-emoji emoji-id="{ent.document_id}">', "</tg-emoji>")
    return None

def entities_to_html(text: str, items) -> str:
    """items = [(offset_utf16, length_utf16, entity)] -> Bot API HTML (formatting + premium emoji kept)."""
    if not text:
        return ""
    u = text.encode("utf-16-le")
    total = len(u) // 2
    def sl(a, b):
        return esc(u[a * 2:b * 2].decode("utf-16-le", "ignore"))
    spans = []
    for off, ln, ent in items:
        tags = _entity_tags(ent)
        if tags and ln > 0 and off >= 0 and off + ln <= total:
            spans.append((off, off + ln, tags))
    spans.sort(key=lambda s: (s[0], -s[1]))
    out, stack, pos = [], [], 0
    def close_to(limit):
        nonlocal pos
        while stack and stack[-1][0] <= limit:
            end, cl = stack.pop()
            if end > pos:
                out.append(sl(pos, end))
                pos = end
            out.append(cl)
    for s, e, (op, cl) in spans:
        close_to(s)
        if s > pos:
            out.append(sl(pos, s))
            pos = s
        out.append(op)
        stack.append((e, cl))
    close_to(total)
    if pos < total:
        out.append(sl(pos, total))
    return "".join(out)

def message_html(message) -> str:
    items = [(e.offset, e.length, e) for e in (getattr(message, "entities", None) or [])]
    return entities_to_html(message.message or "", items).strip()

def args_html(message) -> str:
    """HTML of everything after the command word (formatting + premium emoji preserved)."""
    raw = message.message or ""
    m = re.match(r"\s*\S+\s*", raw)
    start_py = m.end() if m else len(raw)
    start16 = len(raw[:start_py].encode("utf-16-le")) // 2
    items = [(e.offset - start16, e.length, e) for e in (message.entities or []) if e.offset >= start16]
    return entities_to_html(raw[start_py:], items).strip()

async def rich_arg(event) -> str:
    """Formatted text from the command arguments, or from the replied message."""
    txt = args_html(event.message)
    if txt:
        return txt
    if event.is_reply:
        r = await event.get_reply_message()
        if r and (r.message or "").strip():
            return message_html(r)
    return ""

def render_template(tmpl: str, **kw) -> str:
    for k, v in kw.items():
        tmpl = tmpl.replace("{" + k + "}", str(v))
    return tmpl


# ============================================================
# 🗄️  DATABASE & CLIENT
# ============================================================
_mongo = AsyncIOMotorClient(MONGO_URI, io_loop=_loop)
db = _mongo["group_manager"]

tracked_bots_col    = db["tracked_bots"]
mute_daily_col      = db["mute_daily"]
warns_col           = db["warns"]
settings_col        = db["group_settings"]
report_cooldown_col = db["report_cooldown"]
emoji_col           = db["emoji_map"]
captcha_col         = db["captcha_pending"]   # legacy: only read once to free members left over from the old captcha
afk_col             = db["afk_users"]

bot = TelegramClient("manager_bot_session", API_ID, API_HASH, loop=_loop)
_my_id = None
_my_username = None

async def _ensure_me():
    global _my_id, _my_username
    if _my_id is None:
        me = await bot.get_me()
        _my_id, _my_username = me.id, me.username
    return _my_id


# ============================================================
# ⚙️  PER-GROUP SETTINGS
# ============================================================
SETTING_DEFAULTS = {
    "antilink": False, "antimedia": False, "badwords": False, "antiflood": False,
    "welcome": WELCOME_DEFAULT, "reminder": False,
    "warn_limit": DEFAULT_WARN_LIMIT, "warn_action": "mute",
    "rules": "", "welcome_text": "", "words": [],
}
# The official group keeps the behaviour it had before the multi-group upgrade.
LEGACY_DEFAULTS = {"antilink": True, "antimedia": True, "badwords": True, "reminder": True}

_settings_cache: dict[int, tuple[float, dict]] = {}

async def get_settings(chat_id: int) -> dict:
    now = _tm.time()
    hit = _settings_cache.get(chat_id)
    if hit and hit[0] > now:
        return hit[1]
    s = dict(SETTING_DEFAULTS)
    s["words"] = []
    if chat_id == OFFICIAL_GROUP_ID:
        s.update(LEGACY_DEFAULTS)
    try:
        doc = await settings_col.find_one({"chat_id": chat_id})
    except Exception:
        doc = None
    if doc:
        s.update({k: v for k, v in doc.items() if k != "_id"})
    s["chat_id"] = chat_id
    _settings_cache[chat_id] = (now + 30, s)
    return s

async def set_setting(chat_id: int, **kv):
    kv["updated_at"] = datetime.now(timezone.utc)
    await settings_col.update_one({"chat_id": chat_id}, {"$set": kv}, upsert=True)
    _settings_cache.pop(chat_id, None)

_seen_groups: set[int] = set()
_title_cache: dict[int, str] = {}

async def get_group_title(chat_id: int) -> str:
    if chat_id in _title_cache:
        return _title_cache[chat_id]
    title = None
    try:
        title = getattr(await bot.get_entity(chat_id), "title", None)
    except Exception:
        pass
    if not title:
        res = await api("getChat", chat_id=chat_id)
        title = (res.get("result") or {}).get("title")
    title = title or str(chat_id)
    _title_cache[chat_id] = title
    return title

async def register_group(chat_id: int):
    try:
        title = await get_group_title(chat_id)
        await settings_col.update_one(
            {"chat_id": chat_id},
            {"$set": {"title": title, "active": True},
             "$setOnInsert": {"added_at": datetime.now(timezone.utc)}},
            upsert=True)
        _settings_cache.pop(chat_id, None)
    except Exception:
        pass

async def get_member_count(chat_id: int):
    res = await api("getChatMemberCount", chat_id=chat_id)
    return res.get("result") if res.get("ok") else None


# ============================================================
# 🛡️  ADMIN / USER HELPERS
# ============================================================
_admin_cache: dict[int, dict] = {}

def _full_name(u) -> str:
    return f"{getattr(u, 'first_name', '') or ''} {getattr(u, 'last_name', '') or ''}".strip()

def _usernames(u) -> list[str]:
    out = []
    un = getattr(u, "username", None)
    if un:
        out.append(un.lower())
    for x in (getattr(u, "usernames", None) or []):
        n = getattr(x, "username", None)
        if n and getattr(x, "active", True):
            out.append(n.lower())
    return out

async def _load_admins(chat_id: int) -> dict:
    now = _tm.time()
    c = _admin_cache.get(chat_id)
    if c and now < c["expiry"]:
        return c
    entry = {"ids": set(), "list": [], "expiry": now + 10}
    try:
        res = await bot(GetParticipantsRequest(chat_id, ChannelParticipantsAdmins(), 0, 200, 0))
        users = {u.id: u for u in res.users}
        for p in res.participants:
            u = users.get(getattr(p, "user_id", None))
            if not u:
                continue
            entry["ids"].add(u.id)
            entry["list"].append({"id": u.id, "name": _full_name(u) or "Admin",
                                  "bot": bool(getattr(u, "bot", False)),
                                  "creator": isinstance(p, ChannelParticipantCreator),
                                  "usernames": _usernames(u)})
        entry["expiry"] = now + ADMIN_CACHE_TTL
    except Exception:
        try:  # basic (non-super) groups
            async for u in bot.iter_participants(chat_id, filter=ChannelParticipantsAdmins):
                entry["ids"].add(u.id)
                entry["list"].append({"id": u.id, "name": _full_name(u) or "Admin",
                                      "bot": bool(getattr(u, "bot", False)),
                                      "creator": isinstance(getattr(u, "participant", None),
                                                            (ChannelParticipantCreator, ChatParticipantCreator)),
                                      "usernames": _usernames(u)})
            entry["expiry"] = now + ADMIN_CACHE_TTL
        except Exception:
            pass
    _admin_cache[chat_id] = entry
    return entry

async def get_admin_ids(chat_id: int) -> set[int]:
    return (await _load_admins(chat_id))["ids"]

async def is_admin(chat_id: int, user_id: int) -> bool:
    if user_id == OWNER_ID or user_id == chat_id:     # owner, or anonymous admin posting as the group
        return True
    return user_id in await get_admin_ids(chat_id)

async def get_admin_list(chat_id: int) -> list[dict]:
    lst = list((await _load_admins(chat_id))["list"])
    if chat_id == OFFICIAL_GROUP_ID and not any(a["id"] == OWNER_ID for a in lst):
        lst.append({"id": OWNER_ID, "name": "Owner", "bot": False, "creator": False})
    return lst

async def get_group_owner(chat_id: int):
    """The creator of the group as {"id", "name", "usernames", ...}, or None when unknown."""
    for a in (await _load_admins(chat_id))["list"]:
        if a.get("creator") and not a.get("bot"):
            return a
    return None

async def get_user_name(user_id: int) -> str:
    try:
        u = await bot.get_entity(user_id)
        return _full_name(u) or getattr(u, "title", None) or str(user_id)
    except Exception:
        return str(user_id)

async def target_and_rest(event) -> tuple[int | None, str]:
    """Target = replied user, else first argument (@username / id). Returns (id, remaining args)."""
    _, args = _split_cmd(event.raw_text or "")
    if event.is_reply:
        r = await event.get_reply_message()
        if r and r.sender_id:
            return r.sender_id, args
    if not args:
        return None, ""
    tok, _, rest = args.partition(" ")
    try:
        if tok.startswith("@"):
            return (await bot.get_entity(tok)).id, rest.strip()
        return int(tok), rest.strip()
    except Exception:
        return None, args

def _split_cmd(text: str) -> tuple[str, str]:
    parts = (text or "").strip().split(None, 1)
    if not parts:
        return "", ""
    cmd = parts[0].split("@", 1)[0]
    return cmd, (parts[1].strip() if len(parts) > 1 else "")

async def protect_check(event, tid, *, allow_bots: bool = True, allow_admins: bool = False):
    """Return an HTML error string if the target must not be actioned, else None."""
    if tid is None:
        return f"{head('warn', 'Target Required')}\n\nReply to a member, or use <code>@username</code> / user ID."
    if tid < 0:
        return f"{head('warn', 'Not Allowed')}\n\nChannels and anonymous senders cannot be targeted."
    if tid == event.sender_id:
        return f"{head('warn', 'Not Allowed')}\n\nYou cannot target yourself."
    if tid == OWNER_ID:
        return f"{head('shield', 'Owner is protected')}"
    if tid == await _ensure_me():
        return f"{head('shield', 'I will not do that to myself')}"
    if not allow_admins and await is_admin(event.chat_id, tid):
        return f"{head('shield', 'Protected Member')}\n\nAdmins cannot be targeted."
    if not allow_bots:
        try:
            if getattr(await bot.get_entity(tid), "bot", False):
                return f"{head('warn', 'Not Allowed')}\n\nBots cannot be muted."
        except Exception:
            pass
    return None

def perm_error(e) -> str:
    err = str(e)
    if any(k in err.lower() for k in ("admin", "right", "permission")):
        return (f"{head('cross', 'Insufficient Permissions')}\n\n"
                f"Make me an admin with <b>Ban Users</b> and <b>Delete Messages</b>.")
    return f"{head('warn', 'Failed')}\n\n{code(err)}"


# ============================================================
# 🔨  MODERATION CORE
# ============================================================
def rights_mute(until: int = 0) -> ChatBannedRights:
    return ChatBannedRights(until_date=until, view_messages=False, send_messages=True, send_media=True,
                            send_stickers=True, send_gifs=True, send_games=True, send_inline=True,
                            embed_links=True, send_polls=True)

def rights_ban() -> ChatBannedRights:
    return ChatBannedRights(until_date=0, view_messages=True, send_messages=True, send_media=True,
                            send_stickers=True, send_gifs=True, send_games=True, send_inline=True,
                            embed_links=True, send_polls=True)

async def do_mute(chat_id, uid, seconds: int = 0):
    until = int(_tm.time() + seconds) if seconds else 0
    await bot(EditBannedRequest(chat_id, uid, rights_mute(until)))

async def do_unmute(chat_id, uid):
    await bot(EditBannedRequest(chat_id, uid, ChatBannedRights(until_date=0)))

async def do_ban(chat_id, uid):
    await bot(EditBannedRequest(chat_id, uid, rights_ban()))

async def do_kick(chat_id, uid):
    await bot(EditBannedRequest(chat_id, uid, ChatBannedRights(until_date=int(_tm.time() + KICK_BAN_SECONDS), view_messages=True)))

async def get_mute_count(admin_id: int, chat_id: int) -> int:
    doc = await mute_daily_col.find_one({"admin_id": admin_id, "chat_id": chat_id, "date": today_str()})
    return int(doc["count"]) if doc else 0

async def increment_mute_count(admin_id: int, chat_id: int):
    await mute_daily_col.update_one({"admin_id": admin_id, "chat_id": chat_id, "date": today_str()},
                                    {"$inc": {"count": 1}}, upsert=True)

async def mute_flow(chat_id: int, admin_id: int, tid: int, name: str, seconds: int = 0):
    """Quota check + mute. Returns (ok, html)."""
    if admin_id != OWNER_ID:
        used = await get_mute_count(admin_id, chat_id)
        if used >= MUTE_DAILY_LIMIT:
            return False, (f"{head('clock', 'Daily Mute Quota Reached')}\n\n"
                           f"Used: {code(used)} / {code(MUTE_DAILY_LIMIT)}")
    try:
        await do_mute(chat_id, tid, seconds)
    except Exception as e:
        return False, perm_error(e)
    line = f"<b>Target:</b> {make_mention(name, tid)}\n"
    line += f"<b>Duration:</b> {code(fmt_secs(seconds))}\n" if seconds else "<b>Duration:</b> Permanent\n"
    if admin_id != OWNER_ID:
        await increment_mute_count(admin_id, chat_id)
        used_after = await get_mute_count(admin_id, chat_id)
        line += (f"<b>Quota Used:</b> {code(used_after)} / {code(MUTE_DAILY_LIMIT)}\n"
                 f"<b>Remaining:</b> {code(max(0, MUTE_DAILY_LIMIT - used_after))}")
    return True, f"{head('mute', 'Member Muted')}\n\n{line}".rstrip()

async def warn_flow(chat_id: int, tid: int, reason: str):
    """Add a warning, apply the group's warn action at the limit. Returns (html, keyboard)."""
    s = await get_settings(chat_id)
    limit = int(s["warn_limit"])
    doc = await warns_col.find_one_and_update(
        {"chat_id": chat_id, "user_id": tid},
        {"$inc": {"count": 1}, "$push": {"reasons": {"$each": [reason], "$slice": -20}},
         "$set": {"updated_at": datetime.now(timezone.utc)}},
        upsert=True, return_document=ReturnDocument.AFTER)
    count = int(doc.get("count", 1)) if doc else 1
    name = await get_user_name(tid)
    text = (f"{head('warn', 'Warning Issued')}\n\n<b>Member:</b> {make_mention(name, tid)}\n"
            f"<b>Reason:</b> {code(reason)}\n<b>Count:</b> {code(count)} / {code(limit)}")
    kb = [[btn("Remove warning", f"mod:unwarn:{tid}", icon="check", style="success")]]
    if count >= limit:
        action = s.get("warn_action", "mute")
        try:
            if action == "ban":
                await do_ban(chat_id, tid)
                text += f"\n\n{head('ban', 'Auto-Ban Activated')}"
                kb = [[btn("Unban", f"mod:unban:{tid}", icon="unlock", style="success")]]
            elif action == "kick":
                await do_kick(chat_id, tid)
                text += f"\n\n{head('kick', 'Auto-Kick Activated')}"
                kb = []
            else:
                await do_mute(chat_id, tid, 3600)
                text += f"\n\n{head('mute', 'Auto-Mute Activated')} (1h)"
                kb = [[btn("Unmute", f"mod:unmute:{tid}", icon="unmute", style="success")]]
            await warns_col.delete_one({"chat_id": chat_id, "user_id": tid})
        except Exception as e:
            text += f"\n\n{head('warn', 'Auto-action failed')}\n{code(e)}"
    return text, kb


# ============================================================
# 🧭  COMMAND ROUTER  (slash commands + plain-text triggers + callbacks)
# ============================================================
def safe_handler(ctx: str):
    def deco(fn):
        async def wrapper(*a, **k):
            try:
                return await fn(*a, **k)
            except Exception as e:
                print(f"❌ [{ctx}] {type(e).__name__}: {e}")
                traceback.print_exc()
        wrapper.__name__ = fn.__name__
        return wrapper
    return deco

CMDS: dict[str, dict] = {}
TRIGGERS: dict[str, dict] = {}
CALLBACKS: dict[str, object] = {}

def command(*names, scope: str = "group", perm: str = "any"):
    def deco(fn):
        w = safe_handler(fn.__name__)(fn)
        for n in names:
            CMDS[n.lower()] = {"fn": w, "scope": scope, "perm": perm}
        return fn
    return deco

def trigger(*texts, scope: str = "group", perm: str = "owner"):
    def deco(fn):
        w = safe_handler(fn.__name__)(fn)
        for t in texts:
            TRIGGERS[norm_text(t)] = {"fn": w, "scope": scope, "perm": perm}
        return fn
    return deco

def callback(kind: str):
    def deco(fn):
        CALLBACKS[kind] = safe_handler("cb_" + kind)(fn)
        return fn
    return deco

@bot.on(events.NewMessage(incoming=True))
@safe_handler("router")
async def router(event):
    raw = event.raw_text or ""
    sender = event.sender_id
    if not raw or sender is None:
        return
    if event.is_group and event.chat_id not in _seen_groups:
        _seen_groups.add(event.chat_id)
        spawn(register_group(event.chat_id))
    await _ensure_me()
    text = clean_invisible(raw).strip()
    if not text:
        return
    is_slash = text.startswith("/")
    entry = None
    args = ""
    if is_slash:
        word = text.split(None, 1)[0]
        name, _, target = word[1:].partition("@")
        if target and target.lower() != (_my_username or "").lower():
            return                                        # command addressed to a different bot
        entry = CMDS.get(name.lower())
        args = _split_cmd(text)[1]
    else:
        key = norm_text(text)
        entry = TRIGGERS.get(key)
    if not entry:
        return

    scope, perm = entry["scope"], entry["perm"]
    if scope == "group" and not event.is_group:
        if is_slash:
            await reply(event, head("info", "Use this command inside a group"))
        return
    if scope == "private" and not event.is_private:
        return
    if perm == "owner" and sender != OWNER_ID:
        if is_slash:
            await notice(event, head("crown", "Owner Only"))
        return
    if perm == "admin" and not await is_admin(event.chat_id, sender):
        if is_slash:
            await notice(event, head("lock", "Admin Only"))
        return
    await entry["fn"](event, args)

@bot.on(events.CallbackQuery())
async def callback_router(event):
    try:
        data = (event.data or b"").decode("utf-8", "ignore")
        kind, _, rest = data.partition(":")
        h = CALLBACKS.get(kind)
        if not h:
            await event.answer()
            return
        await h(event, rest)
    except Exception as e:
        print(f"❌ [callback] {type(e).__name__}: {e}")
        traceback.print_exc()
        try:
            await event.answer("Something went wrong.")
        except Exception:
            pass

async def deny(event, text: str = "Admins only."):
    try:
        await event.answer(text, alert=True)
    except Exception:
        pass

async def edit_append(event, line: str, kb=None):
    """Append a status line to the pressed message and replace its buttons."""
    base = ""
    try:
        m = await event.get_message()
        if m:
            base = message_html(m)
    except Exception:
        pass
    await tg_edit(event.chat_id, event.query.msg_id, f"{base}\n\n{line}" if base else line, kb or [])


# ============================================================
# 📖  HELP & START
# ============================================================
def add_to_group_url() -> str:
    rights = "delete_messages+restrict_members+invite_users+pin_messages+manage_chat"
    return f"https://t.me/{_my_username}?startgroup&admin={rights}"

PLACEHOLDERS = "{mention} {name} {username} {title} {count} {id}"
EX_WELCOME   = "/setwelcome ကြိုဆိုပါတယ် {mention}!"

def start_dm_url(param: str = "welcome") -> str:
    return f"https://t.me/{_my_username}?start={param}"

def help_page(page: str):
    c = code
    pages = {
        "mod": (
            f"{head('ban', 'Moderation — Admin များအတွက်')}\n\n"
            f"{pe('warn')} <b>သတိပေးစနစ် (Warn)</b>\n"
            f"• Reply + {c('/warn')} — Member ကို သတိပေးပါတယ်\n"
            f"• {c('/unwarn')} · {c('/warns')} — သတိပေးချက်ပြန်ဖျက် / စစ်ကြည့်\n"
            f"• သတ်မှတ်ကြိမ်ရေပြည့်ရင် Mute / Kick / Ban ကို အလိုအလျောက်လုပ်ပေးပါတယ် ({c('/settings')} မှာပြင်နိုင်)\n\n"
            f"{pe('mute')} <b>Mute / Unmute</b>\n"
            f"• Reply + {c('/mute 30m')} — မိနစ် ၃၀ Mute (s · m · h · d · w သုံးနိုင်)\n"
            f"• Reply + {c('/mute')} သို့ {c(MUTE_TRIGGERS[0])} — ကန့်သတ်ချိန်မရှိ Mute\n"
            f"• Reply + {c('/unmute')} သို့ {c(UNMUTE_TRIGGERS[0])} — ပြန်ဖွင့်\n"
            f"• Admin တစ်ယောက်ကို တစ်ရက် {MUTE_DAILY_LIMIT} ကြိမ်သာ Mute ခွင့်ပေးထားပါတယ်\n\n"
            f"{pe('kick')} <b>Kick / Ban</b>\n"
            f"• {c('/kick')} — Group ကထုတ် (စက္ကန့် {KICK_BAN_SECONDS} အကြာ ပြန်ဝင်လို့ရ)\n"
            f"• {c('/ban')} · {c('/unban')} — အပြီးပိတ် / ပြန်ဖွင့်\n"
            f"• Reply သို့မဟုတ် {c('@username')} / ID နဲ့ သုံးနိုင်ပါတယ်\n\n"
            f"{pe('pin')} <b>Pin / Purge</b>\n"
            f"• {c('/pin')} · {c('/unpin')} — Reply လုပ်တဲ့စာကို Pin / Unpin\n"
            f"• Reply + {c('/purge')} — Reply လုပ်တဲ့စာကနေ အောက်ဆုံးထိ အစုလိုက်ဖျက် (အများဆုံး {PURGE_MAX})\n\n"
            f"{pe('info')} <i>လုပ်ဆောင်ချက်တိုင်းမှာ Undo / Unmute / Unban ခလုတ်လေးတွေ ပါပါတယ်။</i>"),
        "auto": (
            f"{head('alert', 'Auto-Protection — အလိုအလျောက်ကာကွယ်ရေး')}\n\n"
            f"{c('/settings')} ထဲက ခလုတ်တွေနဲ့ တစ်ခုချင်း ဖွင့်/ပိတ်လို့ရပါတယ်။ Admin တွေကို မထိခိုက်ပါဘူး။\n\n"
            f"{pe('link')} <b>Anti-Link</b> — Admin မဟုတ်သူပို့တဲ့ Link ကို ချက်ချင်းဖျက်\n"
            f"{pe('eyes')} <b>Anti-Media</b> — Admin မဟုတ်သူပို့တဲ့ ဓာတ်ပုံ/ဗီဒီယို ဖျက် (Sticker · GIF ကတော့ ခွင့်ပြု)\n"
            f"{pe('warn')} <b>Bad Words</b> — ဆဲဆိုစကားသုံးရင် သတိပေး၊ မိနစ် {BADWORD_WINDOW_SECONDS // 60} အတွင်း ထပ်သုံးရင် {fmt_secs(BADWORD_MUTE_DURATION)} Mute\n"
            f"   စကားလုံးထပ်ထည့်/ဖြုတ် — {c('/addword')} · {c('/delword')} · {c('/badwords')}\n"
            f"{pe('fire')} <b>Anti-Flood</b> — စက္ကန့် {FLOOD_WINDOW} အတွင်း စာ {FLOOD_MESSAGES} စောင်ပို့ရင် {fmt_secs(FLOOD_MUTE_SECONDS)} Mute\n"
            f"{pe('alert')} <b>Reminder</b> — ၃ နာရီတစ်ခါ {c('/report')} သုံးပုံကို သတိပေး\n\n"
            f"{pe('check')} <i>Group တစ်ခုချင်းစီရဲ့ Setting က သီးခြားစီဖြစ်ပါတယ်။</i>"),
        "welcome": (
            f"{head('online', 'Welcome &amp; Rules')}\n\n"
            f"{pe('online')} <b>Welcome စနစ်</b>\n"
            f"Member သို့မဟုတ် Bot အသစ် Group ထဲဝင်လာတိုင်း သူတို့ရဲ့ <b>Profile ပုံ</b> ကို Download လုပ်ပြီး "
            f"Premium Emoji တွေနဲ့ လှလှပပ Caption ပါတဲ့ ကြိုဆိုစာ ပို့ပေးပါတယ်။ အောက်မှာ Bot DM ကို <b>Start</b> နှိပ်ဖို့ ခလုတ်ပါပါတယ်။\n"
            f"• {c('/welcome on|off')} — ဖွင့်/ပိတ်\n"
            f"• {c('/setwelcome')} — ကိုယ်ပိုင်စာသားသတ်မှတ် · {c('/resetwelcome')} — မူလပြန်ထား\n"
            f"• Placeholder: {c(PLACEHOLDERS)}\n\n"
            f"{pe('book')} <b>Rules (စည်းကမ်းချက်)</b>\n"
            f"• {c('/setrules')} — သတ်မှတ် · {c('/rules')} — ကြည့် · {c('/clearrules')} — ဖျက်\n\n"
            f"{pe('info')} <i>စာထဲမှာ Format နဲ့ ကိုယ်ပိုင် Premium Emoji တွေထည့်ရင်လည်း မပျက်ဘဲ သိမ်းပေးပါတယ်။ "
            f"Format လုပ်ထားတဲ့စာကို Reply လုပ်ပြီး /setrules သုံးလို့လည်းရပါတယ်။</i>"),
        "afk": (
            f"{head('afk', 'AFK စနစ် — Owner အတွက်')}\n\n"
            f"Group ရဲ့ <b>Owner</b> (Group ကိုဖန်တီးသူ) ကို @username နဲ့ Mention လုပ်လည်းကောင်း၊ သူ့စာကို Reply လုပ်လည်းကောင်း၊ "
            f"Owner က AFK ဖွင့်ထားရင် Bot က အလိုအလျောက် စာပြန်ပေးပါတယ်။ Group တစ်ခုချင်းစီရဲ့ Owner အားလုံးအတွက် အလုပ်လုပ်ပါတယ်။\n\n"
            f"{pe('lock')} <b>ဖွင့်/ပိတ်နည်း (Group Owner ကိုယ်တိုင်)</b>\n"
            f"• {c('afk on')} — AFK ဖွင့်\n"
            f"• {c('afk off')} — AFK ပိတ် (Online ပြန်လာပြီ)\n"
            f"• {c('afk')} — လက်ရှိအခြေအနေကြည့်\n"
            f"• {c('/afk on စာလေ့လာနေတယ်')} — အကြောင်းပြချက်ပါထည့်ပြီး ဖွင့်\n\n"
            f"{pe('clock')} Spam မဖြစ်အောင် တစ်ယောက်ကို စက္ကန့် {AFK_REPLY_COOLDOWN} တစ်ခါပဲ ပြန်ပေးပါတယ်။\n"
            f"{pe('check')} AFK အခြေအနေကို သိမ်းထားလို့ Bot Restart လုပ်လည်း မပျောက်ပါဘူး။"),
        "tools": (
            f"{head('stats', 'Tools — အသုံးဝင်တဲ့ Command များ')}\n\n"
            f"• {c('/settings')} — {pe('gear')} ခလုတ်နဲ့ Setting အားလုံးထိန်းချုပ် (Admin)\n"
            f"• {c('/id')} · {c('/info')} — {pe('id')} ID နဲ့ User အချက်အလက်ကြည့်\n"
            f"• {c('/admins')} — {pe('admin')} Admin စာရင်း\n"
            f"• {c('/stats')} · {c('/mutecount')} — {pe('stats')} Group စာရင်းအင်း / ကိုယ့် Mute ကွတ်တာ\n"
            f"• {c('/reload')} — {pe('refresh')} Admin စာရင်း Refresh\n"
            f"• Reply + {c('/report')} — {pe('alert')} Admin အားလုံးကို အကြောင်းကြား (၃ နာရီ ၁ ကြိမ်)\n\n"
            f"{pe('info')} <i>Report ရောက်ရင် Admin တွေက Mute / Delete / Resolved ခလုတ်နဲ့ ချက်ချင်းဖြေရှင်းလို့ရပါတယ်။</i>"),
        "owner": (
            f"{head('crown', 'Owner (Bot ပိုင်ရှင်)')}\n\n"
            f"• {c(TRG_LOCK[0])} / {c(TRG_UNLOCK[0])} — {pe('lock')} Group ပိတ် / ဖွင့်\n"
            f"• Reply + {c(TRG_BAN[0])} / {c(TRG_KICK[0])} / {c('adm')} / {c('?')} — Ban / Kick / Moderator ခန့် / User info\n"
            f"• {c('afk on')} · {c('afk off')} — {pe('afk')} AFK (Group တိုင်းမှာ Mention လုပ်ရင် စာပြန်)\n"
            f"• Reply + {c('/del')} သို့ {c(TRG_TRACK)} — {pe('delete')} Bot တစ်ခုရဲ့စာတွေကို အလိုအလျောက်ဖျက် · {c('/untrack id')}\n"
            f"• {c('/groups')} — {pe('globe')} Bot သုံးနေတဲ့ Group အားလုံး\n"
            f"• {c('/emojiid')} · {c('/setemoji')} · {c('/resetemoji')} · {c('/emojis')} — {pe('sparkle')} Premium Emoji"),
    }
    if page in pages:
        return pages[page], [[btn("နောက်သို့", "help:main", icon="back"), btn("ပိတ်မည်", "help:close", icon="close")]]
    text = (f"{head('fire', 'BOD Manager မှ ကြိုဆိုပါတယ်!')}\n\n"
            f"{pe('target')} <b>ဒီ Bot က ဘာတွေလုပ်ပေးလဲ?</b>\n"
            f"Telegram Group တစ်ခုလုံးကို ၂၄ နာရီ အလိုအလျောက် စောင့်ကြည့်ပြီး စီမံပေးတဲ့ <b>Group Guardian Bot</b> ဖြစ်ပါတယ်။\n\n"
            f"{pe('ban')} <b>Moderation</b> — Warn · Mute · Kick · Ban ကို Admin တွေ တစ်ချက်နှိပ်တည်း စီမံနိုင်\n"
            f"{pe('alert')} <b>Auto-Protection</b> — Link၊ Media၊ ဆဲစကား၊ Flood Spam တွေကို အလိုလိုဖျက်/ပိတ်\n"
            f"{pe('online')} <b>Welcome</b> — Member/Bot အသစ်ဝင်တိုင်း Profile ပုံနဲ့ လှလှပပ ကြိုဆို\n"
            f"{pe('afk')} <b>AFK</b> — Group Owner ကို Mention ရင် AFK စာ အလိုအလျောက်ပြန်\n"
            f"{pe('book')} <b>Rules &amp; Report</b> — စည်းကမ်းထုတ်ပြန်၊ ပြဿနာကို Admin အားလုံးဆီ တိုက်ရိုက်တိုင်ကြား\n\n"
            f"{pe('pin')} <b>စတင်အသုံးပြုနည်း</b>\n"
            f"<b>၁.</b> အောက်က <b>Group ထဲသို့ထည့်ရန်</b> ခလုတ်ကိုနှိပ်ပါ\n"
            f"<b>၂.</b> Bot ကို <b>Admin</b> ပေးပါ\n"
            f"<b>၃.</b> Group ထဲမှာ {code('/settings')} ရိုက်ပြီး ခလုတ်တွေနဲ့ ရွေးချယ်ပါ\n\n"
            f"{pe('eyes')} <i>အသေးစိတ်သိချင်တဲ့ အပိုင်းကို အောက်က ခလုတ်တွေနဲ့ နှိပ်ကြည့်ပါ။</i>")
    kb = [
        [btn("Group ထဲသို့ထည့်ရန်", url=add_to_group_url(), icon="plus", style="primary")],
        [btn("Moderation", "help:mod", icon="ban"), btn("Auto-Protection", "help:auto", icon="alert")],
        [btn("Welcome & Rules", "help:welcome", icon="online"), btn("AFK စနစ်", "help:afk", icon="afk")],
        [btn("Tools", "help:tools", icon="stats"), btn("Owner", "help:owner", icon="crown")],
        [btn("Owner ကိုဆက်သွယ်ရန်", url=f"https://t.me/{OWNER_USERNAME}", icon="chat"), btn("ပိတ်မည်", "help:close", icon="close")],
    ]
    return text, kb

@command("help", scope="any")
async def help_cmd(event, args):
    text, kb = help_page("main")
    await reply(event, text, kb)

@callback("help")
async def cb_help(event, rest):
    page = rest or "main"
    if page == "close":
        await tg_delete(event.chat_id, event.query.msg_id)
        await event.answer()
        return
    text, kb = help_page(page)
    await tg_edit(event.chat_id, event.query.msg_id, text, kb)
    await event.answer()

async def send_rules(chat_id, group_id: int, reply_to: int | None = None):
    s = await get_settings(group_id)
    if not s.get("rules"):
        await tg_send(chat_id, f"{head('mailbox', 'No Rules Set Yet')}", reply_to=reply_to)
        return
    title = await get_group_title(group_id)
    await tg_send(chat_id, f"{head('book', 'Group Rules')} — {esc(title)}\n\n{s['rules']}", reply_to=reply_to)

@command("start", scope="any")
async def start_cmd(event, args):
    await _ensure_me()
    if event.is_private:
        if args.startswith("rules_"):
            try:
                await send_rules(event.chat_id, int(args[6:]), reply_to=event.id)
            except ValueError:
                pass
            return
        # plain /start, ?start=welcome and ?start=help all open the full Burmese intro
        await help_cmd(event, "")
        return
    text = (f"{head('online', 'BOD Manager')}\n\n"
            f"Bot က Online ဖြစ်နေပြီး ဒီ Group ကို ၂၄ နာရီ စောင့်ကြည့်ပေးနေပါတယ်။\n\n"
            f"{pe('info')} <i>လုပ်ဆောင်ချက်အားလုံးကို Bot DM မှာ Start နှိပ်ပြီး အသေးစိတ်ကြည့်နိုင်ပါတယ်။</i>")
    kb = [[btn("Bot ကို Start နှိပ်ပါ", url=start_dm_url("welcome"), icon="fire", style="primary")],
          [btn("အကူအညီ", "help:main", icon="book"), btn("စည်းကမ်းများ", url=start_dm_url(f"rules_{event.chat_id}"), icon="rules")],
          [btn("Settings", "set:open", icon="gear")]]
    await reply(event, text, kb)



# ============================================================
# ⚙️  SETTINGS PANEL  (inline buttons)
# ============================================================
TOGGLES = {
    "antilink":  ("Anti-Link",  "link"),
    "antimedia": ("Anti-Media", "eyes"),
    "badwords":  ("Bad Words",  "warn"),
    "antiflood": ("Anti-Flood", "bolt"),
    "welcome":   ("Welcome",    "party"),
    "reminder":  ("Reminder",   "alert"),
}
WARN_ACTIONS = ["mute", "kick", "ban"]

def settings_text(title: str) -> str:
    return (f"{head('gear', 'Group Settings')}\n\n<b>Group:</b> {code(title)}\n\n"
            f"Tap a feature to switch it on/off.  Green = ON, red = OFF.\n"
            f"<i>Rules, welcome text and extra bad words: {code('/setrules')} · {code('/setwelcome')} · {code('/addword')}</i>")

def settings_kb(s: dict):
    def tog(key):
        label, icon = TOGGLES[key]
        on = bool(s.get(key))
        return btn(f"{label}: {'ON' if on else 'OFF'}", f"set:{key}", icon=icon, style="success" if on else "danger")
    return [
        [tog("antilink"), tog("antimedia")],
        [tog("badwords"), tog("antiflood")],
        [tog("welcome"), tog("reminder")],
        [btn("−", "set:wl-"), btn(f"Warn limit: {s['warn_limit']}", "set:noop", icon="warn"), btn("+", "set:wl+")],
        [btn(f"At limit: {str(s['warn_action']).upper()}", "set:wa", icon="hammer")],
        [btn("Help", "help:main", icon="book"), btn("Close", "set:close", icon="close")],
    ]

async def render_settings(chat_id: int, message_id: int):
    s = await get_settings(chat_id)
    await tg_edit(chat_id, message_id, settings_text(await get_group_title(chat_id)), settings_kb(s))

@command("settings", perm="admin")
async def settings_cmd(event, args):
    s = await get_settings(event.chat_id)
    await reply(event, settings_text(await get_group_title(event.chat_id)), settings_kb(s))

@callback("set")
async def cb_set(event, rest):
    chat_id = event.chat_id
    if not await is_admin(chat_id, event.sender_id):
        await deny(event)
        return
    msg_id = event.query.msg_id
    s = await get_settings(chat_id)
    if rest == "close":
        await tg_delete(chat_id, msg_id)
        await event.answer()
        return
    if rest == "noop":
        await event.answer()
        return
    if rest == "open":
        await render_settings(chat_id, msg_id)
        await event.answer()
        return
    if rest == "new":                       # pressed on a photo message -> open the panel as a new message
        await tg_send(chat_id, settings_text(await get_group_title(chat_id)), settings_kb(s))
        await event.answer()
        return
    if rest in TOGGLES:
        new = not bool(s.get(rest))
        await set_setting(chat_id, **{rest: new})
        await event.answer(f"{TOGGLES[rest][0]} {'enabled' if new else 'disabled'}")
    elif rest in ("wl+", "wl-"):
        cur = int(s["warn_limit"])
        new = max(2, min(10, cur + (1 if rest == "wl+" else -1)))
        if new == cur:
            await event.answer("Limit must be between 2 and 10.")
            return
        await set_setting(chat_id, warn_limit=new)
        await event.answer(f"Warn limit: {new}")
    elif rest == "wa":
        cur = str(s.get("warn_action", "mute"))
        nxt = WARN_ACTIONS[(WARN_ACTIONS.index(cur) + 1) % len(WARN_ACTIONS)] if cur in WARN_ACTIONS else "mute"
        await set_setting(chat_id, warn_action=nxt)
        await event.answer(f"Action at limit: {nxt}")
    else:
        await event.answer()
        return
    await render_settings(chat_id, msg_id)


# ============================================================
# 🔇  MUTE / UNMUTE / WARN / KICK / BAN
# ============================================================
@command("mute", perm="admin")
@trigger(*MUTE_TRIGGERS, perm="admin")
async def mute_cmd(event, args):
    tid, rest = await target_and_rest(event)
    seconds = 0
    tok = rest.split()[0] if rest else ""
    if tok:
        seconds = parse_duration(tok) or 0
    err = await protect_check(event, tid, allow_bots=False)
    if err:
        await notice(event, err)
        return
    name = await get_user_name(tid)
    ok, text = await mute_flow(event.chat_id, event.sender_id, tid, name, seconds)
    kb = [[btn("Unmute", f"mod:unmute:{tid}", icon="unmute", style="success")]] if ok else None
    await reply(event, text, kb)

@command("unmute", perm="admin")
@trigger(*UNMUTE_TRIGGERS, perm="admin")
async def unmute_cmd(event, args):
    tid, _ = await target_and_rest(event)
    if tid is None or tid < 0:
        await notice(event, f"{head('warn', 'Reply Required')}\n\nReply to the member you want to unmute.")
        return
    try:
        await do_unmute(event.chat_id, tid)
    except Exception as e:
        await notice(event, perm_error(e))
        return
    name = await get_user_name(tid)
    await reply(event, f"{head('unmute', 'Member Unmuted')}\n\n<b>Target:</b> {make_mention(name, tid)}")

@command("warn", perm="admin")
async def warn_cmd(event, args):
    tid, rest = await target_and_rest(event)
    err = await protect_check(event, tid)
    if err:
        await notice(event, err)
        return
    reason = (rest or "no reason").strip()[:200]
    text, kb = await warn_flow(event.chat_id, tid, reason)
    await reply(event, text, kb)

@command("unwarn", perm="admin")
async def unwarn_cmd(event, args):
    tid, _ = await target_and_rest(event)
    if tid is None or tid < 0:
        await notice(event, f"{head('warn', 'Reply Required')}\n\nReply to a member or use <code>@user</code>.")
        return
    new = await _remove_warn(event.chat_id, tid)
    if new is None:
        await notice(event, head("info", "No Warnings Found"))
        return
    name = await get_user_name(tid)
    await reply(event, f"{head('check', 'Warning Removed')}\n\n<b>Member:</b> {make_mention(name, tid)}\n<b>Updated Count:</b> {code(new)}")

async def _remove_warn(chat_id: int, tid: int):
    doc = await warns_col.find_one({"chat_id": chat_id, "user_id": tid})
    if not doc or not doc.get("count"):
        return None
    new = int(doc["count"]) - 1
    if new <= 0:
        await warns_col.delete_one({"chat_id": chat_id, "user_id": tid})
        return 0
    await warns_col.update_one({"chat_id": chat_id, "user_id": tid}, {"$set": {"count": new}, "$pop": {"reasons": 1}})
    return new

@command("warns", perm="any")
async def warns_cmd(event, args):
    tid, _ = await target_and_rest(event)
    if tid is None or tid < 0:
        tid = event.sender_id
    doc = await warns_col.find_one({"chat_id": event.chat_id, "user_id": tid})
    name = await get_user_name(tid)
    if not doc or not doc.get("count"):
        await reply(event, f"{head('check', 'Clean Record')}\n\n{make_mention(name, tid)}", ttl=60)
        return
    s = await get_settings(event.chat_id)
    lines = [f"{head('warn', 'Warnings')} — {make_mention(name, tid)}\n",
             f"<b>Total:</b> {code(doc['count'])} / {code(s['warn_limit'])}\n"]
    for r in doc.get("reasons", [])[-5:]:
        lines.append(f"• {code(r)}")
    await reply(event, "\n".join(lines), ttl=60)

@command("kick", perm="admin")
@trigger(*TRG_KICK, perm="owner")
async def kick_cmd(event, args):
    tid, _ = await target_and_rest(event)
    err = await protect_check(event, tid)
    if err:
        await notice(event, err)
        return
    try:
        await do_kick(event.chat_id, tid)
    except Exception as e:
        await notice(event, perm_error(e))
        return
    name = await get_user_name(tid)
    await reply(event, f"{head('kick', 'Member Kicked')}\n\n<b>Target:</b> {make_mention(name, tid)}\n<b>Can rejoin after:</b> {code(fmt_secs(KICK_BAN_SECONDS))}")

@command("ban", perm="admin")
@trigger(*TRG_BAN, perm="owner")
async def ban_cmd(event, args):
    tid, _ = await target_and_rest(event)
    err = await protect_check(event, tid)
    if err:
        await notice(event, err)
        return
    try:
        await do_ban(event.chat_id, tid)
    except Exception as e:
        await notice(event, perm_error(e))
        return
    name = await get_user_name(tid)
    await reply(event, f"{head('ban', 'Member Banned')}\n\n<b>Target:</b> {make_mention(name, tid)}",
                [[btn("Unban", f"mod:unban:{tid}", icon="unlock", style="success")]])

@command("unban", perm="admin")
async def unban_cmd(event, args):
    tid, _ = await target_and_rest(event)
    if tid is None or tid < 0:
        await notice(event, f"{head('warn', 'Target Required')}\n\nReply, <code>@user</code> or user ID.")
        return
    try:
        await do_unmute(event.chat_id, tid)
    except Exception as e:
        await notice(event, perm_error(e))
        return
    name = await get_user_name(tid)
    await reply(event, f"{head('check', 'Member Unbanned')}\n\n<b>Target:</b> {make_mention(name, tid)}")

@callback("mod")
async def cb_mod(event, rest):
    chat_id = event.chat_id
    if not await is_admin(chat_id, event.sender_id):
        await deny(event)
        return
    action, _, uid_s = rest.partition(":")
    try:
        tid = int(uid_s)
    except ValueError:
        await event.answer()
        return
    admin_name = await get_user_name(event.sender_id)
    by = f"<i>by {make_mention(admin_name, event.sender_id)}</i>"
    try:
        if action == "unmute":
            await do_unmute(chat_id, tid)
            await edit_append(event, f"{head('unmute', 'Unmuted')} {by}")
        elif action == "unban":
            await do_unmute(chat_id, tid)
            await edit_append(event, f"{head('check', 'Unbanned')} {by}")
        elif action == "unwarn":
            new = await _remove_warn(chat_id, tid)
            await edit_append(event, f"{head('check', 'Warning removed')} → {code(new if new is not None else 0)} {by}")
        else:
            await event.answer()
            return
        await event.answer("Done ✔")
    except Exception as e:
        await event.answer(str(e)[:150], alert=True)


# ============================================================
# 📌  PIN / UNPIN / PURGE / ADMINS / RELOAD
# ============================================================
@command("pin", perm="admin")
async def pin_cmd(event, args):
    if not event.is_reply:
        await notice(event, f"{head('pin', 'Reply to a message to pin it')}")
        return
    r = await event.get_reply_message()
    try:
        await bot(UpdatePinnedMessageRequest(event.chat_id, r.id, silent=False))
        await reply(event, head("pin", "Message Pinned"))
    except Exception as e:
        await notice(event, perm_error(e))

@command("unpin", perm="admin")
async def unpin_cmd(event, args):
    if not event.is_reply:
        await notice(event, f"{head('pin', 'Reply to a message to unpin it')}")
        return
    r = await event.get_reply_message()
    try:
        await bot(UpdatePinnedMessageRequest(event.chat_id, r.id, unpin=True))
        await reply(event, head("pin", "Message Unpinned"))
    except Exception as e:
        await notice(event, perm_error(e))

@command("purge", perm="admin")
async def purge_cmd(event, args):
    if not event.is_reply:
        await notice(event, head("delete", "Reply to the first message in the range"))
        return
    r = await event.get_reply_message()
    ids = list(range(r.id, event.id + 1))
    if len(ids) > PURGE_MAX:
        await notice(event, f"{head('warn', 'Range too large')}\n\nMax {code(PURGE_MAX)} messages per purge.")
        return
    deleted = 0
    for i in range(0, len(ids), 100):
        try:
            await bot.delete_messages(event.chat_id, ids[i:i + 100])
            deleted += len(ids[i:i + 100])
        except Exception:
            pass
    await tg_send(event.chat_id, f"{head('delete', 'Purge Complete')}\n\n<b>Messages Deleted:</b> {code(deleted)}", ttl=NOTICE_TTL)

@command("admins")
async def admins_cmd(event, args):
    admins = [a for a in await get_admin_list(event.chat_id) if not a["bot"]]
    title = await get_group_title(event.chat_id)
    if not admins:
        await reply(event, head("mailbox", "No Admin Data"))
        return
    lines = [f"{head('admin', 'Group Administration')}\n", f"<b>Group:</b> {code(title)}\n<b>Admins:</b> {code(len(admins))}\n"]
    for i, a in enumerate(admins, 1):
        crown = f"{pe('crown')} " if a["creator"] else ""
        lines.append(f"{i}. {crown}{make_mention(a['name'], a['id'])} — {code(a['id'])}")
    await reply(event, "\n".join(lines))

@command("reload", perm="admin")
async def reload_cmd(event, args):
    _admin_cache.pop(event.chat_id, None)
    _settings_cache.pop(event.chat_id, None)
    n = len(await get_admin_ids(event.chat_id))
    await notice(event, f"{head('refresh', 'Refreshed')}\n\n<b>Admins found:</b> {code(n)}")


# ============================================================
# 📖  RULES / WELCOME / WORDS
# ============================================================
@command("rules")
async def rules_cmd(event, args):
    s = await get_settings(event.chat_id)
    if not s.get("rules"):
        await notice(event, head("mailbox", "No Rules Set Yet"))
        return
    await reply(event, f"{head('book', 'Group Rules')}\n\n{s['rules']}")

@command("setrules", perm="admin")
async def setrules_cmd(event, args):
    txt = await rich_arg(event)
    if not txt:
        await notice(event, f"{head('pencil', 'Usage')}\n\n{code('/setrules your rules...')} or reply to a message with {code('/setrules')}")
        return
    if len(txt) > 3500:
        await notice(event, f"{head('warn', 'Too long')}\n\nKeep rules under 3500 characters.")
        return
    await set_setting(event.chat_id, rules=txt)
    await reply(event, head("check", "Rules Saved"), [[btn("View rules", "rules:show", icon="book")]])

@command("clearrules", perm="admin")
async def clearrules_cmd(event, args):
    await set_setting(event.chat_id, rules="")
    await reply(event, head("delete", "Rules Cleared"))

@callback("rules")
async def cb_rules(event, rest):
    s = await get_settings(event.chat_id)
    if not s.get("rules"):
        await event.answer("No rules set yet.", alert=True)
        return
    await tg_send(event.chat_id, f"{head('book', 'Group Rules')}\n\n{s['rules']}", ttl=120)
    await event.answer()

@command("welcome", perm="admin")
async def welcome_toggle_cmd(event, args):
    s = await get_settings(event.chat_id)
    a = args.lower().strip()
    if a in ("on", "enable", "yes"):
        new = True
    elif a in ("off", "disable", "no"):
        new = False
    elif not a:
        new = not bool(s.get("welcome"))
    else:
        await notice(event, f"{head('warn', 'Usage')}\n\n{code('/welcome on|off')}")
        return
    await set_setting(event.chat_id, welcome=new)
    await reply(event, head("online", "Welcome Messages Enabled") if new else head("offline", "Welcome Messages Disabled"))

def default_welcome() -> str:
    """Default welcome caption for a new MEMBER (premium emoji from the registry)."""
    return (f"{pe('fire')} <b>ကြိုဆိုပါတယ်</b> {pe('fire')}\n\n"
            f"{pe('online')} <b>အမည်</b> : {{mention}}\n"
            f"{pe('id')} <b>ID</b> : <code>{{id}}</code>\n"
            f"{pe('stats')} <b>အဖွဲ့ဝင်စုစုပေါင်း</b> : <b>{{count}}</b> ဦး\n\n"
            f"{pe('pin')} <b>{{title}}</b> မှ နွေးထွေးစွာ ကြိုဆိုပါတယ်။\n"
            f"{pe('book')} စည်းကမ်းချက်တွေကို ဖတ်ပြီး ရင်းနှီးစွာ ပါဝင်ဆွေးနွေးပေးပါနော်။\n\n"
            f"{pe('info')} <i>Bot ရဲ့ လုပ်ဆောင်ချက်တွေကို သိရန် အောက်က ခလုတ်ကိုနှိပ်ပြီး Start လုပ်လိုက်ပါ။</i>")

def default_bot_welcome() -> str:
    """Default caption when a BOT is added to the group."""
    return (f"{pe('target')} <b>Bot အသစ် ဝင်ရောက်လာပါပြီ</b>\n\n"
            f"{pe('online')} <b>Bot</b> : {{mention}}\n"
            f"{pe('link')} <b>Username</b> : {{username}}\n"
            f"{pe('id')} <b>ID</b> : <code>{{id}}</code>\n\n"
            f"{pe('alert')} <b>သတိပြုရန်</b> — မသိတဲ့ Bot တွေကို Admin ရာထူးမပေးခင် ယုံကြည်ရတဲ့ Bot ဟုတ်မဟုတ် အရင်စစ်ပါ။\n"
            f"{pe('pin')} <b>{{title}}</b> ရဲ့ လုံခြုံရေးကို BOD Manager က စောင့်ကြည့်နေပါတယ်။")

async def render_welcome(chat_id: int, uid: int, name: str, tmpl: str | None = None,
                         ent=None, is_bot: bool = False) -> str:
    s = await get_settings(chat_id)
    count = await get_member_count(chat_id)
    if tmpl is None:
        tmpl = default_bot_welcome() if is_bot else (s.get("welcome_text") or default_welcome())
    uname = getattr(ent, "username", None)
    return render_template(tmpl, mention=make_mention(name, uid), name=esc(name),
                           username=esc(f"@{uname}") if uname else "—",
                           title=esc(await get_group_title(chat_id)),
                           count=count if count is not None else "—", id=uid)

@command("setwelcome", perm="admin")
async def setwelcome_cmd(event, args):
    txt = await rich_arg(event)
    if not txt:
        await notice(event, f"{head('pencil', 'Usage')}\n\n{code(EX_WELCOME)}\nPlaceholders: {code(PLACEHOLDERS)}")
        return
    if len(txt) > 3000:
        await notice(event, f"{head('warn', 'Too long')}\n\nKeep it under 3000 characters.")
        return
    await set_setting(event.chat_id, welcome_text=txt)
    sender = await event.get_sender()
    name = _full_name(sender) or "Member"
    preview = await render_welcome(event.chat_id, event.sender_id, name, txt, ent=sender)
    note = ""
    if _u16len(_to_plain(preview)) > WELCOME_CAPTION_MAX:
        note = (f"\n\n{pe('warn')} <i>စာသားက {WELCOME_CAPTION_MAX} လုံးထက်ကျော်နေလို့ Profile ပုံမပါဘဲ "
                f"စာတစ်ခုတည်း ပို့ပါလိမ့်မယ်။ ပုံနဲ့တွဲချင်ရင် စာတိုလိုက်ပါ။</i>")
    await reply(event, f"{head('check', 'Welcome Text Saved')}\n\n<i>Preview:</i>\n{preview}{note}")

@command("resetwelcome", perm="admin")
async def resetwelcome_cmd(event, args):
    await set_setting(event.chat_id, welcome_text="")
    await reply(event, head("check", "Welcome text reset to default"))

# ---------- profile photo -> welcome message ----------
_last_welcome: dict[int, list[int]] = {}      # chat_id -> welcome message ids (only the latest batch is kept)
_photo_sem = asyncio.Semaphore(3)             # at most 3 profile downloads at once (raid protection)
_bot_photo: bytes | None = None

def _u16len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2

async def fetch_profile_photo(entity) -> bytes | None:
    """Download an entity's current profile photo (None when it has none / hides it)."""
    if entity is None:
        return None
    try:
        async with _photo_sem:
            data = await bot.download_profile_photo(entity, file=bytes, download_big=True)
        return data or None
    except Exception as e:
        print(f"⚠️ profile photo: {type(e).__name__}: {e}")
        return None

def welcome_kb(chat_id: int):
    return [
        [btn("Bot ကို Start နှိပ်ပါ", url=start_dm_url("welcome"), icon="fire", style="primary")],
        [btn("စည်းကမ်းများ", url=start_dm_url(f"rules_{chat_id}"), icon="rules"),
         btn("အကူအညီ", url=start_dm_url("help"), icon="info")],
    ]

async def send_photo_or_text(chat_id: int, text: str, kb, ent=None, photo: bytes | None = None):
    """Photo + caption when a photo exists and the caption fits, otherwise a normal text message."""
    if photo is None and ent is not None:
        photo = await fetch_profile_photo(ent)
    if photo and _u16len(_to_plain(text)) <= WELCOME_CAPTION_MAX:
        msg = await tg_send_photo(chat_id, photo, text, kb)
        if msg:
            return msg
    return await tg_send(chat_id, text, kb)

async def send_welcome(chat_id: int, uid: int, name: str, ent=None, *, is_bot: bool = False):
    """Welcome one member/bot with their profile photo. Returns the sent message id (or None)."""
    s = await get_settings(chat_id)
    if not s.get("welcome"):
        return None
    text = await render_welcome(chat_id, uid, name, ent=ent, is_bot=is_bot)
    msg = await send_photo_or_text(chat_id, text, welcome_kb(chat_id), ent=ent)
    return msg["message_id"] if msg else None


@command("addword", perm="admin")
async def addword_cmd(event, args):
    words = [w.strip() for w in re.split(r"[,\n]", args) if w.strip()]
    if not words:
        await notice(event, f"{head('pencil', 'Usage')}\n\n{code('/addword word1, word2')}")
        return
    s = await get_settings(event.chat_id)
    cur = list(s.get("words", []))
    for w in words:
        if w not in cur:
            cur.append(w)
    await set_setting(event.chat_id, words=cur[:300])
    await notice(event, f"{head('check', 'Words Added')}\n\n<b>Custom words:</b> {code(len(cur))}")

@command("delword", perm="admin")
async def delword_cmd(event, args):
    words = {w.strip() for w in re.split(r"[,\n]", args) if w.strip()}
    s = await get_settings(event.chat_id)
    cur = [w for w in s.get("words", []) if w not in words]
    await set_setting(event.chat_id, words=cur)
    await notice(event, f"{head('check', 'Words Removed')}\n\n<b>Custom words:</b> {code(len(cur))}")

@command("badwords", perm="admin")
async def badwords_cmd(event, args):
    s = await get_settings(event.chat_id)
    words = s.get("words", [])
    shown = ", ".join(esc(w) for w in words) if words else "—"
    await reply(event, (f"{head('warn', 'Bad-Word Filter')}\n\n<b>Status:</b> {'ON' if s['badwords'] else 'OFF'}\n"
                        f"<b>Built-in words:</b> {code(len(BADWORDS))}\n<b>Custom words:</b> <tg-spoiler>{shown}</tg-spoiler>"),
                ttl=60)


# ============================================================
# 🔍  AUTO-MODERATION  (per-group: links, media, bad words, flood, tracked bots)
# ============================================================
LINK_REGEX = re.compile(r"(?:https?://|ftp://|www\.|t\.me/|telegram\.me/|tg://)", re.IGNORECASE)

def _has_link(message) -> bool:
    if not message:
        return False
    text = message.text or message.message or ""
    if LINK_REGEX.search(text):
        return True
    try:
        for ent in (getattr(message, "entities", None) or []):
            if isinstance(ent, (MessageEntityUrl, MessageEntityTextUrl)):
                return True
    except Exception:
        pass
    return False

def _contains_badword(text: str, extra=()) -> str | None:
    if not text:
        return None
    masked = clean_invisible(text)
    for safe in _BADWORD_SAFE_SORTED:
        if safe in masked:
            masked = masked.replace(safe, "▢" * len(safe))
    for bw in list(BADWORDS) + list(extra):
        if bw and bw in masked:
            return bw
    return None

badword_tracker: dict[tuple, list] = {}
_flood: dict[tuple, deque] = defaultdict(deque)
tracked_cache: set[tuple[int, int]] = set()          # (chat_id, bot_or_user_id)

async def load_tracked():
    tracked_cache.clear()
    try:
        async for doc in tracked_bots_col.find({}):
            tracked_cache.add((doc["chat_id"], doc["bot_id"]))
    except Exception:
        pass

@bot.on(events.NewMessage(incoming=True, func=lambda e: e.is_group))
@safe_handler("moderation")
async def moderation_handler(event):
    await _moderate(event, edited=False)

@bot.on(events.MessageEdited(func=lambda e: e.is_group))
@safe_handler("moderation_edited")
async def moderation_edited_handler(event):
    await _moderate(event, edited=True)           # stops "post clean text, then edit in a link"

async def _moderate(event, edited: bool):
    chat_id, sender_id = event.chat_id, event.sender_id
    if sender_id is None:
        return
    my_id = await _ensure_me()
    if (chat_id, sender_id) in tracked_cache:
        try: await event.delete()
        except Exception: pass
        return
    if sender_id < 0 or sender_id == my_id:
        return                                              # channel posts / anonymous / myself
    s = await get_settings(chat_id)
    if not (s["antilink"] or s["antimedia"] or s["badwords"] or s["antiflood"]):
        return
    if await is_admin(chat_id, sender_id):
        return
    try:
        sender = await event.get_sender()
        if getattr(sender, "bot", False):
            return
    except Exception:
        pass
    if s["antiflood"] and not edited and await _check_flood(event):
        return
    if s["badwords"] and event.raw_text:
        await _check_badwords(event, s)
    if s["antilink"] or s["antimedia"]:
        await _check_media_link(event, s)

async def _check_flood(event) -> bool:
    chat_id, uid, now = event.chat_id, event.sender_id, _tm.time()
    dq = _flood[(chat_id, uid)]
    dq.append(now)
    while dq and now - dq[0] > FLOOD_WINDOW:
        dq.popleft()
    if len(dq) < FLOOD_MESSAGES:
        return False
    dq.clear()
    try:
        await do_mute(chat_id, uid, FLOOD_MUTE_SECONDS)
    except Exception:
        return False
    name = await get_user_name(uid)
    await tg_send(chat_id, (f"{head('bolt', 'Anti-Flood')}\n\n{make_mention(name, uid)} was muted for "
                            f"{code(fmt_secs(FLOOD_MUTE_SECONDS))} for sending messages too fast."),
                  [[btn("Unmute", f"mod:unmute:{uid}", icon="unmute", style="success")]])
    return True

async def _check_badwords(event, s):
    chat_id, sender_id = event.chat_id, event.sender_id
    if not _contains_badword(event.raw_text, s.get("words", [])):
        return
    name = await get_user_name(sender_id)
    mention = make_mention(name, sender_id)
    key, now = (chat_id, sender_id), _tm.time()
    history = [t for t in badword_tracker.get(key, []) if now - t < BADWORD_WINDOW_SECONDS]
    history.append(now)
    badword_tracker[key] = history
    if len(history) >= 2:
        try:
            await do_mute(chat_id, sender_id, BADWORD_MUTE_DURATION)
        except Exception as e:
            await tg_send(chat_id, f"{head('cross', 'Action Failed')}\n\n{code(str(e))}", reply_to=event.id, ttl=NOTICE_TTL)
            return
        expiry = datetime.fromtimestamp(now + BADWORD_MUTE_DURATION, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        await tg_send(chat_id,
            f"{head('mute', 'Language Restriction Activated')}\n\n"
            f"{mention} — your message contained prohibited language.\n\n"
            f"<b>Restriction:</b> Muted for 1 hour\n<b>Expires:</b> {code(expiry)}\n"
            f"<b>Reason:</b> Second violation within a 5-minute window\n\n"
            f"<i>Respect is the foundation of every healthy community.</i>",
            [[btn("Unmute", f"mod:unmute:{sender_id}", icon="unmute", style="success")]], reply_to=event.id)
        badword_tracker.pop(key, None)
        return
    await tg_send(chat_id,
        f"{head('warn', 'A Gentle Reminder')} {mention}\n\n"
        f"The message you just sent contains language that isn't welcome here.\n\n"
        f"Please be mindful — a second occurrence within the next <b>5 minutes</b> will result in a <b>1-hour mute</b>.\n\n"
        f"<i>Thank you for helping us keep this community welcoming.</i>",
        reply_to=event.id, ttl=60)

async def _check_media_link(event, s):
    msg, chat_id, sender_id = event.message, event.chat_id, event.sender_id
    if getattr(msg, "sticker", None) or getattr(msg, "gif", False):
        return
    try:
        if msg.document:
            for attr in (msg.document.attributes or []):
                if attr.__class__.__name__ == "DocumentAttributeAnimated":
                    return
    except Exception:
        pass
    via_bot = getattr(event, "via_bot_id", None) or getattr(msg, "via_bot_id", None)
    delete_media = bool(s["antimedia"] and (msg.photo or msg.video) and not via_bot)
    delete_link = bool(s["antilink"] and not via_bot and _has_link(msg))
    if not (delete_media or delete_link):
        return
    try:
        await event.delete()
    except Exception:
        pass
    if delete_link:
        name = await get_user_name(sender_id)
        await tg_send(chat_id,
            f"{head('cross', 'Link Sharing Restricted')}\n\n"
            f"{make_mention(name, sender_id)} — links are not permitted here for members. "
            f"Your message has been removed automatically.\n\n"
            f"<i>If this was an error, please contact an admin via /report.</i>", ttl=30)


# ============================================================
# 👋  CHAT ACTIONS  (member / bot joins, this bot added or removed)
# ============================================================
async def release_legacy_captchas():
    """Captcha was removed. Anyone still muted by an old pending verification gets freed once, then the queue is cleared."""
    try:
        docs = [d async for d in captcha_col.find({})]
    except Exception:
        return
    for d in docs:
        try:
            await do_unmute(d["chat_id"], d["user_id"])
        except Exception:
            pass
        if d.get("msg_id"):
            await tg_delete(d["chat_id"], d["msg_id"])
    if docs:
        try:
            await captcha_col.delete_many({})
        except Exception:
            pass
        print(f"🔓 Released {len(docs)} member(s) left over from the old captcha.")

async def _bot_profile_photo() -> bytes | None:
    global _bot_photo
    if _bot_photo is None:
        try:
            me = await bot.get_me()
        except Exception:
            return None
        _bot_photo = await fetch_profile_photo(me) or b""
    return _bot_photo or None

async def on_bot_added(event):
    """This bot was added to a group: intro message with the bot's own profile photo."""
    chat_id = event.chat_id
    await register_group(chat_id)
    title = await get_group_title(chat_id)
    text = (f"{pe('online')} <b>BOD Manager အသင့်ဖြစ်ပါပြီ!</b>\n\n"
            f"<b>{esc(title)}</b> ကို ကာကွယ်စောင့်ရှောက်ပေးဖို့ ရောက်ရှိလာပါပြီ။\n\n"
            f"{pe('ban')} Warn · Mute · Kick · Ban\n"
            f"{pe('alert')} Anti-Link · Anti-Media · Bad Words · Anti-Flood\n"
            f"{pe('online')} Profile ပုံနဲ့ Welcome  ·  {pe('afk')} Owner AFK Auto-Reply\n\n"
            f"{pe('pin')} <b>စတင်ရန်</b>\n"
            f"<b>၁.</b> Bot ကို <b>Admin</b> ပေးပါ (Ban Users · Delete Messages · Pin Messages)\n"
            f"<b>၂.</b> Admin တွေက {code('/settings')} ရိုက်ပြီး ခလုတ်တွေနဲ့ ရွေးပါ")
    kb = [[btn("Settings", "set:new", icon="gear", style="primary"),
           btn("အကူအညီ", url=start_dm_url("help"), icon="book")],
          [btn("Bot ကို Start နှိပ်ပါ", url=start_dm_url("welcome"), icon="fire")]]
    await send_photo_or_text(chat_id, text, kb, photo=await _bot_profile_photo())

@bot.on(events.ChatAction())
@safe_handler("chat_action")
async def chat_action_handler(event):
    my_id = await _ensure_me()
    uids = list(getattr(event, "user_ids", None) or ([event.user_id] if event.user_id else []))
    if my_id in uids and (event.user_added or event.user_joined):
        await on_bot_added(event)
        return
    if my_id in uids and (event.user_left or event.user_kicked):
        await set_setting(event.chat_id, active=False)
        return
    if not (event.user_joined or event.user_added) or not event.is_group:
        return
    s = await get_settings(event.chat_id)
    if not s["welcome"]:
        return
    targets = [u for u in uids if u != my_id][:WELCOME_MAX_PER_EVENT]
    if not targets:
        return
    users: dict[int, object] = {}
    try:
        for u in (await event.get_users() or []):
            users[u.id] = u
    except Exception:
        pass
    for mid in _last_welcome.pop(event.chat_id, []):        # keep the chat tidy: only the newest welcome stays
        await tg_delete(event.chat_id, mid)
    sent: list[int] = []
    for uid in targets:
        ent = users.get(uid)
        if ent is None:
            try:
                ent = await bot.get_entity(uid)
            except Exception:
                ent = None
        name = (_full_name(ent) if ent else "") or await get_user_name(uid)
        mid = await send_welcome(event.chat_id, uid, name, ent, is_bot=bool(getattr(ent, "bot", False)))
        if mid:
            sent.append(mid)
    if sent:
        _last_welcome[event.chat_id] = sent


# ============================================================
# 🚨  REPORT & REMINDER
# ============================================================
@command("report")
@trigger("report", perm="any")
async def report_cmd(event, args):
    is_slash = (event.raw_text or "").lstrip().startswith("/")
    if not event.is_reply:
        if is_slash:
            await notice(event,
                f"{head('alert', 'Report a Message')}\n\nTo report inappropriate content:\n\n"
                f"• <b>Step 1:</b> Reply directly to the offending message\n• <b>Step 2:</b> Send {code('/report')}\n\n"
                f"All group admins will receive an alert immediately.\n\n"
                f"<i>Note: Each member may report once every 3 hours.</i>")
        return
    replied = await event.get_reply_message()
    if not replied:
        await notice(event, head("warn", "Unable to locate the message you replied to"))
        return
    user_id, chat_id, now = event.sender_id, event.chat_id, _tm.time()
    doc = await report_cooldown_col.find_one({"chat_id": chat_id, "user_id": user_id})
    if doc and now - float(doc.get("last_report", 0)) < REPORT_COOLDOWN_SECONDS and user_id != OWNER_ID:
        remaining = int(REPORT_COOLDOWN_SECONDS - (now - float(doc.get("last_report", 0))))
        await notice(event,
            f"{head('clock', 'Report Cooldown Active')}\n\nTo prevent spam, each member may report once every 3 hours.\n\n"
            f"<b>Time remaining:</b> {code(fmt_secs(remaining))}")
        return
    try:
        await report_cooldown_col.update_one({"chat_id": chat_id, "user_id": user_id}, {"$set": {"last_report": now}}, upsert=True)
    except Exception:
        pass

    admins = [a for a in await get_admin_list(chat_id) if not a["bot"]][:ADMIN_PING_LIMIT]
    admin_mentions = " ".join(make_mention(a["name"], a["id"]) for a in admins) or "—"
    reporter_name = _full_name(await event.get_sender()) or "User"
    target_id = replied.sender_id
    target_name = await get_user_name(target_id) if target_id else "Unknown"
    target_mention = make_mention(target_name, target_id) if target_id else "Unknown"

    if chat_id == OFFICIAL_GROUP_ID:
        try: await bot.forward_messages(OWNER_ID, replied.id, chat_id)
        except Exception: pass

    kb = []
    if target_id and target_id > 0 and not await is_admin(chat_id, target_id):
        kb.append([btn("Mute", f"rep:mute:{target_id}", icon="mute", style="danger"),
                   btn("Delete message", f"rep:del:{replied.id}", icon="delete")])
    else:
        kb.append([btn("Delete message", f"rep:del:{replied.id}", icon="delete")])
    kb.append([btn("Resolved", "rep:ok", icon="check", style="success")])

    await tg_send(chat_id,
        f"{head('alert', 'Report Received')}\n\n<b>Reporter:</b> {make_mention(reporter_name, user_id)}\n"
        f"<b>Reported User:</b> {target_mention}\n<b>Message ID:</b> {code(replied.id)}\n\n"
        f"<b>Alerting Admins:</b>\n{admin_mentions}\n\n<i>Admins: use the buttons below.</i>",
        kb, reply_to=replied.id)
    await reply(event, (f"{head('check', 'Report Submitted')}\n\nThank you for helping keep our community safe. "
                        f"Admins have been notified.\n\n<b>Next available report:</b> in 3 hours"), ttl=30)

@callback("rep")
async def cb_rep(event, rest):
    chat_id = event.chat_id
    if not await is_admin(chat_id, event.sender_id):
        await deny(event)
        return
    action, _, val = rest.partition(":")
    admin_name = await get_user_name(event.sender_id)
    by = f"<i>by {make_mention(admin_name, event.sender_id)}</i>"
    if action == "mute":
        tid = int(val)
        if await is_admin(chat_id, tid):
            await deny(event, "Admins cannot be muted.")
            return
        name = await get_user_name(tid)
        ok, text = await mute_flow(chat_id, event.sender_id, tid, name)
        if not ok:
            await event.answer(_to_plain(text)[:190], alert=True)
            return
        await edit_append(event, f"{head('mute', 'Muted')} {make_mention(name, tid)} {by}",
                          [[btn("Unmute", f"mod:unmute:{tid}", icon="unmute", style="success")]])
    elif action == "del":
        await tg_delete(chat_id, int(val))
        await edit_append(event, f"{head('delete', 'Message deleted')} {by}",
                          [[btn("Resolved", "rep:ok", icon="check", style="success")]])
    elif action == "ok":
        await edit_append(event, f"{head('check', 'Resolved')} {by}")
    await event.answer("Done ✔")

_last_reminder: dict[int, float] = {}

async def _reminder_targets() -> set[int]:
    targets, explicit = set(), set()
    try:
        async for d in settings_col.find({"reminder": {"$exists": True}}):
            explicit.add(d["chat_id"])
            if d["reminder"] and d.get("active", True):
                targets.add(d["chat_id"])
    except Exception:
        pass
    if OFFICIAL_GROUP_ID not in explicit:
        targets.add(OFFICIAL_GROUP_ID)
    return targets

async def background_loop():
    """Every minute: send due /report reminders and prune in-memory trackers."""
    await asyncio.sleep(60)
    while True:
        now = _tm.time()
        try:
            for chat_id in await _reminder_targets():
                last = _last_reminder.setdefault(chat_id, now)
                if now - last >= REPORT_REMINDER_SECONDS:
                    _last_reminder[chat_id] = now
                    await tg_send(chat_id,
                        f"{head('alert', 'Community Safety Reminder')}\n\n"
                        f"If you see content that violates our community guidelines — spam, inappropriate language, "
                        f"or anything that feels off — please report it:\n\n"
                        f"<b>1.</b> Reply to the offending message\n<b>2.</b> Send {code('/report')}\n\n"
                        f"All admins will be alerted immediately.\n\n<i>Each member may submit one report every 3 hours.</i>")
            for k in [k for k, dq in _flood.items() if not dq or now - dq[-1] > 60]:
                _flood.pop(k, None)
            for k in [k for k, v in badword_tracker.items() if not v or now - v[-1] > BADWORD_WINDOW_SECONDS]:
                badword_tracker.pop(k, None)
            for k in [k for k, v in afk_cooldown.items() if now - v > AFK_REPLY_COOLDOWN]:
                afk_cooldown.pop(k, None)
        except Exception as e:
            print(f"❌ [background_loop] {type(e).__name__}: {e}")
        await asyncio.sleep(60)


# ============================================================
# 📴  AFK  (every group's owner  +  the bot owner)
# ============================================================
# A group's Owner = the creator of that group. When someone @mentions / replies to an owner who
# switched AFK on, the bot answers for them. The bot owner (Morgan) keeps working in every group.
afk_users: dict[int, dict] = {}             # user_id -> {"since": datetime, "reason": str}
afk_cooldown: dict[tuple, float] = {}       # (chat_id, sender_id, owner_id) -> last auto-reply time
_reply_author: dict[tuple, int | None] = {} # (chat_id, replied_msg_id) -> author id (saves API calls)

async def load_afk():
    afk_users.clear()
    try:
        async for d in afk_col.find({"enabled": True}):
            afk_users[d["user_id"]] = {"since": d.get("since") or datetime.now(timezone.utc),
                                       "reason": d.get("reason", "")}
    except Exception:
        pass

async def set_afk(uid: int, enabled: bool, reason: str = ""):
    if enabled:
        info = {"since": datetime.now(timezone.utc), "reason": reason}
        afk_users[uid] = info
        await afk_col.update_one({"user_id": uid}, {"$set": {"enabled": True, **info}}, upsert=True)
    else:
        afk_users.pop(uid, None)
        await afk_col.update_one({"user_id": uid}, {"$set": {"enabled": False}}, upsert=True)
    for k in [k for k in afk_cooldown if k[2] == uid]:
        afk_cooldown.pop(k, None)

def _mentions_in(message) -> tuple[set, set]:
    """(lower-case @usernames, user ids) mentioned in a message. Offsets are handled by Telethon (UTF-16 safe)."""
    names, ids = set(), set()
    try:
        for ent, txt in message.get_entities_text():
            kind = type(ent).__name__
            if kind == "MessageEntityMention":
                names.add(txt.lstrip("@").lower())
            elif kind == "MessageEntityMentionName":
                ids.add(ent.user_id)
    except Exception:
        pass
    raw = message.message or ""
    names.update(n.lower() for n in re.findall(r"@([A-Za-z0-9_]{4,32})", raw))
    return names, ids

async def _reply_author_id(event) -> int | None:
    rid = event.message.reply_to.reply_to_msg_id
    key = (event.chat_id, rid)
    if key in _reply_author:
        return _reply_author[key]
    uid = None
    try:
        r = await event.get_reply_message()
        uid = r.sender_id if r else None
    except Exception:
        pass
    if len(_reply_author) > 2000:
        _reply_author.clear()
    _reply_author[key] = uid
    return uid

def _is_real_reply(message) -> bool:
    rt = getattr(message, "reply_to", None)
    if not rt or not getattr(rt, "reply_to_msg_id", None):
        return False
    # in forum groups every topic message "replies" to the topic root - that is not a real reply
    if getattr(rt, "forum_topic", False) and not getattr(rt, "reply_to_top_id", None):
        return False
    return True

def afk_reply_text(label: str, info: dict) -> str:
    since = info.get("since") or datetime.now(timezone.utc)
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    elapsed = max(0, int((datetime.now(timezone.utc) - since).total_seconds()))
    text = (f"{head('afk', 'AFK Auto-Reply')}\n\n"
            f"{esc(AFK_EN_MSG.format(name=label))}\n\n{esc(AFK_MM_MSG.format(name=label))}\n\n")
    if info.get("reason"):
        text += f"{pe('info')} <b>အကြောင်းပြချက်:</b> {esc(info['reason'])}\n"
    text += f"{pe('clock')} <b>AFK ဖြစ်နေတာ:</b> {code(fmt_secs(elapsed))} ရှိပါပြီ"
    return text

@bot.on(events.NewMessage(incoming=True, func=lambda e: e.is_group))
@safe_handler("afk_mention")
async def afk_mention_handler(event):
    if not afk_users:
        return
    sender_id = event.sender_id
    my_id = await _ensure_me()
    if sender_id is None or sender_id == my_id:
        return
    msg, chat_id = event.message, event.chat_id
    names, ids = _mentions_in(msg)
    replied = _is_real_reply(msg)
    if not (names or ids or replied):
        return
    # who counts as "the owner" here: the bot owner (everywhere) + this group's creator
    cands: dict[int, dict] = {}
    if OWNER_ID in afk_users:
        cands[OWNER_ID] = {"name": OWNER_DISPLAY_NAME, "usernames": {OWNER_USERNAME.lower()}}
    if any(u != OWNER_ID for u in afk_users):
        go = await get_group_owner(chat_id)
        if go and go["id"] in afk_users:
            c = cands.setdefault(go["id"], {"name": go["name"], "usernames": set()})
            c["usernames"].update(go.get("usernames") or [])
    cands.pop(sender_id, None)                        # owners never get an AFK reply for talking about themselves
    if not cands:
        return
    reply_uid = await _reply_author_id(event) if replied else None
    hit = next((uid for uid, c in cands.items()
                if uid in ids or uid == reply_uid or (names & c["usernames"])), None)
    if hit is None:
        return
    now, key = _tm.time(), (chat_id, sender_id, hit)
    if now - afk_cooldown.get(key, 0) < AFK_REPLY_COOLDOWN:
        return
    afk_cooldown[key] = now
    await tg_send(chat_id, afk_reply_text(f"Owner {cands[hit]['name']}", afk_users[hit]), reply_to=event.id)

async def _afk_can_toggle(event) -> bool:
    """Bot owner anywhere; in groups only the group's creator; in DM anyone (it only matters where they own a group)."""
    if event.sender_id == OWNER_ID or event.is_private:
        return True
    go = await get_group_owner(event.chat_id)
    return bool(go and go["id"] == event.sender_id)

async def _afk_do(event, action: str, reason: str = ""):
    is_slash = (event.raw_text or "").lstrip().startswith("/")
    if not await _afk_can_toggle(event):
        if is_slash:                                   # plain-text "afk" from a normal member stays silent
            await notice(event, f"{head('lock', 'Owner Only')}\n\nGroup Owner ကိုယ်တိုင်သာ AFK ကို ဖွင့်/ပိတ်လို့ရပါတယ်။")
        return
    uid = event.sender_id
    sender = await event.get_sender()
    label = OWNER_DISPLAY_NAME if uid == OWNER_ID else (_full_name(sender) or "Owner")
    if action == "on":
        reason = reason.strip()[:200]
        await set_afk(uid, True, reason)
        why = f"{pe('info')} <b>အကြောင်းပြချက်:</b> {esc(reason)}\n" if reason else ""
        await reply(event, (f"{head('afk', 'AFK Mode ဖွင့်လိုက်ပါပြီ')}\n\n"
                            f"{pe('check')} <b>{esc(label)}</b> ကို Mention / Reply လုပ်သူတွေကို AFK စာ အလိုအလျောက်ပြန်ပေးပါမယ်။\n"
                            f"{why}"
                            f"{pe('clock')} <b>Cooldown:</b> တစ်ယောက်ကို စက္ကန့် {AFK_REPLY_COOLDOWN} တစ်ခါ\n\n"
                            f"<i>ပြန်လာပြီဆိုရင် {code('afk off')} လို့ ရိုက်ပါ။</i>"))
    elif action == "off":
        await set_afk(uid, False)
        await reply(event, (f"{head('online', 'AFK Mode ပိတ်လိုက်ပါပြီ')}\n\n"
                            f"Online ပြန်ရောက်လာတာ ကြိုဆိုပါတယ်။ AFK Auto-Reply တွေ ရပ်သွားပါပြီ။"))
    else:
        info = afk_users.get(uid)
        status = f"{pe('afk')} Active" if info else f"{pe('online')} Inactive"
        since = ""
        if info:
            s0 = info["since"] if info["since"].tzinfo else info["since"].replace(tzinfo=timezone.utc)
            since = f"\n<b>စတင်ချိန်:</b> {code(s0.strftime('%Y-%m-%d %H:%M UTC'))}"
            if info.get("reason"):
                since += f"\n<b>အကြောင်းပြချက်:</b> {esc(info['reason'])}"
        await reply(event, f"{head('stats', 'AFK Status')}\n\n<b>လက်ရှိအခြေအနေ:</b> {status}{since}")

@command("afk", scope="any", perm="any")
async def afk_cmd(event, args):
    parts = args.strip().split(None, 1)
    word = parts[0].lower() if parts else ""
    if word == "on":
        await _afk_do(event, "on", parts[1] if len(parts) > 1 else "")
    elif word == "off":
        await _afk_do(event, "off")
    else:
        await _afk_do(event, "status")

@trigger("afk on", perm="any", scope="any")
async def afk_on(event, args):
    await _afk_do(event, "on")

@trigger("afk off", perm="any", scope="any")
async def afk_off(event, args):
    await _afk_do(event, "off")

@trigger("afk", perm="any", scope="any")
async def afk_status(event, args):
    await _afk_do(event, "status")


# ============================================================
# 👑  OWNER COMMANDS
# ============================================================
@trigger(*TRG_LOCK, perm="owner")
async def lock_chat(event, args):
    try:
        await bot(EditChatDefaultBannedRightsRequest(event.chat_id, rights_mute()))
        await reply(event, f"{head('lock', 'Group Locked')}\n\nOnly admins can send messages now.",
                    [[btn("Unlock", "own:unlock", icon="unlock", style="success")]])
    except Exception as e:
        await notice(event, perm_error(e))

@trigger(*TRG_UNLOCK, perm="owner")
async def unlock_chat(event, args):
    try:
        await bot(EditChatDefaultBannedRightsRequest(event.chat_id, ChatBannedRights(until_date=0)))
        await reply(event, f"{head('unlock', 'Group Unlocked')}\n\nAll members can send again.")
    except Exception as e:
        await notice(event, perm_error(e))

@callback("own")
async def cb_owner(event, rest):
    if event.sender_id != OWNER_ID:
        await deny(event, "Owner only.")
        return
    if rest == "unlock":
        try:
            await bot(EditChatDefaultBannedRightsRequest(event.chat_id, ChatBannedRights(until_date=0)))
            await edit_append(event, head("unlock", "Group Unlocked"))
        except Exception as e:
            await event.answer(str(e)[:150], alert=True)
            return
    await event.answer("Done ✔")

@trigger("adm", perm="owner")
async def adm_cmd(event, args):
    tid, _ = await target_and_rest(event)
    if tid is None or tid < 0:
        return
    try:
        await bot(EditAdminRequest(event.chat_id, tid, ChatAdminRights(
            change_info=False, post_messages=False, edit_messages=False, delete_messages=True, ban_users=False,
            invite_users=True, pin_messages=True, add_admins=False, anonymous=False, manage_call=False,
            other=False, manage_topics=False), rank="Moderator"))
        _admin_cache.pop(event.chat_id, None)
        name = await get_user_name(tid)
        await reply(event, (f"{head('shield', 'Moderator Granted')}\n\n<b>Member:</b> {make_mention(name, tid)}\n\n"
                            f"{pe('check')} Delete · Invite · Pin\n{pe('ban')} Ban · Change info · Add admins"))
    except Exception as e:
        await notice(event, perm_error(e))

async def _send_info(event, tid: int):
    try:
        u = await bot.get_entity(tid)
    except Exception:
        u = None
    name = (_full_name(u) if u else "") or str(tid)
    uname = f"@{u.username}" if u and getattr(u, "username", None) else "—"
    kind = "Bot" if u and getattr(u, "bot", False) else "User"
    prem = "Yes" if u and getattr(u, "premium", False) else "No"
    lines = [f"{head('info', 'User Info')}\n", f"<b>Name:</b> {make_mention(name, tid)}", f"<b>ID:</b> {code(tid)}",
             f"<b>Username:</b> {code(uname)}", f"<b>Type:</b> {kind}", f"<b>Premium:</b> {prem}"]
    if event.is_group:
        lines.append(f"<b>Admin here:</b> {'Yes' if await is_admin(event.chat_id, tid) else 'No'}")
        doc = await warns_col.find_one({"chat_id": event.chat_id, "user_id": tid})
        lines.append(f"<b>Warnings:</b> {code(doc['count'] if doc else 0)}")
    await reply(event, "\n".join(lines))

@trigger("?", perm="owner")
async def info_trigger(event, args):
    if event.is_reply:
        r = await event.get_reply_message()
        if r and r.sender_id:
            await _send_info(event, r.sender_id)

@command("info", scope="any", perm="any")
async def info_cmd(event, args):
    tid, _ = await target_and_rest(event)
    await _send_info(event, tid if tid and tid > 0 else event.sender_id)

@command("del", perm="owner")
@trigger(TRG_TRACK, perm="owner")
async def del_track_cmd(event, args):
    if not event.is_reply:
        await notice(event, (f"{head('delete', 'Bot Tracking System')}\n\nReply directly to a bot's message with "
                             f"{code('/del')} or {code(TRG_TRACK)}."))
        return
    r = await event.get_reply_message()
    if not r or not r.sender_id:
        await notice(event, head("warn", "Unable to identify the message sender"))
        return
    tid = r.sender_id
    try: sender = await bot.get_entity(tid)
    except Exception: sender = None
    is_bot = bool(sender and getattr(sender, "bot", False))
    username = getattr(sender, "username", None) if sender else None
    display = _full_name(sender) if sender else str(tid)
    try:
        await tracked_bots_col.update_one(
            {"bot_id": tid, "chat_id": event.chat_id},
            {"$set": {"bot_id": tid, "chat_id": event.chat_id, "username": username, "display_name": display,
                      "is_bot": is_bot, "added_by": event.sender_id, "added_at": datetime.now(timezone.utc)}}, upsert=True)
        tracked_cache.add((event.chat_id, tid))
    except Exception as e:
        await notice(event, f"{head('warn', 'Failed to save')}\n\n{code(e)}")
        return
    try: await r.delete()
    except Exception: pass
    uname = f" ({code('@' + username)})" if username else ""
    await reply(event, (f"{head('check', 'Auto-Delete Activated')}\n\n<b>Type:</b> {'Bot' if is_bot else 'User'}\n"
                        f"<b>Name:</b> {make_mention(display, tid)}{uname}\n<b>ID:</b> {code(tid)}"),
                [[btn("Stop tracking", f"trk:{tid}", icon="cross", style="danger")]])

@command("untrack", perm="owner")
async def untrack_cmd(event, args):
    if not args or not args.split()[0].isdigit():
        await notice(event, f"{head('warn', 'Usage')}\n\n{code('/untrack [id]')}")
        return
    tid = int(args.split()[0])
    res = await tracked_bots_col.delete_one({"bot_id": tid, "chat_id": event.chat_id})
    tracked_cache.discard((event.chat_id, tid))
    await reply(event, f"{head('check', 'Deactivated')}\n\nEntity {code(tid)} removed." if res.deleted_count else head("info", "Not Found"))

@callback("trk")
async def cb_track(event, rest):
    if event.sender_id != OWNER_ID:
        await deny(event, "Owner only.")
        return
    try:
        tid = int(rest)
    except ValueError:
        await event.answer()
        return
    await tracked_bots_col.delete_one({"bot_id": tid, "chat_id": event.chat_id})
    tracked_cache.discard((event.chat_id, tid))
    await edit_append(event, head("check", "Tracking stopped"))
    await event.answer("Done ✔")

@command("groups", scope="any", perm="owner")
async def groups_cmd(event, args):
    rows = []
    try:
        async for d in settings_col.find({"title": {"$exists": True}, "active": {"$ne": False}}):
            rows.append(d)
    except Exception:
        pass
    lines = [f"{head('globe', 'Groups using BOD Manager')}\n", f"<b>Total:</b> {code(len(rows))}\n"]
    for i, d in enumerate(rows[:40], 1):
        lines.append(f"{i}. {esc(str(d.get('title', '?')))} — {code(d['chat_id'])}")
    if len(rows) > 40:
        lines.append(f"… and {len(rows) - 40} more")
    await reply(event, "\n".join(lines))


# ============================================================
# ✨  PREMIUM EMOJI TOOLS  (owner)
# ============================================================
def _custom_emojis(message) -> list[tuple[int, str]]:
    try:
        return [(ent.document_id, txt) for ent, txt in message.get_entities_text(MessageEntityCustomEmoji)]
    except Exception:
        return []

async def load_emoji_overrides():
    try:
        async for d in emoji_col.find({}):
            if d.get("key") in PREMIUM_EMOJI and d.get("id"):
                PREMIUM_EMOJI[d["key"]] = int(d["id"])
    except Exception:
        pass

@command("emojiid", scope="any", perm="owner")
async def emojiid_cmd(event, args):
    found = _custom_emojis(event.message)
    if event.is_reply:
        r = await event.get_reply_message()
        if r:
            found += _custom_emojis(r)
    if not found:
        await reply(event, (f"{head('sparkle', 'Premium Emoji IDs')}\n\nSend {code('/emojiid')} together with premium emoji "
                            f"(or reply to a message that has them) and I'll show their IDs."))
        return
    lines = [f"{head('sparkle', 'Premium Emoji IDs')}\n"]
    for pid, ch in found[:30]:
        lines.append(f'<tg-emoji emoji-id="{pid}">{esc(ch) or "▫️"}</tg-emoji>  {code(pid)}')
    await reply(event, "\n".join(lines))

@command("setemoji", scope="any", perm="owner")
async def setemoji_cmd(event, args):
    keys = re.findall(r"[A-Za-z_]+", args)
    emojis = _custom_emojis(event.message)
    if event.is_reply and not emojis:
        r = await event.get_reply_message()
        emojis = _custom_emojis(r) if r else []
    if not keys:
        await reply(event, (f"{head('sparkle', 'Set Premium Emoji')}\n\n"
                            f"{code('/setemoji crown 👑 shield 🛡')} — use <b>premium</b> emoji, keys and emoji in the same order.\n"
                            f"Or reply to a premium emoji with {code('/setemoji crown')}.\n\n"
                            f"See all keys with {code('/emojis')}."))
        return
    bad = [k for k in keys if k not in EMOJI_FALLBACK]
    if bad:
        await reply(event, f"{head('warn', 'Unknown key')}\n\n{code(', '.join(bad))}\nUse {code('/emojis')} to list valid keys.")
        return
    if len(keys) != len(emojis):
        await reply(event, (f"{head('warn', 'Mismatch')}\n\nYou gave {code(len(keys))} key(s) but {code(len(emojis))} premium emoji. "
                            f"They must match one-to-one."))
        return
    done = []
    for k, (pid, _ch) in zip(keys, emojis):
        PREMIUM_EMOJI[k] = pid
        await emoji_col.update_one({"key": k}, {"$set": {"key": k, "id": pid}}, upsert=True)
        done.append(f'{code(k)} → <tg-emoji emoji-id="{pid}">{EMOJI_FALLBACK[k]}</tg-emoji>')
    await reply(event, f"{head('check', 'Premium Emoji Saved')}\n\n" + "\n".join(done))

@command("resetemoji", scope="any", perm="owner")
async def resetemoji_cmd(event, args):
    keys = [k for k in re.findall(r"[A-Za-z_]+", args) if k in EMOJI_FALLBACK]
    if not keys:
        await reply(event, f"{head('warn', 'Usage')}\n\n{code('/resetemoji crown shield')}")
        return
    for k in keys:
        PREMIUM_EMOJI[k] = BUILTIN_EMOJI.get(k)
        await emoji_col.delete_one({"key": k})
    await reply(event, f"{head('check', 'Reset')}\n\n{code(', '.join(keys))}")

@command("emojis", scope="any", perm="owner")
async def emojis_cmd(event, args):
    have = [k for k in EMOJI_FALLBACK if PREMIUM_EMOJI.get(k)]
    miss = [k for k in EMOJI_FALLBACK if not PREMIUM_EMOJI.get(k)]
    coverage = f"{len(have)}/{len(EMOJI_FALLBACK)}"
    text = (f"{head('sparkle', 'Premium Emoji Coverage')}\n\n<b>Set:</b> {code(coverage)}\n\n"
            f"{pe('check')} <b>Have:</b>\n" + " ".join(f"{pe(k)}{code(k)}" for k in have) +
            f"\n\n{pe('cross')} <b>Missing</b> (showing the normal emoji until you set them):\n" +
            " ".join(f"{EMOJI_FALLBACK[k]}{code(k)}" for k in miss) +
            f"\n\n<i>Add one with {code('/setemoji key')} + a premium emoji.</i>")
    await reply(event, text)


# ============================================================
# 📊  STATS / ID / MUTE COUNT
# ============================================================
@command("stats", perm="admin")
async def stats_cmd(event, args):
    title = await get_group_title(event.chat_id)
    admins = [a for a in await get_admin_list(event.chat_id) if not a["bot"]]
    count = await get_member_count(event.chat_id)
    s = await get_settings(event.chat_id)
    def st(k): return pe("on") if s.get(k) else pe("off")
    go = await get_group_owner(event.chat_id)
    afk = f"{pe('afk')} Active" if (go and go["id"] in afk_users) else f"{pe('online')} Inactive"
    await reply(event, (f"{head('stats', 'Group Statistics')}\n\n<b>Group:</b> {code(title)}\n<b>ID:</b> {code(event.chat_id)}\n"
                        f"<b>Members:</b> {code(count if count is not None else '—')}\n<b>Admins:</b> {code(len(admins))}\n"
                        f"<b>Owner AFK:</b> {afk}\n\n"
                        f"{st('antilink')} Anti-Link   {st('antimedia')} Anti-Media   {st('badwords')} Bad Words\n"
                        f"{st('antiflood')} Anti-Flood   {st('welcome')} Welcome   {st('reminder')} Reminder"),
                [[btn("Settings", "set:open", icon="gear")]])

@command("id", scope="any")
async def id_cmd(event, args):
    if event.is_reply:
        r = await event.get_reply_message()
        if r and r.sender_id:
            name = await get_user_name(r.sender_id)
            await reply(event, (f"{head('id', 'User ID')}\n\n<b>Name:</b> {make_mention(name, r.sender_id)}\n"
                                f"<b>ID:</b> {code(r.sender_id)}\n<b>Msg ID:</b> {code(r.id)}"))
            return
    name = _full_name(await event.get_sender()) or "User"
    await reply(event, (f"{head('id', 'Chat Identification')}\n\n<b>You:</b> {make_mention(name, event.sender_id)}\n"
                        f"<b>Your ID:</b> {code(event.sender_id)}\n<b>Chat ID:</b> {code(event.chat_id)}"))

@command("mutecount", perm="admin")
async def mutecount_cmd(event, args):
    used = await get_mute_count(event.sender_id, event.chat_id)
    remaining = max(0, MUTE_DAILY_LIMIT - used)
    bar = "🟩" * min(used, MUTE_DAILY_LIMIT) + "⬜" * (MUTE_DAILY_LIMIT - min(used, MUTE_DAILY_LIMIT))
    await reply(event, (f"{head('stats', 'Your Mute Quota Today')}\n\n{bar}\n\n<b>Used:</b> {code(used)} / {code(MUTE_DAILY_LIMIT)}\n"
                        f"<b>Remaining:</b> {code(remaining)}\n<b>Resets:</b> UTC 00:00"), ttl=60)


# ============================================================
# 🌍  HEALTH CHECK & STARTUP
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

async def startup():
    print("⏳ BOD Manager starting...")
    spawn(start_health_server())
    try:
        await bot.start(bot_token=BOT_TOKEN)
        me = await _ensure_me()
        print(f"🤖 Bot connected: @{_my_username} (id={me})")
    except Exception as e:
        print(f"❌ Bot start failed: {e}")
        return

    await load_emoji_overrides()
    await load_tracked()
    await release_legacy_captchas()
    await load_afk()
    spawn(background_loop())

    have = sum(1 for k in EMOJI_FALLBACK if PREMIUM_EMOJI.get(k))
    coverage = f"{have}/{len(EMOJI_FALLBACK)}"
    try:
        n_groups = await settings_col.count_documents({"title": {"$exists": True}, "active": {"$ne": False}})
    except Exception:
        n_groups = 0
    await tg_send(OWNER_ID,
        f"{head('online', 'BOD Manager Online')}\n\nAll systems operational.\n\n"
        f"<b>Groups:</b> {code(n_groups)}\n<b>Premium emoji set:</b> {code(coverage)}\n"
        f"<b>Tracked bots:</b> {code(len(tracked_cache))}")
    print("🚀 Ready.")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    if _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    try:
        _loop.run_until_complete(startup())
    except KeyboardInterrupt:
        pass
    finally:
        try:
            _loop.close()
        except Exception:
            pass
