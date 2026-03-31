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

async def check_permission(update: Update):
    uid = update.effective_user.id
    if is_allow(uid): return True
    await update.message.reply_text(
        "<blockquote>မင်းမှာ BoDxBrotherhood_of_Dexter bot Command သုံးခွင့်မရှိသေးဘူး🫵 @Besties_with_BoD ကိုလာပြီးယူလို့ရတယ်</blockquote>", 
        parse_mode=ParseMode.HTML
    )
    return False

# --- MEMBER UPDATES ---
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
                    log = f"<blockquote>👋 ကိုခန့်သူရိန်ဗျ @Wyaaqq_Zxyfanzt ကျနော်တို့ Bot ကို ယူသုံးထားပါတယ်\nGP: {update.effective_chat.title}</blockquote>"
                    await context.bot.send_message(ADMIN_GROUP_ID, log, parse_mode=ParseMode.HTML)
                except: pass
        return

    mention_u = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    if old_status in ["left", "kicked"] and new_status in ["member", "administrator"]:
        await context.bot.send_message(chat_id, f"<blockquote>ဟိတ် {mention_u}! ကြိုဆိုပါတယ်!🫵</blockquote>", parse_mode=ParseMode.HTML)

# --- SMART TARGET GETTER (Reply or ID) ---
async def get_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id, update.message.reply_to_message.from_user.full_name
    if context.args:
        arg = context.args[0].replace('@', '')
        if arg.isdigit():
            return int(arg), f"User {arg}"
    return None, None

