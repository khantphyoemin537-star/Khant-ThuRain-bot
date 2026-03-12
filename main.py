# -*- coding: utf-8 -*-
import os
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ChatMemberHandler
from telegram.constants import ParseMode

# 1. Bot Token
TOKEN = '8698177279:AAGEAbRNSPoIxhfoh-Kx0BHjlsVbJvC63EA'

# Data Storage
custom_filters = {}
message_count = 0 
BAD_WORDS = ["လီး", "စပ", "သပ", "သပ့", "စပ့", "လဥ", "ယီး", "လိ", "စောက်ပတ်", "စောက်ဖုတ်", "အဖုတ်", "ဇောက်ပတ်", "ဇောက်ဖုတ်", "လိုး", "ငါလိုး"]

# --- Music Downloader Logic ---
def download_song(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'default_search': 'ytsearch1', 
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'outtmpl': 'song.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        # Bot detection ကျော်ရန် အပိုဆောင်း settings များ
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'addmetadata': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=True)
        video_info = info['entries'][0]
        return f"song.mp3", video_info.get('title', 'သီချင်း')

# --- Music Handler (Command: /music only) ---
async def play_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("<b>ကျေးဇူးပြု၍ သီချင်းအမည် ရိုက်ပေးပါ။\nဥပမာ - /music သတိရရင်</b>", parse_mode=ParseMode.HTML)
        return

    status_msg = await update.message.reply_text("<b>ခဏစောင့်ပါ... သီချင်းရှာဖွေနေပါတယ်။ 🎧</b>", parse_mode=ParseMode.HTML)
    
    try:
        file_path, title = download_song(query)
        await context.bot.send_audio(
            chat_id=update.effective_chat.id,
            audio=open(file_path, 'rb'),
            title=title,
            caption=f"<b>🎵 {title}\nRequested by: {update.effective_user.first_name}</b>",
            parse_mode=ParseMode.HTML
        )
        await status_msg.delete()
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        await status_msg.edit_text("<b>သီချင်းရှာမတွေ့ပါ သို့မဟုတ် YouTube မှ ပိတ်ထားပါသည်။ ခဏနေမှ ပြန်ကြိုးစားကြည့်ပါ။</b>", parse_mode=ParseMode.HTML)

# --- Welcome, Filters, ID & Other Handlers ---
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

async def delete_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global message_count
    if not update.message: return
    message_count += 1
    user_text = update.message.text or ""
    user_id = update.effective_user.id
    mention = f'<b><a href="tg://user?id={user_id}">{update.effective_user.first_name}</a></b>'
    group_name = update.effective_chat.title
    member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
    is_admin = member.status in ['administrator', 'creator']

    if any(word in user_text for word in BAD_WORDS):
        try:
            await update.message.delete()
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"ဟိတ် {mention}...\n<b>{group_name} ထဲတွင် ရိုင်းစိုင်းသော စကားလုံးများအား ပို့ခွင့်မပြုတော့ပါ။ နောက်နောင်ဆင်ခြင်သတိပြုပါ။</b>", parse_mode=ParseMode.HTML)
            return
        except: pass

    if not is_admin and any(e.type in ['url', 'text_link'] for e in (update.message.entities or [])):
        try:
            await update.message.delete()
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"<b>ဟိတ် {mention}...\nဒီ {group_name} ထဲတွင် Link share ခြင်းများကို ခွင့်မပြုပါ။</b>", parse_mode=ParseMode.HTML)
            return
        except: pass

    keyword = user_text.lower()
    if keyword in custom_filters:
        await update.message.reply_text(text=f"<b>{custom_filters[keyword]}</b>", parse_mode=ParseMode.HTML)

async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ['administrator', 'creator']: return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("<b>အသုံးပြုပုံ - /filter [keyword] [reply]</b>", parse_mode=ParseMode.HTML)
        return
    custom_filters[args[0].lower()] = " ".join(args[1:])
    await update.message.reply_text("<b>ဟုတ်..ခန့်သူရိန်မှ(Reply)များ သတ်မှတ်လိုက်ပါသေးတယ်။</b>", parse_mode=ParseMode.HTML)

async def get_id(update: Update, context: ContextTypes.DEFAULT_USER_TYPE):
    target_user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    await update.message.reply_text(f"<b>ထိုသူ၏ ID: <code>{target_user.id}</code></b>", parse_mode=ParseMode.HTML)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, delete_service_message))
    app.add_handler(CommandHandler("music", play_music)) # /music ပဲ ချန်ထားပါတယ်
    app.add_handler(CommandHandler("filter", add_filter))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & (~filters.COMMAND), message_handler))
    app.run_polling(allowed_updates=["message", "chat_member"])
