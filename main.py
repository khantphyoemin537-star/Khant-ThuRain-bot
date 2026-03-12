# -*- coding: utf-8 -*-
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ChatMemberHandler
from telegram.constants import ParseMode

TOKEN = '8698177279:AAGEAbRNSPoIxhfoh-Kx0BHjlsVbJvC63EA'
custom_filters = {}
BAD_WORDS = ["လီး", "စပ", "သပ", "သပ့", "စပ့", "လဥ", "ယီး", "လိ", "စောက်ပတ်", "စောက်ဖုတ်", "အဖုတ်", "ဇောက်ပတ်", "ဇောက်ဖုတ်", "လိုး", "ငါလိုး"]

async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return
    chat_id, group_name = result.chat.id, result.chat.title
    user = result.new_chat_member.user
    mention = f'<b><a href="tg://user?id={user.id}">{user.first_name}</a></b>'
    if result.old_chat_member.status in ["left", "kicked", "restricted"] and result.new_chat_member.status == "member":
        await context.bot.send_message(chat_id=chat_id, text=f"<b>ဟိတ် {mention} ရေ Dexter ThuRainᴮᵒᴰ နှင့်အတူ Adminများရဲ့ {group_name} မှ ကြိုဆိုပါတယ်။</b>", parse_mode=ParseMode.HTML)
    elif result.old_chat_member.status == "member" and result.new_chat_member.status == "left":
        await context.bot.send_message(chat_id=chat_id, text=f"<b>နှုတ်ဆက်ပါတယ် {mention} ရေ... နောက်မှပြန်တွေ့ကြမယ်နော်။</b>", parse_mode=ParseMode.HTML)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_text = update.message.text
    user_id = update.effective_user.id
    mention = f'<b><a href="tg://user?id={user_id}">{update.effective_user.first_name}</a></b>'
    group_name = update.effective_chat.title
    
    if any(word in user_text for word in BAD_WORDS):
        try:
            await update.message.delete()
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"ဟိတ် {mention}...\n<b>{group_name} ထဲတွင် ရိုင်းစိုင်းသော စကားလုံးများအား ပို့ခွင့်မပြုတော့ပါ။ နောက်နောင်ဆင်ခြင်သတိပြုပါ။</b>", parse_mode=ParseMode.HTML)
            return
        except: pass

    if user_text.lower() in custom_filters:
        await update.message.reply_text(text=f"<b>{custom_filters[user_text.lower()]}</b>", parse_mode=ParseMode.HTML)

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    await update.message.reply_text(f"<b>ထိုသူ၏ ID: <code>{target_user.id}</code></b>", parse_mode=ParseMode.HTML)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    app.run_polling()
