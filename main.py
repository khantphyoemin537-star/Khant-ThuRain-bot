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
    ChatMemberHandler, filters, ContextTypes
)

# --- CONFIGURATION ---
TOKEN = "8575371720:AAHjBOXArgOAtBUqPY_8xnZjQe-w4Dk4uRc"
OWNER_ID = 6015356597
DB_FILE = "bot_database.json"

# --- DATABASE LOGIC ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return default_db()
    return default_db()

def default_db():
    return {
        "groups": {}, 
        "group_ids": [], 
        "allowed_users": [OWNER_ID],
        "bully_list": ["မင်းကတော့ဗျာ...", "ညံ့လိုက်တာကွာ", "လူကောင်ကသာကြီးတာ ဦးနှောက်ကမပါဘူး"],
        "reply_list": ["ဟုတ်ကဲ့ဗျ", "ဘာခိုင်းမလို့လဲ", "ရှိတယ်လေ"]
    }

db = load_db()

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def get_gs(chat_id):
    cid = str(chat_id)
    if cid not in db["groups"]:
        db["groups"][cid] = {
            "welcome_on": True, "goodbye_on": True,
            "welcome_msg": "ဟိတ် {mention} {group} မှ ကြိုဆိုပါတယ်!",
            "goodbye_msg": "{mention} {group} ကနေ ထွက်သွားပါပြီ",
            "filters": {}
        }
    if chat_id not in db["group_ids"]:
        db["group_ids"].append(chat_id)
    save_db()
    return db["groups"][cid]

# --- HELP MENU ---
async def help_command(update, context):
    help_text = (
        "<b>🛠 Young Master ThuRain Bot Help</b>\n\n"
        "<b>📌 Settings (Admin Only)</b>\n"
        "• /welcome - Welcome On/Off\n"
        "• /setwelcome [စာသား] - ကြိုဆိုစာသားပြင်ရန်\n"
        "• /goodbye - Goodbye On/Off\n"
        "• /setgoodbye [စာသား] - နှုတ်ဆက်စာသားပြင်ရန်\n"
        "• /filter [key] [reply] - Filter မှတ်ရန်\n\n"
        "<b>🆔 Info Commands</b>\n"
        "• /myid /gpid /id - ID များကြည့်ရန်\n\n"
        "<b>🔨 Moderation (Admin)</b>\n"
        "• /ban - အပြီးပိုင် Ban ရန်\n"
        "• /kick - Kick ထုတ်ရန်\n"
        "• /mute - Mute လုပ်ရန်\n\n"
        "<b>🔄 Fun (Allowed Users)</b>\n"
        "• /bully /reply - Loop စရန်\n"
        "• /stopbully /stopreply - Loop ရပ်ရန်\n\n"
        "<b>👑 Owner Only</b>\n"
        "• /addallow [ID] - Permission ပေးရန်\n"
        "• /sendallgp [စာသား] - GP အားလုံးစာပို့ရန်"
    )
    await update.message.reply_text(f"<blockquote>{help_text}</blockquote>", parse_mode=ParseMode.HTML)

# --- UTILS ---
def get_mention(user):
    return f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

async def is_admin(update, context):
    if not update.effective_chat or update.effective_chat.type == "private": return True
    try:
        m = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return m.status in ["administrator", "creator"]
    except: return False

# --- COMMAND HANDLERS ---
async def get_ids(update, context):
    chat, user = update.effective_chat, update.effective_user
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else user
    text = f"📍 <b>GP ID:</b> <code>{chat.id}</code>\n👤 <b>Your ID:</b> <code>{user.id}</code>\n🎯 <b>Target ID:</b> <code>{target.id}</code>"
    await update.message.reply_text(f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML)

