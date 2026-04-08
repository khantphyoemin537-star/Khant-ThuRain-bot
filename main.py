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
def home(): return "BoD Userbot Active!"
def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION (Dexter's Info) ---
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

# မင်းပေးထားတဲ့ App ID နဲ့ Hash ကို ဒီမှာ ထည့်ထားတယ်
APP_ID = 30765851
APP_HASH = '235b0bc6f03767302dc75763508f7b75'

# --- STRING SESSION (မျက်တောင် ၃ ခုကြားထဲမှာ မင်းရဲ့ String ကို သေချာထည့်ပါ) ---
#
SESSION_STRING = """1BVtsOL0BuxAw-QQQ5apkSh1QPU0xiI0YgaW6g-WUzKVMYjiQ0R5fANemxkcuIUNL_-jT_CMjoNHJ0jv9J_MBIHPMESwMhnvQeLMUoZDImmjJuuXtndvi4xM2yv_G28rqOYp3VZKKtqS6bxN91Vs0-g7K5fWhyx6gdIalXWVQzMv-Ry3EqfJmDhcB-RFE5dSnQnMB09SoD3Sj78drH3S6P3oE1fnno2nziuu6eWP_mi9wuVvugx9YTXsekiMmv5np4j4NT0DuHObJOX5Besx1_HOwI4uuO9JBLWHso3STxj0SY2I0dmm5t_oTYepJEP5IetVz3y949UEr8b1T6vwmEQDmhXKMrxw="""
client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]

kill_tasks = {}

# Session String စစ်ဆေးခြင်း
if not SESSION_STRING or "ဒီနေရာမှာ" in SESSION_STRING:
    print("❌ Error: SESSION_STRING ကို Code ထဲမှာ အစားမထိုးရသေးပါ!")
    user_client = None
else:
    try:
        # String ထဲမှာ space တွေပါရင် ဖယ်ဖို့ .strip() သုံးထားတယ်
        user_client = TelegramClient(StringSession(SESSION_STRING.strip()), APP_ID, APP_HASH, auto_reconnect=True)
    except Exception as e:
        print(f"❌ Session Error: {e}")
        user_client = None

def bot_style(text):
    return f"<blockquote><b>{text}</b></blockquote>"

# --- USERBOT LOGIC ---

@user_client.on(events.NewMessage(pattern='/kill', outgoing=True))
async def kill_handler(event):
    reply = await event.get_reply_message()
    if not reply: return
    
    chat_id = event.chat_id
    kill_tasks[chat_id] = True
    await event.delete() # /kill စာသားကို ဖျက်မယ်
    
    while kill_tasks.get(chat_id) == True:
        try:
            # MongoDB ထဲက စာသားတွေကို လှမ်းယူမယ်
            words_data = list(db.filters.find())
            words = [w.get("text") for w in words_data if w.get("text")]
            if not words:
                await asyncio.sleep(2)
                continue
            
            word = random.choice(words)
            await user_client.send_message(
                chat_id, bot_style(word), 
                reply_to=reply.id, parse_mode='html'
            )
            # Flood limit မထိအောင် ၀.၅ စက္ကန့် စောင့်မယ်
            await asyncio.sleep(0.5)
        except Exception as e:
            logging.error(f"Kill Error: {e}")
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
    if not user_client: return
    threading.Thread(target=run_flask, daemon=True).start()
    print("Connecting User Client...")
    await user_client.start()
    print("✅ Userbot is Running as Dexter Morgan!")
    await user_client.run_until_disconnected()

if __name__ == "__main__":
    if user_client:
        try:
            asyncio.run(main())
        except (KeyboardInterrupt, SystemExit):
            pass

