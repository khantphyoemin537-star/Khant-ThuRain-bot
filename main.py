import logging
import asyncio
import random
import os
import re
from datetime import timedelta
from pymongo import MongoClient
from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes
)
# --- UPTIMEROBOT & FLASK SETUP ---
from flask import Flask
from threading import Thread

app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Young Master KhantThuRain Bot is Alive!"

def run():
    # Hugging Face Spaces က port 7860 ကို သုံးပါတယ်
    app_flask.run(host='0.0.0.0', port=7860)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURATION ---
TOKEN = "8575371720:AAHjBOXArgOAtBUqPY_8xnZjQe-w4Dk4uRc"
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

# --- MONGODB SETUP ---
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
            "warns": {},
            "settings": {"antilink": False}
        }
        collection.insert_one(data)
    return data

def update_db(key, value):
    collection.update_one({"_id": "config"}, {"$set": {key: value}})

# --- PERMISSION CHECK ---
async def is_admin(update: Update):
    data = get_data()
    if update.effective_user.id in data["allowed_users"]:
        return True
    await update.message.reply_text(
        "<blockquote>ညီမင်းမှာ သုံးခွင့်မရှိဘူး၊သုံးမယ်ဆို @Besties_with_BoD ကိုလာတောင်း🫵</blockquote>", 
        parse_mode=ParseMode.HTML
    )
    return False

# --- BULLY LOGIC ---
async def add_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    text = " ".join(context.args)
    if not text:
        return await update.message.reply_text("<blockquote>Usage: /addbully [message]</blockquote>", parse_mode=ParseMode.HTML)
    data = get_data()
    bully_list = data.get("bully_list", [])
    bully_list.append(text)
    update_db("bully_list", bully_list)
    await update.message.reply_text(f"<blockquote>✅ Added: {text}</blockquote>", parse_mode=ParseMode.HTML)

async def start_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("Bully ချင်တဲ့သူကို Reply ပြန်ပါ။")
    target = update.message.reply_to_message.from_user
    target_mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
    chat_id = update.effective_chat.id
    job_name = f"bully_{chat_id}"
    for j in context.job_queue.get_jobs_by_name(job_name): j.schedule_removal()
    await update.message.reply_text(f"<blockquote>ငါစ bully ပြီ {target_mention}။</blockquote>", parse_mode=ParseMode.HTML)
    async def loop_cb(ctx):
        data = get_data()
        phrase = random.choice(data["bully_list"])
        try: await ctx.bot.send_message(chat_id, f"<blockquote>{target_mention} {phrase}</blockquote>", parse_mode=ParseMode.HTML)
        except: pass
    context.job_queue.run_repeating(loop_cb, interval=3, name=job_name)

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    jobs = context.job_queue.get_jobs_by_name(f"bully_{update.effective_chat.id}")
    if jobs:
        for j in jobs: j.schedule_removal()
        await update.message.reply_text("<blockquote>✅ Bully ရပ်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- ADMIN & SECURITY ---
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message: return
    user = update.message.reply_to_message.from_user
    await context.bot.ban_chat_member(update.effective_chat.id, user.id)
    await update.message.reply_text(f"<blockquote>{user.mention_html()} has been banned.</blockquote>", parse_mode=ParseMode.HTML)

async def security_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    data = get_data()
    if data["settings"].get("antilink") and not (await is_admin(update)):
        if re.search(r'(https?://\S+|t\.me/\S+)', update.message.text):
            await update.message.delete()
            return

async def add_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    data = get_data()
    allowed = data.get("allowed_users", [])
    if update.message.reply_to_message: target_id = update.message.reply_to_message.from_user.id
    elif context.args: target_id = int(context.args[0])
    else: return
    if target_id not in allowed:
        allowed.append(target_id)
        update_db("allowed_users", allowed)
        await update.message.reply_text(f"<blockquote>ID: {target_id} Granted.</blockquote>", parse_mode=ParseMode.HTML)

# --- BROADCAST & HELP ---
async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_data()
    if update.effective_chat.id not in data["registered_groups"]:
        data["registered_groups"].append(update.effective_chat.id)
        update_db("registered_groups", data["registered_groups"])

async def send_all_gp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    text = " ".join(context.args)
    if not text: return
    data = get_data()
    for gid in data.get("registered_groups", []):
        try: await context.bot.send_message(gid, f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML)
        except: pass
    await update.message.reply_text("<blockquote>Broadcast sent.</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("addbully", add_bully))
    app.add_handler(CommandHandler("bully", start_bully))
    app.add_handler(CommandHandler("stopbully", stop_bully))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler("sendallgp", send_all_gp))
    app.add_handler(CommandHandler("id", lambda u, c: u.message.reply_text(f"🆔 ID: {u.effective_user.id}")))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), security_monitor))

    print("Young Master Bot is starting with Keep-Alive...")
    app.run_polling()

if __name__ == "__main__":
    keep_alive() # Web Server ကို Background မှာ အရင်ဖွင့်မယ်
    main()       # ပြီးမှ Bot ကို Run မယ်
