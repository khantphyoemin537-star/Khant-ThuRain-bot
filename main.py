import re
import asyncio
import sqlite3
from telegram import ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ChatMemberHandler, 
    MessageHandler, filters, ContextTypes
)

# --- CONFIGURATION ---
TOKENS = [
    "8575371720:AAE8kNulIQw27ocepXFO16aVP2Mga9mJEjg",
    "8698177279:AAEVFPPMfkm-m7aiWRsIo_n-pK0vOvmZegg"
]

# --- DATABASE SETUP ---
def init_db():
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings 
            (chat_id TEXT PRIMARY KEY, welcome TEXT, goodbye TEXT, rules TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS filters 
            (chat_id TEXT, keyword TEXT, reply TEXT, PRIMARY KEY (chat_id, keyword))''')
        conn.commit()

def get_setting(chat_id, key, default):
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {key} FROM settings WHERE chat_id = ?", (str(chat_id),))
        res = cursor.fetchone()
        return res[0] if res and res[0] else default

def update_setting(chat_id, key, value):
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO settings (chat_id, {key}) VALUES (?, ?) ON CONFLICT(chat_id) DO UPDATE SET {key}=?", 
                       (str(chat_id), value, value))
        conn.commit()

# --- ADMIN UTILS ---
async def is_user_admin(update, context):
    if not update.effective_chat or update.effective_chat.type == "private": return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return member.status in ["administrator", "creator"]
    except: return False

# --- COMMAND HANDLERS ---
async def set_welcome(update, context):
    if not await is_user_admin(update, context): return
    text = " ".join(context.args)
    if text:
        update_setting(update.effective_chat.id, "welcome", text)
        await update.message.reply_text("<blockquote>✅ Welcome message updated!</blockquote>", parse_mode=ParseMode.HTML)

async def set_goodbye(update, context):
    if not await is_user_admin(update, context): return
    text = " ".join(context.args)
    if text:
        update_setting(update.effective_chat.id, "goodbye", text)
        await update.message.reply_text("<blockquote>✅ Goodbye message updated!</blockquote>", parse_mode=ParseMode.HTML)

async def filter_ktr(update, context):
    if not await is_user_admin(update, context): return
    if len(context.args) < 2:
        await update.message.reply_text("<blockquote>💡 Usage: /filterktr hi မင်္ဂလာပါ</blockquote>", parse_mode=ParseMode.HTML)
        return
    keyword, reply = context.args[0].lower(), " ".join(context.args[1:])
    with sqlite3.connect("bot_database.db") as conn:
        conn.execute("INSERT OR REPLACE INTO filters VALUES (?, ?, ?)", (str(update.effective_chat.id), keyword, reply))
        conn.commit()
    await update.message.reply_text(f"<blockquote>✅ Filter saved: {keyword}</blockquote>", parse_mode=ParseMode.HTML)

# --- EVENT HANDLERS ---
async def member_handler(update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    chat = result.chat
    
    if result.new_chat_member.status in ["member", "administrator"] and result.old_chat_member.status in ["left", "kicked", "none"]:
        template = get_setting(chat.id, "welcome", "ဟိတ် {name} {group} မှ ကြိုဆိုပါတယ်!")
        mention = f'<a href="tg://user?id={result.new_chat_member.user.id}">{result.new_chat_member.user.first_name}</a>'
        await context.bot.send_message(chat.id, f"<blockquote>{template.format(name=mention, group=chat.title)}</blockquote>", parse_mode=ParseMode.HTML)
    
    elif result.new_chat_member.status in ["left", "kicked"]:
        template = get_setting(chat.id, "goodbye", "{name} {group} ကနေထွက်သွားပါပြီ")
        mention = f'<a href="tg://user?id={result.old_chat_member.user.id}">{result.old_chat_member.user.first_name}</a>'
        await context.bot.send_message(chat.id, f"<blockquote>{template.format(name=mention, group=chat.title)}</blockquote>", parse_mode=ParseMode.HTML)

async def handle_msg(update, context):
    if not update.message or not update.message.text: return
    chat_id = str(update.effective_chat.id)
    raw_text = update.message.text
    lower_text = raw_text.lower()

    # 1. Anti-Link
    if re.search(r"(https?://|t\.me|www\.)", lower_text) and not await is_user_admin(update, context):
        try:
            await update.message.delete()
            return
        except: pass

    # 2. Database Filters (Exact or Word Match)
    with sqlite3.connect("bot_database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT keyword, reply FROM filters WHERE chat_id = ?", (chat_id,))
        all_filters = cursor.fetchall()
        
        for kw, rep in all_filters:
            # Word boundary သုံးပြီး စစ်တာက ပိုတိကျပါတယ် (ဥပမာ "hi" ဆိုမှ ပြန်မယ်၊ "high" ထဲက hi ကို မယူဘူး)
            if re.search(rf"\b{re.escape(kw)}\b", lower_text):
                await update.message.reply_text(f"<blockquote>{rep}</blockquote>", parse_mode=ParseMode.HTML)
                break

async def ban(update, context):
    if await is_user_admin(update, context) and update.message.reply_to_message:
        try:
            user = update.message.reply_to_message.from_user
            await context.bot.ban_chat_member(update.effective_chat.id, user.id)
            await update.message.reply_text(f"<blockquote>🚫 <b>{user.first_name}</b> Banned!</blockquote>", parse_mode=ParseMode.HTML)
        except: pass

async def mute(update, context):
    if await is_user_admin(update, context) and update.message.reply_to_message:
        try:
            user = update.message.reply_to_message.from_user
            await context.bot.restrict_chat_member(update.effective_chat.id, user.id, ChatPermissions(can_send_messages=False))
            await update.message.reply_text(f"<blockquote>🔇 <b>{user.first_name}</b> Muted!</blockquote>", parse_mode=ParseMode.HTML)
        except: pass

# --- BOT RUNNER ---
async def run_bot(token):
    app = ApplicationBuilder().token(token).build()
    
    app.add_handler(CommandHandler("setwelcome", set_welcome))
    app.add_handler(CommandHandler("setgoodbye", set_goodbye))
    app.add_handler(CommandHandler("filterktr", filter_ktr))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(ChatMemberHandler(member_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))

    print(f"Bot Online: {token[:10]}...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=["message", "chat_member"])
    while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    init_db()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*(run_bot(token) for token in TOKENS)))
