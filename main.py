import logging
import asyncio
import random
import os
from datetime import timedelta
from pymongo import MongoClient
from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes, JobQueue
)

# --- CONFIGURATION ---
TOKEN = "8575371720:AAHjBOXArgOAtBUqPY_8xnZjQe-w4Dk4uRc"
OWNER_ID = 6015356597
# မင်းပေးထားတဲ့ MongoDB String ကို ဒီမှာ ထည့်လိုက်ပြီ
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
            "bully_list": [
                "မင်းရုပ်က error တစ်ခုပဲ", "မအေလိုး... ဖုန်မှုန့်လောက်တောင် တန်ဖိုးမရှိဘူး",
                "စောက်ရူး... မင်းရဲ့ ဦးနှောက်က သုတ်ပိုးတွေနဲ့ပဲ ပြည့်နေတာလား",
                "မင်းအမေကို ငါလိုးတာ ခါးတောင်ကျိုးနေပြီ စောက်ဆင့်မရှိတဲ့ကောင်",
                "ကလစ်ဆိုမင်းမေခေါင်းပန်လိုက်ကွာ", "လီးပဲပြန်ဆဲစမ်း"
            ],
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
        await update.message.reply_text(
            "<blockquote>ညီမင်းမှာ သုံးခွင့်မရှိဘူး၊သုံးမယ်ဆို @Besties_with_BoD ကိုလာတောင်း🫵</blockquote>", 
            parse_mode=ParseMode.HTML
        )
        return False
    return True

# --- ADMIN TOOLS ---
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("Ban ချင်တဲ့သူကို Reply ပြန်ပါ။")
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"<blockquote>🚫 <b>Banned:</b> {target.first_name}</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("Mute ချင်တဲ့သူကို Reply ပြန်ပါ။")
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, 
            target.id, 
            ChatPermissions(can_send_messages=False), 
            until_date=timedelta(days=1)
        )
        await update.message.reply_text(f"<blockquote>🔇 <b>Muted:</b> {target.first_name} (24hr)</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# --- BULLY LOGIC ---
async def start_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("Bully ချင်တဲ့သူကို Reply ပြန်ပါ။")

    target = update.message.reply_to_message.from_user
    target_mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
    chat_id = update.effective_chat.id
    job_name = f"bully_{chat_id}"

    # အရင်ရှိနေတဲ့ job တွေကို အကုန်အရင်ဖြုတ်မယ်
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for j in current_jobs: 
        j.schedule_removal()
    
    await update.message.reply_text(f"<blockquote>ငါစ bully ပြီ {target_mention}။</blockquote>", parse_mode=ParseMode.HTML)

    async def loop_cb(ctx: ContextTypes.DEFAULT_TYPE):
        data = get_data()
        phrase = random.choice(data["bully_list"])
        try:
            await ctx.bot.send_message(chat_id, f"<blockquote>{target_mention} {phrase}</blockquote>", parse_mode=ParseMode.HTML)
        except:
            pass

    context.job_queue.run_repeating(loop_cb, interval=3, name=job_name)

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update): return
    job_name = f"bully_{update.effective_chat.id}"
    jobs = context.job_queue.get_jobs_by_name(job_name)
    if jobs:
        for j in jobs: 
            j.schedule_removal()
        await update.message.reply_text("<blockquote>✅ Bully ရပ်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("<blockquote>လက်ရှိမှာ bully နေတာ မရှိပါဘူး။</blockquote>", parse_mode=ParseMode.HTML)

# --- DATABASE COMMANDS ---
async def add_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try: target_id = int(context.args[0])
        except: pass

    if target_id:
        data = get_data()
        if target_id not in data["allowed_users"]:
            data["allowed_users"].append(target_id)
            update_db("allowed_users", data["allowed_users"])
            await update.message.reply_text(f"<blockquote>✅ User <code>{target_id}</code> ကို ပါမစ်ပေးလိုက်ပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def add_bully_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update): return
    phrase = " ".join(context.args)
    if phrase:
        data = get_data()
        data["bully_list"].append(phrase)
        update_db("bully_list", data["bully_list"])
        await update.message.reply_text(f"<blockquote>✅ စာသားသစ် ထည့်ပြီးပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("bully", start_bully))
    app.add_handler(CommandHandler("stopbully", stop_bully))
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler("addbully", add_bully_phrase))
    app.add_handler(CommandHandler("id", lambda u, c: u.message.reply_text(f"🆔 Your ID: <code>{u.effective_user.id}</code>", parse_mode=ParseMode.HTML)))

    print("Bot is starting with MongoDB Atlas...")
    app.run_polling()

if __name__ == "__main__":
    main()
