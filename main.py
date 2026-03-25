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

# --- DATABASE LOGIC ---
def load_db():
    defaults = {
        "groups": {}, "group_ids": [], "allowed_users": [OWNER_ID],
        "bully_list": ["မင်းကတော့ဗျာ...", "ညံ့လိုက်တာကွာ", "ဘာတွေလျှောက်လုပ်နေတာလဲ"],
        "reply_list": ["ဟုတ်ကဲ့ဗျ", "ဘာခိုင်းမလို့လဲ", "ရှိပါတယ်ခင်ဗျ"]
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

# --- PERMISSION & ADMIN CHECK ---
async def is_admin(update: Update):
    if update.effective_chat.type == "private": return True
    m = await update.effective_chat.get_member(update.effective_user.id)
    return m.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

async def check_perm(update: Update):
    if update.effective_user.id not in db["allowed_users"]:
        await update.message.reply_text("<blockquote>ဟိတ်မင်းမှာ command များသုံးစွဲခွင့်မရှိသေးဘူး၊ယူချင်ရင် @Besties_with_BoD ကိုလာတောင်း🫵</blockquote>", parse_mode=ParseMode.HTML)
        return False
    return True

# --- BULLY / REPLY LOOP ---
async def start_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    mode = "bully" if "bully" in update.message.text.lower() else "reply"
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    
    if not target:
        await update.message.reply_text("<blockquote>ဘယ်သူ့ကို လုပ်မှာလဲ Reply ပြန်ပေးပါဗျ။</blockquote>", parse_mode=ParseMode.HTML)
        return
    
    job_name = f"{mode}_{update.effective_chat.id}_{target.id}"
    
    async def loop_cb(ctx):
        phrase = random.choice(db["bully_list"] if mode == "bully" else db["reply_list"])
        mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
        await ctx.bot.send_message(update.effective_chat.id, f"<blockquote>{mention} {phrase}</blockquote>", parse_mode=ParseMode.HTML)

    context.job_queue.run_repeating(loop_cb, interval=3, name=job_name)
    await update.message.reply_text(f"<blockquote>🔥 {mode} စတင်ပါပြီ...</blockquote>", parse_mode=ParseMode.HTML)

async def stop_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    chat_id = str(update.effective_chat.id)
    for j in context.job_queue.jobs():
        if chat_id in j.name: j.schedule_removal()
    await update.message.reply_text("<blockquote>ရပ်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- ADD TO LISTS (NEW) ---
async def add_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    new_text = " ".join(context.args)
    if not new_text:
        await update.message.reply_text("<blockquote>ထည့်မယ့်စာသား ထည့်ပေးပါဦး။</blockquote>", parse_mode=ParseMode.HTML)
        return
    
    if "/addbully" in update.message.text.lower():
        db["bully_list"].append(new_text)
        msg = "Bully စာသားအသစ် ထည့်ပြီးပါပြီ"
    else:
        db["reply_list"].append(new_text)
        msg = "Reply စာသားအသစ် ထည့်ပြီးပါပြီ"
    
    save_db()
    await update.message.reply_text(f"<blockquote>✅ {msg}</blockquote>", parse_mode=ParseMode.HTML)

# --- ADMIN / OWNER TOOLS ---
async def add_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await check_perm(update)
        return
    try:
        target_id = update.message.reply_to_message.from_user.id if update.message.reply_to_message else int(context.args[0])
        if target_id not in db["allowed_users"]:
            db["allowed_users"].append(target_id)
            save_db()
            await update.message.reply_text("<blockquote>✅ Permission ပေးလိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    except: pass

async def send_all_gp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    msg = " ".join(context.args)
    if not msg: return
    # database ထဲမှာ group_ids သိမ်းထားတဲ့ logic လိုပါတယ် (ဒီမှာ default အနေနဲ့ loop ပတ်ထားပါတယ်)
    for gid in db.get("group_ids", []):
        try: await context.bot.send_message(gid, f"<blockquote>📢 Admin Message:\n\n{msg}</blockquote>", parse_mode=ParseMode.HTML)
        except: continue
    await update.message.reply_text("<blockquote>အကုန်ပို့ပြီးပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- MESSAGE HANDLER (LINK PROTECT) ---
async def handle_msgs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    text = (update.message.text or update.message.caption or "").lower()
    user = update.effective_user

    # Link ဖျက်ရန် (Admin မဟုတ်ရင်)
    if re.search(r'(https?://|t\.me|www\.)', text) and not await is_admin(update):
        try:
            await update.message.delete()
            mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
            await context.bot.send_message(update.effective_chat.id, f"<blockquote>link မပို့နဲ့ မshareနဲ့👉 {mention}</blockquote>", parse_mode=ParseMode.HTML)
            return
        except: pass

    # Music Bot Cleaner
    if user.is_bot and any(x in text for x in ["playing", "🎵", "track"]):
        try: await update.message.delete()
        except: pass

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Register Commands
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler(["bully", "reply"], start_loop))
    app.add_handler(CommandHandler(["stopbully", "stopreply"], stop_loop))
    app.add_handler(CommandHandler(["addbully", "addreply"], add_to_list))
    app.add_handler(CommandHandler("sendallgp", send_all_gp))
    
    # Message Handlers
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_msgs))
    
    print("ThuRain Bot is Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
