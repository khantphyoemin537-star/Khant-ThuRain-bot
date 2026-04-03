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

# --- PILLOW IMAGE GENERATOR (CHAT GPT STYLE) ---
async def generate_welcome_image(context, user, chat):
    try:
        # Canvas size
        width, height = 1000, 500
        canvas = Image.new('RGBA', (width, height), (20, 20, 25, 255)) # Dark Theme Background
        
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
                return Image.new('RGBA', (400, 400), (50, 50, 50))

        user_pfp = await get_img(user.id, True)
        group_pfp = await get_img(chat.id, False)

        # Draw Circles
        size = (280, 280)
        mask = Image.new('L', size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0) + size, fill=255)

        u_p = ImageOps.fit(user_pfp, size); u_p.putalpha(mask)
        g_p = ImageOps.fit(group_pfp, size); g_p.putalpha(mask)

        # Paste PFPs
        canvas.paste(u_p, (120, 110), u_p)
        canvas.paste(g_p, (600, 110), g_p)

        # Draw Borders
        draw = ImageDraw.Draw(canvas)
        draw.ellipse((115, 105, 115+290, 105+290), outline="#FFFFFF", width=5)
        draw.ellipse((595, 105, 595+290, 105+290), outline="#FFFFFF", width=5)

        # Text
        draw.text((360, 40), "WELCOME TO THE GROUP", fill="white")
        draw.text((430, 420), f"{user.first_name[:15]}", fill="white")
        draw.text((420, 450), f"ID: {user.id}", fill="#FF4444")

        buf = io.BytesIO()
        canvas.convert("RGB").save(buf, format='JPEG', quality=95)
        buf.seek(0)
        return buf
    except Exception as e:
        logging.error(f"Image Error: {e}")
        return None

# --- COMMANDS ---
async def add_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text(bot_style("ခွင့်ပြုမည့်သူကို Reply ပြန်ပေးပါ Chief!"), parse_mode=ParseMode.HTML)
    
    db.allow_users.update_one({"user_id": target.id}, {"$set": {"name": target.full_name, "id": target.id}}, upsert=True)
    await update.message.reply_text(bot_style(f"✅ {target.full_name} ({target.id}) ကို Database ထဲသို့ အမြဲတမ်းခွင့်ပြုချက် သိမ်းဆည်းလိုက်ပါပြီ။"), parse_mode=ParseMode.HTML)

async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id):
        return await update.message.reply_text(bot_style("ဟေ့🫵မင်းမှာ ဒီcommandသုံးခွင့်မရှိဘူး"), parse_mode=ParseMode.HTML)
    
    reply = update.message.reply_to_message
    if not reply: return await update.message.reply_text(bot_style("ဘယ်သူ့ကို Bully ရမလဲ (Reply ပြန်ပါ)"), parse_mode=ParseMode.HTML)
    
    target, chat_id = reply.from_user, update.effective_chat.id
    if target.id == OWNER_ID: return await update.message.reply_text("Bot Creator ကို bullyခွင့်မရှိဘူးညီ🫵", parse_mode=ParseMode.HTML)
    
    words = [w.get("text") for w in list(db.filters.find()) if w.get("text")]
    if not words: return await update.message.reply_text(bot_style("Database ထဲမှာ Bully ရန် စာသားများ မရှိသေးပါ။"), parse_mode=ParseMode.HTML)
    
    if chat_id in stop_events: stop_events[chat_id].set()
    stop_events[chat_id] = asyncio.Event()

    async def loop():
        while not stop_events[chat_id].is_set():
            w = random.choice(words)
            try:
                mention = f"<a href='tg://user?id={target.id}'>{target.full_name}</a>"
                await context.bot.send_message(chat_id, f"{mention} {w}", parse_mode=ParseMode.HTML)
            except: break
            await asyncio.sleep(3.5)
            
    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(bot_style(f"🔥 {target.full_name} ကို စတင် Bully နေပါပြီ..."), parse_mode=ParseMode.HTML)

# --- SAVE CHAT LOGIC ---
async def global_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    chat_id, user, text = update.effective_chat.id, update.effective_user, update.message.text or update.message.caption

    # Save logic for SAVE_CHAT_ID
    if chat_id == SAVE_CHAT_ID:
        res = db.settings.find_one({"_id": f"save_{chat_id}"})
        if res and res.get("data") and text and not text.startswith('/'):
            db.filters.update_one({"text": text}, {"$set": {"text": text, "added_by": user.id}}, upsert=True)
            await update.message.reply_text(bot_style("📝 စာသားကို Bully Database ထဲသို့ မှတ်သားပြီးပါပြီ။"), parse_mode=ParseMode.HTML)

