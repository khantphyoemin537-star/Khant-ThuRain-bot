import asyncio
import logging
import random
import io
import re
from datetime import datetime
from pymongo import MongoClient
from PIL import Image, ImageDraw, ImageOps, ImageFilter, ImageFont

from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ChatMemberHandler,
    filters
)

# ---------------- CONFIG ---------------- #

TOKEN = "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU"
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["telegram_bot"]

logging.basicConfig(level=logging.INFO)

bully_tasks = {}
stop_events = {}

# ---------------- STYLE ---------------- #

def bot_style(text):
    return f"<blockquote><b>{text}</b></blockquote>"

# ---------------- ADMIN CHECK ---------------- #

async def is_admin(chat, user_id):
    try:
        member = await chat.get_member(user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False


# ---------------- ALLOW SYSTEM ---------------- #

async def addallow(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    reply = update.message.reply_to_message
    if not reply:
        return

    user = reply.from_user

    db.allow.insert_one({
        "id":user.id,
        "name":user.full_name
    })

    await update.message.reply_text(
        bot_style(f"{user.full_name} ကို Allow List ထဲ ထည့်လိုက်ပါပြီ"),
        parse_mode=ParseMode.HTML
    )


async def removeallow(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    reply = update.message.reply_to_message
    if not reply:
        return

    user = reply.from_user

    db.allow.delete_one({"id":user.id})

    await update.message.reply_text(
        bot_style(f"{user.full_name} ကို Allow List ထဲက ဖျက်လိုက်ပါပြီ"),
        parse_mode=ParseMode.HTML
    )


async def allowlist(update:Update,context:ContextTypes.DEFAULT_TYPE):

    users = list(db.allow.find())

    if not users:
        return await update.message.reply_text(bot_style("Allow list empty"),parse_mode=ParseMode.HTML)

    text="📜 Allow List\n\n"

    for u in users:
        text+=f"{u['name']} ({u['id']})\n"

    await update.message.reply_text(bot_style(text),parse_mode=ParseMode.HTML)


def is_allow(uid):
    if uid == OWNER_ID:
        return True

    return db.allow.find_one({"id":uid}) != None


# ---------------- BULLY ---------------- #

async def bully(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if not is_allow(update.effective_user.id):
        return

    reply = update.message.reply_to_message
    if not reply:
        return

    target = reply.from_user
    chat_id = update.effective_chat.id

    words = [
        "နင်တော့ မလှဘူး",
        "ငိုတော့မယ်ထင်တယ်",
        "ဟာဟာဟာ",
        "အော်ကြီးလား"
    ]

    if chat_id in stop_events:
        stop_events[chat_id].set()

    stop_events[chat_id]=asyncio.Event()

    async def loop():

        while not stop_events[chat_id].is_set():

            word=random.choice(words)

            mention=f"<a href='tg://user?id={target.id}'>{target.full_name}</a>"

            await context.bot.send_message(
                chat_id,
                bot_style(f"{mention} {word}"),
                parse_mode=ParseMode.HTML
            )

            await asyncio.sleep(3)

    asyncio.create_task(loop())

    await update.message.reply_text(
        bot_style("Bully start 🔥"),
        parse_mode=ParseMode.HTML
    )


async def stopbully(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if update.effective_chat.id in stop_events:

        stop_events[update.effective_chat.id].set()

        await update.message.reply_text(
            bot_style("Bully stopped"),
            parse_mode=ParseMode.HTML
        )


# ---------------- LINK FILTER ---------------- #

link_regex = r"(https?://|t\.me/|www\.)"

async def link_filter(update:Update,context:ContextTypes.DEFAULT_TYPE):

    msg=update.message
    text=msg.text

    if not text:
        return

    if re.search(link_regex,text):

        if not await is_admin(update.effective_chat,msg.from_user.id):

            await msg.delete()

            await msg.reply_text(
                bot_style("🚫 Link မပို့ရပါ"),
                parse_mode=ParseMode.HTML
            )


# ---------------- MENTION SPAM ---------------- #

async def mention_filter(update:Update,context:ContextTypes.DEFAULT_TYPE):

    msg=update.message

    if msg.entities:

        count=0

        for e in msg.entities:

            if e.type=="mention":
                count+=1

        if count>=5:

            await msg.delete()

            await msg.reply_text(
                bot_style("🚫 Mention spam ဖျက်လိုက်ပါပြီ"),
                parse_mode=ParseMode.HTML
            )


# ---------------- WELCOME ULTRA IMAGE ---------------- #

async def welcome_image(context,user,chat):

    width=900
    height=450

    bg=Image.new("RGB",(width,height),(20,20,20))

    draw=ImageDraw.Draw(bg)

    draw.text((350,40),"WELCOME",fill="white")

    draw.text((300,330),f"Name : {user.full_name}",fill="white")

    draw.text((300,360),f"ID : {user.id}",fill="red")

    buf=io.BytesIO()

    bg.save(buf,"JPEG")

    buf.seek(0)

    return buf


async def member_update(update:Update,context:ContextTypes.DEFAULT_TYPE):

    result=update.chat_member

    chat=update.effective_chat
    user=result.new_chat_member.user

    old=result.old_chat_member.status
    new=result.new_chat_member.status

    if new=="member" and old!="member":

        img=await welcome_image(context,user,chat)

        await context.bot.send_photo(
            chat.id,
            img,
            caption=bot_style(f"{user.full_name} joined"),
            parse_mode=ParseMode.HTML
        )


# ---------------- MAIN ---------------- #

def main():

    app=ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("addallow",addallow))
    app.add_handler(CommandHandler("removeallow",removeallow))
    app.add_handler(CommandHandler("allowlist",allowlist))

    app.add_handler(CommandHandler("bully",bully))
    app.add_handler(CommandHandler("stopbully",stopbully))

    app.add_handler(MessageHandler(filters.TEXT,link_filter))
    app.add_handler(MessageHandler(filters.TEXT,mention_filter))

    app.add_handler(ChatMemberHandler(member_update,ChatMemberHandler.CHAT_MEMBER))

    print("BOT RUNNING")

    app.run_polling()


if __name__=="__main__":
    main()
