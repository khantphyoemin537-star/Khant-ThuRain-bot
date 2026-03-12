# -*- coding: utf-8 -*-
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ChatMemberHandler
from telegram.constants import ParseMode

# 1. Bot Token
TOKEN = '8698177279:AAGEAbRNSPoIxhfoh-Kx0BHjlsVbJvC63EA'

# Data Storage
custom_filters = {}
# သင်ပေးထားတဲ့ လက်ရှိအရေအတွက်ကနေ စတင်ရေတွက်ပါမယ်
message_count = 416350 

# --- Welcome & Leave Message Handler ---
async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return
    chat_id, group_name = result.chat.id, result.chat.title
    user = result.new_chat_member.user
    mention = f'<b><a href="tg://user?id={user.id}">{user.first_name}</a></b>'
    
    if result.old_chat_member.status in ["left", "kicked", "restricted"] and result.new_chat_member.status == "member":
        welcome_text = f"<b>ဟိတ် {mention} ရေ Dexter ThuRainᴮᵒᴰ နှင့်အတူ Adminများရဲ့ {group_name} မှ ကြိုဆိုပါတယ်။</b>"
        await context.bot.send_message(chat_id=chat_id, text=welcome_text, parse_mode=ParseMode.HTML)
    elif result.old_chat_member.status == "member" and result.new_chat_member.status == "left":
        leave_text = f"<b>နှုတ်ဆက်ပါတယ် {mention} ရေ... နောက်မှပြန်တွေ့ကြမယ်နော်။</b>"
        await context.bot.send_message(chat_id=chat_id, text=leave_text, parse_mode=ParseMode.HTML)

# --- Main Message Handler (Counting All Types) ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global message_count
    if not update.effective_chat: return
    
    # Message အားလုံးကို ရေတွက်ခြင်း (Text, Photo, Sticker, Video, GIF, Voice)
    message_count += 1
    group_name = update.effective_chat.title
    
    # ၁၀၀ တိုးတိုင်း Milestone ပို့ပေးခြင်း (ဥပမာ - 416400, 416500, ...)
    if message_count % 100 == 0:
        milestone_text = (
            f"<b>ဟုတ်... {group_name} မှာ "
            f"စုစုပေါင်း မက်ဆေ့ {message_count:,} ခုကို ပေးပို့ကြပြီးပါပြီ။ "
            f"ပိုပျော်စရာကောင်းတာလေးတွေ ဆက်ပြောပေးကြပါအုံး။</b>"
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=milestone_text, parse_mode=ParseMode.HTML)

    # Custom Filter (စာသားဖြစ်မှသာ အလုပ်လုပ်မည်)
    if update.message.text:
        user_text = update.message.text.lower()
        if user_text in custom_filters:
            await update.message.reply_text(text=f"<b>{custom_filters[user_text]}</b>", parse_mode=ParseMode.HTML)

# --- ID Getter Command ---
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    await update.message.reply_text(f"<b>ထိုသူ၏ ID: <code>{target_user.id}</code></b>", parse_mode=ParseMode.HTML)

# --- Add Filter Command ---
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ['administrator', 'creator']: return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("<b>အသုံးပြုပုံ - /filter [keyword] [reply]</b>", parse_mode=ParseMode.HTML)
        return
    custom_filters[args[0].lower()] = " ".join(args[1:])
    await update.message.reply_text("<b>ဟုတ်.. Filter အသစ် သတ်မှတ်လိုက်ပါပြီ။</b>", parse_mode=ParseMode.HTML)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(CommandHandler("filter", add_filter))
    
    # Filters.ALL သုံးထားလို့ GIF, Sticker, Photo အကုန်ရေတွက်ပါမယ်
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), message_handler))
    
    app.run_polling(allowed_updates=["message", "chat_member"])
