# -*- coding: utf-8 -*-
import os
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ChatMemberHandler
from telegram.constants import ParseMode

TOKEN = '8698177279:AAGEAbRNSPoIxhfoh-Kx0BHjlsVbJvC63EA'
DB_FILE = "bot_data.db"

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS stats (id INTEGER PRIMARY KEY, count INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS filters (keyword TEXT PRIMARY KEY, reply TEXT)")
    c.execute("SELECT count FROM stats WHERE id = 1")
    if not c.fetchone():
        c.execute("INSERT INTO stats (id, count) VALUES (1, 416350)")
    conn.commit()
    conn.close()

def get_message_count():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT count FROM stats WHERE id = 1")
    count = c.fetchone()[0]
    conn.close()
    return count

def update_message_count(new_count):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE stats SET count = ? WHERE id = 1", (new_count,))
    conn.commit()
    conn.close()

def save_filter(keyword, reply):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO filters (keyword, reply) VALUES (?, ?)", (keyword.lower(), reply))
    conn.commit()
    conn.close()

def get_filters():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT keyword, reply FROM filters")
    all_filters = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return all_filters

init_db()

# --- .info Command Logic ---
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Reply ပြန်ထားတဲ့သူရှိရင် ထိုသူရဲ့ info ကိုယူမယ်၊ မရှိရင် ကိုယ့် info ကိုယူမယ်
    target_msg = update.message.reply_to_message
    user = target_msg.from_user if target_msg else update.effective_user
    chat = update.effective_chat
    
    # Member Status ကိုစစ်ဆေးခြင်း
    member = await context.bot.get_chat_member(chat.id, user.id)
    status = member.status.capitalize()
    
    # Custom Tags/Roles (Dexter's Hierarchy)
    # ဒီမှာ သင့်ရဲ့ Chiefs တွေ Allys တွေရဲ့ ID ကို ထည့်ထားရင် ပိုကောင်းပါတယ်
    role_tag = "Member"
    if member.status == 'creator':
        role_tag = "Founder • Dexter"
    elif member.status == 'administrator':
        role_tag = "Chief • BoD"
    
    # Join Date (Bot ရှိမှ သိနိုင်တာမို့ လက်ရှိအချိန်ကိုပဲ Format လှလှလေးပြပေးထားပါတယ်)
    now = datetime.now().strftime("%d.%m.%y at %I:%M %p")

    info_text = (
        f"<b>─── USER INFORMATION ───</b>\n\n"
        f"<b>ID:</b> <code>{user.id}</code>\n"
        f"<b>Name:</b> {user.first_name}\n"
        f"<b>Username:</b> @{user.username if user.username else 'None'}\n"
        f"<b>Situation:</b> {status}\n"
        f"<b>Tag:</b> {role_tag}\n"
        f"<b>Join:</b> {now}\n\n"
        f"<b>────────────────────</b>"
    )
    await update.message.reply_text(info_text, parse_mode=ParseMode.HTML)

# --- Other Handlers ---
async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return
    chat_id, group_name = result.chat.id, result.chat.title
    user = result.new_chat_member.user
    mention = f'<b><a href="tg://user?id={user.id}">{user.first_name}</a></b>'
    
    if result.old_chat_member.status in ["left", "kicked", "restricted"] and result.new_chat_member.status == "member":
        welcome_text = f"<b>ჰိတ် {mention} ရေ Dexter ThuRainᴮᵒᴰ နှင့်အတူ Adminများရဲ့ {group_name} မှ ကြိုဆိုပါတယ်။</b>"
        await context.bot.send_message(chat_id=chat_id, text=welcome_text, parse_mode=ParseMode.HTML)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat: return
    
    # Command တွေကို Count မလုပ်ချင်ရင် ရှောင်ရန်
    if update.message.text and (update.message.text.startswith('.') or update.message.text.startswith('/')):
        pass 
    else:
        current_count = get_message_count() + 1
        update_message_count(current_count)
        if current_count % 100 == 0:
            milestone_text = f"<b>ဟုတ်... {update.effective_chat.title} မှာ စုစုပေါင်း မက်ဆေ့ {current_count:,} ခုကို ပေးပို့ကြပြီးပါပြီ။</b>"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=milestone_text, parse_mode=ParseMode.HTML)

    if update.message.text:
        user_text = update.message.text.lower()
        active_filters = get_filters()
        if user_text in active_filters:
            await update.message.reply_text(text=f"<b>{active_filters[user_text]}</b>", parse_mode=ParseMode.HTML)

async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ['administrator', 'creator']: return
    args = context.args
    if len(args) < 2: return
    save_filter(args[0], " ".join(args[1:]))
    await update.message.reply_text("<b>Filter Added.</b>", parse_mode=ParseMode.HTML)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    # .info Command အတွက် Handler (Regex သုံးပြီး .info ကိုဖမ်းတာပါ)
    app.add_handler(MessageHandler(filters.Regex(r'^\.info$'), info_command))
    
    app.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("filter", add_filter))
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), message_handler))
    
    app.run_polling(allowed_updates=["message", "chat_member"])
