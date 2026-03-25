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

def get_gs(chat_id):
    cid = str(chat_id)
    if chat_id not in db["group_ids"]: db["group_ids"].append(chat_id)
    if cid not in db["groups"]:
        db["groups"][cid] = {
            "welcome": True, "goodbye": True,
            "w_msg": "ဟိတ် {mention} {group} မှ ကြိုဆိုလိုက်ပါသေးတယ်",
            "g_msg": "ဟုတ် {mention} {group} ကနေ ထွက်သွားပါပြီ",
            "filters": {}
        }
    save_db()
    return db["groups"][cid]

# --- UTILS & ADMIN CHECK ---
async def is_admin(update: Update):
    if update.effective_chat.type == "private": return True
    m = await update.effective_chat.get_member(update.effective_user.id)
    return m.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

# --- ID COMMANDS ---
async def get_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text.lower()
    if "/myid" in cmd:
        await update.message.reply_text(f"<blockquote>သင့် ID: <code>{update.effective_user.id}</code></blockquote>", parse_mode=ParseMode.HTML)
    elif "/gpid" in cmd:
        await update.message.reply_text(f"<blockquote>GP ID: <code>{update.effective_chat.id}</code></blockquote>", parse_mode=ParseMode.HTML)
    elif "/id" in cmd:
        target = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
        await update.message.reply_text(f"<blockquote>User ID: <code>{target.id}</code></blockquote>", parse_mode=ParseMode.HTML)

# --- PREVIOUS COMMANDS ---

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "<b>🛠 ThuRain Bot Full Commands List</b>\n\n"
        "<b>⚙️ Settings (Admins Only)</b>\n"
        "• /welcome [on/off]\n"
        "• /goodbye [on/off]\n"
        "• /setwelcome [စာသား]\n"
        "• /setgoodbye [စာသား]\n"
        "• /filter [key] [reply]\n\n"
        "<b>🛡 Moderation (Admins Only)</b>\n"
        "• /kick, /ban, /mute\n\n"
        "<b>🆔 Info Commands</b>\n"
        "• /myid, /gpid, /id\n\n"
        "<b>🔥 Fun Features</b>\n"
        "• /bully, /reply\n"
        "• /stopbully, /stopreply\n"
        "• /addbully, /addreply\n\n"
        "<b>📢 Owner Only</b>\n"
        "• /addallow [ID/Reply]\n"
        "• /sendallgp [စာသား]"
    )
    await update.message.reply_text(f"<blockquote>{help_text}</blockquote>", parse_mode=ParseMode.HTML)

