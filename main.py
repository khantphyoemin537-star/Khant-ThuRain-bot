import asyncio
import logging
import random
import re
from pymongo import MongoClient

from telegram import Update, ChatPermissions, ChatMember
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
    ContextTypes
)

TOKEN = "8575371720:AAHR_1fCkRxlALIbhMH0yufXGJiUSQYJyYE"
OWNER_ID = 6015356597
SAVE_CHAT = -1003864912245

MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

logging.basicConfig(level=logging.INFO)

client = MongoClient(MONGO_URI)
db = client["bod_bot"]

bully_tasks = {}
stop_events = {}

# ---------- DATABASE ----------

def get_list(name):
    d = db.settings.find_one({"_id": name})
    return d["data"] if d and "data" in d else []

def set_list(name, data):
    db.settings.update_one({"_id": name}, {"$set": {"data": data}}, upsert=True)

def get_bool(name):
    d = db.settings.find_one({"_id": name})
    return d["data"] if d else False

def set_bool(name, val):
    db.settings.update_one({"_id": name}, {"$set": {"data": val}}, upsert=True)

# ---------- PERMISSION ----------

async def is_admin(update, context):
    uid = update.effective_user.id
    if uid == OWNER_ID:
        return True
    try:
        m = await context.bot.get_chat_member(update.effective_chat.id, uid)
        return m.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return False

# ---------- MEMBER EVENTS ----------

async def member_update(update: Update, context):

    res = update.chat_member if update.chat_member else update.my_chat_member
    if not res:
        return

    chat = update.effective_chat
    chat_id = chat.id

    user = res.new_chat_member.user
    old = res.old_chat_member.status
    new = res.new_chat_member.status

    mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    group = f'<a href="https://t.me/{chat.username}">{chat.title}</a>' if chat.username else chat.title

    # BOT ENTRY
    if user.id == context.bot.id:

        groups = get_list("groups")

        if chat_id not in groups:
            groups.append(chat_id)
            set_list("groups", groups)

        entry = (
            "<blockquote>"
            "ဟိတ်ရို့ /admins မင်းတို့ရဲ့ဒီ group ဟိတ် ကို ထည့်သွင်းအသုံးပြုပေးတဲ့အတွက် ကျေးဇူး၊ "
            "အမ် အသုံးဝင်မယ့် တချို့ကန့်သန့်ထားတဲ့ bot command တွေသုံးမယ်ဆို "
            "@Besties_with_BoD က OWNER ခန့်သူရိန် ဆီကိုလာဆက်သွယ်ပေးပါ"
            "</blockquote>"
        )

        await context.bot.send_message(chat_id, entry, parse_mode=ParseMode.HTML)
        return

    # WELCOME
    if old in [ChatMember.LEFT, ChatMember.KICKED] and new in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:

        await context.bot.send_message(
            chat_id,
            f"<blockquote>{mention} ကို {group} မှ ကြိုဆိုပါတယ်</blockquote>",
            parse_mode=ParseMode.HTML
        )

    # GOODBYE
    if old in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR] and new in [ChatMember.LEFT, ChatMember.KICKED]:

        await context.bot.send_message(
            chat_id,
            f"<blockquote>{mention} သည် {group} မှ ထွက်သွားပါပြီ</blockquote>",
            parse_mode=ParseMode.HTML
        )

# ---------- SAVE SYSTEM ----------

async def save_on(update, context):

    if update.effective_chat.id != SAVE_CHAT:
        return

    set_bool("save", True)

    await update.message.reply_text(
        "<blockquote>Save ON</blockquote>",
        parse_mode=ParseMode.HTML
    )

async def save_off(update, context):

    if update.effective_chat.id != SAVE_CHAT:
        return

    set_bool("save", False)

    await update.message.reply_text(
        "<blockquote>Save OFF</blockquote>",
        parse_mode=ParseMode.HTML
    )

# ---------- AUTO SAVE BULLY ----------

