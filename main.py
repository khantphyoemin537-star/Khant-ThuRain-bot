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
TARGET_GP_ID = -1003864912245 

# --- DATABASE LOGIC ---
def load_db():
    # မင်းပို့ထားတဲ့ bully စာသားတွေအကုန် တစ်လုံးမကျန် ပြန်ထည့်ထားပါတယ်
    hardcoded_bully = [
        "မင်းရုပ်က error တစ်ခုပဲ", "Young Master Khant ThuRain ရဲ့ ခြေဖျားကို မီအောင် အရင် ကြိုးစားလိုက်ဦး",
        "မအေလိုး... Young Master ရဲ့ အရှိန်အဝါအောက်မှာ မင်းက ဖုန်မှုန့်လောက်တောင် တန်ဖိုးမရှိဘူး",
        "စောက်ရူး... မင်းရဲ့ ဦးနှောက်က သုတ်ပိုးတွေနဲ့ပဲ ပြည့်နေတာလား",
        "မင်းအမေကို ငါလိုးတာ ခါးတောင်ကျိုးနေပြီ စောက်ဆင့်မရှိတဲ့ကောင်",
        "မင်းရုပ်က error တစ်ခုပဲ", "မင်းအမေအားသုဘအတွက်ဘယ်လောက်လှူဒါန်းရမလဲ",
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
        "လေးလိုးမသား", "ငါလိုးမသား", "လီးလိုးမသား", "ပန်းသေမသားခွေးမသားလေးငိုတာလားစောက်ရူးမအေလိုးတေတောသားခွေးမသား",
        "မင်းမေ စောက်ဖုတ်လိုးမသား ငါလိုးလိုးမသား ခွေးရူးမသား", "စောက်ရူးလိုးမသား",
        "ငကြောင်မသား", "ရေသန့်ဘူးနှစ်ခါလိုးမသား", "မီလုံးလိုးမသား ဂျွန်ပြန်လိုးမသား",
        "ရေငုပ်တာလား", "ရေကူးတာလား", "ရေသောက်တာလား", "ရေချိုးတာလား", "စောက်ပေါ",
        "ငတိ", "ကျွန်ပိန်း", "ခွေးပိန်း", "ရှော", "ကြောက်သွားပြီထင်တယ်", "စာပြန်လေး",
        "ပြေးတာလား", "ချော်လဲတာလား", "နှေးတယ်", "တဗဲ့", "ဆရာခေါ်", "ချစ်သား",
        "ပါပါးခေါ်", "ဘိုင်တစ်", "စာစီပြ", "ရေငုပ်တော်ချက်", "ရေထဲထိလိုက်ဖမ်းမှာနော်",
        "ငပိန်းလေး", "ပြေးတိုင်းမလွတ်ဘူး", "သုပ်ကြောင်", "သုပ်ရည်သောက်ပြီးမွေးလာတဲ့ကောင်",
        "မင်းအဖေ ကွန်ပေါက်တယ်ထင်တယ်", "ညဏ်မမှီဘူး", "သုံးစားလို့မရဘူး", "ချစ်သား",
        "ပညာမဲ့", "လေ့လာမူအားနည်းတယ်", "နင်းပြား", "မင်းရဲ့ချေပမူဒါအကုန်ဘဲလား",
        "မထိရောက်ဘူး", "ပိန်းဥလေး", "ဂူအောင်းတာလား", "အင်အားသူံးတာလား", "ပြေးစမ်း",
        "ဖြစ်ထွန်းမူမရှိဘူး", "နောက်ပေါက်", "ကွန်ကြောင်", "ကျွန်စုပ်", "ခွေးတိုးပေါက်ကကောင်",
        "ခုန်ကိုက်ခြင်တာလား", "ထရံအိမ်နဲ့ကောင်", "ဆင်းရဲသား", "ဆက်ဟောင်", "လက်တုန်နေတာလား",
        "ငိုပြ", "ငါပြောလို့ငိုတာဆို", "ဖာသည်မသား", "လိပ်လိုးမသား", "နွားလိုးမသား",
        "လောက်လိုးမသား", "ဖားလိုးမသား", "ဆန်ကုန်မြေလေး", "ဆရာသခင်ကိုပြန်တောင်းပန်စမ်း",
        "ခြေမစုပ်", "မင်းအမေကဖာသည်မဆို", "ကြက်ပေါ", "ငမိုက်သား", "အရာရာအင်အားသုံးစရာမလို",
        "စောက်ရူး", "လိပ်မသား", "Typယှဥ်မလား", "ဟားမယ်", "Knယှဥ်မလား", "ဒီဘိတ်မယ်",
        "အောက်လုံး", "မင်းချေပမူ မထိရောက်ဘူး", "မပြေးနဲ့", "ဘယ်ကောင်မှမကယ်နိုင်တော့ဘူး",
        "ငါ့သား", "မင်းအားကိုးရတဲ့ကောင်တွေခေါ်လာခဲ့", "စောက်ပိန်း အားကိုးမဲ့နေပီလား"
    ]
    defaults = {
        "allowed_users": [OWNER_ID],
        "bully_list": list(set(hardcoded_bully)) # Duplicate တွေ ဖယ်ထားပေးတယ်
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

async def check_perm(update: Update):
    if update.effective_user.id in db["allowed_users"]: return True
    await update.message.reply_text("<blockquote>ဟိတ်မင်းမှာ command များသုံးစွဲခွင့်မရှိသေးဘူး၊ယူချင်ရင် @Besties_with_BoD ကိုလာတောင်း🫵</blockquote>", parse_mode=ParseMode.HTML)
    return False

async def start_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return

    job_name = f"bully_{update.effective_chat.id}"
    for j in context.job_queue.get_jobs_by_name(job_name): j.schedule_removal()
    
    starter_mention = f'<a href="tg://user?id={update.effective_user.id}">{update.effective_user.first_name}</a>'
    target_mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
    await update.message.reply_text(f"<blockquote>ဟုတ် {starter_mention} သူက bully ဆိုလို့ ငါစ bully ပြီ။</blockquote>", parse_mode=ParseMode.HTML)

    async def loop_cb(ctx: ContextTypes.DEFAULT_TYPE):
        if db["bully_list"]:
            phrase = random.choice(db["bully_list"])
            await ctx.bot.send_message(update.effective_chat.id, f"<blockquote>{target_mention} {phrase}</blockquote>", parse_mode=ParseMode.HTML)

    context.job_queue.run_repeating(loop_cb, interval=3, name=job_name)

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    job_name = f"bully_{update.effective_chat.id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    if current_jobs:
        for job in current_jobs: job.schedule_removal()
        await update.message.reply_text("<blockquote>✅ Bully ရပ်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def remove_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_perm(update): return
    target_text = ""
    if update.message.reply_to_message and update.message.reply_to_message.text:
        raw = update.message.reply_to_message.text
        target_text = re.sub(r'^.*? ', '', raw).strip()
    elif context.args:
        target_text = " ".join(context.args).strip()

    if target_text in db["bully_list"]:
        db["bully_list"].remove(target_text)
        save_db()
        await update.message.reply_text(f"<blockquote>🗑️ '{target_text}' ကို ဖျက်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    else:
        # Partial match
        found = False
        for item in db["bully_list"]:
            if target_text and target_text in item:
                db["bully_list"].remove(item)
                save_db()
                found = True
                break
        if found:
            await update.message.reply_text("<blockquote>🗑️ ဖျက်ပြီးပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("<blockquote>ဖျက်စရာစာသား မတွေ့ပါ။</blockquote>", parse_mode=ParseMode.HTML)

async def get_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    reply_id = update.message.reply_to_message.from_user.id if update.message.reply_to_message else "None"
    
    text = (f"👤 Your ID: {user_id}\n👥 Group ID: {chat_id}\n🎯 Reply ID: {reply_id}")
    await update.message.reply_text(f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML)

async def handle_msgs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    text = update.message.text or update.message.caption
    if not text or text.startswith("/"): return
    
    if update.effective_chat.id == TARGET_GP_ID and update.effective_user.id in db["allowed_users"]:
        if text not in db["bully_list"]:
            db["bully_list"].append(text)
            save_db()

def main():
    # Job Queue support ပါတဲ့ builder
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("bully", start_bully))
    app.add_handler(CommandHandler("stopbully", stop_bully))
    app.add_handler(CommandHandler("removebully", remove_bully))
    app.add_handler(CommandHandler("id", get_ids))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msgs))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__": main()
