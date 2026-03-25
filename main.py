import logging
import asyncio
import json
import os
import re
import random
from telegram import Update
from telegram.constants import ParseMode, ChatMemberStatus
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
        "မင်းရုပ်က error တစ်ခုပဲ", "Young Master Khant ThuRain ရဲ့ ခြေဖျားကို မီအောင် အရင် ကြိုးစားလိုက်ဦး",
        "မအေလိုး... Young Master ရဲ့ အရှိန်အဝါအောက်မှာ မင်းက ဖုန်မှုန့်လောက်တောင် တန်ဖိုးမရှိဘူး",
        "စောက်ရူး... မင်းရဲ့ ဦးနှောက်က သုတ်ပိုးတွေနဲ့ပဲ ပြည့်နေတာလား",
        "မင်းအမေကို ငါလိုးတာ ခါးတောင်ကျိုးနေပြီ စောက်ဆင့်မရှိတဲ့ကောင်",
        "မင်းအမေအားသုဘအတွက်ဘယ်လောက်လှူဒါန်းရမလဲ",
        "ဖာအိုမသားစကားပြောရင်ဒေါက်မကျိုးဘူးရိုက်ချိုးလိုက်မယ်", "ငါလိုးမသားစပ်ဖြဲဖြဲနဲ့ရောက်တာလား",
        "မအေလိုးနာနာကိုက်အိယောင်ဝါးမလုပ်နဲ့", "ငါရိုက်လိုက်လို့ဘဝပါကျွတ်နေမယ်",
        "ဥာဏ်မင်းအမေဟသသည်မဖြစ်စေနဲ့", "Kpay numberလွှဲထားဒီဘက်တိုင်မင်းညီစဖုတ်လိုးနဲ့လွဲထိုးအောင်လို့",
        "ဖာတက်ဆိုမင်းမေခေါင်းပန်လိုက်ကာ", "မအေလိုးငါစာတေခိုးဖတ်နေတာလား",
        "ဂုဏ်ယူပါတယ်သင်ဟာနေ့လျှင်သင့်အမေကိုငါကြိမ်မြောက်လိင်ဆက်ဆံပြီးနေ့စဉ်တာဝန်ကိုပြီးမြောက်ခဲ့ပြီ",
        "သင့်အမေဟာသည်မဆုကိုစွတ်ခဲတဲ့ဆုငွေကိုယခုလာထုတ်နိုင်မည်ဖြစ်သည်",
        "သဖွတ်ရိုက်ဖားမင်းဦးနှောက်ကဖင်နဲ့စပ်စုဖို့လောက်ပဲသိတာ",
        "မသိချင်ဘူးမင်းငါကိုပြန်ဆဲရင်ဖာသည်မသားပဲ", "မအေလိုးကိုစာရာရှိတာကိုက်မစားနဲ့",
        "မင်းအမေစပတ်ကြီးချက်ခြင်းခွဲလိုက်တာပြသွားရောလား", "မင်းအမေbodyကောက်ကြောင်းကိုငါ့ဖော်ကံတစ်ကြောင်းနဲ့သိမ်းလိုက်ပြီ",
        "ဘာကိုရပ်ကြည့်နေတာလဲအားထည့်ကိုက်လေမအေလိုး", "လီးထိပ်ဆားအိုးလိုးပေးလို့အာရုံငါးပါးချုပ်ငြိမ်းသွားမယ်",
        "စောက်ဝက်ကြီးဖော်ပြီလား", "ငါလိုးမသားအူကြောင်ကြောင်မလုပ်နဲ့",
        "လီးထိပ်ဖော်တာတပ်ပြီးမင်းအမေစပတ်တည်းလိုးလိုက်မယ်",
        "ငါကိုအံတုချင်သလိုလိုမာန်ဖီချင်သလိုလိုနဲ့မအေလိုးအဆဲခံgeneration bully dogကြီး",
        "ပျော့ငှက်ဝက်ကလေးအဆဲခံရတာများပြီးကြောက်သွားတာလားငေါင်သွားတာလားသတ်သေချင်စိတ်ပေါက်သွားတာလားနှလုံးမျိုးစိတ်ခေါင်းဆောင်လေးဟပ်",
        "မင်းစောက်ခွက်ကရုက္ခစိုးကိုဖုတ်တိုက်လိုးထားသလိုရုပ်နဲ့မင်းအမေမေတာငါ့ကိုလာစိတ်ကောက်နေတာလားတီး",
        "မင်းအမေကုလားမစောက်ဖုတ်ကိုခါစာဗစ်ရင်တောင်သရဲမလိုဘူးမအေလိုးကြားလားဟပ်",
        "အာခံတာလားတပည့်မိုက်", "နောက်မဆဲတော့ဘူးမင်းကိုမင်းအမေကိုလိုးပြီ",
        "တောက်တဲ့လူညှပ်မင်းသံနဲ့မင်းအမေဟာသည်ဖင်ကုန်းအော်မနေနဲ့", "ဗျာဟာသည်မသား",
        "လီးပဲပြန်ဆဲစမ်း", "စောက်သုံးမကျဘူးအစကပြန်ရေး", "မအေလိုးခုမှကွယ်ပါလား",
        "ဗျာမင်းကြီးဒေါ်စောက်ဖတ်", "မသိချင်ဘူးမင်းစအိုဖွာလန်ကျကြောင်း",
        "မင်းအမေထုတ်ပိုးကြောင်ပြီးမင်းကိုမွေးလာအဲ့တာကြောင့်မင်းဦးနှောက်ထဲမှာသုတ်ပိုးတေပြည့်နှက်နေတာစောက်သုတ်ပိုးလိုးမသား",
        "မင်းပျော့လှချင်လားသေချာကိုက်လေအရွယ်မထွက်သေးဘူးဖြစ်နေတယ်ငါချွေးတောင်မထွက်သေးဘူးဘယ်လိုလုပ်မလဲဘောမ",
        "ဘုရားသခင်လီးကျွေးပါစေ", "လဒ်တော်နဲ့အရပ်ဖော်ပေးမယ်", "ဟေ့ကောင်ခွေးသိုး",
        "ဖာမူလိုးမသားကြီး", "ဆင်းရဲသားရာကျူးမှာပဲနေ", "မင်းနှမတရုတ်လိုးလို့လား",
        "အေးမင်းအဖွားကိုပြန်လိုးတာဆို", "မင်းကနှင်းပြားလေးလား", "ငါလိုးမသားရာ",
        "မင်းရှင်ပြလည်းမင်းညီမနဲ့ငါနဲ့လိုးတဲ့အတိုင်းပဲ", "ကမ္ဘာစံချိန်ချိုးပြီးဖာခံသွားတဲ့မင်းအမေဖာသည်မကြီး",
        "မင်းကိုအဆဲခံရဆုံးဆုပေးလိုက်ပြီ", "ဒီemotနဲ့မင်းကိုbullyနေတာ",
        "တပည့်ဘယ်လိုရေးနေတာလဲသေချာရေးလေကွာစောက်သုံးမကျဘူးဖြစ်နေတယ်ခွေးမသားလေးဘာပန်ကန်တာလည်းမင်းစောက်ခွက်နဲ့ငါ့ခြေဖျားနဲ့တစ်သားတည်းဖြစ်သွားမယ်ကိုမေကိုလိုး",
        "စောက်ခွက်ကိုလေလီးနဲ့ဘယ်တစ်ဖက်ညာတစ်ဖက်ခဲထောက်ပြီးနားထဲတည့်တည့်ဟောက်ပိုးနောက်ကိုလီးနဲ့နားကြားထဲကနေကလော်ထုတ်ပေးလိုက်မယ်",
        "အခုထိကလစ်နေသေးတယ်ဆိုရင်တော့အဲ့ကလစ်မင်းအမေစောက်ဖတ်မှာညှပ်ထားလိုက်တော့အနုအညတယုတယကဗျာလာမဆန်နဲ့ကွ",
        "မင်းဘာကိုရပ်ကြည့်နေတာလဲထပ်ကိုက်လေဘာဖြစ်တာလည်းအားအင်တွေကုန်ခမ်းသွားပြီလားငါလိုးမခွေးကိုမေကိုလိုးဘာဖြစ်တာလည်းမင်းအမေဘယ်ကောင်တက်တက်လိုးလို့လည်းပြောလေငါကို",
        "အမှိုက်ပုံးထဲကခွေးအိုလိုအစာဟောင်းကိုပြန်စားနဲ့", "ကယောင်ကတမ်းစကားတွေကငါ့အတွက်တော့ကလေးကလားအိပ်မက်",
        "ငါကြောက်တာခွေးပဲရှိတယ်မင်းကိုကြောက်စေချင်ရင်ဝုတ်ဝုတ်လို့ဟောင်ပြလေ",
        "ဟိတ်ယောင်၇အိမ်ကြား၈အိမ်ကြားတေမအော်နဲ့မင်းကငါလက်ခုပ်ထဲကရေလိုပဲ",
        "ငါ့ရဲ့တော်ကီတွေကိုကော်ပီပြီးမင်းမေစပတ်ကိုဂေါ်လီနဲ့ထိုးလိုးမလို့လား",
        "မင်းမေစဖုတ်ကြီးဖွဲလိုးပြလေဖင်မကုလား", "မင်းအမေလိုးပေးလို့စိတ်ကောက်နေတာလားဟပ်တီး",
        "မင်းမေစဖုတ်ကြီးကိုတုတ်ပြီးကားစင်တင်စားဖိုမီးကင်ခွဲပြီးကျလာတဲ့အညော်ဆီကိုမင်းစောက်ခွက်ပေါ်လောင်းပီး 90kတန် usa made yeezeနဲ့အချက်၁ထောင်ရိုက်မယ်ကိုနှမကိုလိုး",
        "မင်းအမေစပတ်ကို ဓာတ်ခဲနဲ့တို့ပြီး လျှပ်စစ်စွမ်းအင်ထုတ်ယူနေတာ ကြာပြီ မအေလိုး",
        "စောက်ရူး... မင်းရဲ့ ဦးနှောက်က သုတ်ပိုးတွေနဲ့ပဲ ပြည့်နေတာလား",
        "ဖာသည်မသား... မင်းစကားပြောရင် ငါ့လီးက တောင်တောင်လာတယ် (လိုးချင်လို့)",
        "မင်းနှမစပတ်ကို လမ်းဘေးက ခွေးတွေ စုပြုံလိုးနေတာ သွားကြည့်ဦး",
        "မင်းအမေကို ငါလိုးတာ ခါးတောင်ကျိုးနေပြီ စောက်ဆင့်မရှိတဲ့ကောင်",
        "မအေလိုး... မင်းပါးစပ်ကထွက်တဲ့ စကားတိုင်းက ငါ့လီးကို လာစုပ်နေသလိုပဲ",
        "မင်းအမေ စပတ်ကြီးကို ခွဲစိတ်ပြီး ငါ့လီးနဲ့ ပြန်ချုပ်ပေးလိုက်မယ်",
        "မင်းရဲ့ IQ နဲ့က လမ်းဘေးက ခွေးတောင် မင်းအမေကို တက်လိုးသွားလိမ့်မယ်",
        "မင်းအမေကို ငါလိုးပေးလို့ မင်းက အခုလို စောက်ဖတ်လုပ်နေတာလား",
        "မင်းရဲ့ တည်ရှိမှုက ငါ့လီးထိပ်မှာတင် အဆုံးသတ်သွားသင့်တာ မအေလိုး",
        "ခွေးမသား", "ငမန်းလိုးမသား", "ကားလိုးမသား", "မျောက်လိုးမသား", "ဝက်လိုးမသာ",
        "ဒိုင်နိုဆောလိုးမသား", "ဝက်ဝံလိုးမသား", "ပုရွတ်ဆိတ်လိုးမသား", "ဆိုင်ကယ်လိုးမသား",
        "ကိုယ့်အမေသေလို့ထိုင်ငိုမသား", "ခွေးမဒိန်းကျင့်မသား", "ငမန်းလီးကြိုက်မသား",
        "မျောက်စောက်ဖုတ်တက်လိုးမသား", "ငပဲ့မသား", "ခွေးမသား", "အတူရာမင်းလိုးမသား",
        "ပုဂံလိုးမသား", "သက်မဲ့လိုးမသား", "သစ်ပင်လိုးမသား", "မင်းသားလိုးမသား",
        "လေးလိုးမသား", "ငါလိုးမသား", "လီးလိုးမသား", "ပန်းသေမသားခွေးမသားလေးငိုတာလားစောက်ရူးမအေလိုးတေတောသားခွေးမသား"
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

