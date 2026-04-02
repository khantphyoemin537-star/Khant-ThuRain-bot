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
    except:
        return "Chief Dexter"

# --- IMAGE GENERATOR ---
async def generate_welcome_image(context, user, chat):
    try:
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

        u_p = await get_pfp(user.id, True)
        g_p = await get_pfp(chat.id, False)
        mask = Image.new('L', (200, 200), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 200, 200), fill=255)
        
        u_p = ImageOps.fit(u_p, mask.size, centering=(0.5, 0.5)); u_p.putalpha(mask)
        g_p = ImageOps.fit(g_p, mask.size, centering=(0.5, 0.5)); g_p.putalpha(mask)

        base.paste(u_p, (70, 125), u_p)
        base.paste(g_p, (630, 125), g_p)
        draw.text((320, 50), "WELCOME TO", fill="white")
        draw.text((280, 85), f"{chat.title[:20]}", fill="#FF3131")
        draw.text((330, 340), f"NAME: {user.first_name[:15]}", fill="white")
        draw.text((330, 375), f"USER ID: {user.id}", fill="#FF3131")

        buf = io.BytesIO(); base.save(buf, format='PNG'); buf.seek(0)
        return buf
    except Exception as e:
        logging.error(f"Image Gen Error: {e}")
        return None

# --- COMMANDS ---
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
    if not is_allow(update.effective_user.id):
        return await update.message.reply_text(bot_style("ဟေ့🫵မင်းမှာ ဒီcommandသုံးခွင့်မရှိဘူး"), parse_mode=ParseMode.HTML)
    
    reply = update.message.reply_to_message
    if not reply: 
        return await update.message.reply_text(bot_style("ဘယ်သူ့ကို Bully ရမလဲ (Reply ပြန်ပါ)"), parse_mode=ParseMode.HTML)
    
    target, chat_id = reply.from_user, update.effective_chat.id
    
    if target.id == OWNER_ID:
        mention = f"<a href='tg://user?id={update.effective_user.id}'>{update.effective_user.full_name}</a>"
        return await update.message.reply_text(f"ဟားတိုက်ခံရတော့မယ်၊ မင်းမှာ Bot Creator ကို bullyခွင့်မရှိဘူးညီ🫵 {mention}", parse_mode=ParseMode.HTML)

    all_filters = list(db.filters.find())
    words = [w.get("text") for w in all_filters if w.get("text")]

    if not words: 
        return await update.message.reply_text(bot_style("Database ထဲမှာ Bully ရန် စာသားများ မရှိသေးပါ။"), parse_mode=ParseMode.HTML)
    
    if chat_id in stop_events: 
        stop_events[chat_id].set()
    
    stop_events[chat_id] = asyncio.Event()

    async def loop():
        while not stop_events[chat_id].is_set():
            w = random.choice(words)
            try:
                mention = f"<a href='tg://user?id={target.id}'>{target.full_name}</a>"
                await context.bot.send_message(chat_id, bot_style(f"{mention} {w}"), parse_mode=ParseMode.HTML)
                
                res = db.settings.find_one({"_id": f"save_{chat_id}"})
                if res and res.get("data"):
                    log_text = f"📝 <b>Bully Log</b>\n🏰 Group: {update.effective_chat.title}\n👤 Target: {target.full_name}\n💬 Word: {w}"
                    await context.bot.send_message(SAVE_CHAT_ID, log_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logging.error(f"Error in bully loop: {e}")
                break
            await asyncio.sleep(3.5) 

    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(
        bot_style(f"🔥 စာသား {len(words)} ခုဖြင့် {target.full_name} ကို စတင် Bully နေပါပြီ..."), 
        parse_mode=ParseMode.HTML
    )

async def stop_bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id):
        return await update.message.reply_text(bot_style("ဟေ့🫵မင်းမှာ ဒီcommandသုံးခွင့်မရှိဘူး"), parse_mode=ParseMode.HTML)
    
    chat_id = update.effective_chat.id
    if chat_id in stop_events:
        stop_events[chat_id].set()
        await update.message.reply_text(bot_style("🛑 Bully လုပ်ခြင်းကို ရပ်တန့်လိုက်ပါပြီ။"), parse_mode=ParseMode.HTML)

