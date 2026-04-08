import asyncio
import logging
import random
import os
import threading
from io import BytesIO
from flask import Flask
from pymongo import MongoClient

# Pillow
try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:
    logging.error("Pillow library is missing.")

# Telegram Libraries
from telegram import Update, ChatPermissions, User
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
def home(): return "BoD Sovereign System Active!"
def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION ---
TOKEN = os.environ.get("BOT_TOKEN", "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU")
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

APP_ID = 30765851
APP_HASH = '235b0bc6f03767302dc75763508f7b75'
RAW_SESSION = """1BVtsOIMBu6T2JS4dXdDeFN6z1SN2lf8uWRRYBYFcpfI1oczj5bRYv0BbhIFX6Q89RzFC9-ol__4k0FRqOXpXQpKQ5vZ2p4wc0ce3c23ArgnOPcVV-UZMABd1tQlTvgc4OkK_h1sL3J7d9fQ1zMJyzxLiM6umL-o9gSOAeCxeuujXG4WIFT6n3aGpmDOwrbOamVY-g6CxrXJaP0_rlkD8jsESs3-59Gqgs3SIEzhc32Kz4RZ4T760TxEAmpe2AJ7gZ1aCqO7Q2ntwUH1GCHv7BS9Kd_T_sgXsXmUX61gSxj9C1go_6NK0n0omC8XqtL5tKKFU_JcOpPFqdnAX5R4S4xHL_s-CaFU="""
SESSION_STRING = RAW_SESSION.strip().replace("\n", "").replace(" ", "")

# --- DATABASE SETUP ---
client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]
filters_col = db["filters"]      
allow_col = db["allowed_users"]  
groups_col = db["active_groups"] 

# --- SYSTEM VARIABLES ---
kill_tasks = {}   # For User Account (/kill)
bully_tasks = {}  # For Bot Account (/bully)
save_chats = {} 

user_client = TelegramClient(StringSession(SESSION_STRING), APP_ID, APP_HASH, auto_reconnect=True)

def bot_style(text):
    return f"<blockquote><b>{text}</b></blockquote>"

# ==========================================
# 🔴 USER ACCOUNT LOGIC (/kill, /unkill)
# ==========================================

@user_client.on(events.NewMessage(pattern='/kill', outgoing=True))
async def kill_handler(event):
    reply = await event.get_reply_message()
    if not reply: return
    chat_id = event.chat_id
    kill_tasks[chat_id] = True  # Task စတင်မယ်
    await event.delete()
    
    target_name = reply.sender.first_name if reply.sender else "ဒီကောင်"
    
    while kill_tasks.get(chat_id) is True:
        words = [w.get("text") for w in list(filters_col.find()) if w.get("text")]
        if words:
            insult = f"<a href='tg://user?id={reply.sender_id}'>{target_name}</a> {random.choice(words)}"
            try:
                await user_client.send_message(chat_id, bot_style(insult), reply_to=reply.id, parse_mode='html')
            except Exception as e:
                logging.error(f"Kill Error: {e}")
                break
        await asyncio.sleep(0.5)

@user_client.on(events.NewMessage(pattern='/unkill', outgoing=True))
async def unkill_handler(event):
    chat_id = event.chat_id
    kill_tasks[chat_id] = False # Task ရပ်တန့်မယ်
    await event.edit("နားဦးမယ် ဖာသည်မသား 😎")
    await asyncio.sleep(2); await event.delete()

# ==========================================
# 🔵 BOT LOGIC
# ==========================================

async def check_bot_permission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == OWNER_ID or allow_col.find_one({"user_id": user_id}): return True
    bot_me = await context.bot.get_me()
    await update.message.reply_text(f"ဟိတ်... {update.effective_user.mention_html()} မင်းမှာ {bot_me.mention_html()} ရဲ့ Commandတွေ သုံးခွင့်မရှိဘူး🫵😎", parse_mode=ParseMode.HTML)
    return False

