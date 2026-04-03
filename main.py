import asyncio
import logging
import random
import io
from datetime import datetime
from pymongo import MongoClient
from PIL import Image, ImageDraw, ImageOps, ImageFilter, ImageFont
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

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIG ---
TOKEN = "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU" 
OWNER_ID = 6015356597 
ADMIN_GROUP_ID = -1003580630981 
SAVE_CHAT_ID = -1003864912245 
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["telegram_bot"] 

bully_tasks = {} 
stop_events = {} 

# --- HELPERS ---
def bot_style(text):
    return f"<blockquote><b>{text}</b></blockquote>"

def is_allow(uid):
    if uid == OWNER_ID: return True
    return db.allow_users.find_one({"user_id": uid}) is not None

async def check_admin(chat, user_id):
    try:
        member = await chat.get_member(user_id)
        return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except: return False

async def get_owner_mention(context):
    try:
        owner = await context.bot.get_chat(OWNER_ID)
        return f"<a href='tg://user?id={OWNER_ID}'>{owner.full_name}</a>"
    except: return "Chief Dexter"

# --- PILLOW IMAGE GENERATOR ---
async def generate_welcome_image(context, user, chat):
    try:
        width, height = 1000, 500
        canvas = Image.new('RGBA', (width, height), (15, 15, 20, 255)) 
        
        async def get_img(target_id, is_user=True):
            try:
                if is_user:
                    photos = await context.bot.get_user_profile_photos(target_id, limit=1)
                    file_id = photos.photos[0][-1].file_id
                else:
                    c_info = await context.bot.get_chat(target_id)
                    file_id = c_info.photo.big_file_id
                file = await context.bot.get_file(file_id)
                b = await file.download_as_bytearray()
                return Image.open(io.BytesIO(b)).convert("RGBA")
            except:
                return Image.new('RGBA', (400, 400), (40, 40, 40))

        user_pfp = await get_img(user.id, True)
        group_pfp = await get_img(chat.id, False)

        size = (300, 300)
        mask = Image.new('L', size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0) + size, fill=255)

        u_p = ImageOps.fit(user_pfp, size); u_p.putalpha(mask)
        g_p = ImageOps.fit(group_pfp, size); g_p.putalpha(mask)

        canvas.paste(u_p, (100, 100), u_p)
        canvas.paste(g_p, (600, 100), g_p)

        draw = ImageDraw.Draw(canvas)
        draw.ellipse((95, 95, 95+310, 95+310), outline="#00D2FF", width=8)
        draw.ellipse((595, 95, 595+310, 95+310), outline="#9D50BB", width=8)

        draw.text((380, 40), "WELCOME TO BoD FAMILY", fill="white")
        draw.text((430, 430), f"{user.first_name[:15]}", fill="white")

        buf = io.BytesIO()
        canvas.convert("RGB").save(buf, format='JPEG', quality=95)
        buf.seek(0)
        return buf
    except Exception as e:
        logging.error(f"Image Error: {e}")
        return None

# --- ADMIN ACTIONS ---
async def admin_mod_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if not await check_admin(chat, user.id): return
    
    cmd = update.message.text.split()[0][1:].lower()
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    
    if not target: return
    if target.id == OWNER_ID: return await update.message.reply_text("Boss ကိုတော့ ထိလို့မရဘူးဗျ။")

    try:
        if cmd == "ban": await chat.ban_member(target.id); msg = f"🚫 {target.full_name} ကို အပြီးထုတ်လိုက်ပါပြီ။"
        elif cmd == "unban": await chat.unban_member(target.id); msg = f"🔊 {target.full_name} ကို ပြန်ဝင်ခွင့်ပေးလိုက်ပါပြီ။"
        elif cmd == "mute": await chat.restrict_member(target.id, ChatPermissions(can_send_messages=False)); msg = f"🔇 {target.full_name} ကို စာရိုက်ခွင့် ပိတ်လိုက်ပါပြီ။"
        elif cmd == "unmute": await chat.restrict_member(target.id, ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)); msg = f"🔊 {target.full_name} ကို စာပြန်ရိုက်ခွင့် ပေးလိုက်ပါပြီ။"
        elif cmd == "kick": await chat.unban_member(target.id); msg = f"👋 {target.full_name} ကို ကန်ထုတ်လိုက်ပါပြီ။"
        await update.message.reply_text(bot_style(msg), parse_mode=ParseMode.HTML)
    except Exception as e: await update.message.reply_text(f"Error: {e}")

