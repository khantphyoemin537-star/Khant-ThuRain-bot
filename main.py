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
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0")

# Telethon Config
APP_ID = 30765851
APP_HASH = '235b0bc6f03767302dc75763508f7b75'
SESSION_STRING = os.environ.get("SESSION_STRING", "1BVtsOKEBu8OA71fVy10wv1z1Z9ZcH34wjlY6tfWbHgtwpEFv_n1kMtMAiPSrqbpBJYqtwXx6NgeEHuyHnsPtK1xO4tafvqCxF3x3qvH_WErij_TtNmA0P9F2Jb21DwIzUM48e2hugakBdxnXoR24M0HFKG19b2MQHhBdZZMpp354h9K-YPUPwWHsELu0rtGOqep48GxcJ9Gkp_noBSeRcRO-i2pe7vg6ak4g_f7hsBoOfeHwkpyG-sbXY1CfyDmBYTbDKEEv9sGZYfwTb8Kx7KBivgchV0_fu0W3u30eD-fHUfSynZK3uCapqyKLXmIK6AtDPj6vCXvLHUHrXWsLe0IkP8urBbE=")

client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]

# Tasks Storage
bully_tasks = {}
kill_tasks = {}

# User Client Initial (Global ထားထားမယ်)
user_client = TelegramClient(StringSession(SESSION_STRING), APP_ID, APP_HASH)

def bot_style(text):
    return f"<blockquote><b>{text}</b></blockquote>"

# --- REFINED KILL LOGIC ---
async def kill_logic(chat_id, reply_to_id):
    """User account ကနေ background မှာ loop ပတ်ပြီး bully ဖို့"""
    while kill_tasks.get(chat_id):
        try:
            # Connect မဖြစ်သေးရင် အတင်း connect ခိုင်းမယ်
            if not user_client.is_connected():
                await user_client.connect()
                
            words_data = list(db.filters.find())
            words = [w.get("text") for w in words_data if w.get("text")]
            
            if not words:
                logging.warning("No words in database!")
                await asyncio.sleep(2)
                continue
            
            word = random.choice(words)
            await user_client.send_message(
                chat_id, 
                f"<blockquote><b>{word}</b></blockquote>", 
                reply_to=reply_to_id,
                parse_mode='html'
            )
            # အရှိန်ကို အနည်းငယ်လျှော့ထားတာ ပိုစိတ်ချရတယ် (Flood limit မမိအောင်)
            await asyncio.sleep(0.3)
        except Exception as e:
            logging.error(f"Kill Loop Error: {e}")
            await asyncio.sleep(1)

# --- COMMAND HANDLERS ---
async def kill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    reply = update.message.reply_to_message
    if not reply:
        return await update.message.reply_text(bot_style("Bully ချင်တဲ့သူရဲ့ စာကို Reply ပြန်ပြီး /kill သုံးပါ!"), parse_mode=ParseMode.HTML)
    
    chat_id = update.effective_chat.id
    
    # အရင်ရှိနေတဲ့ task ရှိရင် ဖျက်မယ် (ထပ်ခါထပ်ခါ မဖြစ်အောင်)
    kill_tasks[chat_id] = True
    
    # Task အသစ်အနေနဲ့ စမယ်
    asyncio.create_task(kill_logic(chat_id, reply.message_id))
    await update.message.reply_text(bot_style("😎😎..."), parse_mode=ParseMode.HTML)

async def unkill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    chat_id = update.effective_chat.id
    kill_tasks[chat_id] = False
    await update.message.reply_text(bot_style("မင်းကိုတစ်ချီပဲလိုးမယ် ဖာသည်မသား."), parse_mode=ParseMode.HTML)

# --- OTHERS (BULLY/BROADCAST/ADMIN) ---
async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # (မင်းရဲ့ bully logic ကို ဒီမှာ ဆက်ထားနိုင်ပါတယ်)
    pass

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
    # User Client ကို connect အရင်လုပ်မယ်
    await user_client.start()
    print("✅ User Client Connected!")
    
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("kill", kill_cmd))
    application.add_handler(CommandHandler("unkill", unkill_cmd))
    application.add_handler(CommandHandler("send", broadcast_send))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, global_handler))
    
    async with application:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        print("🚀 PTB Bot Running!")
        await asyncio.Event().wait()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        asyncio.run(start_everything())
    except KeyboardInterrupt:
        pass

