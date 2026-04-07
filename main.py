import asyncio
import logging
import random
import os
import threading
from flask import Flask
from pymongo import MongoClient
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# --- FLASK KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "BoD Userbot is Active!"
def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION ---
OWNER_ID = 6015356597
# MongoDB URI ကို ဒီမှာ တစ်ခါတည်း ထည့်ထားပေးတယ်
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"
APP_ID = 30765851
APP_HASH = '235b0bc6f03767302dc75763508f7b75'

# SESSION_STRING ကိုတော့ Railway Variables ထဲမှာ SESSION_STRING ဆိုတဲ့ နာမည်နဲ့ ထည့်ပေးပါ
SESSION_STRING = os.environ.get("SESSION_STRING")

client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]

kill_tasks = {}

if not SESSION_STRING:
    print("❌ Error: SESSION_STRING ကို Railway Variables မှာ မထည့်ရသေးပါ!")
else:
    user_client = TelegramClient(StringSession(SESSION_STRING), APP_ID, APP_HASH, auto_reconnect=True)

def bot_style(text):
    return f"<blockquote><b>{text}</b></blockquote>"

# --- USERBOT LOGIC ---

@user_client.on(events.NewMessage(pattern='/kill', outgoing=True))
async def kill_handler(event):
    reply = await event.get_reply_message()
    if not reply:
        return
    
    chat_id = event.chat_id
    kill_tasks[chat_id] = True
    await event.delete()
    
    while kill_tasks.get(chat_id) == True:
        try:
            words_data = list(db.filters.find())
            words = [w.get("text") for w in words_data if w.get("text")]
            if not words:
                await asyncio.sleep(2)
                continue
            
            word = random.choice(words)
            await user_client.send_message(
                chat_id, 
                bot_style(word), 
                reply_to=reply.id, 
                parse_mode='html'
            )
            await asyncio.sleep(0.5)
        except Exception as e:
            logging.error(f"Kill Loop Error: {e}")
            await asyncio.sleep(1)

@user_client.on(events.NewMessage(pattern='/unkill', outgoing=True))
async def unkill_handler(event):
    chat_id = event.chat_id
    kill_tasks[chat_id] = False
    await event.edit("အားတိုင်းထပ်ထပ်လိုးမယ်ဖာသည်မသား 😎")
    await asyncio.sleep(2)
    await event.delete()

# --- STARTUP ---
async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    print("Connecting User Client...")
    await user_client.start()
    print("✅ Userbot is Running as Dexter Morgan!")
    await user_client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
