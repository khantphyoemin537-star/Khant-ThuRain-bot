# -*- coding: utf-8 -*-
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ChatMemberHandler
from telegram.constants import ParseMode

# 1. Bot Token
TOKEN = '8698177279:AAGEAbRNSPoIxhfoh-Kx0BHjlsVbJvC63EA'

# Data Storage
custom_filters = {}
message_count = 0 

# 2. Welcome & Goodbye
async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result:
        return

    chat_id = result.chat.id
    group_name = result.chat.title
    user = result.new_chat_member.user
    mention = f'<b><a href="tg://user?id={user.id}">{user.first_name}</a></b>'

    if result.old_chat_member.status in ["left", "kicked", "restricted"] and result.new_chat_member.status == "member":
        welcome_text = f"<b>ဟိတ် {mention} ရေ Dexter ThuRainᴮᵒᴰ နှင့်အတူ Adminများရဲ့ {group_name} မှ ကြိုဆိုပါတယ်။</b>"
        await context.bot.send_message(chat_id=chat_id, text=welcome_text, parse_mode=ParseMode.HTML)

    elif result.old_chat_member.status == "member" and result.new_chat_member.status == "left":
        goodbye_text = f"<b>နှုတ်ဆက်ပါတယ် {mention} ရေ... နောက်မှပြန်တွေ့ကြမယ်နော်။</b>"
        await context.bot.send_message(chat_id=chat_id, text=goodbye_text, parse_mode=ParseMode.HTML)

# 3. Service Message Deletion
async def delete_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except:
        pass

# 4. Message Handler (Counter, Link Blocker with Group Name, Filter)
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global message_count
    if not update.message:
        return
    
    # Message Counter (၅၀ ပြည့်တိုင်း အချက်ပြမယ်)
    message_count += 1
    if message_count % 50 == 0:
        count_text = f"<b>မက်ဆေ့အရေအတွက် {message_count} ရောက်ရှိပါပြီ။ ပျော်စရာကောင်းတာလေးတွေ ဆက်ပြောကြရအောင်။</b>"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=count_text, parse_mode=ParseMode.HTML)

    # Admin Check
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    is_admin = member.status in ['administrator', 'creator']
    
    user_text = update.message.text or update.message.caption or ""
    entities = update.message.entities or update.message.caption_entities or []

    # Link Protection (Admin မဟုတ်ရင် ဖျက်ပြီး Group နာမည်နဲ့ သတိပေးမယ်)
    if not is_admin:
        if any(entity.type in ['url', 'text_link'] for entity in entities):
            try:
                user_id = update.effective_user.id
                user_name = update.effective_user.first_name
                mention = f'<b><a href="tg://user?id={user_id}">{user_name}</a></b>'
                group_name = update.effective_chat.title # Group Name ယူခြင်း
                
                await update.message.delete()
                warning_text = f"<b>ဟိတ် {mention}...\nဒီ {group_name} ထဲတွင် Link share ခြင်းများကို ခွင့်မပြုပါ။</b>"
                await context.bot.send_message(chat_id=update.effective_chat.id, text=warning_text, parse_mode=ParseMode.HTML)
                return
            except:
                pass

    # Filter System
    keyword = user_text.lower()
    if keyword in custom_filters:
        await update.message.reply_text(text=f"<b>{custom_filters[keyword]}</b>", parse_mode=ParseMode.HTML)

# 5. Commands
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ['administrator', 'creator']:
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("<b>အသုံးပြုပုံ - /filter [keyword] [reply]</b>", parse_mode=ParseMode.HTML)
        return
    keyword = args[0].lower()
    custom_filters[keyword] = " ".join(args[1:])
    await update.message.reply_text("<b>ဟုတ်..ခန့်သူရိန်မှ(Reply)များ သတ်မှတ်လိုက်ပါသေးတယ်။</b>", parse_mode=ParseMode.HTML)

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"<b>သင့်ရဲ့ Telegram ID: <code>{update.effective_user.id}</code></b>", parse_mode=ParseMode.HTML)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, delete_service_message))
    app.add_handler(CommandHandler("filter", add_filter))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & (~filters.COMMAND), message_handler))

    print("Power Smart Bot is starting... Link Protection with Group Name updated.")
    app.run_polling(allowed_updates=["message", "chat_member"])

