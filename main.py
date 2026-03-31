import asyncio
import re
import os
import logging
import random
from pymongo import MongoClient
from telegram import Update, ChatPermissions, ChatMember
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    ChatMemberHandler
)

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIG ---
TOKEN = "8575371720:AAHR_1fCkRxlALIbhMH0yufXGJiUSQYJyYE" 
OWNER_ID = 6015356597
ADMIN_GROUP_ID = -1003580630981
SAVE_CHAT_ID = -1003864912245  
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

# --- DB CONNECTION ---
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
bully_tasks = {} 
stop_events = {} 

# --- PERMISSIONS HELPERS ---
def is_owner(uid): return uid == OWNER_ID

def is_allow(uid):
    if uid == OWNER_ID: return True
    return db.allow_users.find_one({"user_id": uid}) is not None

def is_admin(uid):
    if uid == OWNER_ID: return True
    return db.admin_users.find_one({"user_id": uid}) is not None

# --- MEMBER UPDATES (Bot Tracker & Welcome) ---
async def member_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member if update.chat_member else update.my_chat_member
    if not result: return
    
    chat_id = update.effective_chat.id
    user = result.new_chat_member.user
    old_status, new_status = result.old_chat_member.status, result.new_chat_member.status

    # Bot Joined Group
    if user.id == context.bot.id:
        if new_status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
            if not db.groups.find_one({"chat_id": chat_id}):
                db.groups.insert_one({"chat_id": chat_id, "title": update.effective_chat.title})
                
                # Admin Log
                try:
                    log = f"<blockquote>👋 ကိုခန့်သူရိန်ဗျ @Wyaaqq_Zxyfanzt ကျနော်တို့ BoD_Brotherhood_of_Dexter Bot ကို ယူသုံးထားပါတယ်\n━━━━━━━━━━━━━━━━━━━━\n<b>Group Name:</b> {update.effective_chat.title}\n<b>Group ID:</b> <code>{chat_id}</code></blockquote>"
                    await context.bot.send_message(ADMIN_GROUP_ID, log, parse_mode=ParseMode.HTML)
                except: pass
                
                # Entry Message
                entry = "<blockquote>ဟိတ်ရို့ /admins မင်းတို့ရဲ့ဒီ group ဟိတ် ကို ထည့်သွင်းအသုံးပြုပေးတဲ့အတွက် ကျေးဇူး၊ အမ် အသုံးဝင်မယ့် တချို့ကန့်သန့်ထားတဲ့ bot command တွေသုံးမယ်ဆို @Besties_with_BoD က OWNER ခန့်သူရိန် ဆီကိုလာဆက်သွယ်ပေးပါ။</blockquote>"
                await context.bot.send_message(chat_id, entry, parse_mode=ParseMode.HTML)
        return

    # User Welcome/Goodbye
    mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    if old_status in ["left", "kicked"] and new_status in ["member", "administrator"]:
        await context.bot.send_message(chat_id, f"<blockquote>ဟိတ် {mention}! {update.effective_chat.title} ကနေ ကြိုဆိုလိုက်ပါတယ်!🫵</blockquote>", parse_mode=ParseMode.HTML)
    elif new_status in ["left", "kicked"]:
        await context.bot.send_message(chat_id, f"<blockquote>{mention} ထွက်သွားပါပြီ။ သွားတော့ ဝေးရာဆီ!</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN MESSAGE HANDLER (Filters, Link, Save) ---
async def main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat_id, uid, text = update.effective_chat.id, update.effective_user.id, update.message.text

    # 1. Link Filter (Strict)
    if not is_admin(uid):
        if re.search(r"(https?://\S+|t\.me/\S+|www\.\S+)", text):
            try: 
                await update.message.delete()
                return await update.message.reply_text(f"<blockquote><a href='tg://user?id={uid}'>{update.effective_user.full_name}</a>🫵 ဒီမှာ link ချမရဘူး၊ မင်း link ကို ဖျက်လိုက်ပြီ</blockquote>", parse_mode=ParseMode.HTML)
            except: pass

    # 2. Custom Filter Check
    f_data = db.filters.find_one({"chat_id": chat_id, "keyword": text.lower()})
    if f_data: await update.message.reply_text(f"<blockquote>{f_data['reply']}</blockquote>", parse_mode=ParseMode.HTML)

    # 3. Auto Save (Only in Save Chat)
    save_status = db.settings.find_one({"_id": "save_mode"})
    if chat_id == SAVE_CHAT_ID and save_status and save_status.get("data"):
        if is_allow(uid):
            if not text.startswith('/') and not db.bully_messages.find_one({"text": text}):
                db.bully_messages.insert_one({"text": text})
                count = db.bully_messages.count_documents({})
                await update.message.reply_text(f"<blockquote>Bully text သိမ်းလိုက်ပြီ စုစုပေါင်း ({count}) ရှိပြီ Chief!</blockquote>", parse_mode=ParseMode.HTML)

# --- BULLY COMMAND ---
async def bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id):
        return await update.message.reply_text("<blockquote>မင်းမှာ ဒီ command သုံးခွင့်မရှိဘူး 🚫</blockquote>", parse_mode=ParseMode.HTML)
    
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text("<blockquote>Reply ပြန်ပြီး လိုးသတ်။</blockquote>", parse_mode=ParseMode.HTML)
    
    if target.id == OWNER_ID:
        return await update.message.reply_text("<blockquote>Creator ကိုတော့ ပြန်မလိုးပါနဲ့ Chief ရယ်! 🙇‍♂️</blockquote>", parse_mode=ParseMode.HTML)

    chat_id = update.effective_chat.id
    words = [w["text"] for w in db.bully_messages.find()]
    if not words: return await update.message.reply_text("<blockquote>Bully list အလွတ်ဖြစ်နေသည်။</blockquote>", parse_mode=ParseMode.HTML)

    if chat_id in bully_tasks: 
        stop_events[chat_id].set()
        bully_tasks[chat_id].cancel()
    
    stop_events[chat_id] = asyncio.Event()
    target_m = f'<a href="tg://user?id={target.id}">{target.full_name}</a>'

    async def loop():
        while not stop_events[chat_id].is_set():
            pool = random.sample(words, min(len(words), 5))
            for w in pool:
                if stop_events[chat_id].is_set(): break
                await context.bot.send_message(chat_id, f"<blockquote>{target_m} {w}</blockquote>", parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.4)
            await asyncio.sleep(4)
    
    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(f"<blockquote>🔥 {target.full_name} ကို အသေလိုးနေပါပြီ Chief! 😎</blockquote>", parse_mode=ParseMode.HTML)