async def set_welcome(update, context):
    if not await is_admin(update, context): return
    gs = get_gs(update.effective_chat.id)
    if context.args:
        gs["welcome_msg"] = " ".join(context.args)
        save_db()
        await update.message.reply_text("<blockquote>✅ ကြိုဆိုစာသားကို ပြောင်းလဲလိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def set_goodbye(update, context):
    if not await is_admin(update, context): return
    gs = get_gs(update.effective_chat.id)
    if context.args:
        gs["goodbye_msg"] = " ".join(context.args)
        save_db()
        await update.message.reply_text("<blockquote>✅ နှုတ်ဆက်စာသားကို ပြောင်းလဲလိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def set_filter(update, context):
    if not await is_admin(update, context) or len(context.args) < 2: return
    kw, rep = context.args[0].lower(), " ".join(context.args[1:])
    get_gs(update.effective_chat.id)["filters"][kw] = rep
    save_db()
    await update.message.reply_text(f"<blockquote>✅ Filter မှတ်သားပြီး: {kw}</blockquote>", parse_mode=ParseMode.HTML)

async def loop_task(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id, target_id, target_name, mode = job.data
    mention = f'<a href="tg://user?id={target_id}">{target_name}</a>'
    msg_list = db["bully_list"] if mode == "bully" else db["reply_list"]
    await context.bot.send_message(chat_id, f"<blockquote>{mention} {random.choice(msg_list)}</blockquote>", parse_mode=ParseMode.HTML)

async def start_loop(update, context):
    if update.effective_user.id not in db["allowed_users"]: return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return
    mode = "bully" if update.message.text.startswith("/bully") else "reply"
    job_name = f"{mode}_{update.effective_chat.id}_{target.id}"
    context.job_queue.run_repeating(loop_task, interval=3, first=1, name=job_name, data=(update.effective_chat.id, target.id, target.first_name, mode))
    await update.message.reply_text(f"<blockquote>{mode.capitalize()} စတင်ပါပြီ... 🔥</blockquote>", parse_mode=ParseMode.HTML)

async def stop_loop(update, context):
    if update.effective_user.id not in db["allowed_users"]: return
    for j in context.job_queue.jobs():
        if str(update.effective_chat.id) in j.name: j.schedule_removal()
    await update.message.reply_text(f"<blockquote>{get_mention(update.effective_user)} ဟုတ်အစ်ကို ရပ်ခိုင်းလို့ ကျနော်ရပ်ပြီဗျ 😎</blockquote>", parse_mode=ParseMode.HTML)

async def mod_action(update, context):
    if not await is_admin(update, context) or not update.message.reply_to_message: return
    cmd = update.message.text.split()[0].lower()
    target_id = update.message.reply_to_message.from_user.id
    try:
        if "ban" in cmd: await context.bot.ban_chat_member(update.effective_chat.id, target_id)
        elif "kick" in cmd: await context.bot.unban_chat_member(update.effective_chat.id, target_id)
        elif "mute" in cmd: await context.bot.restrict_chat_member(update.effective_chat.id, target_id, ChatPermissions(can_send_messages=False))
        await update.message.reply_text(f"<blockquote>✅ လုပ်ဆောင်ချက် အောင်မြင်ပါသည်။</blockquote>", parse_mode=ParseMode.HTML)
    except: pass

async def send_all_gp(update, context):
    if update.effective_user.id != OWNER_ID: return
    msg = " ".join(context.args)
    if not msg: return
    for gid in db["group_ids"]:
        try: await context.bot.send_message(gid, f"<blockquote>📢 <b>Admin Message</b>\n\n{msg}</blockquote>", parse_mode=ParseMode.HTML); await asyncio.sleep(0.3)
        except: continue
    await update.message.reply_text("<blockquote>✅ ပို့ဆောင်ပြီးပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- MSG HANDLER ---
async def handle_msg(update, context):
    if not update.message or not update.message.text: return
    text, user, chat_id = update.message.text.lower(), update.effective_user, update.effective_chat.id
    if (re.search(r"(https?://|t\.me|www\.)", text) and not await is_admin(update, context)) or (user.is_bot and any(x in text for x in ["playing", "music", "song"])):
        try:
            await update.message.delete()
            rep = "link မချရဘူး" if not user.is_bot else "သီချင်းဖွင့်တာတွေ ဖျက်ပေးမယ်"
            warn = await context.bot.send_message(chat_id, f"<blockquote>ဟိတ် {get_mention(user)} {rep}</blockquote>", parse_mode=ParseMode.HTML)
            await asyncio.sleep(5); await warn.delete()
        except: pass
        return
    gs = get_gs(chat_id)
    for kw, rep in gs["filters"].items():
        if kw in text: await update.message.reply_text(f"<blockquote>{rep}</blockquote>", parse_mode=ParseMode.HTML)

async def member_handler(update, context):
    result = update.chat_member
    gs = get_gs(result.chat.id)
    user = result.new_chat_member.user if result.new_chat_member and result.new_chat_member.status != "left" else result.old_chat_member.user
    mention = get_mention(user)
    if result.new_chat_member and result.new_chat_member.status in ["member", "administrator"] and gs["welcome_on"]:
        await context.bot.send_message(result.chat.id, f"<blockquote>{gs['welcome_msg'].format(mention=mention, group=result.chat.title)}</blockquote>", parse_mode=ParseMode.HTML)
    elif result.new_chat_member and result.new_chat_member.status in ["left", "kicked"] and gs["goodbye_on"]:
        await context.bot.send_message(result.chat.id, f"<blockquote>{gs['goodbye_msg'].format(mention=mention, group=result.chat.title)}</blockquote>", parse_mode=ParseMode.HTML)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler(["myid", "gpid", "id"], get_ids))
    app.add_handler(CommandHandler("setwelcome", set_welcome))
    app.add_handler(CommandHandler("setgoodbye", set_goodbye))
    app.add_handler(CommandHandler("filter", set_filter))
    app.add_handler(CommandHandler(["bully", "reply"], start_loop))
    app.add_handler(CommandHandler(["stopbully", "stopreply"], stop_loop))
    app.add_handler(CommandHandler(["ban", "kick", "mute"], mod_action))
    app.add_handler(CommandHandler("sendallgp", send_all_gp))
    app.add_handler(ChatMemberHandler(member_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    print("Bot is Running..."); app.run_polling()

if __name__ == "__main__": main()
