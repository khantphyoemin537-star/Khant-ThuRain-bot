import re
from telegram import ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ChatMemberHandler, MessageHandler, filters

# --- CONFIGURATION SECTION ---
TOKEN = "8575371720:AAE8kNulIQw27ocepXFO16aVP2Mga9mJEjg"
WELCOME_TEXT = "ဟိတ် {name} {group} မှ ကြိုဆိုပါတယ်!"
GOODBYE_TEXT = "{name} {group} ကနေထွက်သွားပါပြီ"
WARN_LIMIT = 5
warns = {}
rules_text = "Respect everyone. No spam."

# --- UTILS SECTION ---
async def is_admin(update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if update.effective_chat.type == "private":
        return True
        
    admins = await context.bot.get_chat_administrators(chat_id)  
    for admin in admins:  
        if admin.user.id == user_id:  
            return True  
    return False

# --- HANDLERS SECTION ---

# Start Command
async def start(update, context):
    text = "<blockquote>Hello! Moderation bot active.\n/rules ကိုနှိပ်ပြီး စည်းကမ်းချက်များဖတ်ပါ။</blockquote>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# Welcome/Goodbye
async def member_handler(update, context):
    result = update.chat_member
    user = result.new_chat_member.user
    chat = result.chat
    mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

    if result.old_chat_member.status in ["left", "kicked"] and result.new_chat_member.status == "member":  
        raw_text = WELCOME_TEXT.format(name=mention, group=chat.title)
        text = f"<blockquote>{raw_text}</blockquote>"
        await context.bot.send_message(chat.id, text, parse_mode=ParseMode.HTML)  
    elif result.new_chat_member.status in ["left", "kicked"]:  
        raw_text = GOODBYE_TEXT.format(name=mention, group=chat.title)
        text = f"<blockquote>{raw_text}</blockquote>"
        await context.bot.send_message(chat.id, text, parse_mode=ParseMode.HTML)

# Rules
async def rules(update, context):
    text = f"📜 <b>Group Rules</b>\n<blockquote>{rules_text}</blockquote>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def setrules(update, context):
    global rules_text
    if not await is_admin(update, context):
        return
    text_args = " ".join(context.args)
    if text_args:
        rules_text = text_args
        await update.message.reply_text("<blockquote>✅ Rules updated!</blockquote>", parse_mode=ParseMode.HTML)

# Ban
async def ban(update, context):
    if not await is_admin(update, context):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("<blockquote>❌ Ban ချင်တဲ့သူရဲ့ message ကို reply ပြန်ပါ။</blockquote>", parse_mode=ParseMode.HTML)
        return

    chat = update.effective_chat  
    user = update.message.reply_to_message.from_user  
    try:
        await context.bot.ban_chat_member(chat.id, user.id)  
        await update.message.reply_text(f"🚫 <b>{user.first_name}</b>\n<blockquote>အဖွဲ့ထဲကနေ Ban လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"<blockquote>Error: {e}</blockquote>", parse_mode=ParseMode.HTML)

# Mute
async def mute(update, context):
    if not await is_admin(update, context):
        return
    if not update.message.reply_to_message:
        return

    chat = update.effective_chat  
    user = update.message.reply_to_message.from_user  
    try:
        await context.bot.restrict_chat_member(chat.id, user.id, ChatPermissions(can_send_messages=False))  
        await update.message.reply_text(f"🔇 <b>{user.first_name}</b>\n<blockquote>စာရိုက်ခွင့် ပိတ်လိုက်ပါပြီ (Muted)။</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"<blockquote>Error: {e}</blockquote>", parse_mode=ParseMode.HTML)

# Warn
async def warn(update, context):
    if not await is_admin(update, context):
        return
    if not update.message.reply_to_message:
        return
    
    user = update.message.reply_to_message.from_user
    uid = user.id
    warns[uid] = warns.get(uid, 0) + 1  

    if warns[uid] >= WARN_LIMIT:  
        await context.bot.ban_chat_member(update.effective_chat.id, uid)  
        warns.pop(uid)  
        await update.message.reply_text(f"🚫 <b>{user.first_name}</b>\n<blockquote>သတိပေးချက် အကြိမ်ရေပြည့်သွားသဖြင့် Ban လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)  
    else:  
        await update.message.reply_text(f"⚠️ <b>{user.first_name}</b>\n<blockquote>သတိပေးချက် ရရှိသည် - {warns[uid]}/{WARN_LIMIT}</blockquote>", parse_mode=ParseMode.HTML)

# Anti-Link
async def antilink(update, context):
    if not update.message or not update.message.text:
        return
    if await is_admin(update, context):
        return

    text = update.message.text.lower()  
    if re.search(r"(https?://|t\.me|www\.)", text):  
        try:
            await update.message.delete()  
            user = update.effective_user  
            mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'  
            await context.bot.send_message(update.effective_chat.id, f"🚫 {mention}\n<blockquote>Link share လို့မရပါဘူး!</blockquote>", parse_mode=ParseMode.HTML)
        except:
            pass

# --- MAIN APP ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    # Add Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("setrules", setrules))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(ChatMemberHandler(member_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, antilink))

    print("Bot is running with Blockquote Style...")
    app.run_polling()
