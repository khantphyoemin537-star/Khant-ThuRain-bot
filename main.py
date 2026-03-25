import logging
import asyncio
import json
import os
import re
import random
from telegram import Update, ChatPermissions
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ChatMemberHandler, filters, ContextTypes
)

# --- CONFIGURATION ---
TOKEN = "8575371720:AAHjBOXArgOAtBUqPY_8xnZjQe-w4Dk4uRc" 
OWNER_ID = 6015356597
DB_FILE = "bot_database.json"
TARGET_GP_ID = -1003864912245  # လူကြီးမင်း ပေးထားတဲ့ ID အမှန်

# --- DATABASE LOGIC ---
def load_db():
    defaults = {
        "groups": {}, "group_ids": [], "allowed_users": [OWNER_ID],
        "bully_list": ["မင်းရုပ်က error တစ်ခုပဲ", "စောက်ရူး... သွားသေလိုက်"],
        "auto_save_enabled": False,
        "reply_list": ["ဟုတ်ကဲ့ဗျ", "ဘာခိုင်းမလို့လဲ"]
    }
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for key, val in defaults.items():
                    if key not in data: data[key] = val
                return data
        except: return defaults
    return defaults

db = load_db()

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def get_gs(chat_id):
    cid = str(chat_id)
    if chat_id not in db["group_ids"]: db["group_ids"].append(chat_id)
    if cid not in db["groups"]:
        db["groups"][cid] = {
            "welcome": True, "goodbye": True,
            "w_msg": "ဟိတ် {name} {group} မှ ကြိုဆိုလိုက်ပါသေးတယ်",
            "g_msg": "ဟုတ် {name} {group} ကနေ ထွက်သွားပါပြီ"
        }
    save_db()
    return db["groups"][cid]

# --- PERMISSION CHECK ---
async def check_perm(update: Update):
    if update.effective_user.id in db["allowed_users"]: return True
    await update.message.reply_text("<blockquote>ဟိတ်မင်းမှာ command များသုံးစွဲခွင့်မရှိသေးဘူး၊ယူချင်ရင် @Besties_with_BoD ကိုလာတောင်း🫵</blockquote>", parse_mode=ParseMode.HTML)
    return False

# --- COMMANDS ---
async def auto_add_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    if update.effective_chat.id != TARGET_GP_ID:
        await update.message.reply_text(f"<blockquote>ဒီ Command ကို Target GP ထဲမှာပဲ သုံးလို့ရပါတယ်။</blockquote>", parse_mode=ParseMode.HTML)
        return
    db["auto_save_enabled"] = not db.get("auto_save_enabled", False)
    save_db()
    status = "ဖွင့်" if db["auto_save_enabled"] else "ပိတ်"
    await update.message.reply_text(f"<blockquote>✅ Auto-save ကို {status} လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def start_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return

    # Chat ID ကို အခြေခံပြီး Job နာမည်ပေးမယ်
    job_name = f"bully_{update.effective_chat.id}"
    
    # ရှိပြီးသား job တွေကို အရင်အရင် ရှင်းမယ်
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for j in current_jobs: j.schedule_removal()
    
    async def loop_cb(ctx):
        if db["bully_list"]:
            phrase = random.choice(db["bully_list"])
            mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
            await ctx.bot.send_message(update.effective_chat.id, f"<blockquote>{mention} {phrase}</blockquote>", parse_mode=ParseMode.HTML)

    context.job_queue.run_repeating(loop_cb, interval=3, name=job_name)
    await update.message.reply_text("<blockquote>🔥 Bully စတင်ပါပြီ (Random စနစ်)...</blockquote>", parse_mode=ParseMode.HTML)

async def stop_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    job_name = f"bully_{update.effective_chat.id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    
    if not current_jobs:
        # job name နဲ့ ရှာမရရင် chat_id ပါတာ အကုန်လိုက်ရှာမယ်
        current_jobs = [j for j in context.job_queue.jobs() if str(update.effective_chat.id) in j.name]

    if current_jobs:
        for job in current_jobs:
            job.schedule_removal()
        await update.message.reply_text("<blockquote>✅ အကုန်ရပ်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("<blockquote>ရပ်စရာ Loop မရှိပါဘူး။</blockquote>", parse_mode=ParseMode.HTML)

# --- MEMBER HANDLER ---
async def member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = update.chat_member
    if not res: return
    gs = get_gs(res.chat.id)
    user = res.new_chat_member.user
    
    if res.new_chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR] and \
       res.old_chat_member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
        if gs.get("welcome", True):
            text = gs["w_msg"].format(name=user.first_name, group=res.chat.title)
            await context.bot.send_message(res.chat.id, f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML)
    
    elif res.new_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED, ChatMemberStatus.KICKED]:
        if gs.get("goodbye", True):
            text = gs["g_msg"].format(name=user.first_name, group=res.chat.title)
            await context.bot.send_message(res.chat.id, f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML)

# --- MESSAGE HANDLER (AUTO-SAVE) ---
async def handle_msgs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # စာသားယူမယ် (Forward စာဆိုရင်လည်း ယူမယ်)
    text = update.message.text or update.message.caption
    if not text: return

    # Target GP မှာ Auto Save လုပ်ခြင်း
    if chat_id == TARGET_GP_ID and db.get("auto_save_enabled", False):
        if user_id in db["allowed_users"] and not text.startswith("/"):
            if text not in db["bully_list"]:
                db["bully_list"].append(text)
                save_db()

    # Anti-Link
    if re.search(r'(https?://|t\.me|www\.)', text.lower()):
        m = await update.effective_chat.get_member(user_id)
        if m.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            try:
                await update.message.delete()
                mention = f'<a href="tg://user?id={user_id}">{update.effective_user.first_name}</a>'
                await context.bot.send_message(chat_id, f"<blockquote>link မပို့နဲ့ မshareနဲ့👉 {mention}</blockquote>", parse_mode=ParseMode.HTML)
            except: pass

async def add_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    try:
        target_id = update.message.reply_to_message.from_user.id if update.message.reply_to_message else int(context.args[0])
        if target_id not in db["allowed_users"]:
            db["allowed_users"].append(target_id)
            save_db()
            await update.message.reply_text(f"<blockquote>✅ Permission ပေးလိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    except: pass

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler("autoaddbully", auto_add_toggle))
    app.add_handler(CommandHandler(["bully", "reply"], start_loop))
    app.add_handler(CommandHandler(["stopbully", "stopreply"], stop_loop))
    app.add_handler(ChatMemberHandler(member_handler, ChatMemberHandler.CHAT_MEMBER))
    # filters.ALL သုံးထားလို့ စာတင်မကဘဲ caption တွေကိုပါ သိမ်းပေးမှာပါ
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_msgs))
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__": main()
