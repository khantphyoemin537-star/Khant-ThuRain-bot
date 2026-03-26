import asyncio
from pymongo import MongoClient
from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ---------------- CONFIG ----------------
TOKEN = "8575371720:AAHOa0swN0u4NI0hLI2nJTMVs8u7BDkPpQA"
MONGO = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"
SAVE_CHAT = -1003864912245
ALWAYS_ALLOW_ID = 6015356597  # သင့် ID အတွက် auto allow

# ---------------- DATABASE ----------------
client = MongoClient(MONGO)
db = client["telegram_bot"]

def get_list(name):
    d = db.settings.find_one({"_id": name})
    if d:
        return d["data"]
    db.settings.insert_one({"_id": name, "data": []})
    return []

def set_list(name, data):
    db.settings.update_one({"_id": name}, {"$set": {"data": data}}, upsert=True)

def get_bool(name):
    d = db.settings.find_one({"_id": name})
    if d:
        return bool(d["data"])
    db.settings.insert_one({"_id": name, "data": False})
    return False

def set_bool(name, val):
    db.settings.update_one({"_id": name}, {"$set": {"data": bool(val)}}, upsert=True)

# ---------------- PERMISSIONS ----------------
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id == ALWAYS_ALLOW_ID:
        return True

    admins = await context.bot.get_chat_administrators(chat_id)
    if any(a.user.id == user_id for a in admins):
        return True

    allow = get_list("allow")
    if user_id in allow:
        return True

    await update.message.reply_text("No permission")
    return False

# ---------------- ALLOW ----------------
async def addallow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to allow them")
        return
    uid = update.message.reply_to_message.from_user.id
    allow = get_list("allow")
    if uid not in allow:
        allow.append(uid)
        set_list("allow", allow)
    await update.message.reply_text("User allowed ✅")

# ---------------- BAN ----------------
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to ban them")
        return
    uid = update.message.reply_to_message.from_user.id
    await context.bot.ban_chat_member(update.effective_chat.id, uid)
    await update.message.reply_text("User banned ✅")

# ---------------- MUTE ----------------
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to mute them")
        return
    uid = update.message.reply_to_message.from_user.id
    perms = ChatPermissions(can_send_messages=False)
    await context.bot.restrict_chat_member(update.effective_chat.id, uid, perms)
    await update.message.reply_text("User muted ✅")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to unmute them")
        return
    uid = update.message.reply_to_message.from_user.id
    perms = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True,
    )
    await context.bot.restrict_chat_member(update.effective_chat.id, uid, perms)
    await update.message.reply_text("User unmuted ✅")

# ---------------- BULLY ----------------
bully_tasks = {}

async def bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to bully them")
        return
    chat_id = update.effective_chat.id
    user = update.message.reply_to_message.from_user
    mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    bully_list = get_list("bully")
    if not bully_list:
        await update.message.reply_text("Bully list is empty! Add phrases with /addbully")
        return
    key = (chat_id, user.id)
    async def loop():
        try:
            while True:
                for w in bully_list:
                    await context.bot.send_message(chat_id, f"{mention} {w}", parse_mode=ParseMode.HTML)
                    await asyncio.sleep(3)
        except asyncio.CancelledError:
            pass
    if key in bully_tasks:
        bully_tasks[key].cancel()
    task = asyncio.create_task(loop())
    bully_tasks[key] = task
    await update.message.reply_text(f"Bully started for {mention} ✅")

async def stopbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ALWAYS_ALLOW_ID:
        await update.message.reply_text(
            "ညီမင်းမှာ bot သုံးစွဲခွင့်မရသေးဘူး @Besties_with_BoD ကိုလာခဲ့"
        )
        return

    chat_id = update.effective_chat.id
    keys_to_cancel = [k for k in bully_tasks if k[0] == chat_id]
    if not keys_to_cancel:
        await update.message.reply_text("No active bully task in this chat")
        return

    for key in keys_to_cancel:
        bully_tasks[key].cancel()
        del bully_tasks[key]

    await update.message.reply_text("Bully stopped for entire chat ✅")

