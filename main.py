import asyncio
import logging
import random
import io
import os
import threading
from datetime import datetime
from flask import Flask
from pymongo import MongoClient

# Libraries for Bot and User Client
from telegram import Update, ChatMember, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes, ChatMemberHandler
)
from telethon import TelegramClient, events

# --- FLASK KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "BoD Premium Bot is Active!"
def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION ---
TOKEN = "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU"
OWNER_ID = 6015356597
ADMIN_GROUP_ID = -1003580630981
SAVE_CHAT_ID = -1003580630981
ADMIN_CHAT_MENTION = "@Besties_with_BoD"
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

# User Account Config (Telethon)
APP_ID = 30765851
APP_HASH = '235b0bc6f03767302dc75763508f7b75'

client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]

# Tasks Storage
bully_tasks = {} # Bot Bully
kill_tasks = {}  # User Account Kill

# Telethon Client Initial
user_client = TelegramClient('dexter_session', APP_ID, APP_HASH)

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

# --- BULLY & KILL SYSTEM ---
async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_user(update.effective_user.id): return
    reply = update.message.reply_to_message
    if not reply: return
    
    target, chat_id = reply.from_user, update.effective_chat.id
    if chat_id in bully_tasks: bully_tasks[chat_id].cancel()

    async def loop():
        while True:
            try:
                words = [w.get("text") for w in list(db.filters.find()) if w.get("text")]
                if not words: break
                mention = f"<a href='tg://user?id={target.id}'>{target.full_name}</a>"
                await context.bot.send_message(chat_id, bot_style(f"{mention} {random.choice(words)}"), parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.1)
            except: await asyncio.sleep(1); continue
            
    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(bot_style(f"Bruhh Bruhh ငါလိုးမသား😎..."), parse_mode=ParseMode.HTML)

# --- USER ACCOUNT KILL SYSTEM (/kill) ---
async def kill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    reply = update.message.reply_to_message
    if not reply: return
    
    target_id = reply.from_user.id
    chat_id = update.effective_chat.id
    
    if chat_id in kill_tasks: kill_tasks[chat_id] = False
    kill_tasks[chat_id] = True

    await update.message.reply_text(bot_style(f"ဖာသည်မလေးရေ မင်းကိုအသေလိုးသတ်ပြီ"), parse_mode=ParseMode.HTML)
    
    while kill_tasks.get(chat_id):
        try:
            words = [w.get("text") for w in list(db.filters.find()) if w.get("text")]
            word = random.choice(words)
            # Telethon syntax for blockquote
            await user_client.send_message(chat_id, f"**{word}**", reply_to=reply.message_id)
            await asyncio.sleep(0.05) # Extreme speed for user account
        except: break

async def unkill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    kill_tasks[chat_id] = False
    await update.message.reply_text(bot_style("တစ်ချီပဲမင်းကိုအသေလိုးတာ"), parse_mode=ParseMode.HTML)

# --- BROADCAST (/send) ---
async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    reply = update.message.reply_to_message
    if not reply: return
    
    groups = list(db.groups.find())
    success, fail = 0, 0
    for g in groups:
        try:
            await context.bot.copy_message(chat_id=g["chat_id"], from_chat_id=update.effective_chat.id, message_id=reply.message_id)
            success += 1
            await asyncio.sleep(0.2)
        except: fail += 1
    await update.message.reply_text(bot_style(f"📢 ပို့ပြီးပြီ!\nအောင်မြင်: {success}\nကျရှုံး: {fail}"), parse_mode=ParseMode.HTML)

# --- OTHER HANDLERS ---
async def admin_mod_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if not await is_real_admin(chat, user.id): return
    cmd = update.message.text.split()[0][1:].lower()
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target or target.id == OWNER_ID: return
    try:
        if cmd == "ban": await chat.ban_member(target.id)
        elif cmd == "mute": await chat.restrict_member(target.id, ChatPermissions(can_send_messages=False))
        await update.message.reply_text(bot_style(f"✅ {cmd.upper()} အောင်မြင်ပါတယ်။"), parse_mode=ParseMode.HTML)
    except Exception as e: logging.error(e)

async def global_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat_id, user, text = update.effective_chat.id, update.effective_user, update.message.text
    if chat_id == SAVE_CHAT_ID and user.id == OWNER_ID:
        res = db.settings.find_one({"_id": f"save_{chat_id}"})
        if res and res.get("data") and not text.startswith('/'):
            db.filters.update_one({"text": text}, {"$set": {"added_by": user.id}}, upsert=True)
            await update.message.reply_text(bot_style("📝 သိမ်းပြီး။"), parse_mode=ParseMode.HTML)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Start Telethon in background
    user_client.start()

    # Start PTB Bot
    app_bot = ApplicationBuilder().token(TOKEN).build()
    
    app_bot.add_handler(CommandHandler("bully", bully_cmd))
    app_bot.add_handler(CommandHandler("stopbully", lambda u,c: bully_tasks.get(u.effective_chat.id).cancel() if bully_tasks.get(u.effective_chat.id) else None))
    app_bot.add_handler(CommandHandler("kill", kill_cmd))
    app_bot.add_handler(CommandHandler("unkill", unkill_cmd))
    app_bot.add_handler(CommandHandler("send", broadcast_send))
    app_bot.add_handler(CommandHandler(["ban", "mute"], admin_mod_actions))
    
    app_bot.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, global_handler))
    
    print("🚀 BoD Premium (DEXTER EDITION) is running...")
    app_bot.run_polling()

if __name__ == "__main__": main()

