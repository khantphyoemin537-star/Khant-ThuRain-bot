import asyncio
import logging
import random
import io
import os
import threading
from datetime import datetime
from flask import Flask
from pymongo import MongoClient
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

# --- FLASK FOR KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "BoD Premium Bot is Active!"
def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIG ---
TOKEN = "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU" 
OWNER_ID = 6015356597 
ADMIN_GROUP_ID = -1003580630981 
SAVE_CHAT_ID = -1003580630981
ADMIN_CHAT_MENTION = "@Besties_with_BoD"
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["telegram_bot"] 

bully_tasks = {} 

# --- HELPERS ---
def bot_style(text):
    return f"<blockquote><b>{text}</b></blockquote>"

def is_allowed_user(uid):
    if uid == OWNER_ID: return True
    return db.allow_users.find_one({"user_id": uid}) is not None

async def is_real_admin(chat, user_id):
    if user_id == OWNER_ID: return True
    try:
        member = await chat.get_member(user_id)
        return member.status in [ChatMember.OWNER, ChatMember.ADMINISTRATOR]
    except: return False

# --- PERMISSION WRAPPERS ---
async def check_bully_perm(update: Update):
    if is_allowed_user(update.effective_user.id): return True
    await update.message.reply_text(bot_style(f"ဟိတ်.. မင်းမှာ Bully ခွင့်မရှိဘူး! {ADMIN_CHAT_MENTION} မှာ အရင်ခွင့်တောင်း။"), parse_mode=ParseMode.HTML)
    return False

