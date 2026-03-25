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
    bully_messages = [
        "မင်းမျက်နှာက ပြုပြင်လို့မရတဲ့ error တစ်ခုလိုပဲ", "စကားပြောရင် ဦးနှောက်လေး သုံးပါဦး", 
        "မင်းထက်စာရင် လမ်းဘေးက ခွေးက ပိုအသုံးကျမယ်", "ရုပ်ကိုက အဆင့်မရှိတာ", 
        "မင်းအမေက မင်းကိုမွေးတာထက် အာလူးစိုက်ခဲ့ရင် ပိုကောင်းမှာ", "နားမလည်ရင် ပါးစပ်ပိတ်ထား",
        "မင်းရှိနေတာကိုက လောကကြီးအတွက် အမှိုက်ပဲ", "စောက်ဆင့်မရှိ စကားလာမပြောနဲ့",
        "မင်းလိုကောင်မျိုးက ဘယ်နေရာမှ အသုံးမကျဘူး", "သွားတိုက်ဆေး ကုန်နေတာလား စကားပြောတာ နံလိုက်တာ",
        "မင်းရဲ့ IQ က ဖိနပ်ဆိုဒ်ထောက်တောင် နည်းသေးတယ်", "လူကြားထဲ ထွက်မလာနဲ့ ရှက်ဖို့ကောင်းတယ်",
        "မင်းစကားပြောရင် ဖုန်းကပါ အနံ့ထွက်လာတယ်", "တော်တော်ကို ညံ့လွန်းတယ်", 
        "ဘဝကို အရှုံးသမားလိုပဲ ဖြတ်သန်းနေတော့မလို့လား", "မင်းအကြောင်းပြောရရင် ကျမ်းတစ်စောင်တောင် ထွက်မယ်",
        "စောက်ရူးကောင်... ဘာတွေလာလုပ်နေတာလဲ", "မင်းကိုကြည့်ရတာ သနားတောင် သနားတယ်",
        "မင်းစကားတွေက တန်ဖိုးမရှိဘူး", "ဒီလောက်ညံ့တာ မရှက်ဘူးလား", "ကိုယ့်အဆင့်ကိုယ်သိပါ",
        "မင်းက လူ့လောကအတွက် ဝန်ထုပ်ဝန်ပိုးပဲ", "စောက်တလွဲတွေ လာမလုပ်နဲ့", "မင်းလိုကောင်ကို ဘယ်သူမှ အလေးမထားဘူး",
        "အဆင့်မရှိတဲ့ကောင်", "မင်းပြောတဲ့ စကားတွေက နားမခံသာဘူး", "တော်တော်ကို အောက်တန်းကျတာပဲ",
        "မင်းကိုမြင်ရင် ဗိုက်တောင် နာတယ် (ရယ်ချင်လွန်းလို့)", "စောက်တုံး... ဘာမှမသိရင် ငြိမ်ငြိမ်နေ",
        "မင်းကတော့ တကယ့်ကို အလကားကောင်ပဲ", "ဘဝမှာ တစ်ခုခု အသုံးကျအောင် လုပ်ပါဦး",
        "မင်းရှိနေတာက ကမ္ဘာကြီး ပူနွေးလာရခြင်း အကြောင်းရင်းပဲ", "စကားတွေ လာမများနဲ့", 
        "မင်းရဲ့ တည်ရှိမှုကကို အမှားတစ်ခုပဲ", "တော်တော် စိတ်ပျက်ဖို့ကောင်းတဲ့ကောင်",
        "မင်းပုံစံက တောမရောက် မြို့မရောက်ပဲ", "စောက်ကောင်... စကားလာမပြောနဲ့", "မင်းက လူပိုပဲ",
        "မင်းဆီမှာ ဦးနှောက်ဆိုတာ တကယ်ရှိရဲ့လား", "ဘာတွေ လာကြောင်နေတာလဲ", "မင်းကတော့ ကယ်လို့မရတော့ဘူး",
        "စောက်ရုပ်ကိုက ကံဆိုးမယ့်ရုပ်", "မင်းစကားပြောရင် လေထုညစ်ညမ်းတယ်", "တကယ့်ကို အဆင့်မရှိတာ",
        "မင်းလိုကောင်မျိုးက သမိုင်းမှာ အမှိုက်ဖြစ်ကျန်ခဲ့မှာ", "စောက်ရူး... သွားသေလိုက်တော့",
        "မင်းကို မွေးခဲ့တာထက် ကွန်ဒုံး သုံးခဲ့သင့်တာ", "ကြည့်ရတာ တော်တော် ဦးနှောက်နည်းပုံပဲ",
        "မင်းစကားတွေက အန်ဖတ်တွေလိုပဲ", "မင်းကတော့ တကယ့်ကို အရှုံးသမားစစ်စစ်ပဲ"
    ]
    
    defaults = {
        "groups": {}, "group_ids": [], "allowed_users": [OWNER_ID],
        "bully_list": bully_messages,
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
            "w_msg": "ဟိတ် {name} {group} မှ ကြိုဆိုလိုက်ပါသေးတယ်",
            "g_msg": "ဟုတ် {name} {group} ကနေ ထွက်သွားပါပြီ",
            "filters": {}
        }
    save_db()
    return db["groups"][cid]

# --- PERMISSION CHECKS ---
async def is_admin(update: Update):
    if update.effective_chat.type == "private": return True
    m = await update.effective_chat.get_member(update.effective_user.id)
    return m.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

