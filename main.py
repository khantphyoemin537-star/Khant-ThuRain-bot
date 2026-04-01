import asyncio
import random
import logging
import aiohttp
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pymongo import MongoClient

from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

TOKEN = "8575371720:AAHR_1fCkRxlALIbhMH0yufXGJiUSQYJyYE"
OWNER_ID = 6015356597
ADMIN_CHAT_ID = -1003580630981
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["telegrambot"]

logging.basicConfig(level=logging.INFO)

bully_tasks = {}
stop_events = {}
save_bully_status = {}  # chat_id -> bool

def mention(uid, name):
    return f"<a href='tg://user?id={uid}'>{name}</a>"

def owner_only(uid):
    return uid == OWNER_ID

async def is_admin(chat, user, context):
    member = await context.bot.get_chat_member(chat, user)
    return member.status in ["administrator", "creator"]

# ---------------- UTILS ---------------- #

async def download_file(file_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            data = await resp.read()
            return Image.open(BytesIO(data))

def circle_crop(img):
    img = img.convert("RGBA").resize((180,180))
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0,0,img.size[0],img.size[1]), fill=255)
    output = ImageOps.fit(img, img.size, centering=(0.5,0.5))
    output.putalpha(mask)
    return output

def make_gradient(size):
    base = Image.new("RGB", size)
    for y in range(size[1]):
        r = 30 + int(25*y/size[1])
        g = 30 + int(25*y/size[1])
        b = 30 + int(25*y/size[1])
        for x in range(size[0]):
            base.putpixel((x,y),(r,g,b))
    return base

def bot_reply(text):
    return f"> {text}"

