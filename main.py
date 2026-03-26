import logging
import asyncio
import json
import os
import re
import random
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes
)

# --- CONFIGURATION ---
TOKEN = "8575371720:AAHjBOXArgOAtBUqPY_8xnZjQe-w4Dk4uRc" 
OWNER_ID = 6015356597
DB_FILE = "bot_database.json"

# --- DATABASE LOGIC ---
def load_db():
    hardcoded_bully = [
        "မင်းရုပ်က error တစ်ခုပဲ", "ငါ့ရဲ့ ခြေဖျားကို မီအောင် အရင် ကြိုးစားလိုက်ဦး",
        "မအေလိုး...ငါတို့ရဲ့ အရှိန်အဝါအောက်မှာ မင်းက ဖုန်မှုန့်လောက်တောင် တန်ဖိုးမရှိဘူး",
        "စောက်ရူး... မင်းရဲ့ ဦးနှောက်က သုတ်ပိုးတွေနဲ့ပဲ ပြည့်နေတာလား",
        "မင်းအမေကို ငါလိုးတာ ခါးတောင်ကျိုးနေပြီ စောက်ဆင့်မရှိတဲ့ကောင်",
        "မင်းအမေအသုဘအတွက်ဘယ်လောက်လှူဒါန်းရမလဲ",
        "ဖာအိုမသားစကားပြောရင် ဒေါက်မကျိုးဘူးရိုက်ချိုးလိုက်မယ်", "ငါလိုးမသားစပ်ဖြဲဖြဲနဲ့ရောတာလား",
        "မအေလိုးနာနာကိုက်အိယောင်ဝါးမလုပ်နဲ့", "ငါရိုက်လိုက်လို့ဘစ်ပါကျွတ်နေမယ်",
        "ဥာဏ်တိမ်တာက မင်းအမေဖာသည်မဆီကရတဲ့ တစ်ခုတည်းသောအမွေလား", "Kpay numberလွှဲထားဒီဘက်ဖုန်းလှည့်မင်းညီစဖုတ်လိုးနဲ့လွှဲထိုးအောင်လို့",
        "ကလစ်ဆိုမင်းမေခေါင်းပန်လိုက်ကွာ", "မအေလိုးငါ့စာတေခိုးဖတ်နေတာလား",
        "ဂုဏ်ယူပါတယ်သင်ဟာဒီနေ့သင့်အမေကိုငါကြိမ်မြောက်လိင်ဆက်ဆံပြီးနေ့စဉ်တာဝန်ကိုပြီးမြောက်ခဲ့ပြီ",
        "သင့်အမေဖာသည်မဆုကိုစွတ်ခူးတဲ့ဆုငွေကိုယခုလာထုတ်နိုင်မည်ဖြစ်သည်",
        "သဖွတ်ရိုက်ဖားမင်းဦးနှောက်ကဖင်နဲ့စပ်စုဖို့လောက်ပဲသိတာ",
        "မသိချင်ဘူးမင်းငါ့ကိုပြန်ဆဲရင်ဖာသည်မသားပဲ", "မအေလိုးကိုက်စရာရှိတာကိုက်မဖားနဲ့",
        "မင်းအမေစပတ်ကြီးချက်ခြင်းခွဲလိုက်တာပြဲသွားရောလား", "မင်းအမေbodyကောက်ကြောင်းကိုငါ့တော်ကီတစ်ကြောင်းနဲ့သိမ်းလိုက်ပြီ",
        "ဘာကိုရပ်ကြည့်နေတာလဲအားထည့်ကိုက်လေမအေလိုး", "လီးထိပ်ဆားအိုးလိုးပေးလို့အာရုံငါးပါးချုပ်ငြိမ်းသွားမယ်",
        "စောက်ဝက်ကြီးဖော်ပြီလား", "ငါလိုးမသားအူကြောင်ကြောင်မလုပ်နဲ့",
        "လီးထိပ်မော်တာတပ်ပြီးမင်းအမေစပတ်တည်းလိုးလိုက်မယ်",
        "ငါကိုအံတုချင်သလိုလိုမာန်ဖီချင်သလိုလိုနဲ့မအေလိုးအဆဲခံgeneration bully dogကြီး",
        "ပျော့ညှပ်ညှပ်ဝက်ကလေးအဆဲခံရတာများပြီးကြောက်သွားတာလားငေါင်သွားတာလားသတ်သေချင်စိတ်ပေါက်သွားတာလားနှလုံးမျိုးစိတ်ခေါင်းဆောင်လေးဟပ်",
        "မင်းစောက်ခွက်ကရုက္ခစိုးကိုဖုတ်တိုက်လိုးထားသလိုရုပ်နဲ့ငါ့ကိုလာစိတ်ကောက်နေတာလားး",
        "မင်းအမေကုလားမစောက်ဖုတ်ကို ခေါစာပစ်ရင်တောင်သရဲမလိုဘူးမအေလိုးကြားလား",
        "အာခံတာလားတပည့်မိုက်", "နောက်မဆဲတော့ဘူးမင်းကိုမင်းအမေကိုလိုးပြီ",
        "တောက်တဲ့လှည်းနင်းသံနဲ့မင်းအမေဖာသည်ဆိုတာကိုဖင်ကုန်းအော်မနေနဲ့", "ဗျာဖာသည်မသား",
        "လီးပဲပြန်ဆဲစမ်း", "စောက်သုံးမကျဘူးအစကပြန်ရေး", "မအေလိုးခုမှကွယ်ပါလား",
        "ဗျာမင်းကြီးဒေါ်စောက်ဖတ်", "မသိချင်ဘူးမင်းစအိုဖွာလန်ကျဲကြောင်း",
        "မင်းအမေသုတ်ပိုးကြောင်ပြီးမင်းကိုမွေးလာအဲ့တာကြောင့်မင်းဦးနှောက်ထဲမှာသုတ်ပိုးတေပြည့်နှက်နေတာစောက်သုတ်ပိုးလိုးမသား",
        "မင်းပျော့လှချည်လားသေချာကိုက်လေအစွယ်မထွက်သေးဘူးဖြစ်နေတယ်ငါချွေးတောင်မထွက်သေးဘူးဘယ်လိုလုပ်မလဲဘောမ",
        "ဘုရားသခင်လီးကျွေးပါစေ", "လဒစ်တော်နဲ့အရစ်ဖော်ပေးမယ်", "ဟေ့ကောင်ခွေးသိုး",
        "ဖာမူလိုးမသားကြီး", "ဆင်းရဲသားရာကျူးမှာပဲနေ", "မင်းနှမတရုတ်လိုးလို့လား",
        "အေးမင်းအဖွားကိုပြန်လိုးတာဆို", "မင်းကနှင်းပြားလေးလား", "ငါလိုးမသားရာ",
        "မင်းရှင်းပြတာကလည်းမင်းညီမနဲ့ငါနဲ့လိုးတဲ့အတိုင်းပဲ", "ကမ္ဘာစံချိန်ချိုးပြီးဖာခံသွားတဲ့မင်းအမေဖာသည်မကြီး",
        "မင်းကိုအဆဲခံရဆုံးဆုပေးလိုက်ပြီ", "ဒီemotနဲ့မင်းကိုbullyနေတာ🤪"
    ]
    defaults = {"allowed_users": [OWNER_ID], "bully_list": hardcoded_bully}
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

