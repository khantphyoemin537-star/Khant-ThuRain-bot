# -*- coding: utf-8 -*-
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ChatMemberHandler
from telegram.constants import ParseMode

# 1. Bot Token
TOKEN = '8698177279:AAGEAbRNSPoIxhfoh-Kx0BHjlsVbJvC63EA'

# --- .info Command Logic ---
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_msg = update.message.reply_to_message
    user = target_msg.from_user if target_msg else update.effective_user
    chat = update.effective_chat
    
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        status = member.status.capitalize()
    except:
        status = "User"

    role_tag = "Member"
    if member.status == 'creator':
        role_tag = "Founder • Dexter"
    elif member.status == 'administrator':
        role_tag = "Chief • BoD"
    
    # Join Date ကို Hidden လုပ်ထားသည်
    info_text = (
        f"<b>─── USER INFORMATION ───</b>\n\n"
        f"<b>ID:</b> <code>{user.id}</code>\n"
        f"<b>Name:</b> {user.first_name}\n"
        f"<b>Username:</b> @{user.username if user.username else 'None'}\n"
        f"<b>Situation:</b> {status}\n"
        f"<b>Tag:</b> {role_tag}\n"
        f"<b>Join:</b> Hidden\n\n"
        f"<b>────────────────────</b>"
    )
    await update.message.reply_text(info_text, parse_mode=ParseMode.HTML)

# --- Welcome Message Handler ---
async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return
    chat_id, group_name = result.chat.id, result.chat.title
    user = result.new_chat_member.user
    mention = f'<b><a href="tg://user?id={user.id}">{user.first_name}</a></b>'
    
    if result.old_chat_member.status in ["left", "kicked", "restricted"] and result.new_chat_member.status == "member":
        welcome_text = f"<b>ဟိတ် {mention} ရေ Dexter ThuRainᴮᵒᴰ နှင့်အတူ Adminများရဲ့ {group_name} မှ ကြိုဆိုပါတယ်။</b>"
        await context.bot.send_message(chat_id=chat_id, text=welcome_text, parse_mode=ParseMode.HTML)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(MessageHandler(filters.Regex(r'^\.info$'), info_command))
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.CHAT_MEMBER))
    
    app.run_polling(allowed_updates=["message", "chat_member"])
