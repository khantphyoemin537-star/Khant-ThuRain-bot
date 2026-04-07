import asyncio
import logging
import random
import io
import os
import threading
from datetime import datetime
from flask import Flask
from pymongo import MongoClient
from PIL import Image, ImageDraw, ImageOps
from telegram import Update, ChatMember, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    ChatMemberHandler
)

# --- FLASK FOR RAILWAY KEEP-ALIVE ---
app = Flask('')

@app.route('/')
def home():
    return "BoD Premium Bot is Running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIG ---
TOKEN = "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU" 
OWNER_ID = 6015356597 
ADMIN_GROUP_ID = -1003580630981 
SAVE_CHAT_ID = -1003864912245 
ADMIN_CHAT_MENTION = "@Besties_with_BoD"
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["telegram_bot"] 

bully_tasks = {} 

# --- HELPERS ---
def bot_style(text):
    return f"<blockquote><b>{text}</b></blockquote>"

def is_allow(uid):
    if uid == OWNER_ID: return True
    return db.allow_users.find_one({"user_id": uid}) is not None

async def check_admin_rights(chat, user_id):
    """အမှန်တကယ် Admin Rights ရှိမရှိ စစ်ဆေးခြင်း"""
    if user_id == OWNER_ID: return True
    try:
        member = await chat.get_member(user_id)
        return member.status in [ChatMember.OWNER, ChatMember.ADMINISTRATOR]
    except: return False

async def get_owner_mention(context):
    try:
        owner = await context.bot.get_chat(OWNER_ID)
        return f"<a href='tg://user?id={OWNER_ID}'>{owner.full_name}</a>"
    except: return "CHIEF DEXTER"

# --- PERMISSION CHECK ---
async def check_perm(update: Update):
    user = update.effective_user
    if is_allow(user.id): return True
    mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    msg = f"ဟိတ် {mention} မင်းမှာ COMMAND သုံးခွင့်မရှိဘူး!! သုံးမယ်ဆို ငါတို့ရဲ့ {ADMIN_CHAT_MENTION} ကိုလာတောင်း"
    await update.message.reply_text(bot_style(msg), parse_mode=ParseMode.HTML)
    return False

# --- ADMIN LIST MENTION (/adm) ---
async def admin_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not await check_perm(update): return
    
    # စာသားပါရင် ယူမယ်
    input_text = " ".join(context.args) if context.args else "ADMINS အကုန်ထွက်ခဲ့စမ်း!!"
    
    try:
        admins = await chat.get_administrators()
        mention_list = []
        for admin in admins:
            if not admin.user.is_bot:
                mention_list.append(f"• <a href='tg://user?id={admin.user.id}'>{admin.user.first_name}</a>")
        
        full_msg = f"{input_text.upper()}\n\n" + "\n".join(mention_list)
        await update.message.reply_text(bot_style(full_msg), parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(bot_style(f"Error: {e}"), parse_mode=ParseMode.HTML)

# --- ADMIN ACTIONS (FIXED PERMISSION) ---
async def admin_mod_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    # Admin Right မရှိရင် လုံးဝသုံးခွင့်မပေးပါ
    if not await check_admin_rights(chat, user.id):
        return await update.message.reply_text(bot_style("မင်းက Admin မဟုတ်ဘဲနဲ့ လာမပိုင်နဲ့နော်!!"), parse_mode=ParseMode.HTML)
    
    if not await check_perm(update): return
    
    cmd = update.message.text.split()[0][1:].lower()
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return
    
    if target.id == OWNER_ID: 
        return await update.message.reply_text(bot_style("Creator ကို ထိရင် မင်းအကောင့်ပါပျံသွားမယ်ညီလေး!"), parse_mode=ParseMode.HTML)
    
    try:
        if cmd == "ban": await chat.ban_member(target.id); msg = f"🚫 {target.full_name} ကို အပြီးထုတ်လိုက်ပါပြီ။"
        elif cmd == "unban": await chat.unban_member(target.id); msg = f"🔊 {target.full_name} ကို ပြန်ဝင်ခွင့်ပေးလိုက်ပါပြီ။"
        elif cmd == "mute": await chat.restrict_member(target.id, ChatPermissions(can_send_messages=False)); msg = f"🔇 {target.full_name} ကို စာရိုက်ခွင့် ပိတ်လိုက်ပါပြီ။"
        elif cmd == "unmute":
            await chat.restrict_member(target.id, ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True))
            msg = f"🔊 {target.full_name} ကို စာပြန်ရိုက်ခွင့် ပေးလိုက်ပါပြီ။"
        elif cmd == "kick": await chat.unban_member(target.id); msg = f"👋 {target.full_name} ကို ကန်ထုတ်လိုက်ပါပြီ။"
        await update.message.reply_text(bot_style(msg), parse_mode=ParseMode.HTML)
    except Exception as e: await update.message.reply_text(bot_style(f"Error: {e}"), parse_mode=ParseMode.HTML)

