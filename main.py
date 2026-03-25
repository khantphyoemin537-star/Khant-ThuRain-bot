import logging
import asyncio
import json
import os
import re
import random
from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ChatMemberHandler, filters, ContextTypes, JobQueue
)

# --- CONFIGURATION ---
TOKEN = "8575371720:AAH0BOXArgOAtBUqPY_8xnZjQe-w4Dk4uRc"
OWNER_ID = 6015356597
DB_FILE = "bot_database.json"

# --- DATABASE LOGIC ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "group_ids" not in data: data["group_ids"] = []
                if "allowed_users" not in data: data["allowed_users"] = [OWNER_ID]
                if "bully_list" not in data: data["bully_list"] = ["မင်းကတော့ဗျာ...", "ညံ့လိုက်တာကွာ"]
                if "reply_list" not in data: data["reply_list"] = ["ဟုတ်ကဲ့ဗျ", "ဘာခိုင်းမလို့လဲ"]
                return data
        except: return default_db()
    return default_db()

def default_db():
    return {
        "groups": {}, "group_ids": [], "allowed_users": [OWNER_ID],
        "bully_list": ["မင်းကတော့ဗျာ...", "ညံ့လိုက်တာကွာ", "လူကောင်ကသာကြီးတာ ဦးနှောက်ကပါဘူး"],
        "reply_list": ["ဟုတ်ကဲ့ဗျ", "ဘာခိုင်းမလို့လဲ", "ရှိတယ်လေ"]
    }

db = load_db()

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def get_gs(chat_id):
    cid = str(chat_id)
    if chat_id not in db["group_ids"]:
        db["group_ids"].append(chat_id)
        save_db()
    if cid not in db["groups"]:
        db["groups"][cid] = {
            "welcome_on": True, "goodbye_on": True,
            "welcome_msg": "ဟိတ် {mention} {group} မှ ကြိုဆိုပါတယ်!",
            "goodbye_msg": "{mention} {group} ကနေ ထွက်သွားပါပြီ",
            "filters": {}
        }
        save_db()
    return db["groups"][cid]

# --- UTILS ---
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private": return True
    m = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return m.status in ["administrator", "creator"]

# --- COMMANDS ---
async def help_command(update, context):
    help_text = (
        "<b>🛠 Young Master ThuRain Full Help</b>\n\n"
        "<b>👑 Owner Commands</b>\n"
        "• /addallow [ID] - Permission ပေးရန်\n"
        "• /sendallgp [စာ] - GP အားလုံးစာပို့ရန်\n\n"
        "<b>📌 Admin Settings</b>\n"
        "• /welcome /goodbye - On/Off လုပ်ရန်\n"
        "• /setwelcome [စာ] - ကြိုဆိုစာပြင်ရန်\n"
        "• /setgoodbye [စာ] - နှုတ်ဆက်စာပြင်ရန်\n\n"
        "<b>🔨 Moderation</b>\n"
        "• /ban /kick /mute /unmute (Reply ပြန်သုံးရန်)\n\n"
        "<b>🔄 Fun & Loops</b>\n"
        "• /bully /reply /stopbully /stopreply\n"
        "• /addbully /addreply - စာသားသစ်ထည့်ရန်\n\n"
        "<b>🆔 Info</b>\n"
        "• /id /myid /gpid"
    )
    await update.message.reply_text(f"<blockquote>{help_text}</blockquote>", parse_mode=ParseMode.HTML)

