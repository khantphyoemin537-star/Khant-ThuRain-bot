import asyncio
import logging
import random
import io
from datetime import datetime
from pymongo import MongoClient
from PIL import Image, ImageDraw, ImageOps, ImageFilter
from telegram import Update, ChatMember, ChatPermissions
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

# --- PILLOW IMAGE GENERATOR ---
async def generate_welcome_image(context, user, chat):
    try:
        canvas_w, canvas_h = 900, 450
        
        async def get_pfp_img(target_id, is_user=True):
            try:
                if is_user:
                    photos = await context.bot.get_user_profile_photos(target_id, limit=1)
                    if not photos.photos: raise Exception()
                    file_id = photos.photos[0][-1].file_id
                else:
                    chat_info = await context.bot.get_chat(target_id)
                    if not chat_info.photo: raise Exception()
                    file_id = chat_info.photo.big_file_id
                
                file = await context.bot.get_file(file_id)
                img_byte = await file.download_as_bytearray()
                return Image.open(io.BytesIO(img_byte)).convert("RGBA")
            except: 
                return Image.new('RGBA', (400, 400), color=(40, 40, 40, 255))

        user_pfp = await get_pfp_img(user.id, True)
        group_pfp = await get_pfp_img(chat.id, False)

        # 1. Background Blur
        background = group_pfp.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)
        background = background.filter(ImageFilter.GaussianBlur(radius=20))
        overlay = Image.new('RGBA', background.size, (0, 0, 0, 150))
        background = Image.alpha_composite(background, overlay)

        # 2. Circular PFPs
        size = 200
        mask = Image.new('L', (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        
        u_p = ImageOps.fit(user_pfp, (size, size)); u_p.putalpha(mask)
        g_p = ImageOps.fit(group_pfp, (size, size)); g_p.putalpha(mask)

        background.paste(u_p, (150, 100), u_p)
        background.paste(g_p, (550, 100), g_p)

        # 3. Text
        draw = ImageDraw.Draw(background)
        draw.text((380, 50), "WELCOME", fill="white")
        draw.text((320, 330), f"Name: {user.first_name[:20]}", fill="white")
        draw.text((320, 360), f"ID: {user.id}", fill="#FF3131")

        buf = io.BytesIO()
        background.convert("RGB").save(buf, format='JPEG')
        buf.seek(0)
        return buf
    except Exception as e:
        logging.error(f"Image Error: {e}")
        return None

# --- ADMIN ACTIONS (FIXED UNMUTE) ---
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if not await check_admin(chat, user.id): return
    
    cmd = update.message.text.split()[0].lower()
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return

    try:
        if "unmute" in cmd:
            # FIX: တိကျတဲ့ Permissions တွေ အကုန်ပြန်ဖွင့်ပေးရပါတယ်
            perms = ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_invite_users=True,
                can_pin_messages=False,
                can_change_info=False
            )
            await chat.restrict_member(target.id, perms)
            msg = f"🔊 {target.full_name} ကို Mute ဖြည်ပေးလိုက်ပါပြီ။"
        elif "mute" in cmd:
            await chat.restrict_member(target.id, ChatPermissions(can_send_messages=False))
            msg = f"🔇 {target.full_name} ကို Mute လိုက်ပါပြီ။"
        elif "ban" in cmd:
            await chat.ban_member(target.id)
            msg = f"🚫 {target.full_name} ကို Ban လိုက်ပါပြီ။"
        
        await update.message.reply_text(bot_style(msg), parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# --- MEMBER EVENTS (FIXED WELCOME/GOODBYE) ---
async def on_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member if update.chat_member else update.my_chat_member
    if not result: return

    chat, user = update.effective_chat, result.new_chat_member.user
    old_s, new_s = result.old_chat_member.status, result.new_chat_member.status

    # 1. Bot Joined Group
    if user.id == context.bot.id and new_s in ["member", "administrator"]:
        entry = (f"ဟိတ်ရို့ /admins မင်းတို့ရဲ့ဒီ <b>{chat.title}</b> ကို အသုံးပြုပေးလို့ ကျေးဇူး!\n"
                 f"Command တွေအတွက် @Besties_with_BoD ကို ဆက်သွယ်ပါ။")
        await context.bot.send_message(chat.id, entry, parse_mode=ParseMode.HTML)
        return

    # 2. User Joined (Member အသစ်ရော အဟောင်းပြန်ဝင်တာရော အကုန်ကြိုဆိုမယ်)
    if new_s in ["member", "administrator"] and old_s not in ["member", "administrator"]:
        img = await generate_welcome_image(context, user, chat)
        caption = f"ဟိတ် <b>{chat.title}</b> ကနေ {user.full_name} ကို ကြိုဆိုပါတယ်!\nID: {user.id}"
        if img: await context.bot.send_photo(chat.id, photo=img, caption=bot_style(caption), parse_mode=ParseMode.HTML)
        else: await context.bot.send_message(chat.id, bot_style(caption), parse_mode=ParseMode.HTML)

    # 3. User Left/Kicked
    elif new_s in ["left", "kicked"] and old_s in ["member", "administrator"]:
        await context.bot.send_message(chat.id, bot_style(f"👋 {user.full_name} ကတော့ ထွက်သွားပါပြီ။"), parse_mode=ParseMode.HTML)

# --- ALLOW LIST ---
async def allow_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id): return
    users = list(db.allow_users.find())
    if not users: return await update.message.reply_text(bot_style("Allow List ထဲမှာ ဘယ်သူမှ မရှိသေးပါ။"), parse_mode=ParseMode.HTML)
    text = "📜 <b>Bully သုံးခွင့်ရှိသူများ စာရင်း:</b>\n\n"
    for idx, u in enumerate(users, 1):
        text += f"{idx}. {u['name']} (<code>{u['user_id']}</code>)\n"
    await update.message.reply_text(bot_style(text), parse_mode=ParseMode.HTML)

# --- BULLY COMMANDS ---
async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id): return
    reply = update.message.reply_to_message
    if not reply: return await update.message.reply_text(bot_style("ဘယ်သူ့ကို Bully ရမလဲ (Reply ပြန်ပါ)"), parse_mode=ParseMode.HTML)
    
    target, chat_id = reply.from_user, update.effective_chat.id
    words = [w.get("text") for w in list(db.filters.find()) if w.get("text")]
    if not words: return
    
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
    await update.message.reply_text(bot_style(f"🔥 {target.full_name} ကို Bully နေပါပြီ..."), parse_mode=ParseMode.HTML)

async def stop_bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id): return
    if update.effective_chat.id in stop_events:
        stop_events[update.effective_chat.id].set()
        await update.message.reply_text(bot_style("🛑 Bully ရပ်တန့်လိုက်ပါပြီ။"), parse_mode=ParseMode.HTML)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("allowlist", allow_list))
    app.add_handler(CommandHandler(["mute", "unmute", "ban"], admin_action))
    app.add_handler(CommandHandler("bully", bully_cmd))
    app.add_handler(CommandHandler("stopbully", stop_bully_cmd))
    app.add_handler(ChatMemberHandler(on_member_update, ChatMemberHandler.ANY_CHAT_MEMBER))
    
    print("🚀 Bot is Running...")
    app.run_polling()

if __name__ == "__main__": main()

