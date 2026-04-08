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
SESSION_STRING = """1BVtsOIMBuzER7bNgY50G3Fym5wLzJ-xzmzsm6_01pXdZYURbhJwzqvDW5pGknHrv8boIAj-b0pLAnEbyIhwQcxDkF786vcckXCvPzs4MPY96Av0Vn0CutkOZO4skVIpTbMnp0JnoHTqtHZCup2tKe5H7aQxtXxcpZ0aagPuUyM8_heNXr8D_GcRTlCPXuJ-S9VrZQZAX0aEEs9LDS02uJWTw9z8RVel7e0nFZm7wFAvvQ228PXhgjrUNH9FKYb2A8MTpraJn_TEkynPMAj6sO-yennYex7-XIyrAXTZ54l5NW-kt6p05rdH5VVNDtFyjiKyKti7OyAEAv147ygDed8zSMjEkdVY="""

# --- DATABASE SETUP ---
client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]
filters_col = db["filters"]      
allow_col = db["allowed_users"]  
groups_col = db["active_groups"] # Chat ID တွေသိမ်းမယ့်နေရာ

# --- SYSTEM VARIABLES ---
kill_tasks = {}
bully_tasks = {}
save_chats = {} 

user_client = TelegramClient(StringSession(SESSION_STRING.strip()), APP_ID, APP_HASH, auto_reconnect=True)

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
    kill_tasks[chat_id] = True
    await event.delete()
    while kill_tasks.get(chat_id):
        words = [w.get("text") for w in list(filters_col.find()) if w.get("text")]
        if words:
            await user_client.send_message(chat_id, bot_style(random.choice(words)), reply_to=reply.id, parse_mode='html')
        await asyncio.sleep(0.5)

@user_client.on(events.NewMessage(pattern='/unkill', outgoing=True))
async def unkill_handler(event):
    kill_tasks[event.chat_id] = False
    await event.edit("အားတိုင်းထပ်ထပ်လိုးမယ်ဖာသည်မသား 😎")
    await asyncio.sleep(2); await event.delete()

# ==========================================
# 🔵 BOT LOGIC
# ==========================================

async def check_bot_permission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == OWNER_ID or allow_col.find_one({"user_id": user_id}): return True
    bot_me = await context.bot.get_me()
    await update.message.reply_text(f"ဟိတ်... {update.effective_user.mention_html()} မင်းမှာ {bot_me.mention_html()} ရဲ့ Commandတွေ သုံးခွင့်မရှိဘူး🫵😎\nသုံးမယ်ဆို @Besties_with_BoD ကိုလာတောင်း!!", parse_mode=ParseMode.HTML)
    return False

async def make_welcome_img(user: User, chat_title: str):
    try:
        base = Image.new('RGB', (600, 300), color=(15, 15, 15))
        draw = ImageDraw.Draw(base)
        img_io = BytesIO()
        base.save(img_io, 'JPEG'); img_io.seek(0)
        return img_io
    except: return None

# Entry, Welcome & Save Chat ID
async def chat_member_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                # Chat ID ကို DB မှာ အသေမှတ်သားမယ် (Broadcast အတွက်)
                groups_col.update_one({"chat_id": chat.id}, {"$set": {"title": chat.title, "added_at": asyncio.get_event_loop().time()}}, upsert=True)
                owner = await context.bot.get_chat(OWNER_ID)
                await update.message.reply_text(f"ဟိတ်ရို့ /adm မင်းတို့ရဲ့ဒီ {chat.title} ကို ထည့်သွင်းအသုံးပြုပေးတဲ့အတွက် ကျေးဇူး၊ အမ် အသုံးဝင်မယ့် တချို့ကန့်သန့်ထားတဲ့ bot command တွေသုံးမယ်ဆို @Besties_with_BoD က {owner.mention_html()} ကိုလာပြော!!", parse_mode=ParseMode.HTML)
            else:
                img = await make_welcome_img(member, chat.title)
                await update.message.reply_text(f"Welcome {member.mention_html()} to {chat.title}! 🦅", parse_mode=ParseMode.HTML)
    elif update.message.left_chat_member:
        if update.message.left_chat_member.id != context.bot.id:
            await update.message.reply_text(f"Good Bye {update.message.left_chat_member.mention_html()}! သွားပါပြီ နောက်တစ်ယောက် 💀", parse_mode=ParseMode.HTML)

# Save Chat to DB Filters
async def save_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if save_chats.get(chat_id) and update.message.text:
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

# Bully & Admin Tools
async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_bot_permission(update, context): return
    reply = update.message.reply_to_message
    if not reply: return
    bully_tasks[update.effective_chat.id] = True
    asyncio.create_task(bully_loop(update.effective_chat.id, reply.message_id, context))
    await update.message.reply_text("Bully Started! 🔥")

async def bully_loop(chat_id, reply_id, context):
    while bully_tasks.get(chat_id):
        words = [w.get("text") for w in list(filters_col.find()) if w.get("text")]
        if words:
            try: await context.bot.send_message(chat_id, bot_style(random.choice(words)), reply_to_message_id=reply_id, parse_mode='html')
            except: pass
        await asyncio.sleep(0.7)

async def stopbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bully_tasks[update.effective_chat.id] = False
    await update.message.reply_text("Bully Stopped! 🛑")

# Admin Tools
async def admin_tools(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    except: pass

# Broadcast with Saved Chat IDs
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
    await update.message.reply_text(f"📢 Broadcast sent to {count} saved groups!")

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
    await user_client.start()
    bot_app = ApplicationBuilder().token(TOKEN).build()
    
    bot_app.add_handler(CommandHandler("save_on", save_on))
    bot_app.add_handler(CommandHandler("save_off", save_off))
    bot_app.add_handler(CommandHandler("bully", bully_cmd))
    bot_app.add_handler(CommandHandler("stopbully", stopbully))
    bot_app.add_handler(CommandHandler(["ban", "mute", "unmute"], admin_tools))
    bot_app.add_handler(CommandHandler("send", broadcast))
    bot_app.add_handler(CommandHandler("adm", adm_call))
    bot_app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, chat_member_events))
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), save_chat_handler))
    
    await bot_app.initialize(); await bot_app.start()
    await bot_app.updater.start_polling(drop_pending_updates=True)
    await user_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
