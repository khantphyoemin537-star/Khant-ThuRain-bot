import asyncio
import re
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

# --- ADVANCED IMAGE GENERATOR ---
async def generate_welcome_image(context, user, chat):
    try:
        canvas_w, canvas_h = 900, 450
        
        async def get_pfp_img(target_id, is_user=True):
            try:
                if is_user:
                    photos = await context.bot.get_user_profile_photos(target_id, limit=1)
                    if not photos.photos: raise Exception("No photo")
                    file_id = photos.photos[0][-1].file_id
                else:
                    chat_info = await context.bot.get_chat(target_id)
                    if not chat_info.photo: raise Exception("No photo")
                    file_id = chat_info.photo.big_file_id
                
                file = await context.bot.get_file(file_id)
                img_byte = await file.download_as_bytearray()
                return Image.open(io.BytesIO(img_byte)).convert("RGBA")
            except: 
                # Default background color if no PFP found
                return Image.new('RGBA', (400, 400), color=(30, 30, 30, 255))

        user_pfp = await get_pfp_img(user.id, True)
        group_pfp = await get_pfp_img(chat.id, False)

        # 1. Background (Group PFP blurred)
        background = group_pfp.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)
        background = background.filter(ImageFilter.GaussianBlur(radius=15))
        overlay = Image.new('RGBA', background.size, (0, 0, 0, 160))
        background = Image.alpha_composite(background, overlay)

        # 2. Circular Masks
        mask = Image.new('L', (220, 220), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 220, 220), fill=255)
        
        u_p = ImageOps.fit(user_pfp, (220, 220)); u_p.putalpha(mask)
        g_p = ImageOps.fit(group_pfp, (220, 220)); g_p.putalpha(mask)

        # Paste PFPs
        background.paste(u_p, (120, 90), u_p)
        background.paste(g_p, (560, 90), g_p)

        # 3. Text Overlay
        draw = ImageDraw.Draw(background)
        draw.text((360, 40), "WELCOME", fill="white", stroke_width=1, stroke_fill="gray")
        draw.text((310, 340), f"Name: {user.first_name[:20]}", fill="white")
        draw.text((310, 370), f"ID: {user.id}", fill="#FF3131")

        buf = io.BytesIO()
        background.convert("RGB").save(buf, format='JPEG')
        buf.seek(0)
        return buf
    except Exception as e:
        logging.error(f"Image Gen Error: {e}")
        return None

# --- COMMANDS ---
async def allow_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id): return
    users = list(db.allow_users.find())
    if not users: return await update.message.reply_text(bot_style("Allow List ထဲမှာ ဘယ်သူမှ မရှိသေးပါ။"), parse_mode=ParseMode.HTML)
    text = "📜 <b>Bully သုံးခွင့်ရှိသူများ စာရင်း:</b>\n\n"
    for idx, u in enumerate(users, 1):
        text += f"{idx}. <a href='tg://user?id={u['user_id']}'>{u['name']}</a> (<code>{u['user_id']}</code>)\n"
    await update.message.reply_text(bot_style(text), parse_mode=ParseMode.HTML)

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

# --- BULLY LOGIC ---
async def bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id):
        return await update.message.reply_text(bot_style("ဟေ့🫵မင်းမှာ ဒီcommandသုံးခွင့်မရှိဘူး"), parse_mode=ParseMode.HTML)
    reply = update.message.reply_to_message
    if not reply: return await update.message.reply_text(bot_style("ဘယ်သူ့ကို Bully ရမလဲ (Reply ပြန်ပါ)"), parse_mode=ParseMode.HTML)
    
    target, chat_id = reply.from_user, update.effective_chat.id
    if target.id == OWNER_ID:
        return await update.message.reply_text(bot_style("Bot Creator ကို bullyခွင့်မရှိဘူးညီ🫵"), parse_mode=ParseMode.HTML)
    
    words = [w.get("text") for w in list(db.filters.find()) if w.get("text")]
    if not words: return await update.message.reply_text(bot_style("Database ထဲမှာ Bully ရန် စာသားများ မရှိသေးပါ။"), parse_mode=ParseMode.HTML)
    
    if chat_id in stop_events: stop_events[chat_id].set()
    stop_events[chat_id] = asyncio.Event()

    async def loop():
        while not stop_events[chat_id].is_set():
            w = random.choice(words)
            try:
                mention = f"<a href='tg://user?id={target.id}'>{target.full_name}</a>"
                await context.bot.send_message(chat_id, bot_style(f"{mention} {w}"), parse_mode=ParseMode.HTML)
            except: break
            await asyncio.sleep(3.5) 
            
    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(bot_style(f"🔥 {target.full_name} ကို စတင် Bully နေပါပြီ..."), parse_mode=ParseMode.HTML)

async def stop_bully_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allow(update.effective_user.id): return
    chat_id = update.effective_chat.id
    if chat_id in stop_events:
        stop_events[chat_id].set()
        await update.message.reply_text(bot_style("🛑 Bully လုပ်ခြင်းကို ရပ်တန့်လိုက်ပါပြီ။"), parse_mode=ParseMode.HTML)

# --- GLOBAL HANDLER & AUTO SAVE ---
async def global_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat, user, text = update.effective_chat, update.effective_user, update.message.text

    # Auto Save
    res = db.settings.find_one({"_id": f"save_{chat.id}"})
    if res and res.get("data"):
        if len(text.strip()) > 2 and not text.startswith('/'):
            db.filters.update_one({"text": text}, {"$set": {"text": text, "added_by": user.id, "chat": chat.title}}, upsert=True)
            # စာသိမ်းတိုင်း အသိပေးရန် (မလိုချင်ရင် ဒီအောက်ကစာကို comment ပိတ်ထားနိုင်ပါတယ်)
            await update.message.reply_text(bot_style("📝 စာသားကို Bully Database ထဲသို့ သိမ်းဆည်းလိုက်ပါပြီ။"), parse_mode=ParseMode.HTML)

