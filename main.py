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
    ContextTypes,
    ChatMemberHandler
)

logging.basicConfig(level=logging.INFO)

TOKEN = "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU"
OWNER_ID = 6015356597

MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["telegram_bot"]

stop_events = {}

# ---------------- STYLE ---------------- #

def bot_style(text):
    return f"<blockquote><b>{text}</b></blockquote>"

# ---------------- ADMIN CHECK ---------------- #

async def check_admin(chat, user_id):
    try:
        member = await chat.get_member(user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False


# ---------------- WELCOME IMAGE ---------------- #

async def generate_welcome_image(context, user, chat):

    width = 900
    height = 450

    async def get_pfp(uid, is_user=True):

        try:
            if is_user:
                photos = await context.bot.get_user_profile_photos(uid, limit=1)
                file_id = photos.photos[0][-1].file_id
            else:
                chat_info = await context.bot.get_chat(uid)
                file_id = chat_info.photo.big_file_id

            file = await context.bot.get_file(file_id)
            data = await file.download_as_bytearray()

            return Image.open(io.BytesIO(data)).convert("RGBA")

        except:
            return Image.new("RGBA",(400,400),(30,30,30))

    user_pfp = await get_pfp(user.id,True)
    group_pfp = await get_pfp(chat.id,False)

    bg = group_pfp.resize((width,height))
    bg = bg.filter(ImageFilter.GaussianBlur(25))

    overlay = Image.new("RGBA",(width,height),(0,0,0,170))
    bg = Image.alpha_composite(bg,overlay)

    size = 200

    mask = Image.new("L",(size,size),0)
    ImageDraw.Draw(mask).ellipse((0,0,size,size),fill=255)

    u = ImageOps.fit(user_pfp,(size,size))
    u.putalpha(mask)

    g = ImageOps.fit(group_pfp,(size,size))
    g.putalpha(mask)

    bg.paste(u,(150,120),u)
    bg.paste(g,(550,120),g)

    draw = ImageDraw.Draw(bg)

    draw.text((360,40),"WELCOME",fill="white")

    draw.text((300,340),f"Name : {user.first_name}",fill="white")
    draw.text((300,370),f"ID : {user.id}",fill="#ff3b3b")

    buf = io.BytesIO()
    bg.convert("RGB").save(buf,"JPEG")
    buf.seek(0)

    return buf


# ---------------- MEMBER UPDATE ---------------- #

async def on_member(update:Update,context:ContextTypes.DEFAULT_TYPE):

    result = update.chat_member

    chat = update.effective_chat
    user = result.new_chat_member.user

    old = result.old_chat_member.status
    new = result.new_chat_member.status

    if new in ["member","administrator"] and old not in ["member","administrator"]:

        img = await generate_welcome_image(context,user,chat)

        username = f"@{user.username}" if user.username else "None"

        text = f"""
✨ Welcome to {chat.title}

👤 Name : {user.full_name}
🆔 ID : {user.id}
🔗 Username : {username}
⏰ Joined : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        await context.bot.send_photo(
            chat.id,
            img,
            caption=bot_style(text),
            parse_mode=ParseMode.HTML
        )

    elif new in ["left","kicked"]:

        await context.bot.send_message(
            chat.id,
            bot_style(f"👋 {user.full_name} left the group"),
            parse_mode=ParseMode.HTML
        )


# ---------------- MUTE SYSTEM ---------------- #

async def admin_action(update:Update,context:ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat
    user = update.effective_user

    if not await check_admin(chat,user.id):
        return

    reply = update.message.reply_to_message
    if not reply:
        return

    target = reply.from_user

    cmd = update.message.text.split()[0]

    if cmd == "/mute":

        await chat.restrict_member(
            target.id,
            ChatPermissions(can_send_messages=False)
        )

        text = f"🔇 {target.full_name} ကို Mute လုပ်လိုက်ပါပြီ"

    elif cmd == "/unmute":

        perms = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_invite_users=True
        )

        await chat.restrict_member(target.id,perms)

        text = f"🔊 {target.full_name} ကို Unmute လုပ်လိုက်ပါပြီ"

    elif cmd == "/ban":

        await chat.ban_member(target.id)

        text = f"🚫 {target.full_name} ကို Ban လုပ်လိုက်ပါပြီ"

    await update.message.reply_text(
        bot_style(text),
        parse_mode=ParseMode.HTML
    )


# ---------------- MAIN ---------------- #

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler(["mute","unmute","ban"],admin_action))

    app.add_handler(
        ChatMemberHandler(on_member,ChatMemberHandler.CHAT_MEMBER)
    )

    print("BOT RUNNING")

    app.run_polling()


if __name__ == "__main__":
    main()
