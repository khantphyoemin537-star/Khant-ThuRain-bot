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
SESSION_STRING = "1BVtsOKEBu6ABEQ_pmpjVhZEry04Sr2zkMxlXk5Vbm_4B6TUjFn_7hU57fEVjddUAdkGE9YISy_vdnIqc-PbxuaB-Pfy2UXSKIfL1GlceFVY6lChhNy5ZkGnPRxIJDVDKhAqUIyUz1GICUjN1TSL5wb8LQBbZxfQV-UlJzDuuP9BuEl0qPQnKKNb32Glmr71rI8W94HD8GQtjTbGUzRGzRDiGqoarULWXRxopzxJdHYJoG-Yfd2eDMMsU2i6yfZdjcU4vc0NjWKl_D_eVcoL8JQ0wTUPnP0XJnn2yM3DYtxwJZhBkaIBwiKyaXtMO2rAa7swIIGjfNBNZue8A53d0aQrFByzcrWk="

client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]

kill_tasks = {}
user_client = TelegramClient(StringSession(SESSION_STRING), APP_ID, APP_HASH, auto_reconnect=True)

def bot_style(text):
    return f"<blockquote><b>{text}</b></blockquote>"

# --- USER ACCOUNT AUTO-STYLE LOGIC ---
@user_client.on(events.NewMessage(outgoing=True))
async def auto_style_handler(event):
    """User Account ကနေ စာပို့တိုင်း blockquote ပြောင်းမယ် (Commands မဟုတ်ရင်)"""
    if not event.text or event.text.startswith('/'):
        return

    # event.text က blockquote ထဲ ရောက်နေပြီးသားဆိုရင် Loop မဖြစ်အောင် ပြန်မပို့တော့ဘူး
    if "<blockquote>" in event.text or "<b>" in event.text:
        return

    try:
        new_text = bot_style(event.text)
        # မူရင်းစာကို အမြန်ဖျက်ပြီး style နဲ့ ပြန်ပို့မယ်
        await event.delete()
        await user_client.send_message(
            event.chat_id, 
            new_text, 
            parse_mode='html',
            reply_to=event.reply_to_msg_id
        )
    except Exception as e:
        logging.error(f"Auto-Style Error: {e}")

# --- MULTI-GROUP KILL LOGIC ---
async def kill_logic(chat_id, reply_to_id):
    while kill_tasks.get(chat_id) == True:
        try:
            if not user_client.is_connected(): await user_client.connect()
            words = [w.get("text") for w in list(db.filters.find()) if w.get("text")]
            if not words: 
                await asyncio.sleep(2)
                continue
            
            word = random.choice(words)
            await user_client.send_message(
                chat_id, 
                bot_style(word), 
                reply_to=reply_to_id, 
                parse_mode='html'
            )
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
    # User Account ကို အရင် Connect လုပ်မယ်
    await user_client.start()
    print("✅ User Account Connected!")
    
    # Bot (PTB) ကို Start လုပ်မယ်
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("kill", kill_cmd))
    application.add_handler(CommandHandler("unkill", unkill_cmd))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    print("🚀 Bot & Userbot are Running!")
    
    # နှစ်ခုလုံးကို တစ်ပြိုင်တည်း run ထားဖို့ wait လုပ်မယ်
    await user_client.run_until_disconnected()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        asyncio.run(start_everything())
    except (KeyboardInterrupt, SystemExit):
        pass