# --- MEMBER HANDLER (WELCOME/GOODBYE) ---
async def on_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member if update.chat_member else update.my_chat_member
    if not result: return
    
    chat = update.effective_chat
    user = result.new_chat_member.user
    old_status, new_status = result.old_chat_member.status, result.new_chat_member.status
    owner_mention = await get_owner_mention(context)

    # Bot Join Entry
    if user.id == context.bot.id and new_status in ["member", "administrator"]:
        db.registered_groups.update_one({"chat_id": chat.id}, {"$set": {"title": chat.title}}, upsert=True)
        entry = (f"ဟိတ်ရို့ /admins မင်းတို့ရဲ့ဒီ <b>{chat.title}</b> ကို ထည့်သွင်းအသုံးပြုပေးတဲ့အတွက် ကျေးဇူး၊\n"
                 f"အသုံးဝင်မယ့် bot command တွေသုံးမယ်ဆို @Besties_with_BoD က OWNER ဆီကိုလာဆက်သွယ်ပေးပါ။\n\n"
                 f"Owner: {owner_mention}")
        await context.bot.send_message(chat.id, entry, parse_mode=ParseMode.HTML)
        return

    # User Joined (Any status change to member/admin)
    if new_status in ["member", "administrator"] and old_status not in ["member", "administrator"]:
        img = await generate_welcome_image(context, user, chat)
        now = datetime.now().strftime("%d:%m:%Y")
        caption = (f"ဟိတ် <b>{chat.title}</b> ကနေ <a href='tg://user?id={user.id}'>{user.full_name}</a> ကို ကြိုဆိုလိုက်ပါတယ်\n\n"
                   f"<b>Name:</b> {user.full_name}\n"
                   f"<b>Joined Date:</b> {now}")
        if img: await context.bot.send_photo(chat.id, photo=img, caption=bot_style(caption), parse_mode=ParseMode.HTML)
        else: await context.bot.send_message(chat.id, bot_style(caption), parse_mode=ParseMode.HTML)

    # User Left/Kicked
    elif new_status in ["left", "kicked"] and old_status in ["member", "administrator"]:
        await context.bot.send_message(chat.id, bot_style(f"👋 {user.full_name} ကတော့ {chat.title} ကနေ ထွက်ခွာသွားပါပြီ။"), parse_mode=ParseMode.HTML)

# --- ADMIN ACTIONS ---
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    text_cmd = update.message.text.split()[0].lower()
    if not await check_admin(chat, user.id): return
    
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text(bot_style("အရေးယူမယ့်သူကို Reply ပြန်ပေးပါ။"), parse_mode=ParseMode.HTML)
    
    try:
        if "ban" in text_cmd: 
            await chat.ban_member(target.id)
            msg = f"🚫 {target.full_name} ကို Ban လိုက်ပါပြီ။"
        elif "mute" in text_cmd: 
            await chat.restrict_member(target.id, ChatPermissions(can_send_messages=False))
            msg = f"🔇 {target.full_name} ကို Mute လိုက်ပါပြီ။"
        elif "unmute" in text_cmd: 
            # Permission အားလုံးကို ပြန်ဖွင့်ပေးရန် Explicit permissions သုံးရပါမယ်
            await chat.restrict_member(target.id, ChatPermissions(
                can_send_messages=True, 
                can_send_media_messages=True, 
                can_send_polls=True, 
                can_send_other_messages=True, 
                can_add_web_page_previews=True,
                can_invite_users=True
            ))
            msg = f"🔊 {target.full_name} ကို Mute ဖြည်ပေးလိုက်ပါပြီ။"
        elif "kick" in text_cmd: 
            await chat.unban_member(target.id)
            msg = f"🚪 {target.full_name} ကို အဖွဲ့ထဲက ကန်ထုတ်လိုက်ပါပြီ။"
        await update.message.reply_text(bot_style(msg), parse_mode=ParseMode.HTML)
    except Exception as e: 
        await update.message.reply_text(f"Admin Error: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers Registration
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler("removeallow", remove_allow))
    app.add_handler(CommandHandler("allowlist", allow_list))
    app.add_handler(CommandHandler("bully", bully_cmd))
    app.add_handler(CommandHandler("stopbully", stop_bully_cmd))
    
    app.add_handler(CommandHandler("save_on", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": True}}, upsert=True), u.message.reply_text(bot_style("✅ Save Chat: ON (စာများကို စတင်မှတ်သားနေပါပြီ)"), parse_mode=ParseMode.HTML))))
    app.add_handler(CommandHandler("save_off", lambda u,c: (db.settings.update_one({"_id": f"save_{u.effective_chat.id}"}, {"$set": {"data": False}}, upsert=True), u.message.reply_text(bot_style("❌ Save Chat: OFF"), parse_mode=ParseMode.HTML))))
    
    app.add_handler(CommandHandler(["ban", "unban", "mute", "unmute", "kick"], admin_action))
    app.add_handler(ChatMemberHandler(on_member_update, ChatMemberHandler.ANY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, global_handler))

    print("🚀 Young Master Dexter Bot Fully Armed & Running!")
    app.run_polling()

if __name__ == "__main__": 
    main()
