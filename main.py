import asyncio
import re
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

# --- HELPERS ---
def get_all_bully_words():
    new_words = [w["text"] for w in db.bully_messages.find()]
    old_data = db.settings.find_one({"_id": "bully"})
    old_words = old_data["data"] if old_data and "data" in old_data else []
    return list(set(new_words + old_words))

def is_allow(uid):
    if uid == OWNER_ID: return True
    if db.allow_users.find_one({"user_id": uid}): return True
    old_data = db.settings.find_one({"_id": "allow"})
    old_list = old_data["data"] if old_data and "data" in old_data else []
    return uid in old_list

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

    if user.id == context.bot.id:
        if new_status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
            if not db.groups.find_one({"chat_id": chat_id}):
                db.groups.insert_one({"chat_id": chat_id, "title": update.effective_chat.title})
                try:
                    log = f"<blockquote>👋 ကိုခန့်သူရိန်ဗျ @Wyaaqq_Zxyfanzt ကျနော်တို့ BoD_Brotherhood_of_Dexter Bot ကို ယူသုံးထားပါတယ်\n━━━━━━━━━━━━━━━━━━━━\n<b>Group Name:</b> {update.effective_chat.title}\n<b>Group ID:</b> <code>{chat_id}</code></blockquote>"
                    await context.bot.send_message(ADMIN_GROUP_ID, log, parse_mode=ParseMode.HTML)
                except: pass
                entry = "<blockquote>ဟိတ်ရို့ /admins မင်းတို့ရဲ့ဒီ group ဟိတ် ကို ထည့်သွင်းအသုံးပြုပေးတဲ့အတွက် ကျေးဇူး၊ အမ် အသုံးဝင်မယ့် တချို့ကန့်သန့်ထားတဲ့ bot command တွေသုံးမယ်ဆို @Besties_with_BoD က OWNER ခန့်သူရိန် ဆီကိုလာဆက်သွယ်ပေးပါ။</blockquote>"
                await context.bot.send_message(chat_id, entry, parse_mode=ParseMode.HTML)
        return

    mention_u = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    if old_status in ["left", "kicked"] and new_status in ["member", "administrator"]:
        await context.bot.send_message(chat_id, f"<blockquote>ဟိတ် {mention_u}! {update.effective_chat.title} ကနေ ကြိုဆိုလိုက်ပါတယ်!🫵</blockquote>", parse_mode=ParseMode.HTML)
    elif new_status in ["left", "kicked"]:
        await context.bot.send_message(chat_id, f"<blockquote>{mention_u} ထွက်သွားပါပြီ။ သွားတော့ ဝေးရာဆီ!</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN MESSAGE HANDLER (Link Filter & Save Chat) ---
async def main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat_id, uid, text = update.effective_chat.id, update.effective_user.id, update.message.text
    user_mention = f'<a href="tg://user?id={uid}">{update.effective_user.full_name}</a>'

    # Link Filter
    if not is_admin(uid):
        if re.search(r"(https?://\S+|t\.me/\S+|www\.\S+)", text):
            try: 
                await update.message.delete()
                return await update.message.reply_text(f"<blockquote>{user_mention}🫵 ဒီမှာ link ချခွင့်မရှိဘူး၊ မင်း link ကို ငါဖျက်လိုက်ပြီ</blockquote>", parse_mode=ParseMode.HTML)
            except: pass

    # Filter Response
    f_data = db.filters.find_one({"chat_id": chat_id, "keyword": text.lower()})
    if f_data: await update.message.reply_text(f"<blockquote>{f_data['reply']}</blockquote>", parse_mode=ParseMode.HTML)

    # Save Chat Logic
    save_status = db.settings.find_one({"_id": "save_mode"})
    if chat_id == SAVE_CHAT_ID and save_status and save_status.get("data"):
        if is_allow(uid):
            if not text.startswith('/') and text not in get_all_bully_words():
                db.bully_messages.insert_one({"text": text})
                await update.message.reply_text(f"<blockquote>Bully text အသစ် သိမ်းလိုက်ပြီ Chief!</blockquote>", parse_mode=ParseMode.HTML)

# --- OWNER ONLY COMMANDS (ADMIN GP ONLY) ---
async def allow_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID or update.effective_chat.id != ADMIN_GROUP_ID: return
    
    # Get from both new and old DB
    new_users = list(db.allow_users.find())
    old_data = db.settings.find_one({"_id": "allow"})
    old_ids = old_data["data"] if old_data and "data" in old_data else []
    
    text = "<blockquote><b>👥 Bot Command အသုံးပြုခွင့်ရှိသူများ</b>\n\n"
    seen = set()
    for u in new_users:
        text += f"• <a href='tg://user?id={u['user_id']}'>{u['name']}</a> (ID: <code>{u['user_id']}</code>)\n"
        seen.add(u['user_id'])
    for oid in old_ids:
        if oid not in seen:
            text += f"• Legacy User (ID: <code>{oid}</code>)\n"
    text += "</blockquote>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def total_bully_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID or update.effective_chat.id != ADMIN_GROUP_ID: return
    count = len(get_all_bully_words())
    await update.message.reply_text(f"<blockquote>📊 <b>Bully Status</b>\n\nစုစုပေါင်း Bully Text အရေအတွက်: <b>{count}</b> ခု ရှိနေပါပြီ Chief!</blockquote>", parse_mode=ParseMode.HTML)

# --- SMART COMMANDS (Add Allow with ID or Reply) ---
async def add_allow_smart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    
    target_id, target_name = None, "User"
    
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target_name = update.message.reply_to_message.from_user.full_name
    elif context.args:
        # Check if argument is an ID (e.g., /addallow 6015356597)
        arg = context.args[0].replace('@', '')
        if arg.isdigit():
            target_id = int(arg)
            target_name = f"User {target_id}"

    if target_id:
        db.allow_users.update_one({"user_id": target_id}, {"$set": {"name": target_name}}, upsert=True)
        await update.message.reply_text(f"<blockquote>✅ <a href='tg://user?id={target_id}'>{target_name}</a> ကို Bot Command သုံးခွင့်ပေးလိုက်ပါပြီ Chief!</blockquote>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("<blockquote>Reply ပြန်ပါ သို့မဟုတ် User ID ထည့်ပေးပါ Chief!</blockquote>", parse_mode=ParseMode.HTML)

# --- BULLY ---
async def bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id):
        return await update.message.reply_text("<blockquote>မင်းမှာ ဒီ command သုံးခွင့်မရှိဘူး 🚫</blockquote>", parse_mode=ParseMode.HTML)
    
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text("<blockquote>Reply ပြန်ပြီး လိုးသတ်။</blockquote>", parse_mode=ParseMode.HTML)
    if target.id == OWNER_ID: return await update.message.reply_text("<blockquote>Creator ကိုမလိုးနဲ့ Chief! 🙇‍♂️</blockquote>", parse_mode=ParseMode.HTML)

    chat_id, words = update.effective_chat.id, get_all_bully_words()
    if not words: return await update.message.reply_text("<blockquote>Bully list အလွတ်ဖြစ်နေသည်။</blockquote>", parse_mode=ParseMode.HTML)

    if chat_id in bully_tasks: 
        stop_events[chat_id].set()
        bully_tasks[chat_id].cancel()
    
    stop_events[chat_id] = asyncio.Event()
    target_mention = f'<a href="tg://user?id={target.id}">{target.full_name}</a>'

    async def loop():
        while not stop_events[chat_id].is_set():
            pool = random.sample(words, min(len(words), 5))
            for w in pool:
                if stop_events[chat_id].is_set(): break
                await context.bot.send_message(chat_id, f"<blockquote>{target_mention} {w}</blockquote>", parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.4)
            await asyncio.sleep(4)
    
    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(f"<blockquote>🔥 {target.full_name} ကို အသေလိုးနေပါပြီ Chief! 😎</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(ChatMemberHandler(member_update_handler, ChatMemberHandler.ANY_CHAT_MEMBER))
    app.add_handler(CommandHandler("allowlist", allow_list_cmd))
    app.add_handler(CommandHandler("totalbullymsg", total_bully_msg))
    app.add_handler(CommandHandler("addallow", add_allow_smart))
    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("stopbully", lambda u,c: stop_events[u.effective_chat.id].set() or u.message.reply_text("<blockquote>ရပ်လိုက်ပြီ!</blockquote>", parse_mode=ParseMode.HTML) if u.effective_chat.id in stop_events else None))
    app.add_handler(CommandHandler("save_on", lambda u,c: db.settings.update_one({"_id": "save_mode"}, {"$set": {"data": True}}, upsert=True) or u.message.reply_text("<blockquote>✅ Auto Save: ON</blockquote>", parse_mode=ParseMode.HTML)))
    app.add_handler(CommandHandler("save_off", lambda u,c: db.settings.update_one({"_id": "save_mode"}, {"$set": {"data": False}}, upsert=True) or u.message.reply_text("<blockquote>❌ Auto Save: OFF</blockquote>", parse_mode=ParseMode.HTML)))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_handler))
    
    print("🚀 Young Master ThuRain V44.0 Running...")
    app.run_polling()

if __name__ == "__main__": main()
