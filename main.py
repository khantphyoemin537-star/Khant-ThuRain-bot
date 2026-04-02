import asyncio
import logging
import random
import io
import re
from datetime import datetime
from pymongo import MongoClient
from PIL import Image, ImageDraw, ImageOps, ImageFilter

from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ChatMemberHandler,
    filters
)

# ---------------- CONFIG ---------------- #
TOKEN = "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU"
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
logging.basicConfig(level=logging.INFO)

bully_tasks = {}
stop_events = {}

# ---------------- STYLE & HELPERS ---------------- #
def bot_style(text):
    return f"<blockquote><b>{text}</b></blockquote>"

def is_allow(uid):
    if uid == OWNER_ID: return True
    return db.allow.find_one({"id": uid}) is not None

async def is_admin(chat, user_id):
    try:
        member = await chat.get_member(user_id)
        return member.status in ["administrator", "creator"]
    except: return False

# ---------------- IMAGE GENERATOR (PILLOW) ---------------- #
async def generate_welcome_image(context, user, chat):
    try:
        width, height = 900, 450
        async def get_pfp(target_id, is_user=True):
            try:
                if is_user:
                    photos = await context.bot.get_user_profile_photos(target_id, limit=1)
                    file_id = photos.photos[0][-1].file_id
                else:
                    info = await context.bot.get_chat(target_id)
                    file_id = info.photo.big_file_id
                file = await context.bot.get_file(file_id)
                byte_arr = await file.download_as_bytearray()
                return Image.open(io.BytesIO(byte_arr)).convert("RGBA")
            except: return Image.new('RGBA', (400, 400), (30, 30, 30, 255))

        u_img = await get_pfp(user.id, True)
        g_img = await get_pfp(chat.id, False)

        # Background Blur
        bg = g_img.resize((width, height), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(20))
        overlay = Image.new('RGBA', bg.size, (0, 0, 0, 160))
        bg = Image.alpha_composite(bg, overlay)

        # Circles
        mask = Image.new('L', (200, 200), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 200, 200), fill=255)
        u_p = ImageOps.fit(u_img, (200, 200)); u_p.putalpha(mask)
        g_p = ImageOps.fit(g_img, (200, 200)); g_p.putalpha(mask)

        bg.paste(u_p, (150, 100), u_p)
        bg.paste(g_p, (550, 100), g_p)

        draw = ImageDraw.Draw(bg)
        draw.text((370, 40), "WELCOME", fill="white")
        draw.text((320, 330), f"Name: {user.first_name[:25]}", fill="white")
        draw.text((320, 360), f"ID: {user.id}", fill="#FF3131")

        buf = io.BytesIO(); bg.convert("RGB").save(buf, "JPEG"); buf.seek(0)
        return buf
    except: return None

# ---------------- HANDLERS ---------------- #
async def member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member if update.chat_member else update.my_chat_member
    if not result: return
    chat, user = update.effective_chat, result.new_chat_member.user
    old_s, new_s = result.old_chat_member.status, result.new_chat_member.status

    if new_s in ["member", "administrator"] and old_s not in ["member", "administrator"]:
        img = await generate_welcome_image(context, user, chat)
        cap = f"ဟိတ် <b>{chat.title}</b> ကနေ {user.full_name} ကို ကြိုဆိုပါတယ်!\nID: {user.id}"
        if img: await context.bot.send_photo(chat.id, img, caption=bot_style(cap), parse_mode=ParseMode.HTML)
        else: await context.bot.send_message(chat.id, bot_style(cap), parse_mode=ParseMode.HTML)
    elif new_s in ["left", "kicked"] and old_s in ["member", "administrator"]:
        await context.bot.send_message(chat.id, bot_style(f"👋 {user.full_name} ထွက်သွားပါပြီ။"), parse_mode=ParseMode.HTML)

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if not await is_admin(chat, user.id): return
    cmd = update.message.text.split()[0].lower()
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return
    try:
        if "unmute" in cmd:
            # Full permissions restore
            p = ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True, can_invite_users=True)
            await chat.restrict_member(target.id, p); msg = f"🔊 {target.full_name} ကို Mute ဖြည်ပေးလိုက်ပါပြီ။"
        elif "mute" in cmd:
            await chat.restrict_member(target.id, ChatPermissions(can_send_messages=False)); msg = f"🔇 {target.full_name} ကို Mute လိုက်ပါပြီ။"
        elif "ban" in cmd:
            await chat.ban_member(target.id); msg = f"🚫 {target.full_name} ကို Ban လိုက်ပါပြီ။"
        await update.message.reply_text(bot_style(msg), parse_mode=ParseMode.HTML)
    except Exception as e: await update.message.reply_text(f"Error: {e}")

async def global_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat, user, text = update.effective_chat, update.effective_user, update.message.text
    
    # Filter Link/Spam
    if re.search(r"(https?://|t\.me/|www\.)", text) and not await is_admin(chat, user.id):
        await update.message.delete(); return
    if update.message.entities and len([e for e in update.message.entities if e.type == "mention"]) >= 5:
        await update.message.delete(); return

    # Save Chat
    if not text.startswith('/'):
        res = db.settings.find_one({"_id": f"save_{chat.id}"})
        if res and res.get("data") == True and len(text.strip()) >= 2:
            db.filters.update_one({"text": text}, {"$set": {"text": text, "by": user.id}}, upsert=True)

# ---------------- BULLY & ALLOW ---------------- #
async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id): return
    reply = update.message.reply_to_message
    if not reply: return
    target, chat_id = reply.from_user, update.effective_chat.id
    words = [w["text"] for w in list(db.filters.find())]
    if not words: return await update.message.reply_text(bot_style("DB ထဲမှာ စာမရှိသေးဘူး Chief!"))
    
    if chat_id in stop_events: stop_events[chat_id].set()
    stop_events[chat_id] = asyncio.Event()
    async def loop():
        while not stop_events[chat_id].is_set():
            w = random.choice(words)
            mention = f"<a href='tg://user?id={target.id}'>{target.full_name}</a>"
            try: await context.bot.send_message(chat_id, bot_style(f"{mention} {w}"), parse_mode=ParseMode.HTML)
            except: break
            await asyncio.sleep(3.5)
    asyncio.create_task(loop())

# ---------------- MAIN ---------------- #
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("addallow", lambda u,c: db.allow.update_one({"id": u.message.reply_to_message.from_user.id}, {"$set": {"name": u.message.reply_to_message.from_user.full_name}}, upsert=True) if u.message.reply_to_message else None))
    app.add_handler(CommandHandler("allowlist", lambda u,c: u.message.reply_text(bot_style("📜 Allow List:\n" + "\n".join([f"- {x['name']}" for x in db.allow.find()])), parse_mode=ParseMode.HTML)))
    app.add_handler(CommandHandler("save_on", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": True}}, upsert=True), u.message.reply_text(bot_style("✅ Auto Save ON")))))
    app.add_handler(CommandHandler("save_off", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": False}}, upsert=True), u.message.reply_text(bot_style("❌ Auto Save OFF")))))
    app.add_handler(CommandHandler(["mute", "unmute", "ban"], admin_action))
    app.add_handler(CommandHandler("bully", bully_cmd))
    app.add_handler(CommandHandler("stopbully", lambda u,c: stop_events[u.effective_chat.id].set() if u.effective_chat.id in stop_events else None))
    
    app.add_handler(ChatMemberHandler(member_update, ChatMemberHandler.ANY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, global_handler))
    
    print("🚀 Master Dexter Bot Started!")
    app.run_polling()

if __name__ == "__main__": main()
