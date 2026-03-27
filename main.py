import asyncio
import re
import os
import logging
from pymongo import MongoClient
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    ChatMemberHandler
)

# --- LOGGING SETUP ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION ---
TOKEN = "8575371720:AAHR_1fCkRxlALIbhMH0yufXGJiUSQYJyYE" 
OWNER_ID = 6015356597
ADMIN_GROUP_ID = -1003806830045
SAVE_CHAT = -1003864912245  
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"
LINK_REGEX = r"(https?://|t\.me|telegram\.me|www\.)"

# --- DATABASE CONNECTION ---
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
bully_tasks = {} 
stop_events = {} 

# --- DB HELPERS ---
def get_list(name):
    data = db.settings.find_one({"_id": name})
    return data["data"] if data and "data" in data else []

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
    if uid == OWNER_ID or uid in get_list("allow"): return True
    await update.message.reply_text("<blockquote>မင်းမှာ BoD's Wyaaqq Zxyfanzt bot Command သုံးခွင့်မရှိသေးဘူး🫵 @Besties_with_BoD ကိုလာပြီးယူလို့ရတယ်</blockquote>", parse_mode=ParseMode.HTML)
    return False

async def is_tg_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid == OWNER_ID: return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, uid)
        return member.status in ['administrator', 'creator']
    except: return False

# --- ROSE-STYLE MEMBER HANDLER ---
async def member_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return
    
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title
    user = result.new_chat_member.user
    
    # Member Status တွေကို စစ်ဆေးခြင်း
    was_member = result.old_chat_member.status in ["member", "administrator", "creator"]
    is_member = result.new_chat_member.status in ["member", "administrator", "creator"]

    # ၁။ Member အသစ်ဝင်လာခြင်း (Join)
    if not was_member and is_member:
        mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
        await context.bot.send_message(
            chat_id, 
            f"<blockquote>ဟိတ် {mention}! {chat_title} ကနေ ကြိုဆိုပါတယ်!</blockquote>", 
            parse_mode=ParseMode.HTML
        )
    
    # ၂။ Member ထွက်သွားခြင်း (Leave/Kick)
    elif was_member and not is_member:
        mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
        await context.bot.send_message(
            chat_id, 
            f"<blockquote>{mention} ထွက်သွားပါပြီ။ သွားတော့ ဖုတ်လိုက်ဖုတ်လိုက်!</blockquote>", 
            parse_mode=ParseMode.HTML
        )

