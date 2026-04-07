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
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0")

# Dexter's User Config
APP_ID = 30765851
APP_HASH = '235b0bc6f03767302dc75763508f7b75'
SESSION_STRING = "1BVtsOIMBuzER7bNgY50G3Fym5wLzJ-xzmzsm6_01pXdZYURbhJwzqvDW5pGknHrv8boIAj-b0pLAnEbyIhwQcxDkF786vcckXCvPzs4MPY96Av0Vn0CutkOZO4skVIpTbMnp0JnoHTqtHZCup2tKe5H7aQxtXxcpZ0aagPuUyM8_heNXr8D_GcRTlCPXuJ-S9VrZQZAX0aEEs9LDS02uJWTw9z8RVel7e0nFZm7wFAvvQ228PXhgjrUNH9FKYb2A8MTpraJn_TEkynPMAj6sO-yennYex7-XIyrAXTZ54l5NW-kt6p05rdH5VVNDtFyjiKyKti7OyAEAv147ygDed8zSMjEkdVY=
"

client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]

# Tasks Storage
kill_tasks = {}
user_client = TelegramClient(StringSession(SESSION_STRING), APP_ID, APP_HASH, auto_reconnect=True)

def bot_style(text):
    return f"<blockquote><b>{text}</b></blockquote>"

# --- USERBOT LOGIC ---

@user_client.on(events.NewMessage(pattern='/kill', outgoing=True))
async def kill_handler(event):
    """User Account ကနေ /kill လို့ရိုက်ရင် စမယ်"""
    reply = await event.get_reply_message()
    if not reply:
        return await event.edit("လိုးမယ့်သူရဲ့စာကို Reply ပြန်ပြီး /kill သုံးပါ!")
    
    chat_id = event.chat_id
    kill_tasks[chat_id] = True
    await event.delete() # /kill ဆိုတဲ့ စာသားကို ဖျက်မယ်
    
    print(f"Started Kill in {chat_id}")
    
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
            # Flood limit လွတ်အောင် ၀.၅ စက္ကန့် စောင့်မယ်
            await asyncio.sleep(0.5)
        except Exception as e:
            logging.error(f"Kill Loop Error: {e}")
            await asyncio.sleep(1)

@user_client.on(events.NewMessage(pattern='/unkill', outgoing=True))
async def unkill_handler(event):
    """User Account ကနေ /unkill လို့ရိုက်ရင် ရပ်မယ်"""
    chat_id = event.chat_id
    kill_tasks[chat_id] = False
    await event.edit("အားတိုင်းထပ်ထပ်လိုးမယ်ဖာသည်မသား 😎")
    await asyncio.sleep(2)
    await event.delete()

# --- STARTUP ---
async def main():
    # Flask Keep-Alive Background Thread
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
