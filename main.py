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
ADMIN_GROUP_ID = -1003580630981  
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
    await update.message.reply_text("<blockquote> မင်းမှာ BoD's Wyaaqq Zxyfanzt bot Command သုံးခွင့်မရှိသေးဘူး @Besties_with_BoD 👈 ကိုလာပြီးယူလို့ရတယ်</blockquote>", parse_mode=ParseMode.HTML)
    return False

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid == OWNER_ID: return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, uid)
        return member.status in ['administrator', 'creator']
    except: return False

# --- SERVICE HANDLER ---
async def service_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title

    # ၁။ Member အသစ်ဝင်လာခြင်း
    if update.message.new_chat_members:
        for m in update.message.new_chat_members:
            if m.id == context.bot.id:
                try: inv_link = await context.bot.export_chat_invite_link(chat_id)
                except: inv_link = "Admin မရသေး၍ Link ယူမရပါ"
                
                alert_text = (
                    f"😎 <b>ဒီ အထာကျတဲ့ BoD's Wyaaqq Zxyfanzt Botကို Group တစ်ခုက ထည့်သွင်းထားပါတယ်</b>\n\n"
                    f"👤 <b>Owner:</b> <a href='tg://user?id={OWNER_ID}'>ခန့်သူရိန် မန်းရှင်း</a>\n"
                    f"🗣 <b>Group Name:</b> {chat_title}\n"
                    f"🆔 <b>Group ID:</b> <code>{chat_id}</code>\n"
                    f"🔗 <b>Link:</b> {inv_link}"
                )
                await context.bot.send_message(ADMIN_GROUP_ID, alert_text, parse_mode=ParseMode.HTML)
                await context.bot.send_message(chat_id, "<blockquote>ဟိုင်းဒီ Group က OWNER မင်းမှာ BoD's Wyaaqq Zxyfanzt bot Command သုံးခွင့်မရှိသေးဘူး @Besties_with_BoD 👈 ကိုလာပြီးယူလို့ရတယ်</blockquote>", parse_mode=ParseMode.HTML)
                continue

            try: await update.message.delete()
            except: pass
            mention = f'<a href="tg://user?id={m.id}">{m.full_name}</a>'
            await context.bot.send_message(chat_id, f"<blockquote>ဟိတ် {mention}! {chat_title} ကနေ ကြိုဆိုလိုက်ပါတယ်!</blockquote>", parse_mode=ParseMode.HTML)

    # ၂။ Member ထွက်သွားခြင်း
    if update.message.left_chat_member:
        m = update.message.left_chat_member
        if m.id == context.bot.id: return
        try: await update.message.delete()
        except: pass
        mention = f'<a href="tg://user?id={m.id}">{m.full_name}</a>'
        await context.bot.send_message(chat_id, f"<blockquote>{mention} ကတော့ ထွက်သွားပါပြီ။ သွားတော့ ဖုတ်လိုက်ဖုတ်လိုက်!</blockquote>", parse_mode=ParseMode.HTML)

