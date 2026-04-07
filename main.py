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
    except: return "CHIEF DEXTER"

# --- PERMISSION CHECK ---
async def check_perm(update: Update):
    user = update.effective_user
    if is_allow(user.id): return True
    mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    msg = f"ဟိတ် {mention} မင်းမှာ COMMAND သုံးခွင့်မရှိဘူး!! သုံးမယ်ဆို ငါတို့ရဲ့ {ADMIN_CHAT_MENTION} ကိုလာတောင်း"
    await update.message.reply_text(bot_style(msg), parse_mode=ParseMode.HTML)
    return False

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
            if not pfp_bytes: img = Image.new("RGBA", size, (40, 40, 40, 255))
            else: img = Image.open(io.BytesIO(pfp_bytes)).convert("RGBA")
            img = img.resize(size); mask = Image.new('L', size, 0)
            draw = ImageDraw.Draw(mask); draw.ellipse((0, 0) + size, fill=255)
            output = ImageOps.fit(img, size, centering=(0.5, 0.5)); output.putalpha(mask)
            return output

        u_bytes = await get_pfp_bytes(user.id, True)
        g_bytes = await get_pfp_bytes(chat.id, False)
        bg.paste(make_circle(g_bytes), (150, 120), make_circle(g_bytes))
        bg.paste(make_circle(u_bytes), (624, 120), make_circle(u_bytes))
        draw = ImageDraw.Draw(bg)
        draw.text((512, 60), "WELCOME TO BOD NEVER DIE", fill="white", anchor="mm")
        draw.text((512, 450), f"NAME: {user.first_name[:15]}", fill="white", anchor="mm")
        draw.text((512, 490), f"USER ID: {user.id}", fill="#aaaaaa", anchor="mm")
        buf = io.BytesIO(); bg.convert("RGB").save(buf, format='JPEG', quality=95); buf.seek(0)
        return buf
    except Exception as e:
        logging.error(f"Image Error: {e}"); return None

# --- ADMIN ACTIONS ---
async def admin_mod_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if not await check_admin(chat, user.id) or not await check_perm(update): return
    cmd = update.message.text.split()[0][1:].lower()
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return
    if target.id == OWNER_ID: 
        return await update.message.reply_text(bot_style("ဟားတိုက်ခံရတော့မယ် Creator ကို bullyမရဘူးညီ!"), parse_mode=ParseMode.HTML)
    
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