# --- BROADCAST & DB ---
async def broadcast_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    reply = update.message.reply_to_message
    if not reply: return await update.message.reply_text(bot_style("Broadcast ပို့မယ့်စာကို Reply ပြန်ပေးပါ Chief!"), parse_mode=ParseMode.HTML)
    
    groups = list(db.registered_groups.find())
    success, fail = 0, 0
    status_msg = await update.message.reply_text(bot_style(f"📡 Group {len(groups)} ခုကို စတင်ပို့ဆောင်နေပါပြီ..."), parse_mode=ParseMode.HTML)
    
    for g in groups:
        try:
            await context.bot.copy_message(chat_id=g['chat_id'], from_chat_id=update.effective_chat.id, message_id=reply.message_id)
            success += 1
        except: fail += 1
        await asyncio.sleep(0.5) 
    await status_msg.edit_text(bot_style(f"✅ Broadcast ပြီးဆုံးပါပြီ။\nအောင်မြင်: {success}\nကျရှုံး: {fail}"), parse_mode=ParseMode.HTML)

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    text_cmd = update.message.text.split()[0].lower()
    if not await check_admin(chat, user.id): return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text(bot_style("အရေးယူမယ့်သူကို Reply ပြန်ပေးပါ Admin Chief!"), parse_mode=ParseMode.HTML)
    
    try:
        if "ban" in text_cmd: await chat.ban_member(target.id); msg = f"🚫 {target.full_name} ကို Ban လိုက်ပါပြီ။"
        elif "unban" in text_cmd: await chat.unban_member(target.id); msg = f"✅ {target.full_name} ကို Unban ပေးလိုက်ပါပြီ။"
        elif "mute" in text_cmd: await chat.restrict_member(target.id, ChatPermissions(can_send_messages=False)); msg = f"🔇 {target.full_name} ကို Mute လိုက်ပါပြီ။"
        elif "unmute" in text_cmd: 
            await chat.restrict_member(target.id, ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True))
            msg = f"🔊 {target.full_name} ကို Unmute ပေးလိုက်ပါပြီ။"
        elif "kick" in text_cmd: await chat.unban_member(target.id); msg = f"🚪 {target.full_name} ကို အဖွဲ့ထဲက ကန်ထုတ်လိုက်ပါပြီ။"
        await update.message.reply_text(bot_style(msg), parse_mode=ParseMode.HTML)
    except Exception as e: await update.message.reply_text(f"Error: {e}")

# --- GLOBAL HANDLER ---
async def global_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    chat, user = update.effective_chat, update.effective_user
    
    if chat.type in ["group", "supergroup"]:
        db.registered_groups.update_one({"chat_id": chat.id}, {"$set": {"title": chat.title, "last_active": datetime.now()}}, upsert=True)

    if not update.message.text: return
    text = update.message.text

    # Link Filter
    if user.id != OWNER_ID and not await check_admin(chat, user.id):
        if re.search(r"(https?://\S+|t\.me/\S+)", text):
            try: await update.message.delete(); return
            except: pass

    # AUTO SAVE CHAT
    res = db.settings.find_one({"_id": f"save_{chat.id}"})
    if res and res.get("data"):
        if len(text.strip()) > 2 and not text.startswith('/'):
            db.filters.update_one({"text": text}, {"$set": {"text": text, "added_by": user.id, "date": datetime.now()}}, upsert=True)
            await update.message.reply_text(bot_style("📝 ဤစာသားကို Bully Database ထဲသို့ သိမ်းဆည်းလိုက်ပါပြီ။"), parse_mode=ParseMode.HTML)

