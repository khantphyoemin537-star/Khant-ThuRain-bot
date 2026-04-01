import asyncio
import re
import logging
import random
import io
from pymongo import MongoClient
from PIL import Image, ImageDraw, ImageOps
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
db = client["telegram_bot"]
bully_tasks = {} 
stop_events = {} 
active_targets = {} 

# --- HELPERS ---
def get_all_bully_words():
    new_words = [w["text"] for w in db.bully_messages.find()]
    old_data = db.settings.find_one({"_id": "bully"})
    old_words = old_data["data"] if old_data and "data" in old_data else []
    return list(set(new_words + old_words))

def is_allow(uid):
    if uid == OWNER_ID: return True
    if db.allow_users.find_one({"user_id": uid}): return True
    old_data = db.settings.find_one({"_id": "allow"})
    old_list = old_data["data"] if old_data and "data" in old_data else []
    return uid in old_list

# --- WELCOME IMAGE GENERATOR ---
async def generate_welcome_image(context, user, chat):
    base = Image.new('RGB', (800, 400), color=(20, 20, 20))
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
            return Image.open(io.BytesIO(img_byte)).convert("RGBA").resize((180, 180))
        except:
            return Image.new('RGBA', (180, 180), color=(50, 50, 50))

    user_pfp = await get_pfp(user.id, True)
    group_pfp = await get_pfp(chat.id, False)
    mask = Image.new('L', (180, 180), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 180, 180), fill=255)
    
    user_pfp = ImageOps.fit(user_pfp, mask.size, centering=(0.5, 0.5))
    user_pfp.putalpha(mask)
    group_pfp = ImageOps.fit(group_pfp, mask.size, centering=(0.5, 0.5))
    group_pfp.putalpha(mask)

    base.paste(group_pfp, (100, 110), group_pfp)
    base.paste(user_pfp, (520, 110), user_pfp)
    draw.text((320, 40), "WELCOME TO", fill="white")
    draw.text((280, 70), f"{chat.title[:20]}", fill="red")
    draw.text((350, 320), f"NAME: {user.full_name[:15]}", fill="white")
    draw.text((350, 350), f"USER ID: {user.id}", fill="red")

    buf = io.BytesIO()
    base.save(buf, format='PNG')
    buf.seek(0)
    return buf

# --- HANDLERS ---
async def member_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member if update.chat_member else update.my_chat_member
    if not result: return
    chat, user = update.effective_chat, result.new_chat_member.user
    if result.old_chat_member.status in ["left", "kicked"] and result.new_chat_member.status in ["member", "administrator"]:
        img = await generate_welcome_image(context, user, chat)
        caption = f"<blockquote>ဟိတ် <a href='tg://user?id={user.id}'>{user.full_name}</a>! {chat.title} ကနေ ကြိုဆိုလိုက်ပါတယ်!🫵</blockquote>"
        await context.bot.send_photo(chat.id, photo=img, caption=caption, parse_mode=ParseMode.HTML)

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid, chat_id = update.effective_user.id, update.effective_chat.id
    member = await context.bot.get_chat_member(chat_id, uid)
    if uid != OWNER_ID and not (member.status == ChatMember.ADMINISTRATOR and member.can_restrict_members):
        return await update.message.reply_text("<blockquote>မင်းမှာ Admin Rights (Ban/Mute) မရှိဘူးညီ 🫵</blockquote>", parse_mode=ParseMode.HTML)

    cmd = update.message.text.split()[0][1:].lower()
    target_id, target_name = None, None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target_name = update.message.reply_to_message.from_user.full_name
    elif context.args:
        arg = context.args[0].replace('@', '')
        if arg.isdigit(): target_id, target_name = int(arg), f"User {arg}"

    if not target_id: return await update.message.reply_text("<blockquote>Reply ပြန်ပါ သို့မဟုတ် ID ထည့်ပါ Chief!</blockquote>", parse_mode=ParseMode.HTML)

    try:
        if cmd == "mute": await context.bot.restrict_chat_member(chat_id, target_id, permissions=ChatPermissions(can_send_messages=False))
        elif cmd == "unmute": await context.bot.restrict_chat_member(chat_id, target_id, permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
        elif cmd == "kick": await context.bot.ban_chat_member(chat_id, target_id); await context.bot.unban_chat_member(chat_id, target_id)
        elif cmd == "ban": await context.bot.ban_chat_member(chat_id, target_id)
        elif cmd == "unban": await context.bot.unban_chat_member(chat_id, target_id)
        await update.message.reply_text(f"<blockquote>✅ {target_name} ကို <b>{cmd}</b> လိုက်ပါပြီ Chief!</blockquote>", parse_mode=ParseMode.HTML)
    except: await update.message.reply_text("<blockquote>❌ Error: Permission မလုံလောက်ပါ။</blockquote>", parse_mode=ParseMode.HTML)

async def allow_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    new_users, old_data = list(db.allow_users.find()), db.settings.find_one({"_id": "allow"})
    old_ids = old_data["data"] if old_data and "data" in old_data else []
    msg = "<blockquote><b>👥 BoD Authorized Users</b>\n\n"
    seen = set()
    for u in new_users:
        msg += f"• <a href='tg://user?id={u['user_id']}'>{u['name']}</a> (ID: <code>{u['user_id']}</code>)\n"
        seen.add(u['user_id'])
    for oid in old_ids:
        if oid not in seen: msg += f"• Legacy User (ID: <code>{oid}</code>)\n"
    msg += "</blockquote>"
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def bully_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id): return
    msg = "<blockquote><b>🎯 Active Bully Targets</b>\n"
    if not active_targets: msg += "<i>- None</i>\n"
    else:
        for cid, t in active_targets.items(): msg += f"• <a href='tg://user?id={t['id']}'>{t['name']}</a> (GP: <code>{cid}</code>)\n"
    msg += "\n<b>🔑 Allow Users:</b>\n"
    for u in db.allow_users.find(): msg += f"• <a href='tg://user?id={u['user_id']}'>{u['name']}</a>\n"
    msg += "</blockquote>"
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id): return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target or target.id == OWNER_ID: return await update.message.reply_text("<blockquote>Reply ပြန်ပါ (သို့) Creator ကို မထိနဲ့!</blockquote>", parse_mode=ParseMode.HTML)
    
    chat_id, words = update.effective_chat.id, get_all_bully_words()
    if chat_id in bully_tasks: stop_events[chat_id].set()
    stop_events[chat_id], active_targets[chat_id] = asyncio.Event(), {"id": target.id, "name": target.full_name}

    async def loop():
        try:
            while not stop_events[chat_id].is_set():
                for w in random.sample(words, min(len(words), 5)):
                    if stop_events[chat_id].is_set(): break
                    await context.bot.send_message(chat_id, f"<blockquote><a href='tg://user?id={target.id}'>{target.full_name}</a> {w}</blockquote>", parse_mode=ParseMode.HTML)
                    await asyncio.sleep(0.5)
                await asyncio.sleep(4)
        finally: active_targets.pop(chat_id, None)
    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(f"<blockquote>🔥 {target.full_name} ကို လိုးနေပါပြီ!</blockquote>", parse_mode=ParseMode.HTML)

