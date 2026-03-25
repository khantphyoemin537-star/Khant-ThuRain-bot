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
    insane_bully = [
        "မင်းရုပ်က ကွန်ဒုံးပေါက်လို့ ထွက်လာတဲ့ အမှားတစ်ခုပဲ", "စောက်ရူး... မင်းအမေက မင်းကိုမွေးတာထက် အာလူးစိုက်ခဲ့ရင် ပိုအသုံးကျမယ်",
        "မင်းစကားပြောရင် အိမ်သာကျင်းထဲက အနံ့ထက် ပိုနံတယ်", "စောက်ဆင့်မရှိတဲ့ကောင်... လူကြားထဲ ထွက်မလာနဲ့ ရှက်ဖို့ကောင်းတယ်",
        "မင်း IQ က လမ်းဘေးက ခွေးလောက်တောင် မရှိဘူး", "မင်းအဖေက မင်းကိုမွေးမယ့်အစား နံရံပေါ် ပန်းထုတ်ခဲ့သင့်တာ",
        "စောက်သုံးမကျတဲ့အကောင်... ဘဝမှာ တစ်ခါလောက်တော့ ဦးနှောက်သုံးကြည့်ပါဦး", "မင်းပုံစံက တကယ့်ကို အောက်တန်းစားပဲ",
        "စောက်ရုပ်ကိုက ကံဆိုးမယ့်ရုပ်... သွားသေလိုက်ရင် ပိုကောင်းမယ်", "မင်းစကားတွေက အန်ဖတ်တွေလိုပဲ ရွံဖို့ကောင်းတယ်",
        "လူ့လောကအတွက် အမှိုက်ဖြစ်နေတဲ့ကောင်... သွားအိပ်တော့", "မင်းကိုကြည့်ရတာ သနားစရာ အရှုံးသမားစစ်စစ်ပဲ",
        "စောက်ရူး... ဘာမှမသိရင် ပါးစပ်ပိတ်ထား", "မင်းရဲ့ တည်ရှိမှုကကို ကမ္ဘာကြီးအတွက် ဝန်ထုပ်ဝန်ပိုးပဲ",
        "အဆင့်မရှိတဲ့ကောင်နဲ့ စကားပြောရတာ ငါ့ဂုဏ်သိက္ခာကျတယ်", "မင်းပုံစံက လူထဲက လူမဟုတ်တဲ့ ပုံစံမျိုး",
        "စောက်ရူးမလေး... ဘာတွေလာကြောင်နေတာလဲ", "မင်းကိုမွေးခဲ့တဲ့ မိဘတွေတောင် နောင်တရနေမှာပဲ",
        "စောက်တုံး... ဘယ်လောက်ပြောပြော နားမလည်တဲ့အကောင်", "မင်းစကားပြောရင် လေထုကအစ ညစ်ညမ်းတယ်",
        "မင်းကတော့ တကယ့်ကို ကယ်လို့မရတဲ့ အမှိုက်ပဲ", "စောက်ရုပ်က အသည်းယားစရာကြီး (ထိုးချင်လို့)",
        "မင်းလိုကောင်မျိုးက ဘယ်နေရာမှ အသုံးမဝင်တဲ့ အပိုပစ္စည်းပဲ", "စောက်ရူးကောင်... စကားလာမများနဲ့",
        "မင်းရဲ့ဦးနှောက်က အလှပြရုံပဲလား... အလုပ်မလုပ်ဘူးလား", "စောက်ဆင့်မရှိ... စကားလာမပြောနဲ့",
        "မင်းစကားပြောရင် ဖုန်းကပါ အနံ့ထွက်လာတယ်", "တော်တော်ကို ညံ့လွန်းတယ်", "ကိုယ့်အဆင့်ကိုယ်သိပါ",
        "လူကြားထဲ ထွက်မလာနဲ့ ရှက်ဖို့ကောင်းတယ်", "မင်းရှိနေတာက ကမ္ဘာကြီး ပူနွေးလာရခြင်း အကြောင်းရင်းပဲ"
    ]
    
    defaults = {
        "groups": {}, "group_ids": [], "allowed_users": [OWNER_ID],
        "bully_list": insane_bully,
        "reply_list": ["ဟုတ်ကဲ့ဗျ", "ဘာခိုင်းမလို့လဲ", "ရှိပါတယ်"]
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
            "g_msg": "ဟုတ် {name} {group} ကနေ ထွက်သွားပါပြီ",
            "filters": {}
        }
    save_db()
    return db["groups"][cid]