async def add_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    try:
        uid = int(context.args[0])
        if uid not in db["allowed_users"]:
            db["allowed_users"].append(uid); save_db()
            try:
                user_obj = await context.bot.get_chat(uid)
                mention = f'<a href="tg://user?id={uid}">{user_obj.first_name}</a>'
            except: mention = f'<code>{uid}</code>'
            await update.message.reply_text(f"<blockquote>✅ User {mention} ကို Permission ပေးလိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    except: await update.message.reply_text("<blockquote>❌ ID မှားယွင်းနေပါသည်။</blockquote>", parse_mode=ParseMode.HTML)

async def send_all_gp(update, context):
    if update.effective_user.id != OWNER_ID: return
    msg = " ".join(context.args)
    if not msg: return
    count = 0
    for gid in db["group_ids"]:
        try:
            await context.bot.send_message(gid, f"<blockquote>📢 <b>Admin Message</b>\n\n{msg}</blockquote>", parse_mode=ParseMode.HTML)
            count += 1; await asyncio.sleep(0.3)
        except: continue
    await update.message.reply_text(f"<blockquote>✅ Group ({count}) ခုဆီ စာပို့ပြီးပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- MODERATION ---
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return
    cmd = update.message.text.split()[0].lower()
    user = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    try:
        if "/ban" in cmd: await context.bot.ban_chat_member(chat_id, user.id); res = "Ban လိုက်ပါပြီ 🔨"
        elif "/kick" in cmd: await context.bot.unban_chat_member(chat_id, user.id); res = "Kick လိုက်ပါပြီ 🦶"
        elif "/mute" in cmd: await context.bot.restrict_chat_member(chat_id, user.id, ChatPermissions(can_send_messages=False)); res = "Mute လိုက်ပါပြီ 🔇"
        elif "/unmute" in cmd: await context.bot.restrict_chat_member(chat_id, user.id, ChatPermissions(can_send_messages=True)); res = "Unmute လိုက်ပါပြီ 🔊"
        await update.message.reply_text(f"<blockquote>✅ {user.first_name} ကို {res}</blockquote>", parse_mode=ParseMode.HTML)
    except: await update.message.reply_text("<blockquote>❌ အခွင့်အာဏာမရှိပါ။</blockquote>", parse_mode=ParseMode.HTML)

# --- SETTINGS ---
async def toggle_set(update, context):
    if not await is_admin(update, context): return
    cmd = update.message.text.split()[0].lower()
    gs = get_gs(update.effective_chat.id)
    if "/welcome" in cmd: gs["welcome_on"] = not gs["welcome_on"]; key = "Welcome"
    else: gs["goodbye_on"] = not gs["goodbye_on"]; key = "Goodbye"
    save_db()
    status = "ON" if (gs["welcome_on"] if "Welcome" in key else gs["goodbye_on"]) else "OFF"
    await update.message.reply_text(f"<blockquote>✅ {key} is now {status}</blockquote>", parse_mode=ParseMode.HTML)

async def set_msg(update, context):
    if not await is_admin(update, context): return
    cmd = update.message.text.split()[0].lower()
    text = " ".join(context.args)
    if not text: return
    gs = get_gs(update.effective_chat.id)
    if "/setwelcome" in cmd: gs["welcome_msg"] = text; key = "Welcome"
    else: gs["goodbye_msg"] = text; key = "Goodbye"
    save_db()
    await update.message.reply_text(f"<blockquote>✅ {key} Message ကို ပြင်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- LOOP LOGIC ---
async def start_loop(update, context):
    if update.effective_user.id not in db["allowed_users"]: return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return
    mode = "bully" if update.message.text.startswith("/bully") else "reply"
    context.job_queue.run_repeating(lambda c: c.bot.send_message(c.job.data[0], f"<blockquote><a href='tg://user?id={c.job.data[1]}'>{c.job.data[2]}</a> {random.choice(db['bully_list'] if c.job.data[3]=='bully' else db['reply_list'])}</blockquote>", parse_mode=ParseMode.HTML), interval=3, name=f"{mode}_{update.effective_chat.id}_{target.id}", data=(update.effective_chat.id, target.id, target.first_name, mode))
    await update.message.reply_text(f"<blockquote>{mode.capitalize()} စတင်ပါပြီ... 🔥</blockquote>", parse_mode=ParseMode.HTML)

async def stop_loop(update, context):
    if update.effective_user.id not in db["allowed_users"]: return
    for j in context.job_queue.jobs():
        if str(update.effective_chat.id) in j.name: j.schedule_removal()
    await update.message.reply_text("<blockquote>ရပ်လိုက်ပါပြီဗျ 😎</blockquote>", parse_mode=ParseMode.HTML)

async def add_to_list(update, context):
    if update.effective_user.id not in db["allowed_users"]: return
    cmd, text = update.message.text.split()[0].lower(), " ".join(context.args)
    if not text: return
    if "/addbully" in cmd: db["bully_list"].append(text); label = "Bully"
    else: db["reply_list"].append(text); label = "Reply"
    save_db(); await update.message.reply_text(f"<blockquote>✅ {label} ထဲသို့ '{text}' ထည့်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- INFO ---
async def get_id(update, context):
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    await update.message.reply_text(f"<blockquote>👤 Name: {target.first_name}\n🆔 ID: <code>{target.id}</code>\n💬 GP ID: <code>{update.effective_chat.id}</code></blockquote>", parse_mode=ParseMode.HTML)

# --- CORE HANDLERS ---
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat_id, user, text = update.effective_chat.id, update.effective_user, update.message.text.lower()
    get_gs(chat_id)
    if (re.search(r"(https?://|t\.me|www\.)", text) and not await is_admin(update, context)) or (user.is_bot and any(x in text for x in ["playing", "music", "song"])):
        try: await update.message.delete()
        except: pass

async def member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = update.chat_member; gs = get_gs(res.chat.id)
    user = res.new_chat_member.user if res.new_chat_member and res.new_chat_member.status != "left" else res.old_chat_member.user
    mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    if res.new_chat_member and res.new_chat_member.status in ["member", "administrator"] and gs["welcome_on"]:
        await context.bot.send_message(res.chat.id, gs["welcome_msg"].format(mention=mention, group=res.chat.title), parse_mode=ParseMode.HTML)
    elif res.new_chat_member and res.new_chat_member.status in ["left", "kicked"] and gs["goodbye_on"]:
        await context.bot.send_message(res.chat.id, gs["goodbye_msg"].format(mention=mention, group=res.chat.title), parse_mode=ParseMode.HTML)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler("sendallgp", send_all_gp))
    app.add_handler(CommandHandler(["ban", "kick", "mute", "unmute"], admin_action))
    app.add_handler(CommandHandler(["welcome", "goodbye"], toggle_set))
    app.add_handler(CommandHandler(["setwelcome", "setgoodbye"], set_msg))
    app.add_handler(CommandHandler(["bully", "reply"], start_loop))
    app.add_handler(CommandHandler(["stopbully", "stopreply"], stop_loop))
    app.add_handler(CommandHandler(["addbully", "addreply"], add_to_list))
    app.add_handler(CommandHandler(["id", "myid", "gpid"], get_id))
    app.add_handler(ChatMemberHandler(member_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    print("Bot Started..."); app.run_polling()

if __name__ == "__main__": main()