# Admin Tools
async def admin_tools(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_bot_permission(update, context): return
    member = await update.effective_chat.get_member(update.effective_user.id)
    if member.status not in ['administrator', 'creator'] and update.effective_user.id != OWNER_ID: return
    reply = update.message.reply_to_message
    if not reply: return
    cmd = update.message.text.split()[0][1:]
    try:
        if cmd == "ban": await context.bot.ban_chat_member(update.effective_chat.id, reply.from_user.id)
        elif cmd == "mute": await context.bot.restrict_chat_member(update.effective_chat.id, reply.from_user.id, permissions=ChatPermissions(can_send_messages=False))
        elif cmd == "unmute": await context.bot.restrict_chat_member(update.effective_chat.id, reply.from_user.id, permissions=ChatPermissions(can_send_messages=True))
        await update.message.reply_text(f"Done: {cmd.upper()}!")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# Save Chat & Broadcast Data
async def save_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    # Broadcast အတွက် ID တွေကို အမြဲ Update လုပ်မယ်
    groups_col.update_one({"chat_id": chat.id}, {"$set": {"title": chat.title}}, upsert=True)
    
    if save_chats.get(chat.id) and update.message.text:
        if not update.message.text.startswith('/'):
            filters_col.update_one({"text": update.message.text}, {"$set": {"text": update.message.text}}, upsert=True)

async def save_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_bot_permission(update, context): return
    save_chats[update.effective_chat.id] = True
    await update.message.reply_text("Save Chat: ON ✅")

async def save_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_bot_permission(update, context): return
    save_chats[update.effective_chat.id] = False
    await update.message.reply_text("Save Chat: OFF 🛑")

# Bully Logic
async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_bot_permission(update, context): return
    reply = update.message.reply_to_message
    if not reply: return
    chat_id = update.effective_chat.id
    bully_tasks[chat_id] = True
    target_mention = reply.from_user.mention_html()
    asyncio.create_task(bully_loop(chat_id, reply.message_id, target_mention, context))
    await update.message.reply_text(f"Bully Started on {target_mention}! 🔥", parse_mode=ParseMode.HTML)

async def bully_loop(chat_id, reply_id, target_mention, context):
    while bully_tasks.get(chat_id) is True:
        words = [w.get("text") for w in list(filters_col.find()) if w.get("text")]
        if words:
            try:
                msg = f"{target_mention} {random.choice(words)}"
                await context.bot.send_message(chat_id, bot_style(msg), reply_to_message_id=reply_id, parse_mode='html')
            except: break
        await asyncio.sleep(0.7)

async def stopbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_bot_permission(update, context): return
    bully_tasks[update.effective_chat.id] = False
    await update.message.reply_text("Bully Stopped! 🛑")

# Management Commands
async def addallow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    reply = update.message.reply_to_message
    if reply:
        allow_col.update_one({"user_id": reply.from_user.id}, {"$set": {"name": reply.from_user.full_name}}, upsert=True)
        await update.message.reply_text(f"Added {reply.from_user.first_name} to Allow List! ✅")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    reply = update.message.reply_to_message
    if not reply: return
    groups = list(groups_col.find())
    count = 0
    for g in groups:
        try:
            await context.bot.copy_message(g['chat_id'], update.effective_chat.id, reply.message_id)
            count += 1
        except: pass
    await update.message.reply_text(f"📢 Broadcast sent to {count} groups!")

async def adm_call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text: return
    admins = await context.bot.get_chat_administrators(update.effective_chat.id)
    mentions = " ".join([a.user.mention_html() for a in admins if not a.user.is_bot])
    await update.message.reply_text(f"{mentions}\n\n<b>UPDATE:</b> {text}", parse_mode=ParseMode.HTML)

# ==========================================
# 🚀 STARTUP
# ==========================================
async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    # User Client Start
    await user_client.start()
    
    # Bot Client Start
    bot_app = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    bot_app.add_handler(CommandHandler("save_on", save_on))
    bot_app.add_handler(CommandHandler("save_off", save_off))
    bot_app.add_handler(CommandHandler("bully", bully_cmd))
    bot_app.add_handler(CommandHandler("stopbully", stopbully))
    bot_app.add_handler(CommandHandler(["ban", "mute", "unmute"], admin_tools))
    bot_app.add_handler(CommandHandler("addallow", addallow_cmd))
    bot_app.add_handler(CommandHandler("send", broadcast))
    bot_app.add_handler(CommandHandler("adm", adm_call))
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), save_chat_handler))
    
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(drop_pending_updates=True)
    
    logging.info("Sovereign System Fully Active!")
    await user_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
