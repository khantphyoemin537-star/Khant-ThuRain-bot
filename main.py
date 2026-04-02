import asyncio
import re
import logging
import random
import io
from datetime import datetime
from pymongo import MongoClient
from PIL import Image, ImageDraw, ImageOps
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
TOKEN = "8575371720:AAHR_1fCkRxlALIbhMH0yufXGJiUSQYJyYE" 
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
    except: returnFalse
async def generate_welcome_image(context, user, chat):
    # Base Background (Dark Theme)
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
        except: 
            return Image.new('RGBA', (200, 200), color=(40, 40, 40))

    # Get PFPs & Masks
    u_p = await get_pfp(user.id, True)
    g_p = await get_pfp(chat.id, False)
    mask = Image.new('L', (200, 200), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 200, 200), fill=255)
    
    u_p = ImageOps.fit(u_p, mask.size, centering=(0.5, 0.5)); u_p.putalpha(mask)
    g_p = ImageOps.fit(g_p, mask.size, centering=(0.5, 0.5)); g_p.putalpha(mask)

    # Paste & Draw Text
    base.paste(u_p, (70, 125), u_p)
    base.paste(g_p, (630, 125), g_p)
    draw.text((320, 50), "WELCOME TO", fill="white")
    draw.text((280, 85), f"{chat.title[:20]}", fill="#FF3131")
    draw.text((330, 340), f"NAME: {user.first_name[:15]}", fill="white")
    draw.text((330, 375), f"USER ID: {user.id}", fill="#FF3131")

    buf = io.BytesIO(); base.save(buf, format='PNG'); buf.seek(0)
    return buf

# --- PERMISSION COMMANDS (OWNER ONLY) ---
async def add_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text(bot_style("ခွင့်ပြုမည့်သူကို Reply ပြန်ပေးပါ Chief!"), parse_mode=ParseMode.HTML)
    
    db.allow_users.update_one({"user_id": target.id}, {"$set": {"name": target.full_name}}, upsert=True)
    await update.message.reply_text(bot_style(f"✅ {target.full_name} ကို Bully သုံးခွင့် ပေးလိုက်ပါပြီ။"), parse_mode=ParseMode.HTML)

async def remove_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text(bot_style("ဖယ်ရှားမယ့်သူကို Reply ပြန်ပေးပါ Chief!"), parse_mode=ParseMode.HTML)
    
    db.allow_users.delete_one({"user_id": target.id})
    await update.message.reply_text(bot_style(f"❌ {target.full_name} ရဲ့ Bully သုံးခွင့်ကို ပယ်ဖျက်လိုက်ပါပြီ။"), parse_mode=ParseMode.HTML)

async def allow_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = list(db.allow_users.find())
    if not users: return await update.message.reply_text(bot_style("Allow List ထဲမှာ ဘယ်သူမှ မရှိသေးပါဘူး။"), parse_mode=ParseMode.HTML)
    text = "📜 <b>Bully သုံးခွင့်ရှိသူများ စာရင်း:</b>\n\n"
    for idx, u in enumerate(users, 1):
        text += f"{idx}. <a href='tg://user?id={u['user_id']}'>{u['name']}</a>\n"
    await update.message.reply_text(bot_style(text), parse_mode=ParseMode.HTML)

# --- BULLY LOGIC ---
async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id): return
    reply = update.message.reply_to_messag
    if not reply: return await update.message.reply_text(bot_style("ဘယ်သူ့ကို Bully ရမလဲ (Reply ပြန်ပါ)"), parse_mode=ParseMode.HTML)
    
    target, chat_id = reply.from_user, update.effective_chat.id
    words = [w.get("text") for w in db.filters.find() if w.get("text")]
    if not words: return await update.message.reply_text(bot_style("Database ထဲမှာ စာသားမရှိပါ!"), parse_mode=ParseMode.HTML)
    
    if chat_id in stop_events: stop_events[chat_id].set() # Reset if running
    stop_events[chat_id] = asyncio.Event()

    async def loop():
        while not stop_events[chat_id].is_set():
            w = random.choice(words)
            try:
                mention = f"<a href='tg://user?id={target.id}'>{target.full_name}</a>"
                await context.bot.send_message(chat_id, bot_style(f"{mention} {w}"), parse_mode=ParseMode.HTML)
                
                # Save Log if status is ON
                res = db.settings.find_one({"_id": f"save_{chat_id}"})
                if res and res.get("data"):
                    log_text = f"📝 <b>Bully Log</b>\n🏰 Group: {update.effective_chat.title}\n👤 Target: {target.full_name}\n💬 Word: {w}"
                    await context.bot.send_message(SAVE_CHAT_ID, log_text, parse_mode=ParseMode.HTML)
                    db.save_chat.insert_one({"target": target.id, "word": w, "time": datetime.now()})
            except: break
            await asyncio.sleep(2)

    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(bot_style(f"🔥 {target.full_name} ကို Bully စတင်နေပါပြီ..."), parse_mode=ParseMode.HTML)

