import asyncio
import re
import os
import logging
from pymongo import MongoClient
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- LOGGING SETUP ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION ---
TOKEN = "8575371720:AAHR_1fCkRxlALIbhMH0yufXGJiUSQYJyYE" 
OWNER_ID = 6015356597
SAVE_CHAT = -1003864912245  
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
async def is_allow(update: Update):
    uid = update.effective_user.id
    if uid == OWNER_ID or uid in get_list("allow"): 
        return True
    await update.message.reply_text(
        "<blockquote>ညီမင်းမှာသုံးခွင့်မရှိဘူး 🫵 @Besties_with_BoD ကိုလာတောင်း</blockquote>", 
        parse_mode=ParseMode.HTML
    )
    return False

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid == OWNER_ID: return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, uid)
        return member.status in ['administrator', 'creator']
    except: return False

# --- ADD ALLOW (ALLY PERMISSION) ---
async def addallow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Owner တစ်ယောက်တည်းပဲ ပါမစ်ပေးခွင့်ရှိမယ်
    if update.effective_user.id != OWNER_ID:
        return

    # Reply ပြန်ထားခြင်း ရှိမရှိ စစ်မယ်
    if not update.message.reply_to_message:
        return await update.message.reply_text(
            "<blockquote>ပါမစ်ပေးမည့်သူကို Reply ပြန်ပြီး command ရိုက်ပါ။</blockquote>", 
            parse_mode=ParseMode.HTML
        )

    target_user = update.message.reply_to_message.from_user
    uid = target_user.id
    allow_list = get_list("allow")
    
    if uid not in allow_list:
        allow_list.append(uid)
        set_list("allow", allow_list)
        await update.message.reply_text(
            f"<blockquote>✅ User <a href='tg://user?id={uid}'>{target_user.full_name}</a> ကို ပါမစ် (Ally) ပေးလိုက်ပါပြီ။</blockquote>", 
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            "<blockquote>ဒီ User က Ally list ထဲမှာ ရှိပြီးသားပါ။</blockquote>", 
            parse_mode=ParseMode.HTML
        )

# --- BULLY LOGIC ---
async def bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allow(update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("<blockquote>Bully လုပ်မယ့်သူကို reply ပြန်ပါ</blockquote>", parse_mode=ParseMode.HTML)

    chat_id = update.effective_chat.id
    user = update.message.reply_to_message.from_user
    mention_link = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    
    bully_words = get_list("bully")
    if not bully_words:
        return await update.message.reply_text("<blockquote>Bully list ထဲမှာ စာသားမရှိသေးပါ</blockquote>", parse_mode=ParseMode.HTML)

    if chat_id in bully_tasks:
        bully_tasks[chat_id].cancel()
    
    async def bully_loop():
        try:
            while True:
                for word in bully_words:
                    await context.bot.send_message(
                        chat_id, 
                        f"<blockquote>{mention_link} {word}</blockquote>", 
                        parse_mode=ParseMode.HTML
                    )
                    await asyncio.sleep(3)
        except asyncio.CancelledError:
            pass 

    bully_tasks[chat_id] = asyncio.create_task(bully_loop())
    await update.message.reply_text(f"<blockquote>🔥 {user.full_name} ကို Bully စတင်ပါပြီ</blockquote>", parse_mode=ParseMode.HTML)

async def stopbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allow(update): return
    
    chat_id = update.effective_chat.id
    if chat_id in bully_tasks:
        bully_tasks[chat_id].cancel() 
        del bully_tasks[chat_id]
        await update.message.reply_text("<blockquote>✅ Bully အကုန်ရပ်လိုက်ပါပြီ</blockquote>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("<blockquote>ရပ်စရာ Bully မရှိပါ</blockquote>", parse_mode=ParseMode.HTML)

# --- WELCOME HANDLER ---
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except:
        pass

    group_name = update.effective_chat.title

    for m in update.message.new_chat_members:
        if m.id == context.bot.id: continue
        mention = f'<a href="tg://user?id={m.id}">{m.full_name}</a>'
        await context.bot.send_message(
            update.effective_chat.id,
            f"<blockquote>ဟိတ် {mention}! {group_name} ကနေ ကြိုဆိုလိုက်ပါတယ်!</blockquote>",
            parse_mode=ParseMode.HTML
        )

# --- MAIN HANDLER (Filters & Save) ---
async def main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    chat_id, uid = update.effective_chat.id, update.effective_user.id
    
    if chat_id == SAVE_CHAT and get_bool("save") and (uid == OWNER_ID or uid in get_list("allow")):
        content = update.message.text or update.message.caption
        if content:
            bully_list = get_list("bully")
            if content not in bully_list:
                bully_list.append(content)
                set_list("bully", bully_list)
                await update.message.reply_text(f"<blockquote>📝 Learned: {content}</blockquote>", parse_mode=ParseMode.HTML)

    if not update.message.text: return
    text = update.message.text

    if not await is_admin(update, context):
        if re.search(LINK_REGEX, text):
            await update.message.delete()
            return

    f_data = db.filters.find_one({"_id": text.lower()})
    if f_data:
        await update.message.reply_text(f"<blockquote>{f_data['reply']}</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN START ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Register Commands
    app.add_handler(CommandHandler("addallow", addallow))
    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("stopbully", stopbully))
    app.add_handler(CommandHandler("save_on", lambda u,c: set_bool("save", True) or u.message.reply_text("<blockquote>✅ Learning Mode: ON</blockquote>", parse_mode=ParseMode.HTML)))
    app.add_handler(CommandHandler("save_off", lambda u,c: set_bool("save", False) or u.message.reply_text("<blockquote>❌ Learning Mode: OFF</blockquote>", parse_mode=ParseMode.HTML)))
    
    # Message Handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION | filters.FORWARDED) & ~filters.COMMAND, main_handler))
    
    print("🚀 Young Master ThuRain is Online...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