# --- BULLY SYSTEM (REGENERATING LOOP) ---
async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_bully_perm(update): return
    reply = update.message.reply_to_message
    if not reply: return await update.message.reply_text(bot_style("Bully ချင်ရင် စာတစ်ကြောင်းကို Reply ပြန်ပေး!"), parse_mode=ParseMode.HTML)
    
    target = reply.from_user
    chat_id = update.effective_chat.id
    
    if chat_id in bully_tasks:
        bully_tasks[chat_id].cancel()

    async def bully_loop():
        last_word = None
        while True:
            try:
                words_cursor = db.filters.find()
                words = [w.get("text") for w in list(words_cursor) if w.get("text")]
                if not words: break
                
                # စာသားမထပ်အောင် ရွေးချယ်ခြင်း
                current_word = random.choice(words)
                while current_word == last_word and len(words) > 1:
                    current_word = random.choice(words)
                last_word = current_word

                mention = f"<a href='tg://user?id={target.id}'>{target.full_name}</a>"
                await context.bot.send_message(chat_id, bot_style(f"{mention} {current_word}"), parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.1) # Extreme Speed

            except Exception as e:
                # Flood ဖြစ်ရင် ၁ စက္ကန့်နားပြီး အလိုအလျောက် Job အသစ်နဲ့ အစားထိုးတယ်
                logging.warning(f"Flood or Error: {e}. Restarting loop...")
                await asyncio.sleep(1)
                continue

    bully_tasks[chat_id] = asyncio.create_task(bully_loop())
    await update.message.reply_text(bot_style(f"🔥 {target.full_name} ကို အနားမပေးဘဲ BULLY နေပါပြီ..."), parse_mode=ParseMode.HTML)

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_bully_perm(update): return
    chat_id = update.effective_chat.id
    if chat_id in bully_tasks:
        bully_tasks[chat_id].cancel()
        del bully_tasks[chat_id]
        await update.message.reply_text(bot_style("Bully အစီအစဉ်ကို ရပ်ဆိုင်းလိုက်ပါပြီ။"), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(bot_style("လက်ရှိမှာ Bully လုပ်နေတာ မရှိပါဘူး။"), parse_mode=ParseMode.HTML)

# --- ADMIN LISTS & PERMS ---
async def allow_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Allowed user စာရင်းကြည့်တာကိုတော့ ဘယ်သူမဆို ကြည့်လို့ရအောင် ထားပေးထားပါတယ်
    users = list(db.allow_users.find())
    if not users:
        return await update.message.reply_text(bot_style("Allow List ထဲမှာ ဘယ်သူမှ မရှိသေးပါ။"), parse_mode=ParseMode.HTML)
    
    msg = "<b>BULLY ALLOWED USERS:</b>\n\n"
    for u in users:
        msg += f"• {u.get('name')} (<code>{u.get('user_id')}</code>)\n"
    await update.message.reply_text(bot_style(msg), parse_mode=ParseMode.HTML)

async def add_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    reply = update.message.reply_to_message
    if not reply: return
    target = reply.from_user
    db.allow_users.update_one({"user_id": target.id}, {"$set": {"name": target.full_name}}, upsert=True)
    await update.message.reply_text(bot_style(f"✅ {target.full_name} ကို Bully Command သုံးခွင့် ပေးလိုက်ပါပြီ။"), parse_mode=ParseMode.HTML)

# --- ADMIN ACTIONS (REAL ADMIN CHECK) ---
async def admin_mod_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if not await is_real_admin(chat, user.id):
        return await update.message.reply_text(bot_style("မင်းက Admin မဟုတ်ဘဲနဲ့ လာမပိုင်နဲ့!"), parse_mode=ParseMode.HTML)
    
    cmd = update.message.text.split()[0][1:].lower()
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target or target.id == OWNER_ID: return
    
    try:
        if cmd == "ban": await chat.ban_member(target.id); msg = f"🚫 {target.full_name} ကို ကန်ထုတ်လိုက်ပြီ။"
        elif cmd == "mute": await chat.restrict_member(target.id, ChatPermissions(can_send_messages=False)); msg = f"🔇 {target.full_name} စကားအ၊ သွားပြီ။"
        elif cmd == "unmute": await chat.restrict_member(target.id, ChatPermissions(can_send_messages=True)); msg = f"🔊 {target.full_name} ပြန်ပြောလို့ရပြီ။"
        await update.message.reply_text(bot_style(msg), parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(bot_style(f"Error: {e}"), parse_mode=ParseMode.HTML)

# --- ADMIN MENTION (/adm) ---
async def admin_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_real_admin(update.effective_chat, update.effective_user.id): return
    admins = await update.effective_chat.get_administrators()
    input_text = " ".join(context.args).upper() if context.args else "ADMINS အကုန်ထွက်ခဲ့စမ်း!"
    mention_msg = f"{input_text}\n\n"
    mention_msg += "\n".join([f"• <a href='tg://user?id={a.user.id}'>{a.user.first_name}</a>" for a in admins if not a.user.is_bot])
    await update.message.reply_text(bot_style(mention_msg), parse_mode=ParseMode.HTML)

# --- GLOBAL HANDLER (SAVE BY OWNER ONLY) ---
async def global_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat_id, user, text = update.effective_chat.id, update.effective_user, update.message.text
    
    if chat_id == SAVE_CHAT_ID and user.id == OWNER_ID:
        res = db.settings.find_one({"_id": f"save_{chat_id}"})
        if res and res.get("data") and not text.startswith('/'):
            db.filters.update_one({"text": text}, {"$set": {"added_by": user.id}}, upsert=True)
            await update.message.reply_text(bot_style("📝 စာသားအသစ် သိမ်းဆည်းပြီး။"), parse_mode=ParseMode.HTML)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app_bot = ApplicationBuilder().token(TOKEN).build()
    
    app_bot.add_handler(CommandHandler("bully", bully_cmd))
    app_bot.add_handler(CommandHandler("stopbully", stop_bully))
    app_bot.add_handler(CommandHandler("allowlist", allow_list))
    app_bot.add_handler(CommandHandler("addallow", add_allow))
    app_bot.add_handler(CommandHandler("adm", admin_mention))
    app_bot.add_handler(CommandHandler(["ban", "mute", "unmute"], admin_mod_actions))
    
    app_bot.add_handler(CommandHandler("save_on", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": True}}, upsert=True), asyncio.create_task(u.message.reply_text(bot_style("✅ Save ON (Owner Only)"), parse_mode=ParseMode.HTML))) if u.effective_user.id == OWNER_ID else None))
    app_bot.add_handler(CommandHandler("save_off", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": False}}, upsert=True), asyncio.create_task(u.message.reply_text(bot_style("❌ Save OFF"), parse_mode=ParseMode.HTML))) if u.effective_user.id == OWNER_ID else None))

    app_bot.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, global_handler))
    
    print("🚀 BoD Premium Bot is running...")
    app_bot.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__": main()
