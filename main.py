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
        "bully_list": ["မင်းကတော့ဗျာ...", "ညံ့လိုက်တာကွာ"],
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
            "w_msg": "ဟိတ် {mention} {group} မှ ကြိုဆိုပါတယ်!",
            "g_msg": "{mention} {group} ကနေ ထွက်သွားပါပြီ",
            "filters": {}
        }
    save_db()
    return db["groups"][cid]

# --- ADMIN CHECK ---
async def is_admin(update: Update):
    if update.effective_chat.type == "private": return True
    m = await update.effective_chat.get_member(update.effective_user.id)
    return m.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

# --- NEW FUNCTIONS (FIXED) ---

async def set_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    gs = get_gs(update.effective_chat.id)
    cmd = update.message.text.lower()
    new_text = " ".join(context.args)
    
    if not new_text:
        await update.message.reply_text("<blockquote>စာသားလေး ထည့်ပေးပါဦးဗျ။ (ဥပမာ- /setwelcome မင်္ဂလာပါ {mention})</blockquote>", parse_mode=ParseMode.HTML)
        return

    if "setwelcome" in cmd:
        gs["w_msg"] = new_text
        await update.message.reply_text("<blockquote>✅ Welcome စာသား ပြောင်းလဲပြီးပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    elif "setgoodbye" in cmd:
        gs["g_msg"] = new_text
        await update.message.reply_text("<blockquote>✅ Goodbye စာသား ပြောင်းလဲပြီးပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    save_db()

async def set_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    gs = get_gs(update.effective_chat.id)
    if len(context.args) < 2:
        await update.message.reply_text("<blockquote>ပုံစံ- /filter [Keyword] [Reply စာသား]</blockquote>", parse_mode=ParseMode.HTML)
        return
    
    keyword = context.args[0].lower()
    reply = " ".join(context.args[1:])
    gs["filters"][keyword] = reply
    save_db()
    await update.message.reply_text(f"<blockquote>✅ Filter ထည့်ပြီးပါပြီ: <code>{keyword}</code> -> <code>{reply}</code></blockquote>", parse_mode=ParseMode.HTML)

# --- OTHER COMMANDS ---

async def add_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["allowed_users"]: return
    cmd = update.message.text.lower()
    new_text = " ".join(context.args)
    if not new_text: return
    if "addbully" in cmd:
        db["bully_list"].append(new_text)
        msg = "Bully စာရင်းထဲ ထည့်ပြီးပါပြီ"
    else:
        db["reply_list"].append(new_text)
        msg = "Reply စာရင်းထဲ ထည့်ပြီးပါပြီ"
    save_db()
    await update.message.reply_text(f"<blockquote>✅ {msg}: <code>{new_text}</code></blockquote>", parse_mode=ParseMode.HTML)

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
            await update.message.reply_text(f"<blockquote>✅ <b>{target_name}</b> ကို ခွင့်ပြုချက် ပေးလိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    except:
        await update.message.reply_text("<blockquote>Error ဖြစ်သွားပါတယ်။ ID မှန်မမှန် ပြန်စစ်ပါဗျ။</blockquote>", parse_mode=ParseMode.HTML)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "<b>🛠 ThuRain Bot Commands</b>\n\n"
        "• /welcome on/off\n"
        "• /goodbye on/off\n"
        "• /setwelcome [စာသား]\n"
        "• /filter [key] [reply]\n"
        "• /addbully, /addreply [စာသား]\n"
        "• /bully, /reply (Reply သုံးရန်)\n"
        "• /kick, /ban, /mute (Admin Only)\n"
        "• /addallow (Owner Only)\n"
        "• /sendallgp [စာသား]"
    )
    await update.message.reply_text(f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML)

async def config_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    gs = get_gs(update.effective_chat.id)
    cmd = update.message.text.lower()
    val = "on" in cmd
    if "welcome" in cmd:
        gs["welcome"] = val
        await update.message.reply_text(f"<blockquote>Welcome ကို {'ဖွင့်' if val else 'ပိတ်'} လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    elif "goodbye" in cmd:
        gs["goodbye"] = val
        await update.message.reply_text(f"<blockquote>Goodbye ကို {'ဖွင့်' if val else 'ပိတ်'} လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    save_db()

async def get_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text.lower()
    if "gpid" in cmd:
        await update.message.reply_text(f"<blockquote>GP ID: <code>{update.effective_chat.id}</code></blockquote>", parse_mode=ParseMode.HTML)
    elif "myid" in cmd:
        await update.message.reply_text(f"<blockquote>သင့် ID: <code>{update.effective_user.id}</code></blockquote>", parse_mode=ParseMode.HTML)
    elif "/id" in cmd:
        target = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
        await update.message.reply_text(f"<blockquote>User ID: <code>{target.id}</code></blockquote>", parse_mode=ParseMode.HTML)

async def moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message:
        await update.message.reply_text("<blockquote>Reply ပြန်ပေးပါဗျ။</blockquote>", parse_mode=ParseMode.HTML)
        return
    target = update.message.reply_to_message.from_user
    cmd = update.message.text.lower()
    try:
        if "kick" in cmd:
            await update.effective_chat.unban_member(target.id)
            await update.message.reply_text(f"<blockquote>{target.first_name} ကို Kick လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
        elif "ban" in cmd:
            await update.effective_chat.ban_member(target.id)
            await update.message.reply_text(f"<blockquote>{target.first_name} ကို Ban လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
        elif "mute" in cmd:
            await update.effective_chat.restrict_member(target.id, ChatPermissions(can_send_messages=False))
            await update.message.reply_text(f"<blockquote>{target.first_name} ကို Mute လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"<blockquote>အမှား: {e}</blockquote>", parse_mode=ParseMode.HTML)

async def start_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["allowed_users"]: return
    mode = "bully" if "bully" in update.message.text.lower() else "reply"
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target:
        await update.message.reply_text("<blockquote>Reply ပြန်ပေးပါဗျ။</blockquote>", parse_mode=ParseMode.HTML)
        return
    
    job_name = f"{mode}_{update.effective_chat.id}_{target.id}"
    async def loop_cb(ctx):
        phrase = random.choice(db["bully_list"] if mode == "bully" else db["reply_list"])
        mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
        await ctx.bot.send_message(update.effective_chat.id, f"<blockquote>{mention} {phrase}</blockquote>", parse_mode=ParseMode.HTML)

    context.job_queue.run_repeating(loop_cb, interval=3, name=job_name)
    await update.message.reply_text(f"<blockquote>🔥 {target.first_name} ကို {mode} စတင်ပါပြီ...</blockquote>", parse_mode=ParseMode.HTML)

async def stop_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["allowed_users"]: return
    cmd = update.message.text.lower()
    mode = "bully" if "bully" in cmd else "reply"
    chat_id = str(update.effective_chat.id)
    found = False
    for j in context.job_queue.jobs():
        if chat_id in j.name and mode in j.name:
            j.schedule_removal()
            found = True
    
    msg = "ရပ်လိုက်ပါပြီခင်ဗျာ။" if found else "ရပ်စရာ Loop မရှိပါဘူး။"
    await update.message.reply_text(f"<blockquote>{msg}</blockquote>", parse_mode=ParseMode.HTML)

async def send_all_gp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    msg = " ".join(context.args)
    if not msg: return
    count = 0
    for gid in db["group_ids"]:
        try:
            await context.bot.send_message(gid, f"<blockquote>📢 <b>Global Message:</b>\n\n{msg}</blockquote>", parse_mode=ParseMode.HTML)
            count += 1
            await asyncio.sleep(0.5)
        except: continue
    await update.message.reply_text(f"<blockquote>✅ GP ({count}) ခုကို ပို့ပြီးပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def handle_msgs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text, user, gs = update.message.text.lower(), update.effective_user, get_gs(update.effective_chat.id)

    if text in gs["filters"]:
        await update.message.reply_text(f"<blockquote>{gs['filters'][text]}</blockquote>", parse_mode=ParseMode.HTML)

    if re.search(r'(https?://|t\.me|www\.)', text) and not await is_admin(update):
        await update.message.delete()
        return

async def member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = update.chat_member
    gs = get_gs(res.chat.id)
    user = res.new_chat_member.user
    mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    if res.new_chat_member.status == ChatMemberStatus.MEMBER and gs["welcome"]:
        await context.bot.send_message(res.chat.id, f"<blockquote>{gs['w_msg'].format(mention=mention, group=res.chat.title)}</blockquote>", parse_mode=ParseMode.HTML)
    elif res.new_chat_member.status == ChatMemberStatus.LEFT and gs["goodbye"]:
        await context.bot.send_message(res.chat.id, f"<blockquote>{gs['g_msg'].format(mention=mention, group=res.chat.title)}</blockquote>", parse_mode=ParseMode.HTML)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler(["welcome", "goodbye"], config_toggle))
    app.add_handler(CommandHandler(["setwelcome", "setgoodbye"], set_msg))
    app.add_handler(CommandHandler("filter", set_filter))
    app.add_handler(CommandHandler(["gpid", "myid", "id"], get_ids))
    app.add_handler(CommandHandler(["kick", "ban", "mute"], moderation))
    app.add_handler(CommandHandler(["bully", "reply"], start_loop))
    app.add_handler(CommandHandler(["stopbully", "stopreply"], stop_loop))
    app.add_handler(CommandHandler(["addbully", "addreply"], add_phrase))
    app.add_handler(CommandHandler("sendallgp", send_all_gp))
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(ChatMemberHandler(member_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msgs))
    app.run_polling()

if __name__ == "__main__": main()