async def autosave(update, context):

    if update.effective_chat.id != SAVE_CHAT:
        return

    if not get_bool("save"):
        return

    txt = update.message.text

    if txt.startswith("/"):
        return

    bl = get_list("bully")

    if txt not in bl:

        bl.append(txt)
        set_list("bully", bl)

        await update.message.reply_text(
            f"<blockquote>bully text save ({len(bl)})</blockquote>",
            parse_mode=ParseMode.HTML
        )

# ---------- ADDALLOW ----------

async def addallow(update, context):

    if update.effective_user.id != OWNER_ID:
        return

    if not update.message.reply_to_message:
        return

    uid = update.message.reply_to_message.from_user.id

    al = get_list("allow")

    if uid not in al:
        al.append(uid)

    set_list("allow", al)

    await update.message.reply_text(
        "<blockquote>Allow added</blockquote>",
        parse_mode=ParseMode.HTML
    )

# ---------- ALLOWLIST ----------

async def allowlist(update, context):

    al = get_list("allow")

    text = "<blockquote>Allow Users\n"

    for i in al:
        text += f'<a href="tg://user?id={i}">{i}</a>\n'

    text += "</blockquote>"

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ---------- BULLY ----------

async def bully(update, context):

    if not update.message.reply_to_message:
        return

    target = update.message.reply_to_message.from_user
    user = update.effective_user

    if target.id == OWNER_ID:
        await update.message.reply_text(
            "<blockquote>Owner ကို bully မရ</blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    allow = get_list("allow")

    if target.id in allow and user.id != OWNER_ID:
        await update.message.reply_text(
            "<blockquote>Bot command user ကို bully မရ</blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    words = get_list("bully")

    chat_id = update.effective_chat.id

    stop_events[chat_id] = asyncio.Event()

    async def loop():

        while not stop_events[chat_id].is_set():

            w = random.choice(words)

            await context.bot.send_message(
                chat_id,
                f"<blockquote>{target.full_name} {w}</blockquote>",
                parse_mode=ParseMode.HTML
            )

            await asyncio.sleep(3)

    bully_tasks[chat_id] = asyncio.create_task(loop())

# ---------- STOP BULLY ----------

async def stopbully(update, context):

    chat_id = update.effective_chat.id

    if chat_id in stop_events:
        stop_events[chat_id].set()

        await update.message.reply_text(
            "<blockquote>Bully stopped</blockquote>",
            parse_mode=ParseMode.HTML
        )

# ---------- BULLYLIST ----------

async def bullylist(update, context):

    bl = get_list("bully")

    text = "<blockquote>Bully Words\n"

    for w in bl:
        text += f"{w}\n"

    text += "</blockquote>"

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ---------- ADDADMIN ----------

async def addadmin(update, context):

    if update.effective_user.id != OWNER_ID:
        return

    if not update.message.reply_to_message:
        return

    target = update.message.reply_to_message.from_user
    giver = update.effective_user

    await context.bot.promote_chat_member(
        update.effective_chat.id,
        target.id,
        can_manage_chat=True,
        can_delete_messages=True,
        can_manage_video_chats=True,
        can_invite_users=True,
        can_pin_messages=True,
        can_manage_topics=True,
        can_change_info=False,
        can_restrict_members=False,
        can_promote_members=False,
        is_anonymous=False
    )

    text = (
        f"<blockquote>"
        f'<a href="tg://user?id={target.id}">{target.full_name}</a> ကို '
        f'<a href="tg://user?id={giver.id}">{giver.full_name}</a> က '
        f"admin ဖြစ်စေလိုက်ပါတယ်။"
        f"</blockquote>"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ---------- GROUPLIST ----------

async def grouplist(update, context):

    groups = get_list("groups")

    text = "<blockquote>Bot Groups\n"

    for g in groups:
        try:
            chat = await context.bot.get_chat(g)

            if chat.username:
                text += f'<a href="https://t.me/{chat.username}">{chat.title}</a>\n'
            else:
                text += f"{chat.title}\n"

        except:
            pass

    text += "</blockquote>"

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ---------- ANTILINK ----------

async def antilink(update, context):

    if not await is_admin(update, context):
        return

    arg = context.args[0]

    if arg == "on":
        set_bool("antilink", True)

    if arg == "off":
        set_bool("antilink", False)

    await update.message.reply_text(
        "<blockquote>Antilink Updated</blockquote>",
        parse_mode=ParseMode.HTML
    )

async def link_check(update, context):

    if not get_bool("antilink"):
        return

    txt = update.message.text

    if re.search(r"http|t.me|telegram.me", txt):
        await update.message.delete()

# ---------- FILTER ----------

async def addfilter(update, context):

    if not await is_admin(update, context):
        return

    keyword = context.args[0].lower()
    reply = " ".join(context.args[1:])

    db.filters.update_one(
        {"chat_id": update.effective_chat.id, "keyword": keyword},
        {"$set": {"reply": reply}},
        upsert=True
    )

    await update.message.reply_text(
        "<blockquote>Filter saved</blockquote>",
        parse_mode=ParseMode.HTML
    )

async def filter_reply(update, context):

    txt = update.message.text.lower()

    f = db.filters.find_one({
        "chat_id": update.effective_chat.id,
        "keyword": txt
    })

    if f:
        await update.message.reply_text(
            f"<blockquote>{f['reply']}</blockquote>",
            parse_mode=ParseMode.HTML
        )

# ---------- BROADCAST ----------

async def sendallgp(update, context):

    if update.effective_user.id != OWNER_ID:
        return

    groups = get_list("groups")
    msg = " ".join(context.args)

    for g in groups:

        try:
            await context.bot.send_message(
                g,
                f"<blockquote>{msg}</blockquote>",
                parse_mode=ParseMode.HTML
            )

            await asyncio.sleep(0.3)

        except:
            pass

# ---------- ADMIN ACTION ----------

async def admin_action(update, context):

    if not await is_admin(update, context):
        return

    cmd = update.message.text.split()[0][1:]
    target = update.message.reply_to_message.from_user

    try:

        if cmd == "mute":

            await context.bot.restrict_chat_member(
                update.effective_chat.id,
                target.id,
                permissions=ChatPermissions(can_send_messages=False)
            )

        elif cmd == "unmute":

            await context.bot.restrict_chat_member(
                update.effective_chat.id,
                target.id,
                permissions=ChatPermissions(can_send_messages=True)
            )

        elif cmd == "ban":

            await context.bot.ban_chat_member(update.effective_chat.id, target.id)

        elif cmd == "kick":

            await context.bot.ban_chat_member(update.effective_chat.id, target.id)
            await context.bot.unban_chat_member(update.effective_chat.id, target.id)

        await update.message.reply_text(
            f"<blockquote>{target.full_name} {cmd} done</blockquote>",
            parse_mode=ParseMode.HTML
        )

    except Exception as e:

        await update.message.reply_text(
            f"<blockquote>Error {e}</blockquote>",
            parse_mode=ParseMode.HTML
        )

# ---------- MAIN ----------

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(ChatMemberHandler(member_update, ChatMemberHandler.ANY_CHAT_MEMBER))

    app.add_handler(CommandHandler("save_on", save_on))
    app.add_handler(CommandHandler("save_off", save_off))

    app.add_handler(CommandHandler("addallow", addallow))
    app.add_handler(CommandHandler("allowlist", allowlist))

    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("stopbully", stopbully))
    app.add_handler(CommandHandler("bullylist", bullylist))

    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("grouplist", grouplist))

    app.add_handler(CommandHandler("antilink", antilink))

    app.add_handler(CommandHandler("filter", addfilter))

    app.add_handler(CommandHandler("sendallgp", sendallgp))

    app.add_handler(CommandHandler(["mute","unmute","ban","kick"], admin_action))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, autosave))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_reply))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_check))

    print("BOT RUNNING")

    app.run_polling()

if __name__ == "__main__":
    main()
