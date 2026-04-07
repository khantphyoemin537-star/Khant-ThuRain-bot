import asyncio
import logging
import random
import os
import threading
from flask import Flask
from pymongo import MongoClient

# Libraries
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes
)
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# --- FLASK KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "BoD Premium Userbot Active!"
def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION ---
TOKEN = os.environ.get("BOT_TOKEN", "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU")
OWNER_ID = 6015356597
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0")

# Telethon Config
APP_ID = 30765851
APP_HASH = '235b0bc6f03767302dc75763508f7b75'
SESSION_STRING = "1BVtsOIMBuyXMUjm3XaVk1f1gtjSiU-4VnJGoNHV9xJidLbX1rWcIIt_UErDiJr2gRjfDAgj2HZr9uQpiRd7WYEI7YAKAwZJH2RMI_GPqBEgdExqn5mIOsfZpkt9_6hhqvlGFaMJ46u7kQ7kxBPwQxxU0kacO1sBk2_cyc4hfaDsAUvaSMYCBmlzRkmDPAWiKcOhtl2AF_ups1rV03adzxv-Lkj7vra1uEgTZLXa-EqrCCnIErg3JUVI5zp3DqanXieDovPfCDjHO2u4JIyQS9kCxProUjHwJ5SoiUC0aYefEoYG_X1mmLz35QjJ_I7nX7PEh6m5znv2KcLH-lebnQhDCbLUl34o="

client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]

kill_tasks = {}
user_client = TelegramClient(StringSession(SESSION_STRING), APP_ID, APP_HASH, auto_reconnect=True)

def bot_style(text):
    """Kill လုပ်တဲ့အချိန်မှာပဲ blockquote သုံးဖို့ style"""
    return f"<blockquote><b>{text}</b></blockquote>"

# --- MULTI-GROUP KILL LOGIC ---
async def kill_logic(chat_id, reply_to_id):
    while kill_tasks.get(chat_id) == True:
        try:
            if not user_client.is_connected(): await user_client.connect()
            
            # MongoDB ထဲက filters တွေကို ဆွဲထုတ်မယ်
            words_data = list(db.filters.find())
            words = [w.get("text") for w in words_data if w.get("text")]
            
            if not words: 
                await asyncio.sleep(2)
                continue
            
            word = random.choice(words)
            # User account ကနေ blockquote နဲ့ လိုးမယ်
            await user_client.send_message(
                chat_id, 
                bot_style(word), 
                reply_to=reply_to_id, 
                parse_mode='html'
            )
            # Flood limit မထိအောင် ၀.၅ စက္ကန့် စောင့်မယ်
            await asyncio.sleep(0.5)
        except Exception as e:
            logging.error(f"Kill Error: {e}")
            await asyncio.sleep(1)

# --- BOT COMMANDS ---
async def kill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    reply = update.message.reply_to_message
    if not reply: return
    
    chat_id = update.effective_chat.id
    kill_tasks[chat_id] = True
    asyncio.create_task(kill_logic(chat_id, reply.message_id))
    await update.message.reply_text("Kill Started! 😎", parse_mode=ParseMode.HTML)

async def unkill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    chat_id = update.effective_chat.id
    kill_tasks[chat_id] = False
    await update.message.reply_text("Kill Stopped! 🛑", parse_mode=ParseMode.HTML)

# --- STARTUP ---
async def start_everything():
    await user_client.start()
    print("✅ User Account Connected!")
    
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("kill", kill_cmd))
    application.add_handler(CommandHandler("unkill", unkill_cmd))
    
    await application.initialize()
    await application.start()
    # drop_pending_updates က bot instance နှစ်ခုငြိတာကို ကာကွယ်ပေးတယ်
    await application.updater.start_polling(drop_pending_updates=True)
    print("🚀 Bot & Userbot are Running!")
    
    await user_client.run_until_disconnected()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        asyncio.run(start_everything())
    except (KeyboardInterrupt, SystemExit):
        pass