async def addbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Usage: /addbully <text>")
        return
    bully_list = get_list("bully")
    bully_list.append(text)
    set_list("bully", bully_list)
    await update.message.reply_text("Bully phrase added ✅")

async def listbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bully_list = get_list("bully")
    if not bully_list:
        await update.message.reply_text("Bully list is empty")
        return
    await update.message.reply_text("\n".join(bully_list))

async def delbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    bully_list = get_list("bully")
    if text in bully_list:
        bully_list.remove(text)
        set_list("bully", bully_list)
        await update.message.reply_text("Bully phrase deleted ✅")
    else:
        await update.message.reply_text("Phrase not found in bully list")

# ---------------- FILTER ----------------
async def addfilter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addfilter <keyword> <reply>")
        return
    key = context.args[0].lower()
    reply = " ".join(context.args[1:])
    db.filters.update_one({"_id": key}, {"$set": {"reply": reply}}, upsert=True)
    await update.message.reply_text("Filter added ✅")

async def delfilter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    key = context.args[0].lower()
    db.filters.delete_one({"_id": key})
    await update.message.reply_text("Filter deleted ✅")

# ---------------- MESSAGE HANDLER ----------------
async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    save = get_bool("save")
    if save:
        try:
            await context.bot.forward_message(SAVE_CHAT, update.effective_chat.id, update.message.id)
        except:
            pass
    f = db.filters.find_one({"_id": text})
    if f:
        await update.message.reply_text(f["reply"])

# ---------------- SAVE ----------------
async def save_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_bool("save", True)
    await update.message.reply_text("Save ON ✅")

async def save_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_bool("save", False)
    await update.message.reply_text("Save OFF ✅")

# ---------------- WELCOME / GOODBYE ----------------
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    add_group_to_db(chat_id)
    for m in update.message.new_chat_members:
        name = m.first_name
        group = update.effective_chat.title
        await update.message.reply_text(f"ဟိတ် {name}\n{group} ကနေ ကြိုဆိုလိုက်ပါတယ်!")

async def goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.left_chat_member.first_name
    await update.message.reply_text(f"{name} group ကနေ ထွက်သွားပါတယ်")

# ---------------- HELP ----------------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
/addallow
/ban
/mute
/unmute

/bully
/stopbully
/addbully
/listbully
/delbully

/addfilter
/delfilter

/save_on
/save_off

/sendallgp <message>
"""
    await update.message.reply_text(text)

# ---------------- GROUP LIST ----------------
def add_group_to_db(chat_id):
    groups = get_list("groups")
    if chat_id not in groups:
        groups.append(chat_id)
        set_list("groups", groups)

# ---------------- SEND TO ALL GROUPS ----------------
async def sendallgp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALWAYS_ALLOW_ID:
        await update.message.reply_text("No permission")
        return
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Usage: /sendallgp <message>")
        return
    groups = get_list("groups")
    if not groups:
        await update.message.reply_text("No groups found")
        return
    success = 0
    for gid in groups:
        try:
            await context.bot.send_message(gid, text)
            success += 1
        except:
            pass
    await update.message.reply_text(f"Message sent to {success}/{len(groups)} groups ✅")

# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Admin & Permission commands
    app.add_handler(CommandHandler("addallow", addallow))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))

    # Bully commands
    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("stopbully", stopbully))
    app.add_handler(CommandHandler("addbully", addbully))
    app.add_handler(CommandHandler("listbully", listbully))
    app.add_handler(CommandHandler("delbully", delbully))

    # Filter commands
    app.add_handler(CommandHandler("addfilter", addfilter))
    app.add_handler(CommandHandler("delfilter", delfilter))

    # Save commands
    app.add_handler(CommandHandler("save_on", save_on))
    app.add_handler(CommandHandler("save_off", save_off))

    # Send all groups
    app.add_handler(CommandHandler("sendallgp", sendallgp))

    # Help
    app.add_handler(CommandHandler("help", help_command))

    # Messages & Status
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye))

    print("BOT RUNNING ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
