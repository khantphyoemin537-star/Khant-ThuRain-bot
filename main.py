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

WARN_LIMIT = 100
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
await update.message.reply_text("Hello! Moderation bot active.")

def setup(app):
app.add_handler(CommandHandler("start", start))
from telegram.constants import ParseMode
from telegram.ext import ChatMemberHandler
from config import WELCOME_TEXT, GOODBYE_TEXT

async def member(update, context):
result = update.chat_member
user = result.new_chat_member.user
chat = result.chat
mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

if result.old_chat_member.status in ["left","kicked"] and result.new_chat_member.status == "member":  
    text = WELCOME_TEXT.format(name=mention, group=chat.title)  
    await context.bot.send_message(chat.id, text, parse_mode=ParseMode.HTML)  
elif result.new_chat_member.status in ["left","kicked"]:  
    text = GOODBYE_TEXT.format(name=mention, group=chat.title)  
    await context.bot.send_message(chat.id, text, parse_mode=ParseMode.HTML)

def setup(app):
app.add_handler(ChatMemberHandler(member, ChatMemberHandler.CHAT_MEMBER))
from telegram.ext import CommandHandler
from database.data import rules_text
from utils.admin import is_admin

async def rules(update, context):
await update.message.reply_text(rules_text)

async def setrules(update, context):
global rules_text
if not await is_admin(update, context):
return
text = " ".join(context.args)
if text:
rules_text = text
await update.message.reply_text("Rules updated")

def setup(app):
app.add_handler(CommandHandler("rules", rules))
app.add_handler(CommandHandler("setrules", setrules))
from telegram.ext import CommandHandler
from utils.admin import is_admin

async def ban(update, context):
if not await is_admin(update, context):
return
if not update.message.reply_to_message:
return

chat = update.effective_chat  
bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)  

if not bot_member.can_restrict_members:  
    await update.message.reply_text("❌ Bot မှာ ban permission မရှိပါ")  
    return  

user = update.message.reply_to_message.from_user  
await context.bot.ban_chat_member(chat.id, user.id)  
await update.message.reply_text("🚫 User banned")

def setup(app):
app.add_handler(CommandHandler("ban", ban))
from telegram import ChatPermissions
from telegram.ext import CommandHandler
from utils.admin import is_admin

async def mute(update, context):
if not await is_admin(update, context):
return
if not update.message.reply_to_message:
return

chat = update.effective_chat  
bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)  
if not bot_member.can_restrict_members:  
    await update.message.reply_text("❌ Bot မှာ mute permission မရှိပါ")  
    return  

user = update.message.reply_to_message.from_user  
await context.bot.restrict_chat_member(chat.id, user.id, ChatPermissions(can_send_messages=False))  
await update.message.reply_text("🔇 User muted")

def setup(app):
app.add_handler(CommandHandler("mute", mute))
from telegram.ext import CommandHandler
from database.data import warns
from config import WARN_LIMIT

async def warn(update, context):
if not update.message.reply_to_message:
return
user = update.message.reply_to_message.from_user
uid = user.id

warns[uid] = warns.get(uid,0)+1  

if warns[uid] >= WARN_LIMIT:  
    await context.bot.ban_chat_member(update.effective_chat.id, uid)  
    warns.pop(uid)  
    await update.message.reply_text(f"🚫 {user.first_name} banned (warn limit)")  
else:  
    await update.message.reply_text(f"⚠️ Warn {warns[uid]}/{WARN_LIMIT}")

def setup(app):
app.add_handler(CommandHandler("warn", warn))
import re
from telegram.ext import MessageHandler, filters
from utils.admin import is_admin

async def antilink(update, context):
if not update.message.text:
return
if await is_admin(update, context):
return

text = update.message.text.lower()  
if re.search(r"(https?://|t\.me|www\.)", text):  
    await update.message.delete()  
    user = update.effective_user  
    mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'  
    await context.bot.send_message(update.effective_chat.id, f"🚫 {mention} Link share လို့မရပါဘူး!", parse_mode="HTML")

def setup(app):
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, antilink))