# --- WELCOME & GOODBYE LOGIC ---
async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            await update.effective_chat.send_message("<blockquote>ဟဲလို! ကျွန်တော်က Dexter ရဲ့ Bully Bot ပါ။</blockquote>", parse_mode=ParseMode.HTML)
        else:
            mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
            msg = f"ဟိတ် {mention} {update.effective_chat.title} ကနေ ကြိုဆိုလိုက်ပါတယ်!"
            await update.effective_chat.send_message(f"<blockquote>{msg}</blockquote>", parse_mode=ParseMode.HTML)

async def goodbye_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    member = update.message.left_chat_member
    if member:
        mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
        msg = f"ဟုတ် {mention} ထွက်သွားလိုက်ပါသေးတယ်"
        await update.effective_chat.send_message(f"<blockquote>{msg}</blockquote>", parse_mode=ParseMode.HTML)

# --- PERMISSION MANAGEMENT ---
async def add_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args and context.args[0].isdigit():
        target_id = int(context.args[0])

    if target_id:
        if target_id not in db["allowed_users"]:
            db["allowed_users"].append(target_id)
            save_db()
            await update.message.reply_text(f"<blockquote>✅ User <code>{target_id}</code> ကို ပါမစ်ပေးလိုက်ပြီ။</blockquote>", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("<blockquote>ဒီလူက ပါမစ်စာရင်းထဲမှာ ရှိပြီးသားဖြစ်ပါတယ်။</blockquote>", parse_mode=ParseMode.HTML)

# --- BULLY LOGIC ---
async def start_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["allowed_users"]:
        await update.message.reply_text("<blockquote>ညီမင်းမှာ သုံးခွင့်မရှိဘူး၊သုံးမယ်ဆို @Besties_with_BoD ကိုလာတောင်း🫵</blockquote>", parse_mode=ParseMode.HTML)
        return

    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target:
        await update.message.reply_text("<blockquote>ဘယ်သူ့ကို bully ရမလဲ? စာတစ်ကြောင်းကို reply ပြန်ပြီး /bully လို့ ရိုက်ပါ။</blockquote>")
        return

    job_name = f"bully_{update.effective_chat.id}"
    for j in context.job_queue.get_jobs_by_name(job_name): 
        j.schedule_removal()
    
    target_mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
    await update.message.reply_text(f"<blockquote>ငါစ bully ပြီ။ {target_mention} တော့ သေပြီသာမှတ်။</blockquote>", parse_mode=ParseMode.HTML)

    async def loop_cb(ctx):
        phrase = random.choice(db["bully_list"])
        try:
            await ctx.bot.send_message(update.effective_chat.id, f"<blockquote>{target_mention} {phrase}</blockquote>", parse_mode=ParseMode.HTML)
        except: pass

    context.job_queue.run_repeating(loop_cb, interval=3, name=job_name)

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["allowed_users"]:
        await update.message.reply_text("<blockquote>ညီမင်းမှာ သုံးခွင့်မရှိဘူး၊သုံးမယ်ဆို @Besties_with_BoD ကိုလာတောင်း🫵</blockquote>", parse_mode=ParseMode.HTML)
        return

    job_name = f"bully_{update.effective_chat.id}"
    found = False
    for job in context.job_queue.get_jobs_by_name(job_name):
        job.schedule_removal()
        found = True
            
    if found:
        await update.message.reply_text("<blockquote>✅ Bully ရပ်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("<blockquote>လက်ရှိမှာ bully နေတာ မရှိပါဘူး။</blockquote>", parse_mode=ParseMode.HTML)

async def get_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"<blockquote>👤 ID: <code>{update.effective_user.id}</code>\n👥 Group ID: <code>{update.effective_chat.id}</code></blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN RUNNER ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_user))
    app.add_handler(CommandHandler("addallow", add_allow))
    app.add_handler(CommandHandler("bully", start_bully))
    app.add_handler(CommandHandler("stopbully", stop_bully))
    app.add_handler(CommandHandler("id", get_ids))
    print("Bot is up and running...")
    app.run_polling()

if __name__ == "__main__":
    main()
