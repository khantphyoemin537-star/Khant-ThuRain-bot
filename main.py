# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ChatMemberHandler
from telegram.constants import ParseMode

# 1. Bot Token
TOKEN = '8698177279:AAGEAbRNSPoIxhfoh-Kx0BHjlsVbJvC63EA'

# တစ်နေ့တာအတွင်း စာပို့ပြီးသားသူများကို မှတ်ထားရန်
first_messengers = set()
current_day = datetime.now().date()

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
    
    info_text = (
        f"<b>─── USER INFORMATION ───</b>\n\n"
        f"<b>သူ/သူမ၏ ID:</b> <code>{user.id}</code>\n"
        f"<b>Name:</b> {user.first_name}\n"
        f"<b>Username:</b> @{user.username if user.username else 'None'}\n"
        f"<b>Situation:</b> {status}\n"
        f"<b>Tag:</b> {role_tag}\n"
        f"<b>Join:</b> Hidden\n\n"
        f"<b>────────────────────</b>"
    )
    await update.message.reply_text(info_text, parse_mode=ParseMode.HTML)

# --- Welcome & Leave Handler (လူဝင်/လူထွက်) ---
async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return
    chat_id, group_name = result.chat.id, result.chat.title
    user = result.new_chat_member.user
    mention = f'<b><a href="tg://user?id={user.id}">{user.first_name}</a></b>'
    
    if result.old_chat_member.status in ["left", "kicked", "restricted"] and result.new_chat_member.status == "member":
        welcome_text = f"<b>ဟိတ် {mention} ရေ Dexter ThuRainᴮᵒᴰ နှင့်အတူ Adminများရဲ့ {group_name} မှ ကြိုဆိုပါတယ်။</b>"
        await context.bot.send_message(chat_id=chat_id, text=welcome_text, parse_mode=ParseMode.HTML)
    elif result.old_chat_member.status == "member" and result.new_chat_member.status in ["left", "kicked"]:
        leave_text = f"<b>နှုတ်ဆက်ပါတယ် {mention} ရေ... နောက်မှပြန်တွေ့ကြမယ်နော်။</b>"
        await context.bot.send_message(chat_id=chat_id, text=leave_text, parse_mode=ParseMode.HTML)

# --- Link Check & First Message Handler ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global first_messengers, current_day
    if not update.effective_chat or not update.effective_user or not update.message: return
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    mention = f'<b><a href="tg://user?id={user_id}">{user_name}</a></b>'
    
    # --- 1. Link Protection (Admin မဟုတ်လျှင် ဖျက်မည်) ---
    text = update.message.text or update.message.caption or ""
    # Link ပါမပါ စစ်ဆေးရန် Regular Expression
    urls = re.findall(r'(https?://\S+|t\.me/\S+|www\.\S+)', text)
    
    if urls:
        member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        if member.status not in ['administrator', 'creator']:
            await update.message.delete()
            warning_msg = f"<b>ဟိတ် {mention}... Group ထဲမှာ Link ပို့ခြင်းကို ခွင့်မပြုပါဘူးဗျ။</b>"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=warning_msg, parse_mode=ParseMode.HTML)
            return # Link ဖြစ်လျှင် အောက်က First Message Logic ကို ဆက်မလုပ်တော့ပါ

    # --- 2. First Message of the Day Logic ---
    today = datetime.now().date()
    if today != current_day:
        first_messengers.clear()
        current_day = today

    if text and not text.startswith('.'):
        if user_id not in first_messengers:
            first_messengers.add(user_id)
            welcome_msg = (
                f"<b>ဟိတ်...မင်္ဂလာပါဗျ ဒါက ဒီကသူငယ်ချင်းလေး {mention} ဒီနေ့ရဲ့ ပထမဆုံးစာလေးပဲနော်။"
                f"ခင်တယ်၊အလေးထားတယ်၊စကားအမြဲဝင်ပြောပေးပါအုံး။</b>"
            )
            await update.message.reply_text(text=welcome_msg, parse_mode=ParseMode.HTML)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(MessageHandler(filters.Regex(r'^\.info$'), info_command))
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & (~filters.COMMAND), message_handler))
    
    app.run_polling(allowed_updates=["message", "chat_member"])
