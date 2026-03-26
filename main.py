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

# --- UPTIMEROBOT & FLASK (Keep Alive) ---
app_flask = Flask('')
@app_flask.route('/')
def home(): return "Bot is Alive!"
def run():
    port = int(os.environ.get("PORT", 7860))
    app_flask.run(host='0.0.0.0', port=port)
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
            "bully_list": ["မင်းရုပ်က error တစ်ခုပဲ", "ငါ့ရဲ့ ခြေဖျားကို မီအောင် အရင် ကြိုးစားလိုက်ဦး", "မအေလိုး...ငါတို့ရဲ့ အရှိန်အဝါအောက်မှာ မင်းက ဖုန်မှုန့်လောက်တောင် တန်ဖိုးမရှိဘူး"],
            "registered_groups": [],
            "filters": {},
            "settings": {"antilink": False}
        }
        collection.insert_one(data)
    return data

def update_db(key, value):
    collection.update_one({"_id": "config"}, {"$set": {key: value}})

# --- IS ADMIN CHECK ---
async def is_admin(update: Update):
    data = get_data()
    if update.effective_user.id in data["allowed_users"]:
        return True
    await update.message.reply_text("❌ မင်းမှာ bot သုံးခွင့်မရှိသေးဘူး။")
    return False

# --- WELCOME & GOODBYE ---
async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    for member in update.message.new_chat_members:
        mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
        await update.message.reply_text(f"ဟိတ် {mention}! <b>{chat.title}</b> မှ ကြိုဆိုလိုက်ပါတယ်!", parse_mode=ParseMode.HTML)
        # Register group for sendallgp
        data = get_data()
        if chat.id not in data["registered_groups"]:
            data["registered_groups"].append(chat.id)
            update_db("registered_groups", data["registered_groups"])

async def goodbye_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.message.left_chat_member
    if member:
        mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
        await update.message.reply_text(f"{mention} ထွက်သွားပါပြီ။ <b>{update.effective_chat.title}</b>", parse_mode=ParseMode.HTML)

# --- FILTERS ---
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if len(context.args) < 2: return await update.message.reply_text("သုံးနည်း: /addfilter [စာသား] [ပြန်ဖြေမည့်စာ]")
    keyword, reply = context.args[0].lower(), " ".join(context.args[1:])
    data = get_data()
    filters_dict = data.get("filters", {})
    filters_dict[keyword] = reply
    update_db("filters", filters_dict)
    await update.message.reply_text(f"✅ Filter ထည့်ပြီးပါပြီ: {keyword}")

# --- BULLY LOOP (SEQUENTIAL) ---
async def start_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply လုပ်ပြီး /bully သုံးပါ")
    
    target = update.message.reply_to_message.from_user
    mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
    job_name = f"bully_{update.effective_chat.id}_{target.id}"
    
    # Remove old job
    for job in context.job_queue.get_jobs_by_name(job_name):
        job.schedule_removal()
    
    await update.message.reply_text(f"😎 Bully start: {mention}", parse_mode=ParseMode.HTML)
    data = get_data()
    bully_list = data["bully_list"]
    index = 0

    async def bully_loop(ctx):
        nonlocal index
        if index >= len(bully_list): index = 0
        phrase = bully_list[index]
        index += 1
        try:
            await ctx.bot.send_message(update.effective_chat.id, f"{mention} {phrase}", parse_mode=ParseMode.HTML)
        except: pass

    context.job_queue.run_repeating(bully_loop, interval=3, name=job_name)

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    jobs = [job for job in context.job_queue.jobs() if "bully_" in job.name and str(update.effective_chat.id) in job.name]
    if not jobs: return await update.message.reply_text("❌ Bully loop မတွေ့ပါ")
    for j in jobs: j.schedule_removal()
    await update.message.reply_text("✅ Bully loop ရပ်လိုက်ပါပြီ")

async def add_bully_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    phrase = " ".join(context.args)
    if phrase:
        data = get_data()
        data["bully_list"].append(phrase)
        update_db("bully_list", data["bully_list"])
        await update.message.reply_text("✅ Bully စာသားအသစ်ထည့်ပြီးပါပြီ။")

# --- MUTE/UNMUTE ---
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message: return
    user_id = update.message.reply_to_message.from_user.id
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, user_id, ChatPermissions(can_send_messages=False))
        await update.message.reply_text("🔇 Mute လုပ်ပြီးပါပြီ")
    except: pass

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message: return
    user_id = update.message.reply_to_message.from_user.id
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, user_id, 
            ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
        )
        await update.message.reply_text("✅ Mute ဖြေပြီးပါပြီ")
    except: pass

# --- MESSAGE MONITOR ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    data = get_data()
    text = update.message.text.lower()
    # filters
    filters_dict = data.get("filters", {})
    if text in filters_dict:
        await update.message.reply_text(filters_dict[text])

# --- ALLOW USERS ---
async def add_allowed_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message: return await update.message.reply_text("Reply someone with /addallow")
    target_id = update.message.reply_to_message.from_user.id
    data = get_data()
    if target_id not in data["allowed_users"]:
        data["allowed_users"].append(target_id)
        update_db("allowed_users", data["allowed_users"])
        await update.message.reply_text(f"✅ User {target_id} ကို allow လုပ်ပြီးပါပြီ")

# --- ID COMMANDS ---
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Your ID: {update.effective_user.id}")

async def gpid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💬 Chat ID: {update.effective_chat.id}")

async def id_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    user_id = update.message.reply_to_message.from_user.id
    await update.message.reply_text(f"🆔 Replied User ID: {user_id}")

# --- SEND ALL GROUPS ---
async def send_all_gp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    text = " ".join(context.args)
    if not text: return await update.message.reply_text("စာသားထည့်ပါ")
    data = get_data()
    for chat_id in data["registered_groups"]:
        try:
            await context.bot.send_message(chat_id, text)
        except: pass
    await update.message.reply_text("✅ စာပို့ပြီးပါပြီ")

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("gpid", gpid))
    app.add_handler(CommandHandler("id", id_reply))
    app.add_handler(CommandHandler("addallow", add_allowed_user))
    app.add_handler(CommandHandler("sendallgp", send_all_gp))

    app.add_handler(CommandHandler("addfilter", add_filter))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))
    app.add_handler(CommandHandler("bully", start_bully))
    app.add_handler(CommandHandler("stopbully", stop_bully))
    app.add_handler(CommandHandler("addbully", add_bully_phrase))
    
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_user))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    
    print("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
