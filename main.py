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