# --- ADMIN ACTIONS ---
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    cmd = update.message.text.split()[0].lower()
    if not await check_admin(chat, user.id): return
    
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text(bot_style("အရေးယူမယ့်သူကို Reply ပြန်ပေးပါ Admin Chief!"), parse_mode=ParseMode.HTML)
    if await check_admin(chat, target.id): return await update.message.reply_text(bot_style("Admin အချင်းချင်းတော့ လုပ်လို့မရဘူးလေ။"), parse_mode=ParseMode.HTML)

    try:
        if "ban" in cmd: await chat.ban_member(target.id); msg = f"🚫 {target.full_name} ကို Ban လိုက်ပါပြီ။"
        elif "unban" in cmd: await chat.unban_member(target.id); msg = f"✅ {target.full_name} ကို Unban ပေးလိုက်ပါပြီ။"
        elif "mute" in cmd: await chat.restrict_member(target.id, ChatPermissions(can_send_messages=False)); msg = f"🔇 {target.full_name} ကို Mute လိုက်ပါပြီ။"
        elif "unmute" in cmd: await chat.restrict_member(target.id, ChatPermissions(can_send_messages=True)); msg = f"🔊 {target.full_name} ကို Unmute ပေးလိုက်ပါပြီ။"
        elif "kick" in cmd: await chat.unban_member(target.id); msg = f"🚪 {target.full_name} ကို အဖွဲ့ထဲက ကန်ထုတ်လိုက်ပါပြီ။"
        await update.message.reply_text(bot_style(msg), parse_mode=ParseMode.HTML)
    except Exception as e: await update.message.reply_text(f"Error: {e}")

# --- SYSTEM HANDLERS ---
async def on_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member if update.chat_member else update.my_chat_member
    if not result: return
    
    chat = update.effective_chat
    user = result.new_chat_member.user
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status

    # --- WELCOME ---
    if old_status in ["left", "kicked"] and new_status in ["member", "administrator"]:
        if user.id != context.bot.id:
            try:
                img = await generate_welcome_image(context, user, chat)
                caption = bot_style(f"✨ Welcome to {chat.title} ✨\n\n🆔 ID: <code>{user.id}</code>\n👋 Mention: <a href='tg://user?id={user.id}'>{user.full_name}</a>")
                await context.bot.send_photo(chat.id, photo=img, caption=caption, parse_mode=ParseMode.HTML)
            except: pass

    # --- GOODBYE ---
    elif old_status in ["member", "administrator"] and new_status in ["left", "kicked"]:
        if user.id != context.bot.id:
            bye_text = bot_style(f"👋 {user.full_name} ကတော့ {chat.title} ကနေ ထွက်ခွာသွားပါပြီ။")
            await context.bot.send_message(chat.id, bye_text, parse_mode=ParseMode.HTML)

    # --- BOT ENTRY ---
    if user.id == context.bot.id and new_status == "member":
        entry_text = (f"ဟိတ်ရို့ /admins မင်းတို့ရဲ့ဒီ <b>{chat.title}</b> ကို ထည့်သွင်းအသုံးပြုပေးတဲ့အတွက် ကျေးဇူး၊ "
                     f"အသုံးဝင်မယ့် bot command တွေသုံးမယ်ဆို @Besties_with_BoD က OWNER ဆီကိုလာဆက်သွယ်ပေးပါ။\n\n"
                     f"Owner: <a href='tg://user?id={OWNER_ID}'>Chief Dexter</a>")
        await context.bot.send_message(chat.id, entry_text, parse_mode=ParseMode.HTML)
        await context.bot.send_message(ADMIN_GROUP_ID, f"📢 <b>Bot Added!</b>\nGroup: {chat.title}\nAdded by: {update.effective_user.full_name}", parse_mode=ParseMode.HTML)

    # 2. Link Filter
    if update.message and update.message.text and user.id != OWNER_ID:
        if not await check_admin(chat, user.id):
            if re.search(r"(https?://\S+|t\.me/\S+)", update.message.text):
                try: await update.message.delete()
                except: pass

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Permission & Stats
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler("removeallow", remove_allow))
    app.add_handler(CommandHandler("allowlist", allow_list))
    app.add_handler(CommandHandler("tbm", lambda u,c: u.message.reply_text(bot_style(f"📊 စုစုပေါင်း Bully Message: {db.save_chat.count_documents({})} ခု"), parse_mode=ParseMode.HTML)))
    
    # Bully Control
    app.add_handler(CommandHandler("bully", bully_cmd))
    app.add_handler(CommandHandler("stopbully", lambda u,c: stop_events[u.effective_chat.id].set() if u.effective_chat.id in stop_events else None))
    app.add_handler(CommandHandler("save_on", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": True}}, upsert=True), u.message.reply_text(bot_style("✅ Save Chat: ON"), parse_mode=ParseMode.HTML))))
    app.add_handler(CommandHandler("save_off", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": False}}, upsert=True), u.message.reply_text(bot_style("❌ Save Chat: OFF"), parse_mode=ParseMode.HTML))))

    # Admin Tools
    app.add_handler(CommandHandler(["ban", "unban", "mute", "unmute", "kick"], admin_action))
    

    app.add_handler(ChatMemberHandler(on_member_update, ChatMemberHandler.ANY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, global_handler))


    print("🚀 Young Master Dexter Bot Fully Armed & Live!")
    app.run_polling()

if __name__ == "__main__": main()
