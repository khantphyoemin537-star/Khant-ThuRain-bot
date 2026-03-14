# -*- coding: utf-8 -*-
import logging
import re
import asyncio
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ChatMemberHandler
from telegram.constants import ParseMode

# 1. Bot Token
TOKEN = '8698177279:AAGEAbRNSPoIxhfoh-Kx0BHjlsVbJvC63EA'

# Data Storage
config = {
    "welcome_text": "မင်္ဂလာပါ {name} ရေ... Group မှ ကြိုဆိုပါတယ်ဗျာ။",
    "goodbye_text": "နှုတ်ဆက်ပါတယ် {name} ရေ... နောက်မှပြန်တွေ့ကြမယ်နော်။",
    "ban_text": "မင်္ဂလာပါ {mention} တားမြစ်ထားသောစကားလုံးများပါနေသောကြောင့် စာဖျက်ချလိုက်ပါတယ်။စိတ်မရှိပါနဲ့ဗျ။",
    "reminder_text": "သူငယ်ချင်းတို့ နွေးထွေးမှုအပြည့်နဲ့ခင်မင်စွာစကားပြောနေကြတာကို မြင်ရတာ ကြည်နူးမိပါတယ်ခင်ဗျ။",
    "reminder_interval": 1200, 
    "banned_words": ["badword1", "badword2"] 
}

# --- Service Messages ဖျက်ရန် (Error ပြင်ဆင်ချက်) ---
async def delete_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except:
        pass

# --- Tag All Logic (၅၀ ယောက်စီ ခွဲခေါ်ခြင်း) ---
async def mention_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_msg = " ".join(context.args) if context.args else "ဟိတ်... အားလုံးပဲ လာကြဦး။"
    try: await update.message.delete()
    except: pass
    all_admins = await context.bot.get_chat_administrators(chat_id)
    members = [f"<a href='tg://user?id={a.user.id}'>\u200b</a>" for a in all_admins if not a.user.is_bot]
    for i in range(0, len(members), 50):
        chunk = members[i:i+50]
        tag_text = f"📢 {user_msg}\n" + "".join(chunk)
        await context.bot.send_message(chat_id=chat_id, text=tag_text, parse_mode=ParseMode.HTML)

async def mention_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    admins = await context.bot.get_chat_administrators(chat_id)
    tag_text = "🛡 <b>Admins Attention!</b>\n\n"
    for admin in admins:
        if not admin.user.is_bot:
            tag_text += f"👑 <a href='tg://user?id={admin.user.id}'>{admin.user.first_name}</a>\n"
    await context.bot.send_message(chat_id=chat_id, text=tag_text, parse_mode=ParseMode.HTML)

# --- Welcome & Goodbye ---
async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    chat_id = result.chat.id
    user = result.new_chat_member.user
    mention = f'<b><a href="tg://user?id={user.id}">{user.first_name}</a></b>'
    if result.old_chat_member.status in ["left", "kicked", "restricted"] and result.new_chat_member.status == "member":
        text = config["welcome_text"].format(name=mention)
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
    elif result.old_chat_member.status == "member" and result.new_chat_member.status in ["left", "kicked"]:
        text = config["goodbye_text"].format(name=mention)
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)

async def message_filter_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text.lower()
    if "/closed" in text:
        await update.message.delete()
        return
    if any(word in text for word in config["banned_words"]):
        await update.message.delete()
        mention = f'<a href="tg://user?id={update.effective_user.id}">{update.effective_user.first_name}</a>'
        ban_notice = config["ban_text"].format(mention=mention)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=ban_notice, parse_mode=ParseMode.HTML)

# --- Reminder System ---
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=context.job.chat_id, text=config["reminder_text"])

async def set_reminder_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    time_val = context.args[0]
    seconds = int(time_val[:-1]) * 60 if 'm' in time_val else int(time_val[:-1]) * 3600 if 'h' in time_val else 1200
    config["reminder_interval"] = seconds
    jobs = context.job_queue.get_jobs_by_name(str(update.effective_chat.id))
    for j in jobs: j.schedule_removal()
    context.job_queue.run_repeating(send_reminder, interval=seconds, first=seconds, chat_id=update.effective_chat.id, name=str(update.effective_chat.id))
    await update.message.reply_text(f"✅ Reminder set to {time_val}.")

# --- Setup Commands ---
async def set_texts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text.split()[0][1:]
    val = " ".join(context.args)
    if val:
        if cmd == "setwelcome": config["welcome_text"] = val
        elif cmd == "setgoodbye": config["goodbye_text"] = val
        elif cmd == "setban": config["ban_text"] = val
        elif cmd == "setremindermsg": config["reminder_text"] = val
        await update.message.reply_text(f"✅ {cmd} updated.")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        await context.bot.restrict_chat_member(update.effective_chat.id, update.message.reply_to_message.from_user.id, ChatPermissions(can_send_messages=False))
        await update.message.reply_text("မသင့်လျော်သောစာများ/စတေကာများပို့သည့်အတွက် muteလိုက်ပါတယ်။")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, delete_service_message))
    app.add_handler(CommandHandler(["all", "call"], mention_all))
    app.add_handler(CommandHandler("admins", mention_admins))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler(["setwelcome", "setgoodbye", "setban", "setremindermsg"], set_texts))
    app.add_handler(CommandHandler("setremindertime", set_reminder_timer))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_filter_logic))
    print("Bot is running...")
    app.run_polling(allowed_updates=["message", "chat_member"])