# --- UTILS ---
async def is_admin(update: Update):
    if update.effective_chat.type == "private": return True
    m = await update.effective_chat.get_member(update.effective_user.id)
    return m.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

async def check_perm(update: Update):
    if update.effective_user.id in db["allowed_users"]: return True
    await update.message.reply_text("<blockquote>ဟိတ်မင်းမှာ command များသုံးစွဲခွင့်မရှိသေးဘူး၊ယူချင်ရင် @Besties_with_BoD ကိုလာတောင်း🫵</blockquote>", parse_mode=ParseMode.HTML)
    return False

# --- COMMANDS ---
async def start_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return

    job_name = f"bully_{update.effective_chat.id}"
    for j in context.job_queue.get_jobs_by_name(job_name): j.schedule_removal()

    context.user_data['bully_idx'] = 0
    async def loop_cb(ctx):
        idx = context.user_data.get('bully_idx', 0)
        if idx < len(db["bully_list"]):
            phrase = db["bully_list"][idx]
            mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
            await ctx.bot.send_message(update.effective_chat.id, f"<blockquote>{mention} {phrase}</blockquote>", parse_mode=ParseMode.HTML)
            context.user_data['bully_idx'] += 1
        else:
            for j in ctx.job_queue.get_jobs_by_name(job_name): j.schedule_removal()

    context.job_queue.run_repeating(loop_cb, interval=3, name=job_name)
    await update.message.reply_text("<blockquote>🔥 Bully စတင်ပါပြီ (အစဉ်လိုက်)...</blockquote>", parse_mode=ParseMode.HTML)

async def stop_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    chat_id = str(update.effective_chat.id)
    found = False
    for job in context.job_queue.jobs():
        if chat_id in job.name:
            job.schedule_removal()
            found = True
    await update.message.reply_text("<blockquote>✅ အကုန်ရပ်လိုက်ပါပြီ။</blockquote>" if found else "<blockquote>ရပ်စရာမရှိပါဘူး။</blockquote>", parse_mode=ParseMode.HTML)

async def add_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    text = " ".join(context.args)
    if text:
        db["bully_list"].append(text)
        save_db()
        await update.message.reply_text("<blockquote>✅ Bully List ထဲ ထည့်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- MEMBER HANDLER (WELCOME/GOODBYE) ---
async def member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m_change = update.chat_member
    if not m_change: return
    gs = get_gs(m_change.chat.id)
    user = m_change.new_chat_member.user
    name_only = user.first_name
    group_name = m_change.chat.title
    
    is_join = m_change.new_chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR] and \
              m_change.old_chat_member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]
    is_leave = m_change.new_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED, ChatMemberStatus.KICKED]

    if is_join and gs["welcome"]:
        text = gs["w_msg"].format(name=name_only, group=group_name)
        await context.bot.send_message(m_change.chat.id, f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML)
    elif is_leave and gs["goodbye"]:
        text = gs["g_msg"].format(name=name_only, group=group_name)
        await context.bot.send_message(m_change.chat.id, f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML)

# --- MESSAGE HANDLER ---
async def handle_msgs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text, user_id = update.message.text, update.effective_user.id
    gs = get_gs(update.effective_chat.id)

    # Auto Save for Permitted Users
    if user_id in db["allowed_users"] and not text.startswith("/"):
        if text not in db["bully_list"]:
            db["bully_list"].append(text)
            save_db()

    # Anti-Link
    if re.search(r'(https?://|t\.me|www\.)', text.lower()) and not await is_admin(update):
        await update.message.delete()
        mention = f'<a href="tg://user?id={user_id}">{update.effective_user.first_name}</a>'
        await context.bot.send_message(update.effective_chat.id, f"<blockquote>link မပို့နဲ့ မshareနဲ့👉 {mention}</blockquote>", parse_mode=ParseMode.HTML)

# --- OWNER TOOLS ---
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
    app.add_handler(CommandHandler(["bully", "reply"], start_loop))
    app.add_handler(CommandHandler(["stopbully", "stopreply"], stop_loop))
    app.add_handler(CommandHandler("addbully", add_to_list))
    app.add_handler(ChatMemberHandler(member_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msgs))
    app.run_polling()

if __name__ == "__main__": main()
