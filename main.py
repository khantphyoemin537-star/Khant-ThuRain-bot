import asyncio
import os
from pymongo import MongoClient
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ---------------- KEEP ALIVE ----------------
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Young Master ThuRain is Online!"

def run():
    port = int(os.environ.get("PORT", 7860))
    app_flask.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# ---------------- CONFIG ----------------
TOKEN = "8575371720:AAHOa0swN0u4NI0hLI2nJTMVs8u7BDkPpQA"
OWNER_ID = 6015356597
RUDE_GP = -1003864912245

MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["bully_bot_db"]
collection = db["bot_data"]

bully_running = {}

# ---------------- DATABASE ----------------
def get_data():
    data = collection.find_one({"_id": "config"})
    if not data:
        data = {
            "_id": "config",
            "allowed_users": [OWNER_ID],
            "bully_list": [],
            "groups": [],
            "autosave": False
        }
        collection.insert_one(data)
    return data

def update_db(key, value):
    collection.update_one({"_id": "config"}, {"$set": {key: value}})

# ---------------- PERMISSION ----------------
async def is_admin(update: Update):

    data = get_data()

    if update.effective_user.id in data["allowed_users"]:
        return True

    await update.message.reply_text(
        "<blockquote>❌ မင်းမှာ command သုံးခွင့်မရှိ</blockquote>",
        parse_mode=ParseMode.HTML
    )

    return False

# ---------------- HELP ----------------
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = """
<blockquote>
🤖 Bully Bot Commands

/bully - mention bully start
/replybully - reply bully start
/stopbully - bully stop

/addallow - user ကို bully permission ပေး

/save_on - rude gp save ON
/save_off - rude gp save OFF

/listbully - bully list ကြည့်
/delbully <number> - bully message delete

/sendallgp message - gp အားလုံး broadcast
</blockquote>
"""

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ---------------- SAVE CONTROL ----------------
async def save_on(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    update_db("autosave", True)

    await update.message.reply_text(
        "<blockquote>✅ rude gp save ON</blockquote>",
        parse_mode=ParseMode.HTML
    )

async def save_off(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    update_db("autosave", False)

    await update.message.reply_text(
        "<blockquote>🛑 rude gp save OFF</blockquote>",
        parse_mode=ParseMode.HTML
    )

# ---------------- AUTO SAVE RUDE GP ----------------
async def rude_gp_save(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id
    data = get_data()

    if chat_id != RUDE_GP:
        return

    if not data["autosave"]:
        return

    text = update.message.text

    if not text:
        return

    bully_list = data["bully_list"]

    bully_list.append(text)

    update_db("bully_list", bully_list)

# ---------------- LIST BULLY ----------------
async def listbully(update: Update, context: ContextTypes.DEFAULT_TYPE):

    data = get_data()
    blist = data["bully_list"]

    if not blist:
        await update.message.reply_text(
            "<blockquote>bully list empty</blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    msg = "<blockquote>📜 Bully List\n\n"

    for i, text in enumerate(blist, start=1):
        msg += f"{i}. {text}\n"

    msg += "</blockquote>"

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# ---------------- DELETE BULLY ----------------
async def delbully(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "<blockquote>/delbully number</blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    num = int(context.args[0]) - 1

    data = get_data()
    blist = data["bully_list"]

    if num < 0 or num >= len(blist):
        await update.message.reply_text(
            "<blockquote>invalid number</blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    blist.pop(num)

    update_db("bully_list", blist)

    await update.message.reply_text(
        "<blockquote>🗑 bully deleted</blockquote>",
        parse_mode=ParseMode.HTML
    )

# ---------------- BULLY ----------------
async def bully(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "<blockquote>Reply user နဲ့ /bully</blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    target = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id

    data = get_data()
    blist = data["bully_list"]

    bully_running[chat_id] = True

    mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'

    await update.message.reply_text("<blockquote>😈 bully start</blockquote>", parse_mode=ParseMode.HTML)

    while bully_running.get(chat_id):

        for text in blist:

            if not bully_running.get(chat_id):
                break

            try:
                await context.bot.send_message(
                    chat_id,
                    f"<blockquote>{mention} {text}</blockquote>",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass

            await asyncio.sleep(3)

# ---------------- STOP ----------------
async def stopbully(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update):
        return

    chat_id = update.effective_chat.id
    bully_running[chat_id] = False

    await update.message.reply_text(
        "<blockquote>🛑 bully stopped</blockquote>",
        parse_mode=ParseMode.HTML
    )

# ---------------- ADD ALLOW ----------------
async def addallow(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "<blockquote>Reply user</blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    target = update.message.reply_to_message.from_user.id

    data = get_data()
    allowed = data["allowed_users"]

    if target not in allowed:
        allowed.append(target)
        update_db("allowed_users", allowed)

        await update.message.reply_text(
            "<blockquote>✅ permission granted</blockquote>",
            parse_mode=ParseMode.HTML
        )

# ---------------- SEND ALL GP ----------------
async def sendallgp(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    if not context.args:
        await update.message.reply_text("/sendallgp message")
        return

    text = " ".join(context.args)

    data = get_data()
    gps = data["groups"]

    for g in gps:
        try:
            await context.bot.send_message(g, text)
        except:
            pass

# ---------------- SAVE GROUP ----------------
async def save_group(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id
    data = get_data()

    gps = data["groups"]

    if chat_id not in gps:
        gps.append(chat_id)
        update_db("groups", gps)

# ---------------- MAIN ----------------
def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("stopbully", stopbully))
    app.add_handler(CommandHandler("addallow", addallow))
    app.add_handler(CommandHandler("save_on", save_on))
    app.add_handler(CommandHandler("save_off", save_off))
    app.add_handler(CommandHandler("listbully", listbully))
    app.add_handler(CommandHandler("delbully", delbully))
    app.add_handler(CommandHandler("sendallgp", sendallgp))
    app.add_handler(CommandHandler("help", help_cmd))

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), rude_gp_save))
    app.add_handler(MessageHandler(filters.ALL, save_group))

    print("Bot running...")

    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