# ---------------- WELCOME IMAGE & ENTRY ---------------- #

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in update.message.new_chat_members:
        chat = update.effective_chat

        # member profile picture
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            file = await context.bot.get_file(photos.photos[0][-1].file_id)
            member_pfp = await download_file(file.file_path)
        else:
            member_pfp = Image.new("RGB", (200, 200), (100, 100, 100))
        member_pfp = circle_crop(member_pfp)

        # group profile picture
        if chat.photo:
            file = await context.bot.get_file(chat.photo.big_file_id)
            group_pfp = await download_file(file.file_path)
        else:
            group_pfp = Image.new("RGB", (200, 200), (80, 80, 80))
        group_pfp = circle_crop(group_pfp)

        # Base with gradient
        base = make_gradient((900,450))
        draw = ImageDraw.Draw(base)

        base.paste(member_pfp,(80,140), member_pfp)
        base.paste(group_pfp,(640,140), group_pfp)

        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

        # Draw centered text
        title_text = f"Welcome to {chat.title}"
        name_text = f"Name: {user.full_name}"
        id_text = f"User ID: {user.id}"
        time_text = datetime.now().strftime("Joined: %Y-%m-%d %H:%M:%S")

        draw.text((450 - draw.textsize(title_text,font=font_big)[0]//2,40), title_text, fill="white", font=font_big)
        draw.text((450 - draw.textsize(name_text,font=font_small)[0]//2,200), name_text, fill="white", font=font_small)
        draw.text((450 - draw.textsize(id_text,font=font_small)[0]//2,240), id_text, fill="white", font=font_small)
        draw.text((450 - draw.textsize(time_text,font=font_small)[0]//2,280), time_text, fill="white", font=font_small)

        bio = BytesIO()
        bio.name = "welcome.png"
        base.save(bio, "PNG")
        bio.seek(0)

        await update.message.reply_photo(
            photo=bio,
            caption=bot_reply(
                f"✨ {chat.title} မှ ကြိုဆိုလိုက်ပါတယ် ✨\n\n"
                f"🏷 Name: {user.full_name}\n"
                f"🆔 ID: {user.id}\n"
                f"👋 Mention: {mention(user.id,user.full_name)}"
            ),
            parse_mode=ParseMode.HTML
        )

        try:
            await context.bot.send_message(
                ADMIN_CHAT_ID,
                bot_reply(f"📥 New User Joined:\n{mention(user.id,user.full_name)}\nChat: {chat.title}\nID: {user.id}"),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logging.error(f"Failed to notify admin: {e}")

# ---------------- GOODBYE ---------------- #

async def goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.left_chat_member
    await update.message.reply_text(bot_reply(f"👋 {user.full_name} left {update.effective_chat.title}"))

# ---------------- BULLY ---------------- #

def get_words():
    return [x["text"] for x in db.bully.find()]

async def bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text(bot_reply("Reply to a user to bully."))
        return

    target = update.message.reply_to_message.from_user

    if target.id == OWNER_ID:
        await update.message.reply_text(
            bot_reply(f"{mention(target.id,target.full_name)} You Can't Bully Bot Creator {mention(OWNER_ID,'Owner')} !")
        )
        return

    words = get_words()
    if not words:
        await update.message.reply_text(bot_reply("No bully words."))
        return

    chat = update.effective_chat.id
    stop_events[chat] = asyncio.Event()

    async def loop():
        while not stop_events[chat].is_set():
            w = random.choice(words)
            await context.bot.send_message(chat, bot_reply(f"{mention(target.id,target.full_name)} {w}"), parse_mode=ParseMode.HTML)
            if save_bully_status.get(chat, False):
                db.bully_messages.insert_one({
                    "chat_id": chat,
                    "target_id": target.id,
                    "word": w,
                    "time": datetime.utcnow()
                })
            await asyncio.sleep(2)

    bully_tasks[chat] = asyncio.create_task(loop())
    await update.message.reply_text(bot_reply("Bully started."))

async def stopbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    if chat in stop_events:
        stop_events[chat].set()
    await update.message.reply_text(bot_reply("Bully stopped."))

async def tbm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = db.bully_messages.count_documents({})
    await update.message.reply_text(bot_reply(f"Total bully messages saved: {count}"))

# ---------------- SAVE ON/OFF ---------------- #

async def save_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update.effective_user.id):
        await update.message.reply_text(bot_reply("Owner only."))
        return
    chat = update.effective_chat.id
    save_bully_status[chat] = True
    await update.message.reply_text(bot_reply("Bully message saving is now ON."))

async def save_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update.effective_user.id):
        await update.message.reply_text(bot_reply("Owner only."))
        return
    chat = update.effective_chat.id
    save_bully_status[chat] = False
    await update.message.reply_text(bot_reply("Bully message saving is now OFF."))

# ---------------- ALLOW ---------------- #

async def addallow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update.effective_user.id):
        await update.message.reply_text(bot_reply("Owner only."))
        return
    u = update.message.reply_to_message.from_user
    db.allow.update_one({"user_id": u.id}, {"$set": {"name": u.full_name}}, upsert=True)
    await update.message.reply_text(bot_reply(f"{mention(u.id,u.full_name)} Added to allowlist."))

async def removeallow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update.effective_user.id):
        await update.message.reply_text(bot_reply("Owner only."))
        return
    u = update.message.reply_to_message.from_user
    db.allow.delete_one({"user_id": u.id})
    await update.message.reply_text(bot_reply(f"{mention(u.id,u.full_name)} Removed from allowlist."))

async def allowlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update.effective_user.id):
        await update.message.reply_text(bot_reply("Owner only."))
        return
    users = list(db.allow.find())
    text = "Allow Users\n\n"
    for u in users:
        text += f"{mention(u['user_id'], u['name'])}\n"
    await update.message.reply_text(bot_reply(text))

# ---------------- BAN MUTE KICK ---------------- #

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    user = update.effective_user.id
    if not await is_admin(chat, user, context):
        await update.message.reply_text(bot_reply("Admin only."))
        return
    target = update.message.reply_to_message.from_user
    await context.bot.ban_chat_member(chat, target.id)
    await update.message.reply_text(bot_reply("User banned."))

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    target = update.message.reply_to_message.from_user
    await context.bot.unban_chat_member(chat, target.id)
    await update.message.reply_text(bot_reply("User unbanned."))

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    target = update.message.reply_to_message.from_user
    await context.bot.restrict_chat_member(chat, target.id, ChatPermissions(can_send_messages=False))
    await update.message.reply_text(bot_reply("User muted."))

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    target = update.message.reply_to_message.from_user
    await context.bot.restrict_chat_member(chat, target.id, ChatPermissions(can_send_messages=True))
    await update.message.reply_text(bot_reply("User unmuted."))

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    target = update.message.reply_to_message.from_user
    await context.bot.ban_chat_member(chat, target.id)
    await context.bot.unban_chat_member(chat, target.id)
    await update.message.reply_text(bot_reply("User kicked."))

# ---------------- MAIN ---------------- #

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Bully commands
    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("stopbully", stopbully))
    app.add_handler(CommandHandler("tbm", tbm))

    # Save commands
    app.add_handler(CommandHandler("save_on", save_on))
    app.add_handler(CommandHandler("save_off", save_off))

    # Allowlist
    app.add_handler(CommandHandler("addallow", addallow))
    app.add_handler(CommandHandler("removeallow", removeallow))
    app.add_handler(CommandHandler("allowlist", allowlist))

    # Admin actions
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("kick", kick))

    # Member updates
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye))

    print("Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