# --- ADMIN ACTIONS (Ban, Mute, Kick) ---
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    cmd = update.message.text.split()[0][1:].lower()
    target_id, target_name = await get_target(update, context)
    
    if not target_id:
        return await update.message.reply_text("<blockquote>Reply ပြန်ပါ သို့မဟုတ် ID ထည့်ပါ Chief!</blockquote>", parse_mode=ParseMode.HTML)

    try:
        chat_id = update.effective_chat.id
        if cmd == "mute": await context.bot.restrict_chat_member(chat_id, target_id, permissions=ChatPermissions(can_send_messages=False))
        elif cmd == "unmute": await context.bot.restrict_chat_member(chat_id, target_id, permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
        elif cmd == "kick": await context.bot.ban_chat_member(chat_id, target_id); await context.bot.unban_chat_member(chat_id, target_id)
        elif cmd == "ban": await context.bot.ban_chat_member(chat_id, target_id)
        elif cmd == "unban": await context.bot.unban_chat_member(chat_id, target_id)
        
        await update.message.reply_text(f"<blockquote>✅ {target_name} ကို <b>{cmd}</b> လိုက်ပါပြီ Chief!</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"<blockquote>❌ Error: {e}</blockquote>", parse_mode=ParseMode.HTML)

# --- FILTER SYSTEM ---
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_GROUP_ID or update.effective_user.id != OWNER_ID: return
    if len(context.args) < 2:
        return await update.message.reply_text("<blockquote>Usage: /filter [keyword] [reply]</blockquote>", parse_mode=ParseMode.HTML)
    
    keyword = context.args[0].lower()
    reply_text = " ".join(context.args[1:])
    db.filters.update_one({"keyword": keyword}, {"$set": {"reply": reply_text}}, upsert=True)
    await update.message.reply_text(f"<blockquote>✅ Filter '{keyword}' ကို Database ထဲ သိမ်းလိုက်ပါပြီ Chief!</blockquote>", parse_mode=ParseMode.HTML)

# --- BROADCAST ---
async def sendallgp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    text = " ".join(context.args) if context.args else (update.message.reply_to_message.text if update.message.reply_to_message else "")
    if not text: return await update.message.reply_text("<blockquote>Broadcast လုပ်မဲ့စာသားထည့်ပါ Chief!</blockquote>", parse_mode=ParseMode.HTML)
    
    groups = db.groups.find()
    success, fail = 0, 0
    for g in groups:
        try:
            await context.bot.send_message(g["chat_id"], f"<blockquote><b>📢 BROADCAST</b>\n\n{text}</blockquote>", parse_mode=ParseMode.HTML)
            success += 1
            await asyncio.sleep(0.3)
        except: fail += 1
    await update.message.reply_text(f"<blockquote>📢 Broadcast ပြီးဆုံး!\n✅ အောင်မြင်: {success}\n❌ ကျရှုံး: {fail}</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN MESSAGE HANDLER ---
async def main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat_id, uid, text = update.effective_chat.id, update.effective_user.id, update.message.text

    # Link Filter
    if not is_admin(uid) and re.search(r"(https?://\S+|t\.me/\S+|www\.\S+)", text):
        try: 
            await update.message.delete()
            return await update.message.reply_text(f"<blockquote><a href='tg://user?id={uid}'>{update.effective_user.full_name}</a>🫵 ဒီမှာ link ချခွင့်မရှိဘူး၊ မင်း link ကို ငါဖျက်လိုက်ပြီ</blockquote>", parse_mode=ParseMode.HTML)
        except: pass

    # Filter Response
    f_data = db.filters.find_one({"keyword": text.lower()})
    if f_data: await update.message.reply_text(f"<blockquote>{f_data['reply']}</blockquote>", parse_mode=ParseMode.HTML)

    # Auto Save
    save_status = db.settings.find_one({"_id": "save_mode"})
    if chat_id == SAVE_CHAT_ID and save_status and save_status.get("data") and is_allow(uid):
        if not text.startswith('/') and text not in get_all_bully_words():
            db.bully_messages.insert_one({"text": text})
            await update.message.reply_text("<blockquote>Bully text အသစ် သိမ်းလိုက်ပြီ Chief!</blockquote>", parse_mode=ParseMode.HTML)

# --- BULLY ---
async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_permission(update): return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text("<blockquote>Reply ပြန်ပြီး လိုးသတ်။</blockquote>", parse_mode=ParseMode.HTML)
    if target.id == OWNER_ID: return await update.message.reply_text("<blockquote>Creator ကို bully လို့မရဘူးညီ 🫵</blockquote>", parse_mode=ParseMode.HTML)

    words = get_all_bully_words()
    if not words: return await update.message.reply_text("<blockquote>Bully list အလွတ်ဖြစ်နေသည်။</blockquote>", parse_mode=ParseMode.HTML)

    chat_id = update.effective_chat.id
    if chat_id in bully_tasks: stop_events[chat_id].set()
    stop_events[chat_id] = asyncio.Event()
    
    async def loop():
        while not stop_events[chat_id].is_set():
            pool = random.sample(words, min(len(words), 5))
            for w in pool:
                if stop_events[chat_id].is_set(): break
                await context.bot.send_message(chat_id, f"<blockquote><a href='tg://user?id={target.id}'>{target.full_name}</a> {w}</blockquote>", parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.4)
            await asyncio.sleep(4)
    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(f"<blockquote>ဟိတ်🫵 {target.full_name} မင်းကိုပျင်းလို့ငါbullyမယ်!</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(member_update_handler, ChatMemberHandler.ANY_CHAT_MEMBER))
    app.add_handler(CommandHandler("filter", add_filter))
    app.add_handler(CommandHandler("sendallgp", sendallgp))
    app.add_handler(CommandHandler(["mute", "unmute", "kick", "ban", "unban"], admin_action))
    app.add_handler(CommandHandler("bully", bully_cmd))
    app.add_handler(CommandHandler("stopbully", lambda u,c: stop_events[u.effective_chat.id].set() or u.message.reply_text("<blockquote>ရပ်လိုက်ပြီ!</blockquote>", parse_mode=ParseMode.HTML) if u.effective_chat.id in stop_events else None))
    app.add_handler(CommandHandler("allowlist", lambda u,c: None if u.effective_user.id != OWNER_ID else u.message.reply_text(f"<blockquote>Users: {[x['name'] for x in db.allow_users.find()]}</blockquote>", parse_mode=ParseMode.HTML)))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_handler))
    
    print("🚀 Young Master ThuRain V44.1 Ready...")
    app.run_polling()

if __name__ == "__main__": main()
