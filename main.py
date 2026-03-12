# -*- coding: utf-8 -*-
import logging
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ChatMemberHandler
from telegram.constants import ParseMode

# 1. Bot Token
TOKEN = '8698177279:AAGEAbRNSPoIxhfoh-Kx0BHjlsVbJvC63EA'

# Data Storage (Filter များအတွက်)
custom_filters = {}

# 2. Welcome & Goodbye (လူဝင်/လူထွက် နှုတ်ဆက်ခြင်း)
async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result:
        return

    chat_id = result.chat.id
    group_name = result.chat.title
    user = result.new_chat_member.user
    mention = f'<b><a href="tg://user?id={user.id}">{user.first_name}</a></b>'

    # လူသစ်ဝင်လာလျှင်
    if result.old_chat_member.status in ["left", "kicked", "restricted"] and result.new_chat_member.status == "member":
        welcome_text = f"<b>ဟိတ် {mention} ရေ Dexter ThuRainᴮᵒᴰ နှင့်အတူ Adminများရဲ့ {group_name} မှ ကြိုဆိုပါတယ်။</b>"
        await context.bot.send_message(chat_id=chat_id, text=welcome_text, parse_mode=ParseMode.HTML)

    # လူထွက်သွားလျှင်
    elif result.old_chat_member.status == "member" and result.new_chat_member.status in ["left", "kicked"]:
        goodbye_text = f"<b>နှုတ်ဆက်ပါတယ် {mention} ရေ... နောက်မှပြန်တွေ့ကြမယ်နော်။</b>"
        await context.bot.send_message(chat_id=chat_id, text=goodbye_text, parse_mode=ParseMode.HTML)

# 3. Service Message Deletion (Joined/Left Service Message များဖျက်ရန်)
async def delete_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except:
        pass

# 4. Message Handler (Link Blocker & Filter System)
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    
    # Admin ဟုတ်မဟုတ် စစ်ဆေးခြင်း
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    is_admin = member.status in ['administrator', 'creator']
    
    user_text = update.message.text or update.message.caption or ""
    
    # --- Link Protection (Admin မဟုတ်လျှင် ဖျက်မည်) ---
    if not is_admin:
        # Regular expression သုံးပြီး link ပါမပါ စစ်ဆေးခြင်း
        urls = re.findall(r'(https?://\S+|t\.me/\S+|www\.\S+)', user_text)
        if urls:
            try:
                user_id = update.effective_user.id
                user_name = update.effective_user.first_name
                mention = f'<b><a href="tg://user?id={user_id}">{user_name}</a></b>'
                group_name = update.effective_chat.title
                
                await update.message.delete()
                warning_text = f"<b>ဟိတ် {mention}...\nဒီ {group_name} ထဲတွင် Link share ခြင်းများကို ခွင့်မပြုပါ။</b>"
                await context.bot.send_message(chat_id=update.effective_chat.id, text=warning_text, parse_mode=ParseMode.HTML)
                return
            except:
                pass

    # --- Filter System (အလိုအလျောက် စာပြန်ခြင်း) ---
    keyword = user_text.lower()
    if keyword in custom_filters:
        await update.message.reply_text(text=f"<b>{custom_filters[keyword]}</b>", parse_mode=ParseMode.HTML)

# 5. Commands
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Admin မှသာ Filter အသစ်ထည့်နိုင်မည်
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ['administrator', 'creator']:
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("<b>အသုံးပြုပုံ - /filter [keyword] [reply]</b>", parse_mode=ParseMode.HTML)
        return
    
    keyword = args[0].lower()
    reply_text = " ".join(args[1:])
    custom_filters[keyword] = reply_text
    await update.message.reply_text("<b>ဟုတ်..ခန့်သူရိန်မှ (Reply) များ သတ်မှတ်လိုက်ပါသေးတယ်။</b>", parse_mode=ParseMode.HTML)

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # User ရဲ့ ID ကို "သူ/သူမ၏ ID" ဟု ဖော်ပြပေးမည်
    await update.message.reply_text(f"<b>သူ/သူမ၏ ID: <code>{update.effective_user.id}</code></b>", parse_mode=ParseMode.HTML)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers စာရင်း
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, delete_service_message))
    app.add_handler(CommandHandler("filter", add_filter))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & (~filters.COMMAND), message_handler))

    print("Bot is starting... Clean Code version without counter.")
    app.run_polling(allowed_updates=["message", "chat_member"])
