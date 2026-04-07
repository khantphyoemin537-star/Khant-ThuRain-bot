import asyncio
import logging
import random
import os
import threading
from flask import Flask
from pymongo import MongoClient

# Libraries
from telegram import Update, ChatMember, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes
)
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- FLASK KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "BoD Premium Bot is Active!"
def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION ---
TOKEN = os.environ.get("BOT_TOKEN", "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU")
OWNER_ID = 6015356597
ADMIN_GROUP_ID = -1003580630981
SAVE_CHAT_ID = -1003580630981
ADMIN_CHAT_MENTION = "@Besties_with_BoD"
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0")

# Telethon Config
APP_ID = 30765851
APP_HASH = '235b0bc6f03767302dc75763508f7b75'
SESSION_STRING = os.environ.get("SESSION_STRING", "1BVtsOKEBu8OA71fVy10wv1z1Z9ZcH34wjlY6tfWbHgtwpEFv_n1kMtMAiPSrqbpBJYqtwXx6NgeEHuyHnsPtK1xO4tafvqCxF3x3qvH_WErij_TtNmA0P9F2Jb21DwIzUM48e2hugakBdxnXoR24M0HFKG19b2MQHhBdZZMpp354h9K-YPUPwWHsELu0rtGOqep48GxcJ9Gkp_noBSeRcRO-i2pe7vg6ak4g_f7hsBoOfeHwkpyG-sbXY1CfyDmBYTbDKEEv9sGZYfwTb8Kx7KBivgchV0_fu0W3u30eD-fHUfSynZK3uCapqyKLXmIK6AtDPj6vCXvLHUHrXWsLe0IkP8urBbE=") # GitHub မှာ run ရင် variables ထဲ ဒါကိုထည့်ပါ

client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]

# Tasks Storage
bully_tasks = {}
kill_tasks = {}

# User Client Setup
user_client = TelegramClient(StringSession(SESSION_STRING), APP_ID, APP_HASH)

# --- HELPERS ---
def bot_style(text):
    return f"<blockquote><b>{text}</b></blockquote>"

def is_allowed_user(uid):
    if uid == OWNER_ID: return True
    return db.allow_users.find_one({"user_id": uid}) is not None

async def is_real_admin(chat, user_id):
    if user_id == OWNER_ID: return True
    try:
        member = await chat.get_member(user_id)
        return member.status in [ChatMember.OWNER, ChatMember.ADMINISTRATOR]
    except: return False

# --- BULLY & KILL LOGIC ---
async def kill_logic(chat_id, reply_to_id):
    """User account ကနေ blockquote နဲ့ အမြန်ဆုံး bully မယ့် loop"""
    while kill_tasks.get(chat_id):
        try:
            words = [w.get("text") for w in list(db.filters.find()) if w.get("text")]
            if not words: break
            word = random.choice(words)
            await user_client.send_message(chat_id, f"<blockquote><b>{word}</b></blockquote>", reply_to=reply_to_id, parse_mode='html')
            await asyncio.sleep(0.15)
        except Exception as e:
            logging.error(f"Kill Error: {e}")
            await asyncio.sleep(1)

# --- COMMAND HANDLERS ---
async def kill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    reply = update.message.reply_to_message
    if not reply: return
    chat_id = update.effective_chat.id
    kill_tasks[chat_id] = True
    asyncio.create_task(kill_logic(chat_id, reply.message_id))
    await update.message.reply_text(bot_style("😎😎..."), parse_mode=ParseMode.HTML)

async def unkill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    kill_tasks[update.effective_chat.id] = False
    await update.message.reply_text(bot_style("မင်းကိုတစ်ချီပဲလိုးမယ် ဖာသည်မသား."), parse_mode=ParseMode.HTML)

async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_user(update.effective_user.id): return
    reply = update.message.reply_to_message
    if not reply: return
    chat_id, target = update.effective_chat.id, reply.from_user
    
    async def loop():
        while True:
            try:
                words = [w.get("text") for w in list(db.filters.find()) if w.get("text")]
                mention = f"<a href='tg://user?id={target.id}'>{target.full_name}</a>"
                await context.bot.send_message(chat_id, bot_style(f"{mention} {random.choice(words)}"), parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.1)
            except: await asyncio.sleep(1); continue

    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(bot_style("🔥 BOT BULLY STARTED..."), parse_mode=ParseMode.HTML)

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_user(update.effective_user.id): return
    chat_id = update.effective_chat.id
    if chat_id in bully_tasks:
        bully_tasks[chat_id].cancel()
        del bully_tasks[chat_id]
    await update.message.reply_text(bot_style("🛑 BULLY STOPPED."), parse_mode=ParseMode.HTML)

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    reply = update.message.reply_to_message
    if not reply: return
    groups = list(db.groups.find())
    for g in groups:
        try:
            await context.bot.copy_message(chat_id=g["chat_id"], from_chat_id=update.effective_chat.id, message_id=reply.message_id)
            await asyncio.sleep(0.3)
        except: continue
    await update.message.reply_text(bot_style("📢 BROADCAST FINISHED!"), parse_mode=ParseMode.HTML)

async def admin_mod_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if not await is_real_admin(chat, user.id): return
    cmd = update.message.text.split()[0][1:].lower()
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target or target.id == OWNER_ID: return
    try:
        if cmd == "ban": await chat.ban_member(target.id)
        elif cmd == "mute": await chat.restrict_member(target.id, ChatPermissions(can_send_messages=False))
        elif cmd == "unmute": await chat.restrict_member(target.id, ChatPermissions(can_send_messages=True))
        await update.message.reply_text(bot_style(f"✅ {cmd.upper()} SUCCESS."), parse_mode=ParseMode.HTML)
    except Exception as e: logging.error(e)

async def global_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat_id, user, text = update.effective_chat.id, update.effective_user, update.message.text
    if chat_id == SAVE_CHAT_ID and user.id == OWNER_ID:
        res = db.settings.find_one({"_id": f"save_{chat_id}"})
        if res and res.get("data") and not text.startswith('/'):
            db.filters.update_one({"text": text}, {"$set": {"added_by": user.id}}, upsert=True)
            await update.message.reply_text(bot_style("📝 SAVED."), parse_mode=ParseMode.HTML)

# --- STARTUP ---
async def start_everything():
    if SESSION_STRING:
        await user_client.start()
        print("✅ User Client Started!")
    
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("kill", kill_cmd))
    application.add_handler(CommandHandler("unkill", unkill_cmd))
    application.add_handler(CommandHandler("bully", bully_cmd))
    application.add_handler(CommandHandler("stopbully", stop_bully))
    application.add_handler(CommandHandler("send", broadcast_send))
    application.add_handler(CommandHandler(["ban", "mute", "unmute"], admin_mod_actions))
    
    application.add_handler(CommandHandler("save_on", lambda u,c: db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": True}}, upsert=True) if u.effective_user.id == OWNER_ID else None))
    application.add_handler(CommandHandler("save_off", lambda u,c: db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": False}}, upsert=True) if u.effective_user.id == OWNER_ID else None))
    
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, global_handler))
    
    async with application:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        print("🚀 PTB Bot Running!")
        await asyncio.Event().wait()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(start_everything())

