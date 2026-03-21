# -*- coding: utf-8 -*-

import re
from telegram import Update, ChatPermissions
from telegram.ext import (
ApplicationBuilder,
CommandHandler,
MessageHandler,
filters,
ContextTypes,
ChatMemberHandler
)
from telegram.constants import ParseMode

TOKEN = "8698177279:AAEVFPPMfkm-m7aiWRsIo_n-pK0vOvmZegg"

config = {
"welcome_text": " ဟိတ် {name} {group} မှ ကြိုဆိုလိုက်ပါတယ်",
"goodbye_text": " ဟုတ် {name} {group} မှ ထွက်ခွာသွားပါပြီ",
"warn_limit": 10
}

rules_text = "အချင်းချင်း လေးစားမှုရှိပါ"
warns = {}

# -----------------
# ADMIN CHECK
# -----------------

async def is_admin(update, context):

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    admins = await context.bot.get_chat_administrators(chat_id)

    for admin in admins:
        if admin.user.id == user_id:
            return True

    return False

# -----------------
# CLEAN SERVICE
# -----------------

async def clean_service(update, context):

    try:
        await update.message.delete()
    except:
        pass

# -----------------
# WELCOME / GOODBYE
# -----------------

async def chat_member(update, context):

    result = update.chat_member
    user = result.new_chat_member.user
    chat = result.chat

    chat_id = chat.id
    group = chat.title

    mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

    if result.old_chat_member.status in ["left","kicked"] and result.new_chat_member.status == "member":

        text = config["welcome_text"].format(
        name=mention,
        group=group
        )

        await context.bot.send_message(
        chat_id,
        text,
        parse_mode=ParseMode.HTML
        )

    elif result.new_chat_member.status in ["left","kicked"]:

        text = config["goodbye_text"].format(
        name=mention,
        group=group
        )

        await context.bot.send_message(
        chat_id,
        text,
        parse_mode=ParseMode.HTML
        )

# -----------------
# RULES
# -----------------

async def rules(update, context):

    await update.message.reply_text(
    f"📜 Group Rules:\n\n{rules_text}"
    )

async def setrules(update, context):

    global rules_text

    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin only")
        return

    text = " ".join(context.args)

    if not text:
        await update.message.reply_text(
        "Example:\n/setrules No spam No link"
        )
        return

    rules_text = text

    await update.message.reply_text("✅ Rules updated")

# -----------------
# WARN
# -----------------

async def warn(update, context):

    if not await is_admin(update, context):
        return

    if not update.message.reply_to_message:
        return

    user = update.message.reply_to_message.from_user
    uid = user.id

    warns[uid] = warns.get(uid,0) + 1

    if warns[uid] >= config["warn_limit"]:

        await context.bot.ban_chat_member(
        update.effective_chat.id,
        uid
        )

        await update.message.reply_text(
        f"{user.first_name} banned (warn limit reached)"
        )

        warns.pop(uid)

    else:

        await update.message.reply_text(
        f"⚠️ Warn {warns[uid]}/{config['warn_limit']}"
        )

# -----------------
# MUTE
# -----------------

async def mute(update, context):

    if not await is_admin(update, context):
        return

    if not update.message.reply_to_message:
        return

    user = update.message.reply_to_message.from_user

    await context.bot.restrict_chat_member(
    update.effective_chat.id,
    user.id,
    ChatPermissions(can_send_messages=False)
    )

    await update.message.reply_text("မသင့်လျော်သော message/mediaများ ပို့သည့်အတွက် muteလိုက်ပါတယ်")

# -----------------
# BAN
# -----------------

async def ban(update, context):

    if not await is_admin(update, context):
        return

    if not update.message.reply_to_message:
        return

    user = update.message.reply_to_message.from_user

    await context.bot.ban_chat_member(
    update.effective_chat.id,
    user.id
    )

    await update.message.reply_text("🚫 ban လိုက်ပါပြီ")

# -----------------
# KICK
# -----------------

async def kick(update, context):

    if not await is_admin(update, context):
        return

    if not update.message.reply_to_message:
        return

    user = update.message.reply_to_message.from_user

    await context.bot.ban_chat_member(
    update.effective_chat.id,
    user.id
    )

    await context.bot.unban_chat_member(
    update.effective_chat.id,
    user.id
    )

    await update.message.reply_text("ထုတ်ပယ်လိုက်ပါတယ်")

# -----------------
# CALL ADMINS
# -----------------

async def call(update, context):

    if not await is_admin(update, context):
        return

    chat_id = update.effective_chat.id

    admins = await context.bot.get_chat_administrators(chat_id)

    text = "📢 Admin Attention!\n"

    for admin in admins:

        if not admin.user.is_bot:

            text += f"<a href='tg://user?id={admin.user.id}'>.</a>"

    await context.bot.send_message(
    chat_id,
    text,
    parse_mode=ParseMode.HTML
    )

# -----------------
# ANTI LINK
# -----------------

async def anti_link(update, context):

    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()

    pattern = r"(https?://|t\.me|telegram\.me|www\.)"

    if re.search(pattern, text):

        try:
            await update.message.delete()
        except:
            pass

        user = update.effective_user

        mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

        await context.bot.send_message(
        update.effective_chat.id,
        f"🚫 {mention} Link မပို့ပါနဲ့",
        parse_mode="HTML"
        )

# -----------------
# MAIN
# -----------------

if __name__ == "__main__":

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(ChatMemberHandler(chat_member, ChatMemberHandler.CHAT_MEMBER))

    app.add_handler(MessageHandler(
    filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER,
    clean_service
    ))

    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("setrules", setrules))

    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("kick", kick))

    app.add_handler(CommandHandler(["all","call"], call))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_link))

    print("Bot Running...")

    app.run_polling()