# --- MEMBER UPDATE HANDLER ---
async def on_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member if update.chat_member else update.my_chat_member
    if not result: return
    
    chat = update.effective_chat
    user = result.new_chat_member.user
    old_s, new_s = result.old_chat_member.status, result.new_chat_member.status
    owner_mention = await get_owner_mention(context)

    # Bot Joined Group
    if user.id == context.bot.id and new_s in ["member", "administrator"] and old_s in ["left", "kicked"]:
        db.registered_groups.update_one({"chat_id": chat.id}, {"$set": {"title": chat.title, "added_at": datetime.now()}}, upsert=True)
        
        # Entry Message
        entry = (f"ဟိတ်ရို့ /admins မင်းတို့ရဲ့ဒီ <b>{chat.title}</b> ကို ထည့်သွင်းအသုံးပြုပေးတဲ့အတွက် ကျေးဇူး၊ "
                 f"အသုံးဝင်မယ့် bot command တွေသုံးမယ်ဆို @Besties_with_BoD က OWNER ဆီကိုလာဆက်သွယ်ပေးပါ။\n\n"
                 f"Owner: {owner_mention}")
        await context.bot.send_message(chat.id, entry, parse_mode=ParseMode.HTML)
        
        # Notify Admin Group
        bot_user = await context.bot.get_me()
        admin_notif = (f"📢 <a href='tg://user?id={bot_user.id}'>{bot_user.first_name}</a> ကို "
                       f"<b>{chat.title}</b> (<code>{chat.id}</code>) ထဲသို့ ထည့်သွင်းလိုက်ပါတယ်။\n\n"
                       f"ပိုင်ရှင်: {owner_mention}")
        await context.bot.send_message(ADMIN_GROUP_ID, admin_notif, parse_mode=ParseMode.HTML)

    # Welcome Logic
    if old_s in ["left", "kicked", "restricted"] and new_s in ["member", "administrator"]:
        if user.id != context.bot.id:
            img = await generate_welcome_image(context, user, chat)
            caption = bot_style(f"✨ Welcome to {chat.title} ✨\n\n🆔 ID: <code>{user.id}</code>\n👋 Mention: <a href='tg://user?id={user.id}'>{user.full_name}</a>")
            if img: await context.bot.send_photo(chat.id, photo=img, caption=caption, parse_mode=ParseMode.HTML)
            else: await context.bot.send_message(chat.id, caption, parse_mode=ParseMode.HTML)

    # Goodbye Logic
    elif old_s in ["member", "administrator"] and new_s in ["left", "kicked"]:
        if user.id != context.bot.id:
            await context.bot.send_message(chat.id, bot_style(f"👋 {user.full_name} ကတော့ {chat.title} ကနေ ထွက်ခွာသွားပါပြီ။"), parse_mode=ParseMode.HTML)

async def check_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    count = db.filters.count_documents({})
    g_count = db.registered_groups.count_documents({})
    await update.message.reply_text(bot_style(f"📊 Database Info:\n\n💬 Bully စာသား: {count} ခု\n🏰 မှတ်သားထားသော Group: {g_count} ခု"), parse_mode=ParseMode.HTML)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler("removeallow", remove_allow))
    app.add_handler(CommandHandler("allowlist", allow_list))
    app.add_handler(CommandHandler("bully", bully_cmd))
    app.add_handler(CommandHandler("stopbully", stop_bully_cmd))
    app.add_handler(CommandHandler("checkdb", check_db))
    app.add_handler(CommandHandler("send", broadcast_msg))
    
    app.add_handler(CommandHandler("save_on", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": True}}, upsert=True), u.message.reply_text(bot_style("✅ Save Chat: ON (စာသားများကို စတင်မှတ်သားနေပါပြီ)"), parse_mode=ParseMode.HTML))))
    app.add_handler(CommandHandler("save_off", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": False}}, upsert=True), u.message.reply_text(bot_style("❌ Save Chat: OFF"), parse_mode=ParseMode.HTML))))
    
    app.add_handler(CommandHandler(["ban", "unban", "mute", "unmute", "kick"], admin_action))
    app.add_handler(ChatMemberHandler(on_member_update, ChatMemberHandler.ANY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, global_handler))

    print("🚀 Young Master Dexter Bot Fully Armed & Live!")
    app.run_polling()

if __name__ == "__main__": 
    main()

