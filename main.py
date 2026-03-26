import logging
import asyncio
import random
import os
import re
from datetime import timedelta
from pymongo import MongoClient
from flask import Flask
from threading import Thread
from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes
)

# --- UPTIMEROBOT & FLASK ---
app_flask = Flask('')
@app_flask.route('/')
def home(): return "Bot is Alive!"
def run(): app_flask.run(host='0.0.0.0', port=7860)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURATION ---
TOKEN = "8575371720:AAHjBOXArgOAtBUqPY_8xnZjQe-w4Dk4uRc"
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client['bully_bot_db']
collection = db['bot_data']

def get_data():
    data = collection.find_one({"_id": "config"})
    if not data:
        data = {
            "_id": "config",
            "allowed_users": [OWNER_ID],
            "bully_list": ["မင်းရုပ်က error တစ်ခုပဲ", "မအေလိုး..."],
            "registered_groups": [],
            "filters": {},
            "settings": {"antilink": False}
        }
        collection.insert_one(data)
    return data

def update_db(key, value):
    collection.update_one({"_id": "config"}, {"$set": {key: value}})

async def is_admin(update: Update):
    data = get_data()
    if update.effective_user.id in data["allowed_users"]: return True
    await update.message.reply_text("<blockquote>ညီမင်းမှာ သုံးခွင့်မရှိဘူး🫵 Bot Permissionရယူရန် @Besties_with_BoD </blockquote>", parse_mode=ParseMode.HTML)
    return False

# --- WELCOME & GOODBYE ---
async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    data = get_data()
    if chat.id not in data["registered_groups"]:
        data["registered_groups"].append(chat.id)
        update_db("registered_groups", data["registered_groups"])

    for member in update.message.new_chat_members:
        mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
        msg = f"ဟိတ် {mention}! <b>{chat.title}</b> မှ ကြိုဆိုလိုက်ပါသေးတယ်!"
        await chat.send_message(f"<blockquote>{msg}</blockquote>", parse_mode=ParseMode.HTML)

async def goodbye_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.message.left_chat_member
    chat_title = update.effective_chat.title
    if member:
        mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
        await update.effective_chat.send_message(f"<blockquote>ဟုတ် {mention} ထွက်သွားလိုက်ပါသေးတယ်! <b>{chat_title}</b> ကတော့ သတိရနေမှာပါ။</blockquote>", parse_mode=ParseMode.HTML)

# --- FILTERS ---
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if len(context.args) < 2: return await update.message.reply_text("Format: /addfilter [keyword] [reply]")
    keyword, reply = context.args[0].lower(), " ".join(context.args[1:])
    data = get_data()
    filters_dict = data.get("filters", {})
    filters_dict[keyword] = reply
    update_db("filters", filters_dict)
    await update.message.reply_text(f"<blockquote>✅ Filterပေါင်းထည့်ပြီး🤪: {keyword}</blockquote>", parse_mode=ParseMode.HTML)

# --- MUTE & UNMUTE ---
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message: return
    user_id = update.message.reply_to_message.from_user.id
    await context.bot.restrict_chat_member(update.effective_chat.id, user_id, ChatPermissions(can_send_messages=False))
    await update.message.reply_text("<blockquote> Muteလိုက်ပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message: return
    user_id = update.message.reply_to_message.from_user.id
    await context.bot.restrict_chat_member(update.effective_chat.id, user_id, ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
    await update.message.reply_text("<blockquote>Muteဖြည်လိုက်ပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- SECURITY MONITOR ---
async def security_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    data = get_data()
    text = update.message.text.lower()
    
    # 1. Anti-Link
    if data["settings"].get("antilink") and not (await is_admin(update)):
        if re.search(r'(https?://\S+|t\.me/\S+)', update.message.text):
            await update.message.delete()
            return

    # 2. Filters
    if text in data.get("filters", {}):
        await update.message.reply_text(f"<blockquote>{data['filters'][text]}</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_user))
    app.add_handler(CommandHandler("addfilter", add_filter))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))
    app.add_handler(CommandHandler("addbully", add_bully)) # ... (Existing commands)
    app.add_handler(CommandHandler("bully", start_bully))
    app.add_handler(CommandHandler("stopbully", stop_bully))
    app.add_handler(CommandHandler("id", lambda u,c: u.message.reply_text(f"🆔 ID: {u.effective_user.id}")))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), security_monitor))
    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
