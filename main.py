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
# လူကြီးမင်းပေးတဲ့ ID အစစ်ကို ပြောင်းလဲသတ်မှတ်လိုက်ပါတယ်
TARGET_GP_ID = -1003864912245 

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
        await update.message.reply_text(f"<blockquote>ဒီ Command ကို သတ်မှတ်ထားတဲ့ GP ({TARGET_GP_ID}) ထဲမှာပဲ သုံးလို့ရပါတယ်။</blockquote>", parse_mode=ParseMode.HTML)
        return
    db["auto_save_enabled"] = not db.get("auto_save_enabled", False)
    save_db()
    status = "ဖွင့်" if db["auto_save_enabled"] else "ပိတ်"
    await update.message.reply_text(f"<blockquote>✅ Auto-save ကို {status} လိုက်ပါပြီ။ အခုကစပြီး ပါမစ်ရှိသူတွေ ပြောသမျှစာကို မှတ်ပါတော့မယ်။</blockquote>", parse_mode=ParseMode.HTML)

async def start_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return

    job_name = f"bully_{update.effective_chat.id}"
    for j in context.job_queue.get_jobs_by_name(job_name): j.schedule_removal()
    
    async def loop_cb(ctx):
        if db["bully_list"]:
            phrase = random.choice(db["bully_list"])
            mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
            await ctx.bot.send_message(update.effective_chat.id, f"<blockquote>{mention} {phrase}</blockquote>", parse_mode=ParseMode.HTML)

    context.job_queue.run_repeating(loop_cb, interval=3, name=job_name)
    await update.message.reply_text("<blockquote>🔥 Bully စတင်ပါပြီ (Random စနစ်)...</blockquote>", parse_mode=ParseMode.HTML)

async def stop_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    chat_id = str(update.effective_chat.id)
    found = False
    for job in context.job_queue.jobs():
        if chat_id in job.name:
            job.schedule_removal()
            found = True
    await update.message.reply_text("<blockquote>✅ အကုန်ရပ်လိုက်ပါပြီ။</blockquote>" if found else "<blockquote>ရပ်စရာမရှိပါ။</blockquote>", parse_mode=ParseMode.HTML)

# --- MEMBER HANDLER (WELCOME/GOODBYE) ---
async def member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = update.chat_member
    if not res: return
    gs = get_gs(res.chat.id)
    user = res.new_chat_member.user
    
    # Join Event
    if res.new_chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR] and \
       res.old_chat_member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
        if gs.get("welcome", True):
            text = gs["w_msg"].format(name=user.first_name, group=res.chat.title)
            await context.bot.send_message(res.chat.id, f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML)
    
    # Leave Event
    elif res.new_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED, ChatMemberStatus.KICKED]:
        if gs.get("goodbye", True):
            text = gs["g_msg"].format(name=user.first_name, group=res.chat.title)
            await context.bot.send_message(res.chat.id, f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML)

# --- MESSAGE HANDLER (AUTO-SAVE & ANTI-LINK) ---
async def handle_msgs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text, user_id, chat_id = update.message.text, update.effective_user.id, update.effective_chat.id
    
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
            await update.message.delete()
            mention = f'<a href="tg://user?id={user_id}">{update.effective_user.first_name}</a>'
            await context.bot.send_message(update.effective_chat.id, f"<blockquote>link မပို့နဲ့ မshareနဲ့👉 {mention}</blockquote>", parse_mode=ParseMode.HTML)

async def add_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    try:
        target_id = update.message.reply_to_message.from_user.id if update.message.reply_to_message else int(context.args[0])
        if target_id not in db["allowed_users"]:
            db["allowed_users"].append(target_id)
            save_db()
            await update.message.reply_text(f"<blockquote>✅ ID: {target_id} ကို Permission ပေးလိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    except: pass

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler("autoaddbully", auto_add_toggle))
    app.add_handler(CommandHandler(["bully", "reply"], start_loop))
    app.add_handler(CommandHandler(["stopbully", "stopreply"], stop_loop))
    app.add_handler(ChatMemberHandler(member_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msgs))
    
    print(f"Bot is running with Target GP ID: {TARGET_GP_ID}")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__": main()