# --- BULLY SYSTEM (0.2s HIGH SPEED + HTML) ---
async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    reply = update.message.reply_to_message
    if not reply: return
    
    target, chat_id = reply.from_user, update.effective_chat.id
    words = [w.get("text") for w in list(db.filters.find()) if w.get("text")]
    if not words: return
    
    if chat_id in bully_tasks:
        bully_tasks[chat_id].cancel()

    async def loop():
        try:
            while True:
                mention = f"<a href='tg://user?id={target.id}'>{target.full_name}</a>"
                bully_text = f"{mention} {random.choice(words)}"
                await context.bot.send_message(chat_id, bot_style(bully_text), parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.2) # Dexter တောင်းဆိုထားတဲ့ အရှိန်
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.error(f"Bully Error: {e}")

    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(bot_style(f"🔥 {target.full_name} ကို အရှိန်အပြည့်နဲ့ စတင် BULLY နေပါပြီ..."), parse_mode=ParseMode.HTML)

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    chat_id = update.effective_chat.id
    task = bully_tasks.get(chat_id)
    if task:
        task.cancel()
        del bully_tasks[chat_id]
        await update.message.reply_text(bot_style("မင်းက ရပ်ခိုင်းလို့ နားလိုက်မယ်.. နောက်တစ်ခါဆို ပိုကြမ်းမယ်!"), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(bot_style("လက်ရှိမှာ ဘယ်သူ့ကိုမှ Bully မလုပ်နေပါဘူး။"), parse_mode=ParseMode.HTML)

# --- BROADCAST SYSTEM ---
async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message:
        return await update.message.reply_text(bot_style("စာတခုခုကို REPLY ပြန်ပြီး /send သုံးပါ!"), parse_mode=ParseMode.HTML)
    
    groups = list(db.groups.find())
    success, fail = 0, 0
    for g in groups:
        try:
            await context.bot.copy_message(chat_id=g["chat_id"], from_chat_id=update.effective_chat.id, message_id=update.message.reply_to_message.message_id)
            success += 1
            await asyncio.sleep(0.3)
        except: fail += 1
    await update.message.reply_text(bot_style(f"📢 BROADCAST ပြီးပါပြီ!\nSUCCESS: {success}\nFAILED: {fail}"), parse_mode=ParseMode.HTML)

# --- MEMBER UPDATES ---
async def on_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member if update.my_chat_member else update.chat_member
    if not result: return
    chat, user = result.chat, result.new_chat_member.user
    new_s = result.new_chat_member.status

    if user.id == context.bot.id and new_s in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
        db.groups.update_one({"chat_id": chat.id}, {"$set": {"title": chat.title}}, upsert=True)
        count = await chat.get_member_count()
        owner_mention = await get_owner_mention(context)
        join_msg = f"WELCOME TO {chat.title}!\n\nTOTAL MEMBERS: {count}\nCREATOR: {owner_mention}"
        await context.bot.send_message(chat.id, bot_style(join_msg), parse_mode=ParseMode.HTML)

# --- GLOBAL HANDLERS ---
async def global_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat_id, user, text = update.effective_chat.id, update.effective_user, update.message.text
    if chat_id == SAVE_CHAT_ID:
        res = db.settings.find_one({"_id": f"save_{chat_id}"})
        if res and res.get("data") and not text.startswith('/'):
            db.filters.update_one({"text": text}, {"$set": {"added_by": user.id}}, upsert=True)
            await update.message.reply_text(bot_style("📝 စာသားအသစ်ကို Database ထဲ သိမ်းလိုက်ပါပြီ။"), parse_mode=ParseMode.HTML)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("adm", admin_mention))
    application.add_handler(CommandHandler("bully", bully_cmd))
    application.add_handler(CommandHandler("stopbully", stop_bully))
    application.add_handler(CommandHandler("send", broadcast_send))
    application.add_handler(CommandHandler(["ban", "unban", "mute", "unmute", "kick"], admin_mod_actions))
    
    application.add_handler(CommandHandler("save_on", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": True}}, upsert=True), asyncio.create_task(u.message.reply_text(bot_style("✅ Auto Save ON"), parse_mode=ParseMode.HTML)))))
    application.add_handler(CommandHandler("save_off", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": False}}, upsert=True), asyncio.create_task(u.message.reply_text(bot_style("❌ Auto Save OFF"), parse_mode=ParseMode.HTML)))))
    
    application.add_handler(ChatMemberHandler(on_member_update, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, global_handler))
    
    print("🚀 BoD Premium Bot is deploying by Dexter...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__": main()

