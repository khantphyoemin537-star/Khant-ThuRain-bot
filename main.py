# -*- coding: utf-8 -*-
import logging
import re
import asyncio
# --- ဒီအပိုင်းက အရေးကြီးဆုံးပါ (Import လုပ်ခြင်း) ---
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ChatMemberHandler
from telegram.constants import ParseMode

# 1. Bot Token
TOKEN = '8698177279:AAGEAbRNSPoIxhfoh-Kx0BHjlsVbJvC63EA'

# Data Storage
config = {
    "welcome_text": "မင်္ဂလာပါ {name} ... {Group} မှ ကြိုဆိုပါတယ်ဗျ။",
    "goodbye_text": "နှုတ်ဆက်ပါတယ် {name} ... နောက်မှပြန်တွေ့ကြမယ်",
    "ban_text": "မင်္ဂလာပါ {mention} တားမြစ်ထားသောစကားလုံးများပါနေသောကြောင့် စာဖျက်ချလိုက်ပါတယ်။စိတ်မရှိပါနဲ့ဗျ။",
    "mute_text": "မသင့်လျော်သောစာများ/စတေကာများပို့သည့်အတွက် muteလိုက်ပါတယ်။",
    "reminder_text": "သူငယ်ချင်းတို့ နွေးထွေးမှုအပြည့်နဲ့ခင်မင်စွာစကားပြောနေကြတာကို မြင်ရတာ ကြည်နူးမိပါတယ်ခင်ဗျ။နောက်လည်းခင်ခင်မင်မင်နေကြမယ်နော်",
    "reminder_interval": 1200, 
    "banned_words": ["လီး", "လိုး"] 
}

# --- Service & Filter Logics ---
async def delete_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass

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

# --- Reminder Functions ---
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=context.job.chat_id, text=config["reminder_text"])

async def reminder_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    interval = config["reminder_interval"]
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs: job.schedule_removal()
    context.job_queue.run_repeating(send_reminder, interval=interval, first=interval, chat_id=chat_id, name=str(chat_id))
    await update.message.reply_text("ခန့်သူရိန်က 🔔 Reminder စနစ်ကို ဖွင့်လိုက်ပါပြီ။")

async def reminder_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs: job.schedule_removal()
    await update.message.reply_text("ခန့်သူရိန်က 🔕 Reminder စနစ်ကို ပိတ်လိုက်ပါပြီ။")

# --- Management Functions ---
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        try:
            await context.bot.restrict_chat_member(update.effective_chat.id, update.message.reply_to_message.from_user.id, ChatPermissions(can_send_messages=False))
            await update.message.reply_text(config["mute_text"])
        except Exception as e: await update.message.reply_text(f"Error: {e}")

async def set_texts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text.split()[0][1:]
    val = " ".join(context.args)
    if val:
        if cmd == "setwelcome": config["welcome_text"] = val
        elif cmd == "setgoodbye": config["goodbye_text"] = val
        elif cmd == "setban": config["ban_text"] = val
        elif cmd == "setremindermsg": config["reminder_text"] = val
        elif cmd == "setmuteword": config["mute_text"] = val
        await update.message.reply_text(f"✅ {cmd} updated.")

# --- Tag All & Chat Member Logic (မူလအတိုင်း) ---
async def mention_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_msg = " ".join(context.args) if context.args else "ဟိတ်...သူငယ်ချင်းတို့ လာကြဦး။"
    all_admins = await context.bot.get_chat_administrators(chat_id)
    members = [f"<a href='tg://user?id={a.user.id}'>\u200b</a>" for a in all_admins if not a.user.is_bot]
    for i in range(0, len(members), 50):
        chunk = members[i:i+50]
        await context.bot.send_message(chat_id=chat_id, text=f"📢 {user_msg}\n" + "".join(chunk), parse_mode=ParseMode.HTML)

async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    chat_id = result.chat.id
    user = result.new_chat_member.user
    mention = f'<b><a href="tg://user?id={user.id}">{user.first_name}</a></b>'
    if result.old_chat_member.status in ["left", "kicked", "restricted"] and result.new_chat_member.status == "member":
        await context.bot.send_message(chat_id=chat_id, text=config["welcome_text"].format(name=mention), parse_mode=ParseMode.HTML)

# --- Main Runner ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, delete_service_message))
    app.add_handler(CommandHandler(["all", "call"], mention_all))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("reminderon", reminder_on))
    app.add_handler(CommandHandler("reminderoff", reminder_off))
    app.add_handler(CommandHandler(["setwelcome", "setgoodbye", "setban", "setremindermsg", "setmuteword"], set_texts))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_filter_logic))
    
    print("Bot is running...")
    app.run_polling(allowed_updates=["message", "chat_member"])
