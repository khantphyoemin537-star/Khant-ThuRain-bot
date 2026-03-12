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
# ပြင်ဆင်ပြီးသော Bad Words စာရင်း
BAD_WORDS = ["လီး", "ယီး", "လိ", "စောက်ပတ်", "စောက်ဖုတ်", "အဖုတ်", "ဇောက်ပတ်", "ဇောက်ဖုတ်", "လိုး", "ငါလိုး"]

# --- Music Downloader Logic ---
def download_song(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'default_search': 'ytsearch1', 
        'noplaylist': True,
        'quiet': True,
        'outtmpl': 'song.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=True)
        video_info = info['entries'][0]
        return f"song.mp3", video_info.get('title', 'သီချင်း')

# --- Handlers ---
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
        if os.path.exists(file_path): os.remove(file_path)
    except Exception:
        await status_msg.edit_text("<b>သီချင်းရှာမတွေ့ပါ သို့မဟုတ် YouTube မှ ကန့်သတ်ထားပါသည်။</b>", parse_mode=ParseMode.HTML)

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
    
    # Bad Words Filter (မက်ဆေ့ကို မဖျက်ဘဲ သတိပေးစာသာ ပို့ခြင်း)
    if any(word in user_text for word in BAD_WORDS):
        try:
            bad_word_warning = f"ဟိတ် {mention}...\n<b>{group_name} ထဲတွင် ရိုင်းစိုင်းသော စကားလုံးများအား ပို့ခွင့်မပြုတော့ပါ။ နောက်နောင်ဆင်ခြင်သတိပြုပါ။</b>"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=bad_word_warning, parse_mode=ParseMode.HTML)
            return # သတိပေးပြီးရင် အောက်က filter တွေ ဆက်မလုပ်ဖို့ return ပြန်ထားတယ်
        except: pass

    # Custom Filter Reply
    if user_text.lower() in custom_filters:
        await update.message.reply_text(text=f"<b>{custom_filters[user_text.lower()]}</b>", parse_mode=ParseMode.HTML)

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    await update.message.reply_text(f"<b>ထိုသူ၏ ID: <code>{target_user.id}</code></b>", parse_mode=ParseMode.HTML)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("music", play_music))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    app.run_polling(allowed_updates=["message", "chat_member"])
