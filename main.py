import asyncio
import re
import logging
import random
import io
from datetime import datetime
from pymongo import MongoClient
from PIL import Image, ImageDraw, ImageOps, ImageFont
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

client = MongoClient(MONGO_URI)
db = client["telegram_bot"] # Database name must match your cluster

bully_tasks = {} 
stop_events = {} 
save_bully_status = {}

# --- HELPERS ---
def bot_style(text):
    return f"<blockquote><b>{text}</b></blockquote>"

def is_allow(uid):
    if uid == OWNER_ID: return True
    if db.allow.find_one({"user_id": uid}): return True
    return False

# --- PREMIUM WELCOME IMAGE GENERATOR ---
async def generate_welcome_image(context, user, chat):
    # Base Background with Dark Gradient
    base = Image.new('RGB', (900, 450), color=(15, 15, 15))
    draw = ImageDraw.Draw(base)

    async def get_pfp(target_id, is_user=True):
        try:
            if is_user:
                photos = await context.bot.get_user_profile_photos(target_id, limit=1)
                file_id = photos.photos[0][-1].file_id
            else:
                chat_info = await context.bot.get_chat(target_id)
                file_id = chat_info.photo.big_file_id
            file = await context.bot.get_file(file_id)
            img_byte = await file.download_as_bytearray()
            return Image.open(io.BytesIO(img_byte)).convert("RGBA").resize((200, 200))
        except: return Image.new('RGBA', (200, 200), color=(40, 40, 40))

    u_p, g_p = await get_pfp(user.id, True), await get_pfp(chat.id, False)
    mask = Image.new('L', (200, 200), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 200, 200), fill=255)
    
    u_p = ImageOps.fit(u_p, mask.size, centering=(0.5, 0.5)); u_p.putalpha(mask)
    g_p = ImageOps.fit(g_p, mask.size, centering=(0.5, 0.5)); g_p.putalpha(mask)

    # Paste PFPs (Left and Right)
    base.paste(u_p, (70, 125), u_p)
    base.paste(g_p, (630, 125), g_p)

    # Draw Text
    draw.text((320, 50), "WELCOME TO", fill="white")
    draw.text((280, 85), f"{chat.title[:20]}", fill="#FF3131")
    draw.text((330, 340), f"NAME: {user.first_name[:15]}", fill="white")
    draw.text((330, 375), f"USER ID: {user.id}", fill="#FF3131")

    buf = io.BytesIO(); base.save(buf, format='PNG'); buf.seek(0)
    return buf

# --- AUTO DELETE SERVICE ---
async def auto_delete(message, delay=60):
    await asyncio.sleep(delay)
    try: await message.delete()
    except: pass

# --- MEMBER UPDATES ---
async def member_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member if update.chat_member else update.my_chat_member
    if not result: return
    chat, user = update.effective_chat, result.new_chat_member.user
    old_s, new_s = result.old_chat_member.status, result.new_chat_member.status

    # Service Clean: Delete "Joined/Left" service messages
    if update.message and (update.message.new_chat_members or update.message.left_chat_member):
        asyncio.create_task(auto_delete(update.message, 5))

    # Welcome
    if old_s in ["left", "kicked"] and new_s in ["member", "administrator"]:
        img = await generate_welcome_image(context, user, chat)
        caption = bot_style(f"✨ Welcome to {chat.title} ✨\n\n🏷 Name: {user.full_name}\n🆔 User ID: {user.id}\n👋 Mention: <a href='tg://user?id={user.id}'>Link</a>\n⏰ Joined at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        msg = await context.bot.send_photo(chat.id, photo=img, caption=caption, parse_mode=ParseMode.HTML)
        asyncio.create_task(auto_delete(msg, 60))

    # Goodbye
    elif old_s in ["member", "administrator"] and new_s in ["left", "kicked"]:
        bye = bot_style(f"👋 {user.full_name} left {chat.title}")
        msg = await context.bot.send_message(chat_id=chat.id, text=bye, parse_mode=ParseMode.HTML)
        asyncio.create_task(auto_delete(msg, 30))

# --- BULLY COMMANDS ---
async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id): return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text(bot_style("Reply ပြန်ပါ Chief!"))

    # Database မှ Bully words များဆွဲထုတ်ခြင်း
    words_data = list(db.bully.find())
    words = [w["text"] for w in words_data]
    
    if not words: return await update.message.reply_text(bot_style("No bully words in Database!"))

    chat_id = update.effective_chat.id
    stop_events[chat_id] = asyncio.Event()

    async def loop():
        while not stop_events[chat_id].is_set():
            w = random.choice(words)
            await context.bot.send_message(chat_id, bot_style(f"<a href='tg://user?id={target.id}'>{target.full_name}</a> {w}"), parse_mode=ParseMode.HTML)
            if save_bully_status.get(chat_id):
                db.bully_messages.insert_one({"word": w, "target": target.id, "time": datetime.now()})
            await asyncio.sleep(2)

    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(bot_style(f"🔥 Bully Started on {target.full_name}"))

async def stop_bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in stop_events:
        stop_events[chat_id].set()
    await update.message.reply_text(bot_style("Bully Stopped!"))

# --- DATABASE VIEWS ---
async def tbm_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = db.bully_messages.count_documents({})
    await update.message.reply_text(bot_style(f"Total bully messages saved: {count}"))

async def allowlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = list(db.allow.find())
    text = "Allow Users List:\n\n"
    for u in users:
        text += f"• <a href='tg://user?id={u['user_id']}'>{u['name']}</a>\n"
    await update.message.reply_text(bot_style(text or "Allowlist is empty!"), parse_mode=ParseMode.HTML)

# --- MAIN HANDLER (Group Tracking & Filter) ---
async def main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    chat_id, uid = update.effective_chat.id, update.effective_user.id
    
    # Auto Group Sync
    if update.effective_chat.type in ["group", "supergroup"]:
        db.groups.update_one({"chat_id": chat_id}, {"$set": {"title": update.effective_chat.title}}, upsert=True)

    # Link Filter
    if uid != OWNER_ID and not (await context.bot.get_chat_member(chat_id, uid)).status == ChatMember.ADMINISTRATOR:
        if re.search(r"(https?://\S+|t\.me/\S+)", update.message.text or ""):
            try: await update.message.delete()
            except: pass

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(ChatMemberHandler(member_update_handler, ChatMemberHandler.ANY_CHAT_MEMBER))
    app.add_handler(CommandHandler("bully", bully_cmd))
    app.add_handler(CommandHandler("stopbully", stop_bully_cmd))
    app.add_handler(CommandHandler("tbm", tbm_cmd))
    app.add_handler(CommandHandler("allowlist", allowlist_cmd))
    app.add_handler(CommandHandler("save_on", lambda u,c: save_bully_status.update({u.effective_chat.id: True}) or u.message.reply_text(bot_style("Save ON"))))
    app.add_handler(CommandHandler("save_off", lambda u,c: save_bully_status.update({u.effective_chat.id: False}) or u.message.reply_text(bot_style("Save OFF"))))
    
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, main_handler))
    
    print("🚀 Young Master ThuRain V45.0 Live...")
    app.run_polling()

if __name__ == "__main__": main()
