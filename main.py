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

# Telegram Admin Check (Links ဖျက်ဖို့အတွက်သာ)
async def is_tg_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid == OWNER_ID: return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, uid)
        return member.status in ['administrator', 'creator']
    except: return False

# --- COMMANDS: ADD ALLOW, ADD BULLY, MARK GP ---
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
        else:
            await update.message.reply_text("<blockquote>ဒီလူက list ထဲမှာ ရှိပြီးသားပါ။</blockquote>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("<blockquote>Reply ပြန်ပါ သို့မဟုတ် ID ရိုက်ပါ။</blockquote>", parse_mode=ParseMode.HTML)

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
    else:
        await update.message.reply_text("<blockquote>စာသားကို Reply ပြန်ပြီး /addbully ရိုက်ပါ။</blockquote>", parse_mode=ParseMode.HTML)

async def markgp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    chat_id = update.effective_chat.id
    marked = get_list("marked_groups")
    if chat_id not in marked:
        marked.append(chat_id)
        set_list("marked_groups", marked)
        await update.message.reply_text("<blockquote>📍 ဒီ Group ကို Broadcast list ထဲ ထည့်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("<blockquote>📍 ဒီ Group က မှတ်သားပြီးသားပါ။</blockquote>", parse_mode=ParseMode.HTML)

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
    await update.message.reply_text(f"<blockquote>🔥 {target.full_name} ကို စဆော်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def stopbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allow(update): return
    chat_id = update.effective_chat.id
    if chat_id in stop_events:
        stop_events[chat_id].set()
        if chat_id in bully_tasks:
            bully_tasks[chat_id].cancel()
            del bully_tasks[chat_id]
        del stop_events[chat_id]
        await update.message.reply_text("<blockquote>✅ ရပ်လိုက်ပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- HANDLERS ---
async def service_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    chat_id, chat_title = update.effective_chat.id, update.effective_chat.title
    if update.message.new_chat_members:
        for m in update.message.new_chat_members:
            if m.id == context.bot.id:
                try: inv_link = await context.bot.export_chat_invite_link(chat_id)
                except: inv_link = "No Link"
                alert_text = f"📢 <b>Bot Added!</b>\n🏘 <b>Group:</b> {chat_title}\n🆔 <code>{chat_id}</code>\n🔗 {inv_link}"
                await context.bot.send_message(ADMIN_GROUP_ID, alert_text, parse_mode=ParseMode.HTML)
                continue
            try: await update.message.delete()
            except: pass
            await context.bot.send_message(chat_id, f"<blockquote>ဟိတ် {m.full_name}! {chat_title} ကနေ ကြိုဆိုပါတယ်!</blockquote>", parse_mode=ParseMode.HTML)

    if update.message.left_chat_member:
        m = update.message.left_chat_member
        if m.id == context.bot.id: return
        try: await update.message.delete()
        except: pass
        await context.bot.send_message(chat_id, f"<blockquote>{m.full_name} ထွက်သွားပါပြီ။ သွားတော့ ဖုတ်လိုက်ဖုတ်လိုက်!</blockquote>", parse_mode=ParseMode.HTML)

async def main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    chat_id, uid = update.effective_chat.id, update.effective_user.id
    text = update.message.text or update.message.caption

        # --- LINK DETECTION (UPDATED) ---
    if text and re.search(LINK_REGEX, text):
        # Telegram Admin မဟုတ်ရင် ဖျက်မယ်
        if not await is_tg_admin(update, context):
            try:
                # ၁. ပို့လိုက်တဲ့ Link ကို အရင်ဖျက်မယ်
                await update.message.delete()
                
                # ၂. သတိပေးစာ ပို့မယ်
                mention = f'<a href="tg://user?id={uid}">{update.effective_user.full_name}</a>'
                warning_text = f"<blockquote>ဟိတ် {mention}! မင်းမှာ link ချခွင့်မရှိဘူး 🫵</blockquote>"
                
                await context.bot.send_message(
                    chat_id, 
                    warning_text, 
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logging.error(f"Link delete error: {e}")
            return # Link ဖြစ်တဲ့အတွက် အောက်က Filter တွေကို ဆက်မသွားတော့ဘူး


    # Auto Save (စာသားရော၊ Forward စာရော)
    if chat_id == SAVE_CHAT and get_bool("save") and (uid == OWNER_ID or uid in get_list("allow")):
        if text:
            bully_list = get_list("bully")
            if text not in bully_list:
                bully_list.append(text)
                set_list("bully", bully_list)
                await update.message.reply_text(f"<blockquote>📝 သိမ်းဆည်းပြီး: {text}</blockquote>", parse_mode=ParseMode.HTML)
                return

    # Filters
    if text:
        f_data = db.filters.find_one({"_id": text.lower()})
        if f_data: await update.message.reply_text(f"<blockquote>{f_data['reply']}</blockquote>", parse_mode=ParseMode.HTML)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Register All Commands
    app.add_handler(CommandHandler("addallow", addallow))
    app.add_handler(CommandHandler("addbully", addbully))
    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("stopbully", stopbully))
    app.add_handler(CommandHandler("markgp", markgp))
    app.add_handler(CommandHandler("sendallgp", sendallgp))
    app.add_handler(CommandHandler("save_on", lambda u,c: set_bool("save", True) or u.message.reply_text("<blockquote>✅ Auto Save: ON</blockquote>", parse_mode=ParseMode.HTML)))
    app.add_handler(CommandHandler("save_off", lambda u,c: set_bool("save", False) or u.message.reply_text("<blockquote>❌ Auto Save: OFF</blockquote>", parse_mode=ParseMode.HTML)))
    
    # Status Updates
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, service_handler))
    
    # Text Messages (Supports Forwards)
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION | filters.FORWARDED) & ~filters.COMMAND, main_handler))
    
    print("🚀 Young Master ThuRain V16 is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__": main()