async def add_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    try:
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_name = update.message.reply_to_message.from_user.first_name
        else:
            target_id = int(context.args[0])
            user_chat = await context.bot.get_chat(target_id)
            target_name = user_chat.first_name

        if target_id not in db["allowed_users"]:
            db["allowed_users"].append(target_id)
            save_db()
            await update.message.reply_text(f"<blockquote>✅ <b>{target_name}</b> ကို Permission ပေးလိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    except:
        await update.message.reply_text("<blockquote>ပုံစံ- /addallow [User ID]</blockquote>", parse_mode=ParseMode.HTML)

async def moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    cmd = update.message.text.lower()
    try:
        if "kick" in cmd: await update.effective_chat.unban_member(target.id)
        elif "ban" in cmd: await update.effective_chat.ban_member(target.id)
        elif "mute" in cmd: await update.effective_chat.restrict_member(target.id, ChatPermissions(can_send_messages=False))
        await update.message.reply_text(f"<blockquote>Done for {target.first_name}</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"<blockquote>Error: {e}</blockquote>", parse_mode=ParseMode.HTML)

async def start_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["allowed_users"]: return
    mode = "bully" if "bully" in update.message.text.lower() else "reply"
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return
    
    job_name = f"{mode}_{update.effective_chat.id}_{target.id}"
    async def loop_cb(ctx):
        phrase = random.choice(db["bully_list"] if mode == "bully" else db["reply_list"])
        mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
        await ctx.bot.send_message(update.effective_chat.id, f"<blockquote>{mention} {phrase}</blockquote>", parse_mode=ParseMode.HTML)

    context.job_queue.run_repeating(loop_cb, interval=3, name=job_name)
    await update.message.reply_text(f"<blockquote>🔥 {mode} စတင်ပါပြီ...</blockquote>", parse_mode=ParseMode.HTML)

async def stop_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["allowed_users"]: return
    mode = "bully" if "bully" in update.message.text.lower() else "reply"
    chat_id = str(update.effective_chat.id)
    for j in context.job_queue.jobs():
        if chat_id in j.name and mode in j.name: j.schedule_removal()
    await update.message.reply_text("<blockquote>ရပ်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- AUTO HANDLERS (UPDATED) ---

async def member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = update.chat_member
    if not res: return
    gs = get_gs(res.chat.id)
    user = res.new_chat_member.user
    mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    group_name = res.chat.title

    # JOIN LOGIC (Auto - ဝင်တာနဲ့ ပို့မည်)
    if res.new_chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR] and \
       res.old_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
        welcome_text = gs["w_msg"].format(mention=mention, group=group_name)
        await context.bot.send_message(res.chat.id, f"<blockquote>{welcome_text}</blockquote>", parse_mode=ParseMode.HTML)

    # LEAVE LOGIC (Auto - ထွက်တာနဲ့ ပို့မည်)
    elif res.new_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
        goodbye_text = gs["g_msg"].format(mention=mention, group=group_name)
        await context.bot.send_message(res.chat.id, f"<blockquote>{goodbye_text}</blockquote>", parse_mode=ParseMode.HTML)

async def handle_msgs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    text = (update.message.text or update.message.caption or "").lower()
    user = update.effective_user
    gs = get_gs(update.effective_chat.id)

    # 1. Music Bot Cleaner (အဖြူတန်း/Bot စာတန်းများ အကုန်ဖျက်ရန်)
    # Playing, YouTube, Duration, Requested စတဲ့ စာလုံးတွေပါရင် ဖျက်မယ်
    music_indicators = ["playing", "duration", "requested", "🎵", "track", "youtube", "music", "song"]
    if user.is_bot or any(x in text for x in music_indicators):
        try:
            await update.message.delete()
            return
        except: pass

    # 2. Filter & Link check
    if text in gs["filters"]:
        await update.message.reply_text(f"<blockquote>{gs['filters'][text]}</blockquote>", parse_mode=ParseMode.HTML)
    if re.search(r'(https?://|t\.me|www\.)', text) and not await is_admin(update):
        try: await update.message.delete()
        except: pass

# --- UTILS ---
async def set_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    gs = get_gs(update.effective_chat.id)
    new_text = " ".join(context.args)
    if not new_text: return
    if "setwelcome" in update.message.text.lower(): gs["w_msg"] = new_text
    else: gs["g_msg"] = new_text
    save_db()
    await update.message.reply_text("<blockquote>✅ ပြောင်းလဲပြီးပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def config_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    gs = get_gs(update.effective_chat.id)
    val = "on" in update.message.text.lower()
    if "welcome" in update.message.text.lower(): gs["welcome"] = val
    else: gs["goodbye"] = val
    save_db()
    await update.message.reply_text(f"<blockquote>✅ {'ဖွင့်' if val else 'ပိတ်'} လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler(["welcome", "goodbye"], config_toggle))
    app.add_handler(CommandHandler(["setwelcome", "setgoodbye"], set_msg))
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler(["kick", "ban", "mute"], moderation))
    app.add_handler(CommandHandler(["bully", "reply"], start_loop))
    app.add_handler(CommandHandler(["stopbully", "stopreply"], stop_loop))
    app.add_handler(CommandHandler(["myid", "gpid", "id"], get_ids))
    
    # Auto Handlers
    app.add_handler(ChatMemberHandler(member_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_msgs))
    
    print("Bot started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__": main()
