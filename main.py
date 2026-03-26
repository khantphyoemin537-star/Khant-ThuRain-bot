import logging
import asyncio
import random
import os
from pymongo import MongoClient
from flask import Flask
from threading import Thread
from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes
)

# --- Keep Alive Section ---
app_flask = Flask('')
@app_flask.route('/')
def home(): return "Young Master ThuRain is Online!"
def run():
    port = int(os.environ.get("PORT", 7860))
    app_flask.run(host='0.0.0.0', port=port)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURATION ---
TOKEN = "8575371720:AAHOa0swN0u4NI0hLI2nJTMVs8u7BDkPpQA" 
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"
TARGET_CHAT_ID = -1003864912245 

client = MongoClient(MONGO_URI)
db = client['bully_bot_db']
collection = db['bot_data']

bully_indexes = {}

def get_data():
    data = collection.find_one({"_id": "config"})
    if not data:
        data = {
            "_id": "config",
            "allowed_users": [OWNER_ID],
            "bully_list": ["မင်းရုပ်က error တစ်ခုပဲ"],
            "autosave": False,
            "registered_groups": [],
            "filters": {}
        }
        collection.insert_one(data)
    return data

def update_db(key, value):
    collection.update_one({"_id": "config"}, {"$set": {key: value}})

async def is_admin(update: Update):
    data = get_data()
    if update.effective_user.id in data["allowed_users"]:
        return True
    await update.message.reply_text("<blockquote>ညီမင်းမှာ သုံးခွင့်မရှိဘူး၊သုံးမယ်ဆို @Besties_with_BoD ကိုလာတောင်း🫵</blockquote>", parse_mode=ParseMode.HTML)
    return False

# --- MODERATION FUNCTIONS (WITH REPLY) ---
async def add_allowed_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message: 
        return await update.message.reply_text("<blockquote>ပါမစ်ပေးမည့်သူကို Reply ပြန်ပါ။</blockquote>", parse_mode=ParseMode.HTML)
    
    target_id = update.message.reply_to_message.from_user.id
    data = get_data()
    allowed = data.get("allowed_users", [])
    if target_id not in allowed:
        allowed.append(target_id)
        update_db("allowed_users", allowed)
        await update.message.reply_text(f"<blockquote>✅ User {target_id} ကို Bot သုံးခွင့်ပေးလိုက်ပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("<blockquote>ဒီ user က list ထဲမှာရှိပြီးသားပါ။</blockquote>", parse_mode=ParseMode.HTML)

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message: 
        return await update.message.reply_text("<blockquote>Ban မည့်သူကို Reply ပြန်ပါ။</blockquote>", parse_mode=ParseMode.HTML)
    try:
        target_id = update.message.reply_to_message.from_user.id
        await context.bot.ban_chat_member(update.effective_chat.id, target_id)
        await update.message.reply_text("<blockquote>🚫 User ကို Ban လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"<blockquote>❌ Error: {e}</blockquote>", parse_mode=ParseMode.HTML)

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("<blockquote>Mute မည့်သူကို Reply ပြန်ပါ။</blockquote>", parse_mode=ParseMode.HTML)
    try:
        target_id = update.message.reply_to_message.from_user.id
        await context.bot.restrict_chat_member(
            update.effective_chat.id, 
            target_id, 
            permissions=ChatPermissions(can_send_messages=False)
        )
        await update.message.reply_text("<blockquote>🔇 User ကို Mute လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"<blockquote>❌ Error: {e}</blockquote>", parse_mode=ParseMode.HTML)

# --- BULLY LOGIC ---
async def start_bully_base(update: Update, context: ContextTypes.DEFAULT_TYPE, mode="mention"):
    if not await is_admin(update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text(f"<blockquote>Reply someone နှင့် /{mode}bully သုံးပါ</blockquote>", parse_mode=ParseMode.HTML)
    
    target_msg = update.message.reply_to_message
    target_user = target_msg.from_user
    mention = f'<a href="tg://user?id={target_user.id}">{target_user.first_name}</a>'
    chat_id = update.effective_chat.id
    job_name = f"bully_{chat_id}"

    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in current_jobs: job.schedule_removal()
    
    await update.message.reply_text(f"<blockquote>😎 Bully {mode} start: {mention}</blockquote>", parse_mode=ParseMode.HTML)
    bully_indexes[chat_id] = 0

    async def bully_loop(ctx):
        data = get_data()
        blist = data.get("bully_list", [])
        if not blist: return
        idx = bully_indexes.get(chat_id, 0)
        if idx >= len(blist): idx = 0
        phrase = blist[idx]
        try:
            if mode == "reply":
                await ctx.bot.send_message(chat_id, f"<blockquote>{phrase}</blockquote>", reply_to_message_id=target_msg.message_id, parse_mode=ParseMode.HTML)
            else:
                await ctx.bot.send_message(chat_id, f"<blockquote>{mention} {phrase}</blockquote>", parse_mode=ParseMode.HTML)
            bully_indexes[chat_id] = idx + 1
        except: pass

    context.job_queue.run_repeating(bully_loop, interval=3, name=job_name)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("bully", lambda u,c: start_bully_base(u,c, mode="mention")))
    app.add_handler(CommandHandler("replybully", lambda u,c: start_bully_base(u,c, mode="reply")))
    app.add_handler(CommandHandler("addallow", add_allowed_user))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("mute", mute_user))
    
    # ... (ကျန်တဲ့ welcome/goodbye နဲ့ message_handler logic တွေ အရင်အတိုင်း ထည့်ပါ)
    
    print("🚀 Young Master ThuRain is starting...")
    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
