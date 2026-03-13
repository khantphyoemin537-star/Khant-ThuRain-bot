# -*- coding: utf-8 -*-
import logging
import re
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ChatMemberHandler
from telegram.constants import ParseMode

# 1. Bot Token
TOKEN = '8698177279:AAGEAbRNSPoIxhfoh-Kx0BHjlsVbJvC63EA'

# Data Storage
config = {
    "welcome_text": "ဟိတ် {name} ရေ Dexter ThuRainᴮᵒᴰ နှင့်အတူ Adminများရဲ့ {group} မှ ကြိုဆိုပါတယ်။",
    "goodbye_text": "နှုတ်ဆက်ပါတယ် {name} ရေ... နောက်မှပြန်တွေ့ကြမယ်နော်။",
    "welcome_enabled": True,
    "goodbye_enabled": True
}
custom_filters = {}

# --- Mention All / Call / Admins Logic (Updated with Emojis & Names) ---
async def mention_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_msg = " ".join(context.args) if context.args else "ဟိတ် အားလုံးပဲ..."
    
    try: await update.message.delete()
    except: pass

    # Admin list ကိုယူပြီး အကုန်လုံးကို tag ခေါ်ခြင်း
    members = await context.bot.get_chat_administrators(chat_id)
    
    tag_text = f"📢 <b>{user_msg}</b>\n"
    tag_text += f"━━━━━━━━━━━━━━━━━\n"
    
    count = 0
    for member in members:
        if not member.user.is_bot:
            name = member.user.first_name
            tag_text += f"✨ <a href='tg://user?id={member.user.id}'>{name}</a>\n"
            count += 1
    
    tag_text += f"━━━━━━━━━━━━━━━━━\n"
    tag_text += f"Total: {count} members tagged! 🚀"

    await context.bot.send_message(chat_id=chat_id, text=tag_text, parse_mode=ParseMode.HTML)

async def mention_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_msg = " ".join(context.args) if context.args else "Chief & Ally တို့ရေ..."
    
    try: await update.message.delete()
    except: pass

    admins = await context.bot.get_chat_administrators(chat_id)
    
    tag_text = f"🛡 <b>{user_msg}</b>\n"
    tag_text += f"⚡ <b>Admin Attention!</b>\n"
    tag_text += f"━━━━━━━━━━━━━━━━━\n"
    
    for admin in admins:
        if not admin.user.is_bot:
            tag_text += f"👑 <a href='tg://user?id={admin.user.id}'>{admin.user.first_name}</a>\n"
            
    tag_text += f"━━━━━━━━━━━━━━━━━"
    
    await context.bot.send_message(chat_id=chat_id, text=tag_text, parse_mode=ParseMode.HTML)

# --- Welcome & Goodbye ---
async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return
    chat_id, group_name = result.chat.id, result.chat.title
    user = result.new_chat_member.user
    mention = f'<b><a href="tg://user?id={user.id}">{user.first_name}</a></b>'
    if result.old_chat_member.status in ["left", "kicked", "restricted"] and result.new_chat_member.status == "member":
        if config["welcome_enabled"]:
            text = config["welcome_text"].format(name=mention, group=group_name)
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
    elif result.old_chat_member.status == "member" and result.new_chat_member.status in ["left", "kicked"]:
        if config["goodbye_enabled"]:
            text = config["goodbye_text"].format(name=mention, group=group_name)
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)

# --- Settings & Admin Tools ---
async def set_welcome_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ['administrator', 'creator']: return
    if not context.args: return
    config["welcome_enabled"] = (context.args[0].lower() == "on")
    await update.message.reply_text(f"<b>Welcome message is {'ON' if config['welcome_enabled'] else 'OFF'}.</b>", parse_mode=ParseMode.HTML)

async def set_welcome_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ['administrator', 'creator']: return
    config["welcome_text"] = " ".join(context.args)
    await update.message.reply_text("<b>Welcome text updated!</b>", parse_mode=ParseMode.HTML)

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ['administrator', 'creator'] or not update.message.reply_to_message: return
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, update.message.reply_to_message.from_user.id, ChatPermissions(can_send_messages=False))
        await update.message.reply_text("<b>Muted for security reasons.</b>", parse_mode=ParseMode.HTML)
    except: pass

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ['administrator', 'creator'] or not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True))
        await update.message.reply_text(f"<b>Unmuted! Speak up, <a href='tg://user?id={target.id}'>{target.first_name}</a>.</b>", parse_mode=ParseMode.HTML)
    except: pass

async def delete_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    is_admin = member.status in ['administrator', 'creator']
    text = update.message.text or update.message.caption or ""
    if not is_admin and re.findall(r'(https?://\S+|t\.me/\S+|www\.\S+)', text):
        await update.message.delete()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"<b>Links are not allowed.</b>", parse_mode=ParseMode.HTML)
        return
    if text.lower() in custom_filters:
        await update.message.reply_text(text=f"<b>{custom_filters[text.lower()]}</b>", parse_mode=ParseMode.HTML)

async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) >= 2:
        custom_filters[context.args[0].lower()] = " ".join(context.args[1:])
        await update.message.reply_text("<b>Filter set!</b>", parse_mode=ParseMode.HTML)

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"<b>ID: <code>{update.effective_user.id}</code></b>", parse_mode=ParseMode.HTML)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, delete_service_message))
    app.add_handler(CommandHandler(["call", "all"], mention_all))
    app.add_handler(CommandHandler("admins", mention_admins))
    app.add_handler(CommandHandler("welcome", set_welcome_status))
    app.add_handler(CommandHandler("setwelcome", set_welcome_text))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))
    app.add_handler(CommandHandler("filter", add_filter))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & (~filters.COMMAND), message_handler))
    
    print("Power Smart Bot is running with Enhanced Tagging...")
    app.run_polling(allowed_updates=["message", "chat_member"])