# --- COMMANDS ---
async def bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allow(update): return
    target_user = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target_user and context.args:
        for entity in update.message.entities:
            if entity.type == "text_mention": target_user = entity.user; break
    if not target_user:
        return await update.message.reply_text("<blockquote>Bully လုပ်မည့်သူကို Reply သို့မဟုတ် Mention လုပ်ပါ။</blockquote>", parse_mode=ParseMode.HTML)
    
    chat_id = update.effective_chat.id
    mention = f'<a href="tg://user?id={target_user.id}">{target_user.full_name}</a>'
    words = get_list("bully")
    if not words: return await update.message.reply_text("<blockquote>Bully list အလွတ်ဖြစ်နေသည်။</blockquote>", parse_mode=ParseMode.HTML)
    
    if chat_id in bully_tasks: bully_tasks[chat_id].cancel()
    async def loop():
        try:
            while True:
                for w in words:
                    await context.bot.send_message(chat_id, f"<blockquote>{mention} {w}</blockquote>", parse_mode=ParseMode.HTML)
                    await asyncio.sleep(3.5)
        except asyncio.CancelledError: return
    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(f"<blockquote>🔥 {target_user.full_name} ကို ဆော်ပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def stopbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allow(update): return
    chat_id = update.effective_chat.id
    if chat_id in bully_tasks:
        bully_tasks[chat_id].cancel(); del bully_tasks[chat_id]
        await update.message.reply_text("<blockquote>✅ ရပ်လိုက်ပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def markgp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    chat_id = update.effective_chat.id
    marked_groups = get_list("marked_groups")
    if chat_id not in marked_groups:
        marked_groups.append(chat_id); set_list("marked_groups", marked_groups)
        await update.message.reply_text("<blockquote>နောက်တွင်သတင်းစကားလာပါးချင်တဲ့အခါရနိုင်အောင် မှတ်သားထားလိုက်ပါ့မယ်။</blockquote>", parse_mode=ParseMode.HTML)

async def sendallgp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    msg = update.message.reply_to_message
    if not msg: return await update.message.reply_text("<blockquote>Reply ပြန်ပါ။</blockquote>", parse_mode=ParseMode.HTML)
    marked_groups = get_list("marked_groups")
    success = 0
    for gid in marked_groups:
        try:
            await context.bot.copy_message(chat_id=gid, from_chat_id=update.effective_chat.id, message_id=msg.message_id)
            success += 1; await asyncio.sleep(0.1)
        except: pass
    await update.message.reply_text(f"<blockquote>📢 Group {success} ခုကို ပို့ဆောင်ပြီးပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- TEXT/LINK HANDLER ---
async def main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat_id, uid, text = update.effective_chat.id, update.effective_user.id, update.message.text

    # Link Detection
    if re.search(LINK_REGEX, text):
        if not await is_admin(update, context):
            try: await update.message.delete()
            except: pass
            mention = f'<a href="tg://user?id={uid}">{update.effective_user.full_name}</a>'
            await context.bot.send_message(chat_id, f"<blockquote>ဟိတ် {mention}! မင်းမှာ link ချခွင့်မရှိဘူး 🫵</blockquote>", parse_mode=ParseMode.HTML)
            return

    # Database Saving
    if chat_id == SAVE_CHAT and get_bool("save") and (uid == OWNER_ID or uid in get_list("allow")):
        bully_list = get_list("bully")
        if text not in bully_list:
            bully_list.append(text); set_list("bully", bully_list)
            await update.message.reply_text(f"<blockquote>📝 သိမ်းလိုက်ပြီ: {text}</blockquote>", parse_mode=ParseMode.HTML)
            return

    # Custom Filters
    f_data = db.filters.find_one({"_id": text.lower()})
    if f_data: await update.message.reply_text(f"<blockquote>{f_data['reply']}</blockquote>", parse_mode=ParseMode.HTML)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # 1. Commands အရင် (အရေးကြီးဆုံး)
    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("stopbully", stopbully))
    app.add_handler(CommandHandler("markgp", markgp))
    app.add_handler(CommandHandler("sendallgp", sendallgp))
    app.add_handler(CommandHandler("save_on", lambda u,c: set_bool("save", True) or u.message.reply_text("<blockquote>✅ Learning: ON</blockquote>", parse_mode=ParseMode.HTML)))
    app.add_handler(CommandHandler("save_off", lambda u,c: set_bool("save", False) or u.message.reply_text("<blockquote>❌ Learning: OFF</blockquote>", parse_mode=ParseMode.HTML)))
    
    # 2. Service Updates (Status updates only)
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, service_handler))
    
    # 3. Text & Captions (Commands မဟုတ်တာတွေပဲ)
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND, main_handler))
    
    print("🚀 Young Master ThuRain V11 (Hybrid Fix) is Live...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__": main()
