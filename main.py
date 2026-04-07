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
# မင်းပေးတဲ့ String အသစ်ကို ဒီမှာ variable ထဲ ထည့်ထားတယ်
SESSION_STRING = "1BVtsOKEBu12u_z4ZOjKP5qeSM4bdDG448GE4e44rNusTysiHUrLLN-lKSmrKX5Ui-Oe2U64V1NuSW1YOiKabT0jZ8dS0PRLvaUs7MEQYXUnKqzXV3-hWVf3-7OxyX4pA025QnZr4Q9fuiZjN_jrpaesNWBXCxzSuC_ZHbJ9WJYoJDj1kEz5FEG_aRQd7nGMotcCkB7ci8jSPFM1f6vCmxLXxw4Rq0TUcDgUkP9IZOh4z008I50SFVfXr3sHtRC1scO77eANZwXrVITrW8caPk1k2V2DXphk1sSNisrFlWfYgCCU_5AXyojofq8gpd7Y_xHur6wNQeyB_KVI7RSF-r5FNVacu5I8="

client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]

# Tasks Storage (Group အလိုက် ခွဲမှတ်ဖို့ Dictionary သုံးထားတယ်)
bully_tasks = {}
kill_tasks = {}

# User Client Setup
user_client = TelegramClient(StringSession(SESSION_STRING), APP_ID, APP_HASH)

# --- HELPERS ---
def bot_style(text):
    return f"<blockquote><b>{text}</b></blockquote>"

async def is_real_admin(chat, user_id):
    if user_id == OWNER_ID: return True
    try:
        member = await chat.get_member(user_id)
        return member.status in [ChatMember.OWNER, ChatMember.ADMINISTRATOR]
    except: return False

# --- MULTI-GROUP KILL LOGIC ---
async def kill_logic(chat_id, reply_to_id):
    """Group တစ်ခုချင်းစီအလိုက် သီးသန့် Loop ပတ်ပေးမယ့် function"""
    while kill_tasks.get(chat_id) == True:
        try:
            if not user_client.is_connected():
                await user_client.connect()
            
            # Database ထဲက စာသားတွေ ဆွဲထုတ်မယ်
            words_data = list(db.filters.find())
            words = [w.get("text") for w in words_data if w.get("text")]
            
            if not words:
                logging.warning(f"No words found in DB for group {chat_id}")
                await asyncio.sleep(2)
                continue
            
            word = random.choice(words)
            # User account နဲ့ စာပို့မယ်
            await user_client.send_message(
                chat_id, 
                f"<blockquote><b>{word}</b></blockquote>", 
                reply_to=reply_to_id, 
                parse_mode='html'
            )
            # Flood limit မမိအောင် ၀.၃ စက္ကန့် စောင့်မယ်
            await asyncio.sleep(0.3)
        except Exception as e:
            logging.error(f"Kill Error in {chat_id}: {e}")
            await asyncio.sleep(1)

# --- COMMAND HANDLERS ---
async def kill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    reply = update.message.reply_to_message
    if not reply:
        return await update.message.reply_text(bot_style("လိုးမယ့်သူရဲ့စာကို Reply ပြန်ပြီး /kill သုံးပါ!"), parse_mode=ParseMode.HTML)
    
    chat_id = update.effective_chat.id
    
    # ဒီ Group အတွက် Task ကိုစတင်မယ် (တခြား group နဲ့ မငြိတော့ဘူး)
    kill_tasks[chat_id] = True
    asyncio.create_task(kill_logic(chat_id, reply.message_id))
    
    await update.message.reply_text(bot_style("😎မင်းကိုအသေလိုးပေးမယ်ဖာသည်မသား"), parse_mode=ParseMode.HTML)

async def unkill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    chat_id = update.effective_chat.id
    
    # ဒီ Group တစ်ခုတည်းကိုပဲ ရပ်ခိုင်းမယ်
    kill_tasks[chat_id] = False
    await update.message.reply_text(bot_style("အားတိုင်းထပ်ထပ်လိုးမယ်ဖာသည်မသား"), parse_mode=ParseMode.HTML)

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    reply = update.message.reply_to_message
    if not reply: return
    # MongoDB ထဲက group list ကိုယူမယ်
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
    
    # Filter သိမ်းတဲ့ logic
    if chat_id == SAVE_CHAT_ID and user.id == OWNER_ID:
        res = db.settings.find_one({"_id": f"save_{chat_id}"})
        if res and res.get("data") and not text.startswith('/'):
            db.filters.update_one({"text": text}, {"$set": {"added_by": user.id}}, upsert=True)
            await update.message.reply_text(bot_style("📝 SAVED."), parse_mode=ParseMode.HTML)

# --- STARTUP ---
async def start_everything():
    # User Client ကို အရင်စမယ်
    await user_client.start()
    print("✅ User Client Connected!")
    
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Commands
    application.add_handler(CommandHandler("kill", kill_cmd))
    application.add_handler(CommandHandler("unkill", unkill_cmd))
    application.add_handler(CommandHandler("send", broadcast_send))
    
    # Save On/Off
    application.add_handler(CommandHandler("save_on", lambda u,c: db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": True}}, upsert=True) if u.effective_user.id == OWNER_ID else None))
    application.add_handler(CommandHandler("save_off", lambda u,c: db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": False}}, upsert=True) if u.effective_user.id == OWNER_ID else None))
    
    # Global Message Handler
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, global_handler))
    
    async with application:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        print("🚀 PTB Bot Running on Railway!")
        await asyncio.Event().wait()

if __name__ == "__main__":
    # Flask ကို background မှာ run ထားမယ်
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        asyncio.run(start_everything())
    except (KeyboardInterrupt, SystemExit):
        pass