# --- WELCOME & GOODBYE LOGIC ---
async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            await update.message.reply_text("<blockquote>ဟဲလို! ကျွန်တော်က Dexter ရဲ့ Bully Bot ပါ။ ခေါ်ယူအသုံးပြုတဲ့အတွက် ကျေးဇူး!</blockquote>", parse_mode=ParseMode.HTML)
        else:
            mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
            group_name = update.effective_chat.title
            msg = f"ဟိတ် {mention} {group_name} ကနေ ကြိုဆိုလိုက်ပါတယ်!"
            await update.message.reply_text(f"<blockquote>{msg}</blockquote>", parse_mode=ParseMode.HTML)

async def goodbye_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.message.left_chat_member
    if member:
        mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
        msg = f"ဟုတ် {mention} ထွက်သွားလိုက်ပါသေးတယ်"
        await update.message.reply_text(f"<blockquote>{msg}</blockquote>", parse_mode=ParseMode.HTML)

# --- COMMANDS ---
async def start_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["allowed_users"]: return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return

    job_name = f"bully_{update.effective_chat.id}"
    for j in context.job_queue.get_jobs_by_name(job_name): j.schedule_removal()
    
    target_mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
    await update.message.reply_text(f"<blockquote>ငါစ bully ပြီ။ {target_mention} တော့ သေပြီသာမှတ်။</blockquote>", parse_mode=ParseMode.HTML)

    async def loop_cb(ctx):
        phrase = random.choice(db["bully_list"])
        await ctx.bot.send_message(update.effective_chat.id, f"<blockquote>{target_mention} {phrase}</blockquote>", parse_mode=ParseMode.HTML)

    context.job_queue.run_repeating(loop_cb, interval=3, name=job_name)

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["allowed_users"]: return
    
    chat_id = update.effective_chat.id
    job_name = f"bully_{chat_id}"
    
    # ပိုသေချာအောင် ရှိသမျှ job အကုန်လုံးကို ပတ်စစ်ပြီး သတ်မယ်
    all_current_jobs = context.job_queue.jobs()
    found = False
    
    for job in all_current_jobs:
        if job.name == job_name:
            job.schedule_removal()
            found = True
            
    if found:
        await update.message.reply_text("<blockquote>✅ Bully ရပ်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("<blockquote>လက်ရှိမှာ bully နေတာ မရှိပါဘူး။</blockquote>", parse_mode=ParseMode.HTML)


async def get_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = f"👤 Your ID: <code>{user_id}</code>\n👥 Group ID: <code>{chat_id}</code>"
    await update.message.reply_text(f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Welcome & Goodbye handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_user))
    
    # Commands
    app.add_handler(CommandHandler("bully", start_bully))
    app.add_handler(CommandHandler("stopbully", stop_bully))
    app.add_handler(CommandHandler("id", get_ids))
    
    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
