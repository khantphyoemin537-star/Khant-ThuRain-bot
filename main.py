import logging
import asyncio
import random
import os
from datetime import timedelta
from pymongo import MongoClient
from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = "8575371720:AAHjBOXArgOAtBUqPY_8xnZjQe-w4Dk4uRc"
OWNER_ID = 6015356597
# MongoDB Connection String (Render ရဲ့ Env မှာ ထည့်ထားရမယ်)
MONGO_URI = os.getenv("MONGO_URI", "မင်းရဲ့_mongodb_connection_string_ဒီမှာထည့်")

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
            "bully_list": ["မင်းရုပ်က error တစ်ခုပဲ", "မအေလိုး... ဖုန်မှုန့်လောက်တောင် တန်ဖိုးမရှိဘူး"],
            "registered_groups": []
        }
        collection.insert_one(data)
    return data

def update_db(key, value):
    collection.update_one({"_id": "config"}, {"$set": {key: value}})

# --- PERMISSION CHECK ---
async def check_permission(update: Update):
    data = get_data()
    if update.effective_user.id not in data["allowed_users"]:
        await update.message.reply_text("<blockquote>ညီမင်းမှာ သုံးခွင့်မရှိဘူး၊သုံးမယ်ဆို @Besties_with_BoD ကိုလာတောင်း🫵</blockquote>", parse_mode=ParseMode.HTML)
        return False
    return True

# --- ADMIN TOOLS ---
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update): return
    if not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"<blockquote>🚫 <b>Banned:</b> {target.first_name}</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e: await update.message.reply_text(f"Error: {e}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update): return
    if not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, ChatPermissions(can_send_messages=False), until_date=timedelta(days=1))
        await update.message.reply_text(f"<blockquote>🔇 <b>Muted:</b> {target.first_name} (24hr)</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e: await update.message.reply_text(f"Error: {e}")

# --- BULLY LOGIC ---
async def start_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update): return
    if not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    target_mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
    job_name = f"bully_{update.effective_chat.id}"
    
    for j in context.job_queue.get_jobs_by_name(job_name): j.schedule_removal()
    await update.message.reply_text(f"<blockquote>ငါစ bully ပြီ {target_mention}။</blockquote>", parse_mode=ParseMode.HTML)

    async def loop_cb(ctx):
        data = get_data()
        phrase = random.choice(data["bully_list"])
        try: await ctx.bot.send_message(update.effective_chat.id, f"<blockquote>{target_mention} {phrase}</blockquote>", parse_mode=ParseMode.HTML)
        except: pass
    context.job_queue.run_repeating(loop_cb, interval=3, name=job_name)

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update): return
    jobs = context.job_queue.get_jobs_by_name(f"bully_{update.effective_chat.id}")
    for j in jobs: j.schedule_removal()
    await update.message.reply_text("<blockquote>✅ Bully ရပ်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def add_bully_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update): return
    phrase = " ".join(context.args)
    if phrase:
        data = get_data()
        data["bully_list"].append(phrase)
        update_db("bully_list", data["bully_list"])
        await update.message.reply_text("<blockquote>✅ စာသားသစ် ထည့်ပြီးပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- BROADCAST & GROUP TRACKING ---
async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ["group", "supergroup"]:
        data = get_data()
        if update.effective_chat.id not in data["registered_groups"]:
            data["registered_groups"].append(update.effective_chat.id)
            update_db("registered_groups", data["registered_groups"])

async def send_all_gp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    msg = " ".join(context.args)
    data = get_data()
    count = 0
    for gp_id in data["registered_groups"]:
        try:
            await context.bot.send_message(gp_id, f"<blockquote>📢 {msg}</blockquote>", parse_mode=ParseMode.HTML)
            count += 1
        except: pass
    await update.message.reply_text(f"✅ {count} groups ဆီ ပို့ပြီးပြီ။")

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & ~filters.COMMAND, track_groups), group=0)
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("bully", start_bully))
    app.add_handler(CommandHandler("stopbully", stop_bully))
    app.add_handler(CommandHandler("addbully", add_bully_phrase))
    app.add_handler(CommandHandler("sendallgp", send_all_gp))
    app.add_handler(CommandHandler("id", lambda u, c: u.message.reply_text(f"ID: {u.effective_user.id}")))
    
    print("Bot is online with MongoDB...")
    app.run_polling()

if __name__ == "__main__":
    main()