# --- ADMIN ACTIONS ---
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    cmd = update.message.text.split()[0][1:].lower()
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return
    
    try:
        if cmd == "mute": await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=False))
        elif cmd == "unmute": await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
        elif cmd == "kick": await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        elif cmd == "ban": await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"<blockquote>{target.full_name} ကို {cmd} လိုက်ပြီ!</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e: await update.message.reply_text(f"<blockquote>Error: {e}</blockquote>", parse_mode=ParseMode.HTML)

# --- BROADCAST ---
async def sendallgp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    text = " ".join(context.args) if context.args else (update.message.reply_to_message.text if update.message.reply_to_message else "")
    if not text: return
    
    groups = db.groups.find()
    success, fail = 0, 0
    for g in groups:
        try:
            await context.bot.send_message(g["chat_id"], f"<blockquote><b>📢 BROADCAST</b>\n\n{text}</blockquote>", parse_mode=ParseMode.HTML)
            success += 1
            await asyncio.sleep(0.3)
        except: fail += 1
    await update.message.reply_text(f"<blockquote>📢 Broadcast ပြီးဆုံး!\n✅ အောင်မြင်: {success}\n❌ ကျရှုံး: {fail}</blockquote>", parse_mode=ParseMode.HTML)

# --- DB COMMANDS (Add Allow, Add Admin) ---
async def add_allow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if target:
        db.allow_users.update_one({"user_id": target.id}, {"$set": {"name": target.full_name}}, upsert=True)
        await update.message.reply_text(f"<blockquote>{target.full_name} ကို Allow List ထဲထည့်လိုက်ပါပြီ</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(ChatMemberHandler(member_update_handler, ChatMemberHandler.ANY_CHAT_MEMBER))
    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("stopbully", lambda u,c: stop_events[u.effective_chat.id].set() or u.message.reply_text("<blockquote>ရပ်လိုက်ပြီ!</blockquote>", parse_mode=ParseMode.HTML) if u.effective_chat.id in stop_events else None))
    app.add_handler(CommandHandler("sendallgp", sendallgp))
    app.add_handler(CommandHandler("addallow", add_allow_cmd))
    app.add_handler(CommandHandler("save_on", lambda u,c: db.settings.update_one({"_id": "save_mode"}, {"$set": {"data": True}}, upsert=True) or u.message.reply_text("<blockquote>✅ Auto Save: ON</blockquote>", parse_mode=ParseMode.HTML)))
    app.add_handler(CommandHandler("save_off", lambda u,c: db.settings.update_one({"_id": "save_mode"}, {"$set": {"data": False}}, upsert=True) or u.message.reply_text("<blockquote>❌ Auto Save: OFF</blockquote>", parse_mode=ParseMode.HTML)))
    app.add_handler(CommandHandler(["mute", "unmute", "kick", "ban"], admin_action))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_handler))
    
    print("🚀 Young Master ThuRain V43.7 Full Merged Running...")
    app.run_polling()

if __name__ == "__main__": main()

