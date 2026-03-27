import asyncio
import re
import os
import logging
from pymongo import MongoClient
from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION ---
TOKEN = "8575371720:AAHjBOXArgOAtBU*Y_8xnZjQe-w4Dk4uRc"
OWNER_ID = 6015356597
SAVE_CHAT = -1003864912245  # မင်းစာလာပို့မည့် GP ID (ဒီထဲပို့ရင် bully words ထဲဝင်မယ်)
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"
LINK_REGEX = r"(https?://|t\.me|telegram\.me|www\.)"

# --- DATABASE CONNECTION ---
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]

bully_tasks = {}

# --- DB HELPERS ---
def get_list(name):
    data = db.settings.find_one({"_id": name})
    return data.get("data", []) if data else []

def set_list(name, data):
    db.settings.update_one({"_id": name}, {"$set": {"data": data}}, upsert=True)

def get_bool(name):
    data = db.settings.find_one({"_id": name})
    return data.get("data", False) if data else False

def set_bool(name, val):
    db.settings.update_one({"_id": name}, {"$set": {"data": val}}, upsert=True)

# --- PERMISSIONS ---
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid == OWNER_ID: return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, uid)
        return member.status in ['administrator', 'creator']
    except: return False

async def is_allow(update: Update):
    uid = update.effective_user.id
    if uid == OWNER_ID or uid in get_list("allow"): return True
    await update.message.reply_text("<blockquote>bot သုံးခွင့်မရှိပါဘူး</blockquote>", parse_mode=ParseMode.HTML)
    return False

# --- COMMANDS ---
async def addallow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message:
        return await update.message.reply_text("<blockquote>ပါမစ်ပေးမည့်သူကို Reply ပြန်ပါ။</blockquote>", parse_mode=ParseMode.HTML)
    uid = update.message.reply_to_message.from_user.id
    allow = get_list("allow")
    if uid not in allow:
        allow.append(uid)
        set_list("allow", allow)
        await update.message.reply_text(f"<blockquote>✅ User {uid} allowed</blockquote>", parse_mode=ParseMode.HTML)

async def save_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allow(update): return
    set_bool("save", True)
    await update.message.reply_text("<blockquote>✅ Auto-Learning ON (SAVE_CHAT ထဲပို့သမျှစာကို bully list ထဲထည့်ပါမည်)</blockquote>", parse_mode=ParseMode.HTML)

async def save_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allow(update): return
    set_bool("save", False)
    await update.message.reply_text("<blockquote>❌ Auto-Learning OFF</blockquote>", parse_mode=ParseMode.HTML)

# --- BULLY LOGIC ---
async def bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allow(update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("<blockquote>Bully လုပ်မယ့်သူကို reply ပြန်ပါ</blockquote>", parse_mode=ParseMode.HTML)

    chat_id = update.effective_chat.id
    user = update.message.reply_to_message.from_user
    full_name = user.first_name
    bully_words = get_list("bully")
    
    if not bully_words:
        return await update.message.reply_text("<blockquote>Bully list ထဲမှာ စာသားမရှိသေးပါ</blockquote>", parse_mode=ParseMode.HTML)

    key = (chat_id, user.id)
    if key in bully_tasks: bully_tasks[key].cancel()

    async def bully_loop():
        try:
            while True:
                for word in bully_words:
                    await context.bot.send_message(chat_id, f"<blockquote>{full_name} {word}</blockquote>", parse_mode=ParseMode.HTML)
                    await asyncio.sleep(3)
        except: pass

    bully_tasks[key] = asyncio.create_task(bully_loop())
    await update.message.reply_text(f"<blockquote>🔥 {full_name} ကို Bully စတင်ပါပြီ</blockquote>", parse_mode=ParseMode.HTML)

async def stopbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allow(update): return
    chat_id = update.effective_chat.id
    for key in list(bully_tasks.keys()):
        if key[0] == chat_id:
            bully_tasks[key].cancel()
            del bully_tasks[key]
    await update.message.reply_text("<blockquote>✅ Bully အကုန်ရပ်လိုက်ပါပြီ</blockquote>", parse_mode=ParseMode.HTML)

# --- WELCOME & GOODBYE ---
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_title = update.effective_chat.title
    for m in update.message.new_chat_members:
        if m.id == context.bot.id: continue
        await update.message.reply_text(f"<blockquote>ဟိတ် {m.first_name}! {group_title} ကနေ ကြိုဆိုလိုက်ပါတယ်!</blockquote>", parse_mode=ParseMode.HTML)

async def goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.left_chat_member
    if user:
        mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
        await update.message.reply_text(f"<blockquote>ဟုတ် {mention} ထွက်သွားလိုက်ပါပြီ!</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN HANDLER ---
async def main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    chat_id = update.effective_chat.id
    uid = update.effective_user.id
    
    # 1. Learning Logic (ဒီအပိုင်းက မင်းပြောတဲ့ feature ပါ)
    if chat_id == SAVE_CHAT and get_bool("save"):
        if uid == OWNER_ID or uid in get_list("allow"):
            # စာသားရယူမယ် (ရိုးရိုးစာ သို့မဟုတ် ပုံနဲ့တွဲပါတဲ့စာ)
            content = update.message.text or update.message.caption
            if content:
                bully_list = get_list("bully")
                if content not in bully_list:
                    bully_list.append(content)
                    set_list("bully", bully_list)
                    # မင်းပို့လိုက်တဲ့စာကို Bot က မှတ်မိသွားကြောင်း အကြောင်းပြန်မယ်
                    await update.message.reply_text(f"<blockquote>📝 Added to Bully Words: {content}</blockquote>", parse_mode=ParseMode.HTML)

    if not update.message.text: return
    text = update.message.text

    # 2. Antilink
    if not await is_admin(update, context):
        if re.search(LINK_REGEX, text):
            await update.message.delete()
            return await context.bot.send_message(chat_id, f"<blockquote>ဒီမှာ link ချခွင့်မရှိပါဘူး {update.effective_user.first_name}</blockquote>", parse_mode=ParseMode.HTML)

    # 3. Filter Reply
    f_data = db.filters.find_one({"_id": text.lower()})
    if f_data:
        await update.message.reply_text(f"<blockquote>{f_data['reply']}</blockquote>", parse_mode=ParseMode.HTML)

# --- APP START ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("addallow", addallow))
    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("stopbully", stopbully))
    app.add_handler(CommandHandler("save_on", save_on))
    app.add_handler(CommandHandler("save_off", save_off))
    app.add_handler(CommandHandler("myid", lambda u,c: u.message.reply_text(f"<blockquote>🆔 ID: {u.effective_user.id}</blockquote>", parse_mode=ParseMode.HTML)))
    
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye))
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION | filters.FORWARDED) & ~filters.COMMAND, main_handler))
    
    print("🚀 Young Master ThuRain is Learning Bully Words...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