# --- MEMBER UPDATE ---
async def on_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member if update.chat_member else update.my_chat_member
    if not result: return
    chat, user = update.effective_chat, result.new_chat_member.user
    old_s, new_s = result.old_chat_member.status, result.new_chat_member.status

    if user.id == context.bot.id and new_s in ["member", "administrator"]:
        # Bot added to group
        owner = await context.bot.get_chat(OWNER_ID)
        owner_mention = f"<a href='tg://user?id={OWNER_ID}'>{owner.full_name}</a>"
        
        await context.bot.send_message(chat.id, f"ဟိတ်ရို့ /admins မင်းတို့ရဲ့ဒီ <b>{chat.title}</b> ကို ထည့်သွင်းအသုံးပြုပေးတဲ့အတွက် ကျေးဇူး၊\nအသုံးဝင်မယ့် bot command တွေသုံးမယ်ဆို @Besties_with_BoD က OWNER ဆီကိုလာဆက်သွယ်ပေးပါ။\n\nOwner: {owner_mention}", parse_mode=ParseMode.HTML)
        
        # Notify Admin Group with Link
        link = f"<a href='https://t.me/c/{str(chat.id)[4:]}/1'>Group Link</a>" if str(chat.id).startswith("-100") else "No Link"
        admin_msg = (f"📢 <b>Group အသစ်သို့ဝင်ရောက်ခြင်း</b>\n\n"
                     f"<b>Group:</b> {chat.title}\n"
                     f"<b>ID:</b> <code>{chat.id}</code>\n"
                     f"<b>Link:</b> {link}\n"
                     f"<b>Owner:</b> {owner_mention}")
        await context.bot.send_message(ADMIN_GROUP_ID, admin_msg, parse_mode=ParseMode.HTML)

    if old_s in ["left", "kicked"] and new_s in ["member", "administrator"] and user.id != context.bot.id:
        img = await generate_welcome_image(context, user, chat)
        caption = (f"✨ <b>Welcome to {chat.title}</b> ✨\n\n"
                   f"🏷️ <b>Name:</b> {user.full_name}\n"
                   f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
                   f"⏰ <b>Joined at:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        btn = [[InlineKeyboardButton("ADD ME TO YOUR GROUP", url=f"https://t.me/{(await context.bot.get_me()).username}?startgroup=true")]]
        if img: await context.bot.send_photo(chat.id, photo=img, caption=caption, reply_markup=InlineKeyboardMarkup(btn), parse_mode=ParseMode.HTML)

# --- ADMIN ACTIONS (FIXED UNBAN) ---
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    text_cmd = update.message.text.split()[0].lower()
    if not await check_admin(chat, user.id): return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return
    
    try:
        if "/ban" in text_cmd: 
            await chat.ban_member(target.id)
            msg = f"🚫 {target.full_name} ကို Ban လိုက်ပါပြီ။"
        elif "/unban" in text_cmd: 
            await chat.unban_member(target.id)
            msg = f"🔊 {target.full_name} ကို Unban ပေးလိုက်ပါပြီ။"
        elif "/mute" in text_cmd: 
            await chat.restrict_member(target.id, ChatPermissions(can_send_messages=False))
            msg = f"🔇 {target.full_name} ကို Mute လိုက်ပါပြီ။"
        elif "/unmute" in text_cmd: 
            await chat.restrict_member(target.id, ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True))
            msg = f"🔊 {target.full_name} ကို Unmute ပေးလိုက်ပါပြီ။"
        await update.message.reply_text(bot_style(msg), parse_mode=ParseMode.HTML)
    except Exception as e: await update.message.reply_text(f"Error: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler("bully", bully_cmd))
    app.add_handler(CommandHandler("stopbully", stop_bully_cmd := lambda u,c: (stop_events[u.effective_chat.id].set() if u.effective_chat.id in stop_events else None, u.message.reply_text(bot_style("🛑 Bully ရပ်လိုက်ပါပြီ။"), parse_mode=ParseMode.HTML))))
    
    app.add_handler(CommandHandler("save_on", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": True}}, upsert=True), u.message.reply_text(bot_style("✅ Save Mode ဖွင့်လိုက်ပါပြီ။ စာသားမှန်သမျှ DB ထဲမှတ်ပါမည်။"), parse_mode=ParseMode.HTML))))
    app.add_handler(CommandHandler("save_off", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": False}}, upsert=True), u.message.reply_text(bot_style("❌ Save Mode ပိတ်လိုက်ပါပြီ။"), parse_mode=ParseMode.HTML))))
    
    app.add_handler(CommandHandler(["ban", "unban", "mute", "unmute", "kick"], admin_action))
    app.add_handler(ChatMemberHandler(on_member_update, ChatMemberHandler.ANY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, global_handler))
    
    print("🚀 BoD Bot Started...")
    app.run_polling()

if __name__ == "__main__": main()
