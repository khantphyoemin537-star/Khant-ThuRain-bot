import re
import asyncio
from telegram import ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    ChatMemberHandler, 
    MessageHandler, 
    filters,
    ContextTypes
)

# --- CONFIGURATION ---
# Bot Token များစာရင်း
TOKENS = [
    "8575371720:AAE8kNulIQw27ocepXFO16aVP2Mga9mJEjg", # Bot 1
    "8698177279:AAEVFPPMfkm-m7aiWRsIo_n-pK0vOvmZegg"  # Bot 2
]

WELCOME_TEXT = "ဟိတ် {name} {group} မှ ကြိုဆိုပါတယ်!"
GOODBYE_TEXT = "{name} {group} ကနေထွက်သွားပါပြီ"
WARN_LIMIT = 5
warns = {}
rules_text = "Respect everyone. No spam."

# --- UTILS ---
async def is_admin(update, context):
    if not update.effective_chat or update.effective_chat.type == "private":
        return True
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        admins = await context.bot.get_chat_administrators(chat_id)  
        return any(admin.user.id == user_id for admin in admins)
    except:
        return False

# --- HANDLERS ---
async def start(update, context):
    text = "<blockquote>Hello! Moderation bot active.\n/rules ကိုနှိပ်ပြီး စည်းကမ်းချက်များဖတ်ပါ။</blockquote>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def member_handler(update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    chat = result.chat
    if result.old_chat_member.status in ["left", "kicked", "none"] and \
       result.new_chat_member.status in ["member", "administrator"]:
        user = result.new_chat_member.user
        mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
        raw_text = WELCOME_TEXT.format(name=mention, group=chat.title)
        await context.bot.send_message(chat.id, f"<blockquote>{raw_text}</blockquote>", parse_mode=ParseMode.HTML)
    elif result.new_chat_member.status in ["left", "kicked"]:
        user = result.old_chat_member.user
        mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
        raw_text = GOODBYE_TEXT.format(name=mention, group=chat.title)
        await context.bot.send_message(chat.id, f"<blockquote>{raw_text}</blockquote>", parse_mode=ParseMode.HTML)

async def rules(update, context):
    text = f"📜 <b>Group Rules</b>\n<blockquote>{rules_text}</blockquote>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def setrules(update, context):
    global rules_text
    if not await is_admin(update, context): return
    text_args = " ".join(context.args)
    if text_args:
        rules_text = text_args
        await update.message.reply_text("<blockquote>✅ Rules updated!</blockquote>", parse_mode=ParseMode.HTML)

async def ban(update, context):
    if not await is_admin(update, context) or not update.message.reply_to_message: return
    chat, user = update.effective_chat, update.message.reply_to_message.from_user  
    try:
        await context.bot.ban_chat_member(chat.id, user.id)  
        await update.message.reply_text(f"🚫 <b>{user.first_name}</b>\n<blockquote>Ban လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"<blockquote>Error: {e}</blockquote>", parse_mode=ParseMode.HTML)

async def antilink(update, context):
    if not update.message or not update.message.text or await is_admin(update, context): return
    if re.search(r"(https?://|t\.me|www\.)", update.message.text.lower()):  
        try:
            await update.message.delete()
            mention = f'<a href="tg://user?id={update.effective_user.id}">{update.effective_user.first_name}</a>'
            await context.bot.send_message(update.effective_chat.id, f"🚫 {mention}\n<blockquote>Link share လို့မရပါဘူး!</blockquote>", parse_mode=ParseMode.HTML)
        except: pass

# --- BOT RUNNER FUNCTION ---
async def run_bot(token):
    app = ApplicationBuilder().token(token).build()
    
    # Add Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("setrules", setrules))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(ChatMemberHandler(member_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), antilink))

    print(f"Bot with token ...{token[-5:]} is starting...")
    
    # Initialize and Start
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=["message", "chat_member"])
    
    # Keep it running
    while True:
        await asyncio.sleep(3600)

async def main():
    # Bot နှစ်ခုလုံးကို Task အနေနဲ့ တစ်ပြိုင်နက် Run ခိုင်းခြင်း
    tasks = [run_bot(token) for token in TOKENS]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bots stopped.")