async def main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat_id, uid, text = update.effective_chat.id, update.effective_user.id, update.message.text
    f_data = db.filters.find_one({"keyword": text.lower()})
    if f_data: await update.message.reply_text(f"<blockquote>{f_data['reply']}</blockquote>", parse_mode=ParseMode.HTML)
    
    save_status = db.settings.find_one({"_id": "save_mode"})
    if chat_id == SAVE_CHAT_ID and save_status and save_status.get("data") and is_allow(uid):
        if not text.startswith('/') and text not in get_all_bully_words():
            db.bully_messages.insert_one({"text": text})
            await update.message.reply_text("<blockquote>Bully text သိမ်းလိုက်ပြီ!</blockquote>", parse_mode=ParseMode.HTML)

    if uid != OWNER_ID and not (await context.bot.get_chat_member(chat_id, uid)).status == ChatMember.ADMINISTRATOR:
        if re.search(r"(https?://\S+|t\.me/\S+|www\.\S+)", text):
            await update.message.delete()
            await update.message.reply_text(f"<blockquote>{update.effective_user.full_name} link ဖျက်လိုက်ပြီ!</blockquote>", parse_mode=ParseMode.HTML)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(member_update_handler, ChatMemberHandler.ANY_CHAT_MEMBER))
    app.add_handler(CommandHandler(["mute", "unmute", "kick", "ban", "unban"], admin_action))
    app.add_handler(CommandHandler("allowlist", allow_list_cmd))
    app.add_handler(CommandHandler("bullylist", bully_list_cmd))
    app.add_handler(CommandHandler("bully", bully_cmd))
    app.add_handler(CommandHandler("stopbully", lambda u,c: stop_events[u.effective_chat.id].set() or u.message.reply_text("<blockquote>ရပ်ပြီ!</blockquote>", parse_mode=ParseMode.HTML)))
    app.add_handler(CommandHandler("save_on", lambda u,c: db.settings.update_one({"_id": "save_mode"}, {"$set": {"data": True}}, upsert=True) or u.message.reply_text("<blockquote>Save ON</blockquote>", parse_mode=ParseMode.HTML) if u.effective_user.id == OWNER_ID else None))
    app.add_handler(CommandHandler("save_off", lambda u,c: db.settings.update_one({"_id": "save_mode"}, {"$set": {"data": False}}, upsert=True) or u.message.reply_text("<blockquote>Save OFF</blockquote>", parse_mode=ParseMode.HTML) if u.effective_user.id == OWNER_ID else None))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_handler))
    app.run_polling()

if __name__ == "__main__": main()

