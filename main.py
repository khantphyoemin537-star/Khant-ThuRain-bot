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
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["telegram_bot"] 

bully_tasks = {} # Chat ID အလိုက် task တွေကို သိမ်းဖို့

# --- HELPERS ---
def bot_style(text):
    # စာလုံးအကြီး၊ Bold နဲ့ Blockquote ပေါင်းထားတာပါ
    return f"<blockquote><b>{text.upper()}</b></blockquote>"

def is_allow(uid):
    if uid == OWNER_ID: return True
    return db.allow_users.find_one({"user_id": uid}) is not None

async def check_admin(chat, user_id):
    try:
        member = await chat.get_member(user_id)
        return member.status in [ChatMember.OWNER, ChatMember.ADMINISTRATOR]
    except: return False

async def get_owner_mention(context):
    try:
        owner = await context.bot.get_chat(OWNER_ID)
        return f"<a href='tg://user?id={OWNER_ID}'>{owner.full_name}</a>"
    except: return "Chief Dexter"

# --- PILLOW IMAGE GENERATOR ---
async def generate_welcome_image(context, user, chat):
    try:
        bg = Image.new("RGBA", (1024, 576), (0, 0, 0, 255))

        async def get_pfp_bytes(target_id, is_user=True):
            try:
                if is_user:
                    photos = await context.bot.get_user_profile_photos(target_id, limit=1)
                    if photos.total_count > 0:
                        file = await context.bot.get_file(photos.photos[0][-1].file_id)
                        return await file.download_as_bytearray()
                else:
                    c_info = await context.bot.get_chat(target_id)
                    if c_info.photo:
                        file = await context.bot.get_file(c_info.photo.big_file_id)
                        return await file.download_as_bytearray()
                return None
            except: return None

        def make_circle(pfp_bytes, size=(250, 250)):
            if not pfp_bytes:
                img = Image.new("RGBA", size, (40, 40, 40, 255))
            else:
                img = Image.open(io.BytesIO(pfp_bytes)).convert("RGBA")
            img = img.resize(size)
            mask = Image.new('L', size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0) + size, fill=255)
            output = ImageOps.fit(img, size, centering=(0.5, 0.5))
            output.putalpha(mask)
            return output

        u_bytes = await get_pfp_bytes(user.id, True)
        g_bytes = await get_pfp_bytes(chat.id, False)

        bg.paste(make_circle(g_bytes), (150, 120), make_circle(g_bytes))
        bg.paste(make_circle(u_bytes), (624, 120), make_circle(u_bytes))

        draw = ImageDraw.Draw(bg)
        draw.text((512, 60), "WELCOME TO BOD NEVER DIE", fill="white", anchor="mm")
        draw.text((512, 450), f"NAME: {user.first_name[:15]}", fill="white", anchor="mm")
        draw.text((512, 490), f"USER ID: {user.id}", fill="#aaaaaa", anchor="mm")

        buf = io.BytesIO()
        bg.convert("RGB").save(buf, format='JPEG', quality=95)
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
    if target.id == OWNER_ID: 
        return await update.message.reply_text(bot_style("ဟားတိုက်ခံရတော့မယ် Creator ကို bullyမရဘူးညီ!"), parse_mode=ParseMode.HTML)

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

    if user.id == context.bot.id and new_s in ["member", "administrator"]:
        count = await chat.get_member_count()
        join_msg = (f"ဟိတ်ရို့ /admins မင်းတို့ရဲ့ဒီ <b>{chat.title} Total Members- ({count})</b> ကို ထည့်သွင်းအသုံးပြုပေးတဲ့အတွက် ကျေးဇူး၊Bot Command Permissionယူမယ်ဆို @Besties_with_BoD ကိုလာရမယ်။\n"
                    f"<b>Bot Creator:</b> {owner_mention}")
        await context.bot.send_message(chat.id, bot_style(join_msg), parse_mode=ParseMode.HTML)

    # ဝင်လာတဲ့ member အသစ်အတွက် welcome image
    if old_s in ["left", "kicked", "both_member_status_unknown"] and new_s in ["member", "administrator"] and user.id != context.bot.id:
        img = await generate_welcome_image(context, user, chat)
        caption = (f"✨ <b>ဟိတ်..{chat.title} ကနေ ကြိုဆိုလိုက်ပါတယ်!</b> ✨\n\n"
                   f"> <b>Name:</b> {user.full_name}\n"
                   f"> <b>User ID:</b> <code>{user.id}</code>\n"
                   f"> <b>Username:</b> @{user.username if user.username else 'None'}\n"
                   f"> <b>Joined at:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        btn = [[InlineKeyboardButton("Support Group", url="https://t.me/BoD_Network")]]
        if img:
            await context.bot.send_photo(chat.id, photo=img, caption=bot_style(caption), reply_markup=InlineKeyboardMarkup(btn), parse_mode=ParseMode.HTML)

# --- BULLY SYSTEM (FIXED) ---
async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id): return
    reply = update.message.reply_to_message
    if not reply: return
    
    target, chat_id = reply.from_user, update.effective_chat.id
    words = [w.get("text") for w in list(db.filters.find()) if w.get("text")]
    if not words: return
    
    # အရင်ရှိနေတဲ့ bully task ကို ရပ်ပစ်မယ်
    if chat_id in bully_tasks:
        bully_tasks[chat_id].cancel()

    async def loop():
        try:
            while True:
                await context.bot.send_message(chat_id, f"<a href='tg://user?id={target.id}'>{target.full_name}</a> <b>{random.choice(words).upper()}</b>", parse_mode=ParseMode.HTML)
                await asyncio.sleep(3.5)
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(loop())
    bully_tasks[chat_id] = task
    await update.message.reply_text(bot_style(f"🔥 {target.full_name} ကို စတင် BULLY နေပါပြီ..."), parse_mode=ParseMode.HTML)

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in bully_tasks:
        bully_tasks[chat_id].cancel()
        del bully_tasks[chat_id]
        await update.message.reply_text(bot_style("🛑 BULLYING STOPPED!"), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(bot_style("လုပ်ဆောင်နေတဲ့ Bully မရှိပါဘူး။"), parse_mode=ParseMode.HTML)

# --- GLOBAL HANDLERS ---
async def global_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat_id, user, text = update.effective_chat.id, update.effective_user, update.message.text
    if chat_id == SAVE_CHAT_ID:
        res = db.settings.find_one({"_id": f"save_{chat_id}"})
        if res and res.get("data") and not text.startswith('/'):
            db.filters.update_one({"text": text}, {"$set": {"added_by": user.id}}, upsert=True)
            await update.message.reply_text(bot_style("📝 သိမ်းဆည်းပြီးပါပြီ။"), parse_mode=ParseMode.HTML)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler("bully", bully_cmd))
    app.add_handler(CommandHandler("stopbully", stop_bully))
    app.add_handler(CommandHandler("save_on", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": True}}, upsert=True), u.message.reply_text(bot_style("✅ Save ON"), parse_mode=ParseMode.HTML))))
    app.add_handler(CommandHandler("save_off", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": False}}, upsert=True), u.message.reply_text(bot_style("❌ Save OFF"), parse_mode=ParseMode.HTML))))
    app.add_handler(CommandHandler(["ban", "unban", "mute", "unmute", "kick"], admin_mod_actions))
    
    app.add_handler(ChatMemberHandler(on_member_update, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, global_handler))
    
    print("🚀 BoD Premium Bot is Running...")
    # ChatMember updates တွေပါ bot က လက်ခံနိုင်ဖို့ allowed_updates ထည့်ထားပါတယ်
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__": main()