# --- BOT JOINS & MEMBER UPDATES ---
async def on_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member if update.chat_member else update.my_chat_member
    if not result: return
    chat, user = update.effective_chat, result.new_chat_member.user
    old_s, new_s = result.old_chat_member.status, result.new_chat_member.status
    owner_mention = await get_owner_mention(context)

    # Bot added to group logic
    if user.id == context.bot.id and new_s in ["member", "administrator"]:
        count = await chat.get_member_count()
        join_msg = (f"ဟိတ်ရို့ /admins မင်းတို့ရဲ့ဒီ <b>{chat.title} ({count})</b> ကို ထည့်သွင်းအသုံးပြုပေးတဲ့အတွက် ကျေးဇူး၊\n"
                    f"အမ် အသုံးဝင်မယ့် တချို့ကန့်သန့်ထားတဲ့ bot command တွေသုံးမယ်ဆို @Besties_with_BoD က OWNER ဆီကို လာတောင်းပါ။\n\n"
                    f"<b>Bot Creator:</b> {owner_mention}")
        await context.bot.send_message(chat.id, join_msg, parse_mode=ParseMode.HTML)
        
        # Log to Admin Group
        admin_log = (f"📢 <b>Bot Added to New Group!</b>\n\n"
                     f"Group: {chat.title}\nID: <code>{chat.id}</code>\n"
                     f"Members: {count}\nCreator: {owner_mention}")
        await context.bot.send_message(ADMIN_GROUP_ID, admin_log, parse_mode=ParseMode.HTML)

    # Welcome Image logic
    if old_s in ["left", "kicked"] and new_s in ["member", "administrator"] and user.id != context.bot.id:
        img = await generate_welcome_image(context, user, chat)
        caption = (f"✨ <b>Welcome to {chat.title}</b> ✨\n"
                   f"🏷️ Name: {user.full_name}\n"
                   f"🆔 ID: <code>{user.id}</code>\n"
                   f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
        btn = [[InlineKeyboardButton("Support Group", url="https://t.me/BoD_Network")]]
        if img: await context.bot.send_photo(chat.id, photo=img, caption=bot_style(caption), reply_markup=InlineKeyboardMarkup(btn), parse_mode=ParseMode.HTML)

# --- BULLY & SYSTEM HANDLERS ---
async def add_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text(bot_style("Reply ပြန်ပေးပါ Chief!"), parse_mode=ParseMode.HTML)
    db.allow_users.update_one({"user_id": target.id}, {"$set": {"name": target.full_name}}, upsert=True)
    await update.message.reply_text(bot_style(f"✅ {target.full_name} ကို Bully ခွင့်ပြုလိုက်ပါပြီ။"), parse_mode=ParseMode.HTML)

async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id): return
    reply = update.message.reply_to_message
    if not reply: return
    target, chat_id = reply.from_user, update.effective_chat.id
    words = [w.get("text") for w in list(db.filters.find()) if w.get("text")]
    if not words: return
    
    stop_events[chat_id] = asyncio.Event()
    async def loop():
        while not stop_events[chat_id].is_set():
            await context.bot.send_message(chat_id, f"<a href='tg://user?id={target.id}'>{target.full_name}</a> {random.choice(words)}", parse_mode=ParseMode.HTML)
            await asyncio.sleep(3.5)
    asyncio.create_task(loop())
    await update.message.reply_text(bot_style(f"🔥 {target.full_name} ကို စတင် Bully နေပါပြီ..."), parse_mode=ParseMode.HTML)

async def global_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat_id, user, text = update.effective_chat.id, update.effective_user, update.message.text
    if chat_id == SAVE_CHAT_ID:
        res = db.settings.find_one({"_id": f"save_{chat_id}"})
        if res and res.get("data") and not text.startswith('/'):
            db.filters.update_one({"text": text}, {"$set": {"added_by": user.id}}, upsert=True)
            await update.message.reply_text(bot_style("📝 သိမ်းဆည်းပြီးပါပြီ။"), parse_mode=ParseMode.HTML)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Basic Cmds
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler("bully", bully_cmd))
    app.add_handler(CommandHandler("stopbully", lambda u,c: (stop_events[u.effective_chat.id].set() if u.effective_chat.id in stop_events else None, u.message.reply_text("🛑 Stop!"))))
    
    # Save Settings
    app.add_handler(CommandHandler("save_on", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": True}}, upsert=True), u.message.reply_text("✅ Save ON"))))
    app.add_handler(CommandHandler("save_off", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": False}}, upsert=True), u.message.reply_text("❌ Save OFF"))))
    
    # Mod Actions
    app.add_handler(CommandHandler(["ban", "unban", "mute", "unmute", "kick"], admin_mod_actions))
    
    # Handlers
    app.add_handler(ChatMemberHandler(on_member_update, ChatMemberHandler.ANY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, global_handler))
    
    print("🚀 BoD Premium Bot is Running...")
    app.run_polling()

if __name__ == "__main__": main()

