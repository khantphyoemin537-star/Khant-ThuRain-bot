import asyncio
import re
from pymongo import MongoClient
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8575371720:AAHOa0swN0u4NI0hLI2nJTMVs8u7BDkPpQA"
OWNER_ID = 6015356597
SAVE_CHAT = -1003864912245
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["telegram_bot"]

bully_tasks = {}

LINK_REGEX = r"(https?://|t\.me|telegram\.me|www\.)"


def get_list(name):
    data = db.settings.find_one({"_id": name})
    if data:
        return data.get("data", [])
    return []


def set_list(name, data):
    db.settings.update_one({"_id": name}, {"$set": {"data": data}}, upsert=True)


def get_bool(name):
    data = db.settings.find_one({"_id": name})
    if data:
        return data.get("data", False)
    return False


def set_bool(name, val):
    db.settings.update_one({"_id": name}, {"$set": {"data": val}}, upsert=True)


def add_group(chat_id):
    groups = get_list("groups")
    if chat_id not in groups:
        groups.append(chat_id)
        set_list("groups", groups)


async def is_admin(update, context):

    uid = update.effective_user.id
    chat = update.effective_chat.id

    if uid == OWNER_ID:
        return True

    admins = await context.bot.get_chat_administrators(chat)

    return any(admin.user.id == uid for admin in admins)


async def is_allow(update):

    uid = update.effective_user.id

    if uid == OWNER_ID:
        return True

    allow = get_list("allow")

    if uid in allow:
        return True

    await update.message.reply_text("> bot သုံးခွင့်မရှိပါဘူး")
    return False


async def addallow(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("> Owner only")

    if not update.message.reply_to_message:
        return await update.message.reply_text("> Reply user")

    uid = update.message.reply_to_message.from_user.id

    allow = get_list("allow")

    if uid not in allow:
        allow.append(uid)
        set_list("allow", allow)

    await update.message.reply_text("> User allowed ✅")


async def save_on(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_allow(update):
        return

    set_bool("save", True)

    await update.message.reply_text("> Save ON ✅")


async def save_off(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_allow(update):
        return

    set_bool("save", False)

    await update.message.reply_text("> Save OFF ❌")


async def save_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not get_bool("save"):
        return

    uid = update.effective_user.id
    allow = get_list("allow")

    if uid == OWNER_ID or uid in allow:

        try:
            await context.bot.forward_message(
                SAVE_CHAT,
                update.effective_chat.id,
                update.message.id
            )
        except:
            pass


async def bully(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_allow(update):
        return

    if not update.message.reply_to_message:
        return await update.message.reply_text("> reply user")

    chat = update.effective_chat.id
    user = update.message.reply_to_message.from_user

    name = user.first_name

    db.bully_users.update_one(
        {"_id": user.id},
        {"$set": {"name": name}},
        upsert=True
    )

    bully_words = get_list("bully")

    if not bully_words:
        return await update.message.reply_text("> bully words empty")

    key = (chat, user.id)

    async def bully_loop():

        try:
            while True:

                for word in bully_words:

                    await context.bot.send_message(
                        chat,
                        f"> {name} {word}"
                    )

                    await asyncio.sleep(3)

        except asyncio.CancelledError:
            pass

    if key in bully_tasks:
        bully_tasks[key].cancel()

    bully_tasks[key] = asyncio.create_task(bully_loop())

    await update.message.reply_text(f"> bully started for {name}")


async def stopbully(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_allow(update):
        return

    chat = update.effective_chat.id

    keys = [k for k in bully_tasks if k[0] == chat]

    for k in keys:
        bully_tasks[k].cancel()
        del bully_tasks[k]

    await update.message.reply_text("> bully stopped")


async def addfilter(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_allow(update):
        return

    if len(context.args) < 2:
        return await update.message.reply_text("> usage: /addfilter word reply")

    key = context.args[0].lower()
    reply = " ".join(context.args[1:])

    db.filters.update_one(
        {"_id": key},
        {"$set": {"reply": reply}},
        upsert=True
    )

    await update.message.reply_text("> filter added")


async def lists(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = """
> List Menu

1️⃣ bullyခံရဖူးတဲ့စာ
2️⃣ bully messages

type:
/list bully
/list words
"""

    await update.message.reply_text(msg)


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        return

    arg = context.args[0]

    if arg == "bully":

        users = db.bully_users.find()

        text = "> Bully Users\n\n"

        for u in users:
            text += f"{u['name']}\n"

        await update.message.reply_text(text)

    elif arg == "words":

        bully_words = get_list("bully")

        msg = "> Bully Words\n\n"

        for w in bully_words:
            msg += f"{w}\n"

        await update.message.reply_text(msg)


async def sendallgp(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_allow(update):
        return

    if not context.args:
        return await update.message.reply_text("> usage: /sendallgp message")

    message = " ".join(context.args)

    groups = get_list("groups")

    count = 0

    for gid in groups:

        try:

            await context.bot.send_message(
                gid,
                f"> {message}"
            )

            count += 1

        except:
            pass

    await update.message.reply_text(f"> sent to {count} groups")


async def antilink(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if await is_admin(update, context):
        return

    text = update.message.text

    if re.search(LINK_REGEX, text):

        await update.message.delete()

        name = update.effective_user.first_name

        await update.message.chat.send_message(
            f"> ဒီမှာlinkချခွင့်မရှိပါဘူး {name}"
        )


async def main_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat.id
    add_group(chat)

    await antilink(update, context)
    await save_messages(update, context)

    text = update.message.text.lower()

    f = db.filters.find_one({"_id": text})

    if f:
        await update.message.reply_text(f"> {f['reply']}")


async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat.id
    group = update.effective_chat.title

    add_group(chat)

    for m in update.message.new_chat_members:

        await context.bot.send_message(
            chat,
            f"> ဟိတ် {m.first_name} {group} ကနေကြိုဆိုလိုက်ပါတယ်!"
        )


async def goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat.id
    group = update.effective_chat.title

    user = update.message.left_chat_member

    mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

    await context.bot.send_message(
        chat,
        f"> ဟုတ် {mention} {group} ကနေထွက်သွားလိုက်ပါပြီ!",
        parse_mode=ParseMode.HTML
    )


def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("addallow", addallow))
    app.add_handler(CommandHandler("save_on", save_on))
    app.add_handler(CommandHandler("save_off", save_off))

    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("stopbully", stopbully))

    app.add_handler(CommandHandler("addfilter", addfilter))

    app.add_handler(CommandHandler("lists", lists))
    app.add_handler(CommandHandler("list", list_command))

    app.add_handler(CommandHandler("sendallgp", sendallgp))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_message))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye))

    print("BOT RUNNING")

    app.run_polling()


if __name__ == "__main__":
    main()