# --- COMMANDS ---
async def addallow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    target_id = None
    if context.args: target_id = int(context.args[0])
    elif update.message.reply_to_message: target_id = update.message.reply_to_message.from_user.id
    
    if target_id:
        allowed = get_list("allow")
        if target_id not in allowed:
            allowed.append(target_id)
            set_list("allow", allowed)
            await update.message.reply_text(f"<blockquote>✅ User: <code>{target_id}</code> ကို Bot Command သုံးခွင့်ပေးလိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def addbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allow(update): return
    if update.message.reply_to_message:
        text = update.message.reply_to_message.text or update.message.reply_to_message.caption
        if text:
            bully_list = get_list("bully")
            if text not in bully_list:
                bully_list.append(text)
                set_list("bully", bully_list)
                await update.message.reply_text(f"<blockquote>📝 Bully list ထဲသို့ ထည့်ပြီးပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def markgp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    chat_id = update.effective_chat.id
    marked = get_list("marked_groups")
    if chat_id not in marked:
        marked.append(chat_id)
        set_list("marked_groups", marked)
        await update.message.reply_text("<blockquote>📍 ဒီ Group ကို Broadcast list ထဲ ထည့်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def sendallgp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    msg = update.message.reply_to_message
    if not msg: return await update.message.reply_text("<blockquote>စာကို Reply ပြန်ပါ။</blockquote>", parse_mode=ParseMode.HTML)
    
    marked = get_list("marked_groups")
    count = 0
    for gid in marked:
        try:
            await context.bot.copy_message(chat_id=gid, from_chat_id=update.effective_chat.id, message_id=msg.message_id)
            count += 1
            await asyncio.sleep(0.2)
        except: pass
    await update.message.reply_text(f"<blockquote>📢 Group {count} ခုကို ပို့ပြီးပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- BULLY LOGIC ---
async def bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allow(update): return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text("<blockquote>Reply ပြန်ပြီး ဆော်ပါ။</blockquote>", parse_mode=ParseMode.HTML)
    
    chat_id = update.effective_chat.id
    words = get_list("bully")
    if not words: return await update.message.reply_text("<blockquote>List အလွတ်ဖြစ်နေသည်။ စာအရင်သွင်းပါ။</blockquote>", parse_mode=ParseMode.HTML)

    if chat_id in bully_tasks:
        stop_events[chat_id].set()
        bully_tasks[chat_id].cancel()

    stop_events[chat_id] = asyncio.Event()
    mention = f'<a href="tg://user?id={target.id}">{target.full_name}</a>'

    async def loop():
        try:
            while not stop_events[chat_id].is_set():
                for w in words:
                    if stop_events[chat_id].is_set(): break
                    await context.bot.send_message(chat_id, f"<blockquote>{mention} {w}</blockquote>", parse_mode=ParseMode.HTML)
                    await asyncio.sleep(3.5)
        except: pass

    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(f"<blockquote>🔥 {target.full_name} ကို ဟိတ်ကောင်ငါ့messageတွေခိုးcopyစမ်း!😜</blockquote>", parse_mode=ParseMode.HTML)

async def stopbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allow(update): return
    chat_id = update.effective_chat.id
    if chat_id in stop_events:
        stop_events[chat_id].set()
        if chat_id in bully_tasks:
            bully_tasks[chat_id].cancel()
            del bully_tasks[chat_id]
        del stop_events[chat_id]
        await update.message.reply_text("<blockquote>မင်းကရပ်ခိုင်းလို့သာငါကဆက်ဘူလီချင်သေးတာ😁</blockquote>", parse_mode=ParseMode.HTML)

# --- SERVICE HANDLER (For Bot Join Alerts) ---
async def service_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    chat_id, chat_title = update.effective_chat.id, update.effective_chat.title
    if update.message.new_chat_members:
        for m in update.message.new_chat_members:
            if m.id == context.bot.id:
                try: inv_link = await context.bot.export_chat_invite_link(chat_id)
                except: inv_link = "No Link"
                alert_text = f"👋<b>Botကို ယူသုံးထားပါတယ်</b>\n Group name- <b>Group:</b> {chat_title}\n🆔Group Id <code>{chat_id}</code>\n🔗 {inv_link}"
                await context.bot.send_message(ADMIN_GROUP_ID, alert_text, parse_mode=ParseMode.HTML)

# --- MAIN HANDLER ---
async def main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    chat_id, uid = update.effective_chat.id, update.effective_user.id
    text = update.message.text or update.message.caption

    # Link Detection
    if text and re.search(LINK_REGEX, text):
        if not await is_tg_admin(update, context):
            try:
                await update.message.delete()
                mention = f'<a href="tg://user?id={uid}">{update.effective_user.full_name}</a>'
                await context.bot.send_message(chat_id, f"<blockquote>ဟိတ် {mention}! မင်းမှာ link ချခွင့်မရှိဘူး 🫵</blockquote>", parse_mode=ParseMode.HTML)
            except: pass
            return

    # Auto Save
    if chat_id == SAVE_CHAT and get_bool("save") and (uid == OWNER_ID or uid in get_list("allow")):
        if text:
            bully_list = get_list("bully")
            if text not in bully_list:
                bully_list.append(text)
                set_list("bully", bully_list)
                await update.message.reply_text(f"<blockquote> မှတ်သားထားပါတယ်: {text}</blockquote>", parse_mode=ParseMode.HTML)
                return

    # Filters
    if text:
        f_data = db.filters.find_one({"_id": text.lower()})
        if f_data: await update.message.reply_text(f"<blockquote>{f_data['reply']}</blockquote>", parse_mode=ParseMode.HTML)

def main():
    # အရေးကြီးဆုံးအချက်: Chat Member updates တွေကို လက်ခံဖို့ allow လုပ်ပေးရပါမယ်
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Register ChatMemberHandler
    app.add_handler(ChatMemberHandler(member_update_handler, ChatMemberHandler.CHAT_MEMBER))
    
    # Command Handlers
    app.add_handler(CommandHandler("addallow", addallow))
    app.add_handler(CommandHandler("addbully", addbully))
    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("stopbully", stopbully))
    app.add_handler(CommandHandler("markgp", markgp))
    app.add_handler(CommandHandler("sendallgp", sendallgp))
    app.add_handler(CommandHandler("save_on", lambda u,c: set_bool("save", True) or u.message.reply_text("<blockquote>✅ Auto Save: ON</blockquote>", parse_mode=ParseMode.HTML)))
    app.add_handler(CommandHandler("save_off", lambda u,c: set_bool("save", False) or u.message.reply_text("<blockquote>❌ Auto Save: OFF</blockquote>", parse_mode=ParseMode.HTML)))
    
    # Status Updates (Bot Join အတွက်)
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, service_handler))
    
    # Message Handlers
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION | filters.FORWARDED) & ~filters.COMMAND, main_handler))
    
    print("🚀 Young Master ThuRain V20 (Ultimate) is running...")
    
    # အရေးကြီး: Chat Member event တွေကို ဖမ်းဖို့ drop_pending_updates ကို True ပေးပြီး run မယ်
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__": main()
