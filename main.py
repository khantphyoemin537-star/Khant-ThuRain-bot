# -*- coding: utf-8 -*-
import logging
import re
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ChatMemberHandler
from telegram.constants import ParseMode

# 1. Bot Token
TOKEN = '8698177279:AAGEAbRNSPoIxhfoh-Kx0BHjlsVbJvC63EA'

# Data Storage
custom_filters = {}

# --- Welcome & Goodbye ---
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
        goodbye_text = f"<b>နှုတ်ဆက်ပါတယ် {mention} ရေ... နောက်မှပြန်တွေ့ကြမယ်နော်။</b>"
        await context.bot.send_message(chat_id=chat_id, text=goodbye_text, parse_mode=ParseMode.HTML)

# --- Mute Command ---
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_admin = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if user_admin.status not in ['administrator', 'creator']: return

    if not update.message.reply_to_message:
        await update.message.reply_text("<b>ကျေးဇူးပြု၍ Mute လုပ်လိုသူကို Reply ပြန်ပြီး Command ရိုက်ပါ။</b>", parse_mode=ParseMode.HTML)
        return

    target_user = update.message.reply_to_message.from_user
    permissions = ChatPermissions(can_send_messages=False)
    
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target_user.id, permissions)
        await update.message.reply_text("<b>တစ်ခြားသူများအား အနှောင့်အယှက်မဖြစ်စေရန် muteလိုက်ပါတယ်။</b>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"<b>အမှားအယွင်းရှိပါသည်: {e}</b>", parse_mode=ParseMode.HTML)

# --- Unmute Command ---
async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_admin = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if user_admin.status not in ['administrator', 'creator']: return

    if not update.message.reply_to_message:
        await update.message.reply_text("<b>ကျေးဇူးပြု၍ Unmute လုပ်လိုသူကို Reply ပြန်ပြီး Command ရိုက်ပါ။</b>", parse_mode=ParseMode.HTML)
        return

    target_user = update.message.reply_to_message.from_user
    mention = f'<b><a href="tg://user?id={target_user.id}">{target_user.first_name}</a></b>'
    permissions = ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True)
    
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target_user.id, permissions)
        await update.message.reply_text(f"<b>ဟုတ်ပြီ {mention}၊ ပြန်စကားပြောပါ။</b>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"<b>အမှားအယွင်းရှိပါသည်: {e}</b>", parse_mode=ParseMode.HTML)

# --- Service Message Deletion ---
async def delete_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass

# --- Message Handler ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    is_admin = member.status in ['administrator', 'creator']
    user_text = update.message.text or update.message.caption or ""
    
    if not is_admin:
        urls = re.findall(r'(https?://\S+|t\.me/\S+|www\.\S+)', user_text)
        if urls:
            try:
                mention = f'<b><a href="tg://user?id={update.effective_user.id}">{update.effective_user.first_name}</a></b>'
                await update.message.delete()
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"<b>ဟိတ် {mention}...\nဒီ {update.effective_chat.title} ထဲတွင် Link share ခြင်းများကို ခွင့်မပြုပါ။</b>", parse_mode=ParseMode.HTML)
                return
            except: pass

    keyword = user_text.lower()
    if keyword in custom_filters:
        await update.message.reply_text(text=f"<b>{custom_filters[keyword]}</b>", parse_mode=ParseMode.HTML)

# --- Filters & ID ---
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ['administrator', 'creator']: return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("<b>အသုံးပြုပုံ - /filter [keyword] [reply]</b>", parse_mode=ParseMode.HTML)
        return
    keyword = args[0].lower()
    custom_filters[keyword] = " ".join(args[1:])
    await update.message.reply_text("<b>ဟုတ်..ခန့်သူရိန်မှ (Reply) များ သတ်မှတ်လိုက်ပါသေးတယ်။</b>", parse_mode=ParseMode.HTML)

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"<b>သူ/သူမ၏ ID: <code>{update.effective_user.id}</code></b>", parse_mode=ParseMode.HTML)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, delete_service_message))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))
    app.add_handler(CommandHandler("filter", add_filter))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & (~filters.COMMAND), message_handler))
    app.run_polling(allowed_updates=["message", "chat_member"])
