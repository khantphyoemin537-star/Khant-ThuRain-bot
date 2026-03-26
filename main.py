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
TOKEN = "8575371720:AAHjBOXArgOAtBU*Y_8xnZjQe-w4Dk4uRc"
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

# --- WELCOME & GOODBYE ---
async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    for member in update.message.new_chat_members:
        if member.id == context.bot.id: continue
        mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
        await context.bot.send_message(
            chat_id=chat.id,
            text=f"<blockquote>ဟိတ် {mention}! <b>{chat.title}</b> မှ ကြိုဆိုလိုက်ပါတယ်!</blockquote>",
            parse_mode=ParseMode.HTML
        )
        data = get_data()
        groups = data.get("registered_groups", [])
        if chat.id not in groups:
            groups.append(chat.id)
            update_db("registered_groups", groups)

async def goodbye_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.message.left_chat_member
    if member:
        mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"<blockquote>ဟုတ် {mention} ထွက်သွားပါပြီ။ <b>{update.effective_chat.title}</b></blockquote>",
            parse_mode=ParseMode.HTML
        )

# --- BULLY LOGIC (MENTION & REPLY) ---
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

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    chat_id = update.effective_chat.id
    job_name = f"bully_{chat_id}"
    jobs = context.job_queue.get_jobs_by_name(job_name)
    if not jobs:
        return await update.message.reply_text("<blockquote>❌ ရပ်စရာ Loop မရှိပါ</blockquote>", parse_mode=ParseMode.HTML)
    for job in jobs: job.schedule_removal()
    await update.message.reply_text("<blockquote>✅ Bully loop အကုန်လုံးကို ရပ်တန့်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- MANAGEMENT & MODERATION ---
async def add_allowed_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message: return await update.message.reply_text("<blockquote>ပါမစ်ပေးမည့်သူကို Reply ပြန်ပါ။</blockquote>", parse_mode=ParseMode.HTML)
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
    if not update.message.reply_to_message: return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, update.message.reply_to_message.from_user.id)
        await update.message.reply_text("<blockquote>🚫 Ban လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    except: await update.message.reply_text("<blockquote>Error: Admin permission လိုအပ်သည်။</blockquote>", parse_mode=ParseMode.HTML)

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message: return
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, update.message.reply_to_message.from_user.id, permissions=ChatPermissions(can_send_messages=False))
        await update.message.reply_text("<blockquote>🔇 Mute လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    except: await update.message.reply_text("<blockquote>Error ဖြစ်သွားသည်။</blockquote>", parse_mode=ParseMode.HTML)

# --- MESSAGES & FILTERS ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text
    chat_id = update.effective_chat.id
    data = get_data()

    filters_dict = data.get("filters", {})
    if text.lower() in filters_dict:
        await update.message.reply_text(f"<blockquote>{filters_dict[text.lower()]}</blockquote>", parse_mode=ParseMode.HTML)

    if chat_id == TARGET_CHAT_ID and data.get("autosave", False):
        if update.effective_user.id in data["allowed_users"]:
            bully_list = data.get("bully_list", [])
            if text not in bully_list:
                bully_list.append(text)
                update_db("bully_list", bully_list)

async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if len(context.args) < 2: return await update.message.reply_text("<blockquote>/addfilter [keyword] [reply]</blockquote>", parse_mode=ParseMode.HTML)
    keyword, reply_msg = context.args[0].lower(), " ".join(context.args[1:])
    data = get_data()
    filters_dict = data.get("filters", {})
    filters_dict[keyword] = reply_msg
    update_db("filters", filters_dict)
    await update.message.reply_text(f"<blockquote>✅ Filter Added: {keyword}</blockquote>", parse_mode=ParseMode.HTML)

async def count_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    data = get_data()
    blist = data.get("bully_list", [])
    await update.message.reply_text(f"<blockquote>📊 Bully list ထဲမှာ <b>{len(blist)}</b> ကြောင်းရှိပါတယ်။</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("bully", lambda u,c: start_bully_base(u,c, mode="mention")))
    app.add_handler(CommandHandler("replybully", lambda u,c: start_bully_base(u,c, mode="reply")))
    app.add_handler(CommandHandler("stopbully", stop_bully))
    app.add_handler(CommandHandler("addallow", add_allowed_user))
    app.add_handler(CommandHandler("addfilter", add_filter))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("count", count_list))
    app.add_handler(CommandHandler("autosave_on", lambda u,c: update_db("autosave", True) or u.message.reply_text("<blockquote>✅ Auto-save On</blockquote>", parse_mode=ParseMode.HTML)))
    app.add_handler(CommandHandler("autosave_off", lambda u,c: update_db("autosave", False) or u.message.reply_text("<blockquote>❌ Auto-save Off</blockquote>", parse_mode=ParseMode.HTML)))
    app.add_handler(CommandHandler("myid", lambda u,c: u.message.reply_text(f"<blockquote>🆔 ID: {u.effective_user.id}</blockquote>", parse_mode=ParseMode.HTML)))
    
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_user))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    
    print("Young Master ThuRain Starting...")
    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
