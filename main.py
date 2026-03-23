# -*- coding: utf-8 -*-

import re
import logging
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

# --- ပြင်ဆင်ပြီးသား TOKEN ---
TOKEN = "8698177279:AAEVFPPMfkm-m7aiWRsIo_n-pK0vOvmZegg"

# Logging (Error တက်ရင် ကြည့်လို့ရအောင်)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

config = {
    "welcome_text": "ဟိတ် {name} အထာကျတဲ့ {group} ကနေ ကြိုဆိုလိုက်ပါတယ်!",
    "goodbye_text": "​Off to new adventures? Go get 'em! 🚀 It’s been real having {name} in the squad. Take it easy and stay awesome. See ya when I see ya! ",
    "warn_limit": 10
}

rules_text = "အချင်းချင်း လေးစားမှုရှိပါ"
warns = {}

# -----------------
# ADMIN CHECK
# -----------------
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        return False
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except:
        return False

# -----------------
# CLEAN SERVICE
# -----------------
async def clean_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except:
        pass

# -----------------
# WELCOME / GOODBYE
# -----------------
async def chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return
    
    user = result.new_chat_member.user
    chat = result.chat
    mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

    if result.old_chat_member.status in ["left", "kicked"] and result.new_chat_member.status == "member":
        text = config["welcome_text"].format(name=mention, group=chat.title)
        await context.bot.send_message(chat.id, text, parse_mode=ParseMode.HTML)
    elif result.new_chat_member.status in ["left", "kicked"]:
        text = config["goodbye_text"].format(name=mention, group=chat.title)
        await context.bot.send_message(chat.id, text, parse_mode=ParseMode.HTML)

# -----------------
# RULES
# -----------------
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📜 Group Rules:\n\n{rules_text}")

async def setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global rules_text
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin only")
        return
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Example: /setrules No spam")
        return
    rules_text = text
    await update.message.reply_text("✅ Rules updated")

# -----------------
# MODERATION
# -----------------
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message:
        return
    user = update.message.reply_to_message.from_user
    uid = user.id
    warns[uid] = warns.get(uid, 0) + 1
    if warns[uid] >= config["warn_limit"]:
        await context.bot.ban_chat_member(update.effective_chat.id, uid)
        await update.message.reply_text(f"🚫 {user.first_name} banned (warn limit reached)")
        warns.pop(uid, None)
    else:
        await update.message.reply_text(f"⚠️ Warn {warns[uid]}/{config['warn_limit']}")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message:
        return
    user = update.message.reply_to_message.from_user
    await context.bot.restrict_chat_member(update.effective_chat.id, user.id, ChatPermissions(can_send_messages=False))
    await update.message.reply_text("🔇 mute လိုက်ပါတယ်")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message:
        return
    user = update.message.reply_to_message.from_user
    await context.bot.ban_chat_member(update.effective_chat.id, user.id)
    await update.message.reply_text("🚫 ban လိုက်ပါပြီ")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message:
        return
    user = update.message.reply_to_message.from_user
    await context.bot.ban_chat_member(update.effective_chat.id, user.id)
    await context.bot.unban_chat_member(update.effective_chat.id, user.id)
    await update.message.reply_text("👢 ထုတ်ပယ်လိုက်ပါတယ်")

async def call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    admins = await context.bot.get_chat_administrators(update.effective_chat.id)
    text = "📢 Admin Attention!\n"
    for admin in admins:
        if not admin.user.is_bot:
            text += f"<a href='tg://user?id={admin.user.id}'>.</a>"
    await context.bot.send_message(update.effective_chat.id, text, parse_mode=ParseMode.HTML)

# -----------------
# ANTI LINK
# -----------------
async def anti_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or await is_admin(update, context):
        return
    if re.search(r"(https?://|t\.me|telegram\.me|www\.)", update.message.text.lower()):
        try:
            await update.message.delete()
            mention = f'<a href="tg://user?id={update.effective_user.id}">{update.effective_user.first_name}</a>'
            await context.bot.send_message(update.effective_chat.id, f"🚫 {mention} Link share လို့မရပါဘူး", parse_mode="HTML")
        except:
            pass

# -----------------
# MAIN
# -----------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(ChatMemberHandler(chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, clean_service))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("setrules", setrules))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler(["all", "call"], call))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_link))

    print("Bot Running...")
    # Koyeb/Railway အတွက် အဓိက လိုအပ်ချက်ဖြစ်တဲ့ allowed_updates ကို ထည့်ပေးထားပါတယ်
    app.run_polling(allowed_updates=["message", "chat_member", "chat_member"])