# --- MEMBER UPDATES (WELCOME & JOIN NOTIFICATION RE-FIXED) ---
async def on_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Determine result
    result = update.my_chat_member if update.my_chat_member else update.chat_member
    if not result: return

    chat = result.chat
    user = result.new_chat_member.user
    old_s = result.old_chat_member.status
    new_s = result.new_chat_member.status

    # Check for Bot Joining
    if user.id == context.bot.id:
        if new_s in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
            db.groups.update_one({"chat_id": chat.id}, {"$set": {"title": chat.title}}, upsert=True)
            count = await chat.get_member_count()
            owner_mention = await get_owner_mention(context)
            join_msg = (f"ဟိတ်ရို့ /admins မင်းတို့ရဲ့ဒီ {chat.title} Total Members- ({count}) ကို ထည့်သွင်းအသုံးပြုပေးတဲ့အတွက် ကျေးဇူး၊\n"
                        f"Bot Command Permissionယူမယ်ဆို @Besties_with_BoD ကိုလာရမယ်။\n"
                        f"Bot Creator: {owner_mention}")
            await context.bot.send_message(chat.id, bot_style(join_msg), parse_mode=ParseMode.HTML)
            admin_log = f"🚀 BOT ADDED TO NEW GROUP\n\nGROUP: {chat.title}\nID: {chat.id}\nMEMBERS: {count}"
            await context.bot.send_message(ADMIN_GROUP_ID, bot_style(admin_log), parse_mode=ParseMode.HTML)
        return

    # Check for User Joining
    if new_s in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR] and old_s not in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
        img = await generate_welcome_image(context, user, chat)
        caption = (f"✨ ဟိတ်..{chat.title} ကနေ ကြိုဆိုလိုက်ပါတယ်! ✨\n\n"
                   f"NAME: {user.full_name}\n"
                   f"USER ID: {user.id}\n"
                   f"JOINED AT: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        btn = [[InlineKeyboardButton("Support Group", url="https://t.me/BoD_Network")]]
        
        if img:
            await context.bot.send_photo(
                chat.id, 
                photo=img, 
                caption=bot_style(caption), 
                reply_markup=InlineKeyboardMarkup(btn), 
                parse_mode=ParseMode.HTML
            )

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
            await asyncio.sleep(0.5)
        except: fail += 1
    await update.message.reply_text(bot_style(f"📢 BROADCAST ပြီးပါပြီ!\nSUCCESS: {success}\nFAILED: {fail}"), parse_mode=ParseMode.HTML)

# --- BULLY SYSTEM (1 LINE PER MSG + HTML MENTION) ---
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
                # ၁ ကြောင်းချင်းစီပဲ ပို့ပါမယ်
                bully_text = f"{mention} {random.choice(words)}"
                await context.bot.send_message(chat_id, bot_style(bully_text), parse_mode=ParseMode.HTML)
                await asyncio.sleep(1) # တစ်ကြောင်းစီ ပို့တာမို့ sleep ကို နည်းနည်းလျှော့ထားပါတယ်
        except asyncio.CancelledError:
            pass

    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(bot_style(f"🔥 {target.full_name} ကို စတင် BULLY နေပါပြီ..."), parse_mode=ParseMode.HTML)

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    chat_id = update.effective_chat.id
    task = bully_tasks.get(chat_id)
    if task:
        task.cancel()
        del bully_tasks[chat_id]
        await update.message.reply_text(bot_style("မင်းကရပ်ဆိုလို့သာ ငါကbullyချင်သေးတယ် အပျင်းပြေလို့!"), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(bot_style("လုပ်ဆောင်နေတဲ့ BULLY မရှိပါဘူး။"), parse_mode=ParseMode.HTML)

# --- LISTS & PERMS ---
async def allow_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    users = list(db.allow_users.find())
    msg = "ALLOW LIST USERS:\n\n" + "\n".join([f"• {u.get('name')} ({u.get('user_id')})" for u in users]) if users else "ALLOW LIST ထဲမှာ ဘယ်သူမှမရှိသေးပါဘူး။"
    await update.message.reply_text(bot_style(msg), parse_mode=ParseMode.HTML)

async def add_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text(bot_style("Reply ပြန်ပြီးသုံး!"), parse_mode=ParseMode.HTML)
    db.allow_users.update_one({"user_id": target.id}, {"$set": {"name": target.full_name}}, upsert=True)
    await update.message.reply_text(bot_style(f"✅ {target.full_name} ကို BULLY ခွင့်ပြုလိုက်ပါပြီ။"), parse_mode=ParseMode.HTML)

# --- GLOBAL HANDLERS ---
async def global_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat_id, user, text = update.effective_chat.id, update.effective_user, update.message.text
    if update.effective_chat.type in ["group", "supergroup"]:
        db.groups.update_one({"chat_id": chat_id}, {"$set": {"title": update.effective_chat.title}}, upsert=True)
    if chat_id == SAVE_CHAT_ID:
        res = db.settings.find_one({"_id": f"save_{chat_id}"})
        if res and res.get("data") and not text.startswith('/'):
            db.filters.update_one({"text": text}, {"$set": {"added_by": user.id}}, upsert=True)
            await update.message.reply_text(bot_style("📝 သိမ်းဆည်းပြီးပါပြီ။"), parse_mode=ParseMode.HTML)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler("allowlist", allow_list))
    app.add_handler(CommandHandler("bully", bully_cmd))
    app.add_handler(CommandHandler("stopbully", stop_bully))
    app.add_handler(CommandHandler("send", broadcast_send))
    app.add_handler(CommandHandler("save_on", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": True}}, upsert=True), asyncio.create_task(u.message.reply_text(bot_style("✅ Save ON"), parse_mode=ParseMode.HTML)))))
    app.add_handler(CommandHandler("save_off", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": False}}, upsert=True), asyncio.create_task(u.message.reply_text(bot_style("❌ Save OFF"), parse_mode=ParseMode.HTML)))))
    app.add_handler(CommandHandler(["ban", "unban", "mute", "unmute", "kick"], admin_mod_actions))
    
    # Combined ChatMemberHandlers
    app.add_handler(ChatMemberHandler(on_member_update, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(ChatMemberHandler(on_member_update, ChatMemberHandler.CHAT_MEMBER))
    
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, global_handler))
    
    print("🚀 BoD Premium Bot is Running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__": main()
