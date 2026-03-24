# -*- coding: utf-8 -*-
from telegram.ext import ApplicationBuilder
from config import TOKEN

from handlers import start, welcome, rules
from modules import ban, mute, warn, antilink

app = ApplicationBuilder().token(TOKEN).build()

start.setup(app)
welcome.setup(app)
rules.setup(app)

ban.setup(app)
mute.setup(app)
warn.setup(app)
antilink.setup(app)

print("Bot Running...")

app.run_polling()
TOKEN = "8575371720:AAE8kNulIQw27ocepXFO16aVP2Mga9mJEjg"

WELCOME_TEXT = "ဟိတ် {name} {group} မှ ကြိုဆိုပါတယ်!"
GOODBYE_TEXT = "{name} {group} ကနေထွက်သွားပါပြီ"

WARN_LIMIT = 20
warns = {}

rules_text = "Respect everyone. No spam."
async def is_admin(update, context):

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    admins = await context.bot.get_chat_administrators(chat_id)

    for admin in admins:
        if admin.user.id == user_id:
            return True

    return False
from telegram.ext import CommandHandler

async def start(update, context):

    await update.message.reply_text(
        "Hello! Moderation bot active."
    )

def setup(app):

    app.add_handler(CommandHandler("start", start))