async def check_perm(update: Update):
    if update.effective_user.id not in db["allowed_users"]:
        await update.message.reply_text("<blockquote>ဟိတ်မင်းမှာ command များသုံးစွဲခွင့်မရှိသေးဘူး၊ယူချင်ရင် @Besties_with_BoD ကိုလာတောင်း🫵</blockquote>", parse_mode=ParseMode.HTML)
        return False
    return True

# --- OWNER COMMAND: ADD ALLOW ---
async def add_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Owner (Dexter) တစ်ယောက်ပဲ သုံးလို့ရမယ်
    if update.effective_user.id != OWNER_ID:
        await check_perm(update)
        return
    try:
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
        else:
            target_id = int(context.args[0])
        
        if target_id not in db["allowed_users"]:
            db["allowed_users"].append(target_id)
            save_db()
            await update.message.reply_text("<blockquote>✅ Permission ပေးလိုက်ပါပြီ။ အခုကစပြီး သူ command တွေ သုံးလို့ရပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("<blockquote>သူ့မှာ Permission ရှိပြီးသားပါ။</blockquote>", parse_mode=ParseMode.HTML)
    except:
        await update.message.reply_text("<blockquote>အသုံးပြုပုံ - /addallow [ID] (ဒါမှမဟုတ် Reply ပြန်ပါ)</blockquote>", parse_mode=ParseMode.HTML)

# --- LOOP COMMANDS: BULLY / REPLY ---
async def start_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    mode = "bully" if "bully" in update.message.text.lower() else "reply"
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    
    if not target:
        await update.message.reply_text("<blockquote>ဘယ်သူ့ကို လုပ်မှာလဲ Reply ပြန်ပေးပါဗျ။</blockquote>", parse_mode=ParseMode.HTML)
        return
    
    job_name = f"{mode}_{update.effective_chat.id}"
    
    async def loop_cb(ctx):
        phrase = random.choice(db["bully_list"] if mode == "bully" else db["reply_list"])
        mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
        await ctx.bot.send_message(update.effective_chat.id, f"<blockquote>{mention} {phrase}</blockquote>", parse_mode=ParseMode.HTML)

    # အရင်ရှိနေတဲ့ Job ကို အရင်ဖျက်
    for job in context.job_queue.get_jobs_by_name(job_name):
        job.schedule_removal()

    context.job_queue.run_repeating(loop_cb, interval=3, name=job_name)
    await update.message.reply_text(f"<blockquote>🔥 {mode} စတင်ပါပြီ...</blockquote>", parse_mode=ParseMode.HTML)

async def stop_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    chat_id = str(update.effective_chat.id)
    found = False
    for job in context.job_queue.jobs():
        if chat_id in job.name:
            job.schedule_removal()
            found = True
    await update.message.reply_text("<blockquote>ရပ်လိုက်ပါပြီ။</blockquote>" if found else "<blockquote>ရပ်စရာ Loop မရှိပါဘူး။</blockquote>", parse_mode=ParseMode.HTML)

# --- ADD TO LISTS ---
async def add_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    new_text = " ".join(context.args)
    if not new_text: return
    if "addbully" in update.message.text.lower():
        db["bully_list"].append(new_text)
        msg = "Bully စာသားအသစ် ထည့်ပြီးပါပြီ"
    else:
        db["reply_list"].append(new_text)
        msg = "Reply စာသားအသစ် ထည့်ပြီးပါပြီ"
    save_db()
    await update.message.reply_text(f"<blockquote>✅ {msg}</blockquote>", parse_mode=ParseMode.HTML)

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
    is_leave = m_change.new_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]

    if is_join:
        text = gs["w_msg"].format(name=name_only, group=group_name)
        await context.bot.send_message(m_change.chat.id, f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML)
    elif is_leave:
        text = gs["g_msg"].format(name=name_only, group=group_name)
        await context.bot.send_message(m_change.chat.id, f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML)

# --- ANTI-LINK ---
async def handle_msgs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    text = (update.message.text or update.message.caption or "").lower()
    user = update.effective_user

    if re.search(r'(https?://|t\.me|www\.)', text) and not await is_admin(update):
        try:
            await update.message.delete()
            mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
            await context.bot.send_message(update.effective_chat.id, f"<blockquote>link မပို့နဲ့ မshareနဲ့👉 {mention}</blockquote>", parse_mode=ParseMode.HTML)
        except: pass

# --- OTHER TOOLS ---
async def get_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text.lower()
    if "myid" in cmd: await update.message.reply_text(f"<blockquote>သင့် ID: <code>{update.effective_user.id}</code></blockquote>", parse_mode=ParseMode.HTML)
    elif "gpid" in cmd: await update.message.reply_text(f"<blockquote>GP ID: <code>{update.effective_chat.id}</code></blockquote>", parse_mode=ParseMode.HTML)
    elif "/id" in cmd:
        target = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
        await update.message.reply_text(f"<blockquote>User ID: <code>{target.id}</code></blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler(["bully", "reply"], start_loop))
    app.add_handler(CommandHandler(["stopbully", "stopreply"], stop_loop))
    app.add_handler(CommandHandler(["addbully", "addreply"], add_to_list))
    app.add_handler(CommandHandler(["myid", "gpid", "id"], get_ids))
    
    app.add_handler(ChatMemberHandler(member_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_msgs))
    
    print("Bot is ready and running...")
    app.run_polling(allowed_updates=["message", "chat_member"])

if __name__ == "__main__":
    main()
