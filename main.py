import logging
import asyncio
import random
import os
import re
from datetime import timedelta
from pymongo import MongoClient
from flask import Flask
from threading import Thread
from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes
)

# --- UPTIMEROBOT & FLASK (Keep Alive) ---
app_flask = Flask('')
@app_flask.route('/')
def home(): return "Bot is Alive!"
def run():
    # Railway/Hugging Face အတွက် Port ကို အလိုအလျောက်ယူမယ်
    port = int(os.environ.get("PORT", 7860))
    app_flask.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURATION ---
TOKEN = "8575371720:AAHjBOXArgOAtBUqPY_8xnZjQe-w4Dk4uRc"
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client['bully_bot_db']
collection = db['bot_data']

def get_data():
    data = collection.find_one({"_id": "config"})
    if not data:
        data = {
            "_id": "config",
            "allowed_users": [OWNER_ID],
            "bully_list": [
    "မင်းရုပ်က error တစ်ခုပဲ", 
    "ငါ့ရဲ့ ခြေဖျားကို မီအောင် အရင် ကြိုးစားလိုက်ဦး",
    "မအေလိုး...ငါတို့ရဲ့ အရှိန်အဝါအောက်မှာ မင်းက ဖုန်မှုန့်လောက်တောင် တန်ဖိုးမရှိဘူး",
    "စောက်ရူး... မင်းရဲ့ ဦးနှောက်က သုတ်ပိုးတွေနဲ့ပဲ ပြည့်နေတာလား",
    "မင်းအမေကို ငါလိုးတာ ခါးတောင်ကျိုးနေပြီ စောက်ဆင့်မရှိတဲ့ကောင်",
    "မင်းအမေအသုဘအတွက်ဘယ်လောက်လှူဒါန်းရမလဲ",
    "ဖာအိုမသားစကားပြောရင် ဒေါက်မကျိုးဘူးရိုက်ချိုးလိုက်မယ်", 
    "ငါလိုးမသားစပ်ဖြဲဖြဲနဲ့ရောတာလား",
    "မအေလိုးနာနာကိုက်အိယောင်ဝါးမလုပ်နဲ့", 
    "ငါရိုက်လိုက်လို့ဘစ်ပါကျွတ်နေမယ်",
    "ဥာဏ်တိမ်တာက မင်းအမေဖာသည်မဆီကရတဲ့ တစ်ခုတည်းသောအမွေလား", 
    "Kpay numberလွှဲထားဒီဘက်ဖုန်းလှည့်မင်းညီစဖုတ်လိုးနဲ့လွှဲထိုးအောင်လို့",
    "ကလစ်ဆိုမင်းမေခေါင်းပန်လိုက်ကွာ", 
    "မအေလိုးငါ့စာတေခိုးဖတ်နေတာလား",
    "ဂုဏ်ယူပါတယ်သင်ဟာဒီနေ့သင့်အမေကိုငါကြိမ်မြောက်လိင်ဆက်ဆံပြီးနေ့စဉ်တာဝန်ကိုပြီးမြောက်ခဲ့ပြီ",
    "သင့်အမေဖာသည်မဆုကိုစွတ်ခူးတဲ့ဆုငွေကိုယခုလာထုတ်နိုင်မည်ဖြစ်သည်",
    "သဖွတ်ရိုက်ဖားမင်းဦးနှောက်ကဖင်နဲ့စပ်စုဖို့လောက်ပဲသိတာ",
    "မသိချင်ဘူးမင်းငါ့ကိုပြန်ဆဲရင်ဖာသည်မသားပဲ", 
    "မအေလိုးကိုက်စရာရှိတာကိုက်မဖားနဲ့",
    "မင်းအမေစပတ်ကြီးချက်ခြင်းခွဲလိုက်တာပြဲသွားရောလား", 
    "မင်းအမေbodyကောက်ကြောင်းကိုငါ့တော်ကီတစ်ကြောင်းနဲ့သိမ်းလိုက်ပြီ",
    "ဘာကိုရပ်ကြည့်နေတာလဲအားထည့်ကိုက်လေမအေလိုး", 
    "လီးထိပ်ဆားအိုးလိုးပေးလို့အာရုံငါးပါးချုပ်ငြိမ်းသွားမယ်",
    "စောက်ဝက်ကြီးဖော်ပြီလား", 
    "ငါလိုးမသားအူကြောင်ကြောင်မလုပ်နဲ့",
    "လီးထိပ်မော်တာတပ်ပြီးမင်းအမေစပတ်တည်းလိုးလိုက်မယ်",
    "ငါကိုအံတုချင်သလိုလိုမာန်ဖီချင်သလိုလိုနဲ့မအေလိုးအဆဲခံgeneration bully dogကြီး",
    "ပျော့ညပ်ညပ်ဝက်ကလေးအဆဲခံရတာများပြီးကြောက်သွားတာလားငေါင်သွားတာလားသတ်သေချင်စိတ်ပေါက်သွားတာလားနှလုံးမျိုးစိတ်ခေါင်းဆောင်လေးဟပ်",
    "မင်းစောက်ခွက်ကရုက္ခစိုးကိုဖုတ်တိုက်လိုးထားသလိုရုပ်နဲ့ငါ့ကိုလာစိတ်ကောက်နေတာလားး",
    "မင်းအမေကုလားမစောက်ဖုတ်ကို ခေါစာပစ်ရင်တောင်သရဲမလိုဘူးမအေလိုးကြားလား",
    "အာခံတာလားတပည့်မိုက်", 
    "နောက်မဆဲတော့ဘူးမင်းကိုမင်းအမေကိုလိုးပြီ",
    "တောက်တဲ့လှည်းနင်းသံနဲ့မင်းအမေဖာသည်ဆိုတာကိုဖင်ကုန်းအော်မနေနဲ့", 
    "ဗျာဖာသည်မသား",
    "လီးပဲပြန်ဆဲစမ်း", 
    "စောက်သုံးမကျဘူးအစကပြန်ရေး", 
    "မအေလိုးခုမှကွယ်ပါလား",
    "ဗျာမင်းကြီးဒေါ်စောက်ဖတ်", 
    "မသိချင်ဘူးမင်းစအိုဖွာလန်ကျဲကြောင်း",
    "မင်းအမေသုတ်ပိုးကြောင်ပြီးမင်းကိုမွေးလာအဲ့တာကြောင့်မင်းဦးနှောက်ထဲမှာသုတ်ပိုးတေပြည့်နှက်နေတာစောက်သုတ်ပိုးလိုးမသား",
    "မင်းပျော့လှချည်လားသေချာကိုက်လေအစွယ်မထွက်သေးဘူးဖြစ်နေတယ်ငါချွေးတောင်မထွက်သေးဘူးဘယ်လိုလုပ်မလဲဘောမ",
    "ဘုရားသခင်လီးကျွေးပါစေ", 
    "လဒစ်တော်နဲ့အရစ်ဖော်ပေးမယ်", 
    "ဟေ့ကောင်ခွေးသိုး",
    "ဖာမူလိုးမသားကြီး", 
    "ဆင်းရဲသားရာကျူးမှာပဲနေ", 
    "မင်းနှမတရုတ်လိုးလို့လား",
    "အေးမင်းအဖွားကိုပြန်လိုးတာဆို", 
    "မင်းကနှင်းပြားလေးလား", 
    "ငါလိုးမသားရာ",
    "မင်းရှင်းပြတာကလည်းမင်းညီမနဲ့ငါနဲ့လိုးတဲ့အတိုင်းပဲ", 
    "ကမ္ဘာစံချိန်ချိုးပြီးဖာခံသွားတဲ့မင်းအမေဖာသည်မကြီး",
    "မင်းကိုအဆဲခံရဆုံးဆုပေးလိုက်ပြီ", 
    "ဒီemotနဲ့မင်းကိုbullyနေတာ🤪"],
            "registered_groups": [],
            "filters": {},
            "settings": {"antilink": False}
        }
        collection.insert_one(data)
    return data

def update_db(key, value):
    collection.update_one({"_id": "config"}, {"$set": {key: value}})

async def is_admin(update: Update):
    data = get_data()
    if update.effective_user.id in data["allowed_users"]: return True
    await update.message.reply_text("<blockquote>ညီမင်းမှာ သုံးခွင့်မရှိဘူး🫵</blockquote>", parse_mode=ParseMode.HTML)
    return False

# --- WELCOME & GOODBYE ---
async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    for member in update.message.new_chat_members:
        mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
        await update.message.reply_text(f"<blockquote>ဟိတ် {mention}! <b>{chat.title}</b> မှ ကြိုဆိုလိုက်ပါတယ်!</blockquote>", parse_mode=ParseMode.HTML)

async def goodbye_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.message.left_chat_member
    if member:
        mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
        await update.message.reply_text(f"<blockquote>ဟုတ် {mention} ထွက်သွားပါပြီ။ <b>{update.effective_chat.title}</b> ကတော့ သတိရနေမှာပါ။</blockquote>", parse_mode=ParseMode.HTML)

# --- FILTERS ---
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if len(context.args) < 2: return await update.message.reply_text("သုံးနည်း: /addfilter [စာသား] [ပြန်ဖြေမည့်စာ]")
    keyword, reply = context.args[0].lower(), " ".join(context.args[1:])
    data = get_data()
    filters_dict = data.get("filters", {})
    filters_dict[keyword] = reply
    update_db("filters", filters_dict)
    await update.message.reply_text(f"<blockquote>✅ Filter ထည့်ပြီးပါပြီ: {keyword}</blockquote>", parse_mode=ParseMode.HTML)

# --- BULLY FUNCTIONS ---
async def start_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
    job_name = f"bully_{update.effective_chat.id}"
    
    for j in context.job_queue.get_jobs_by_name(job_name): j.schedule_removal()
    await update.message.reply_text(f"<blockquote>ငါစ bully ပြီ {mention}။</blockquote>", parse_mode=ParseMode.HTML)

    async def loop_cb(ctx):
        data = get_data()
        phrase = random.choice(data["bully_list"])
        try: await ctx.bot.send_message(update.effective_chat.id, f"<blockquote>{mention} {phrase}</blockquote>", parse_mode=ParseMode.HTML)
        except: pass
    context.job_queue.run_repeating(loop_cb, interval=4, name=job_name)

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    jobs = context.job_queue.get_jobs_by_name(f"bully_{update.effective_chat.id}")
    for j in jobs: j.schedule_removal()
    await update.message.reply_text("<blockquote>✅ Bully ရပ်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def add_bully_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    phrase = " ".join(context.args)
    if phrase:
        data = get_data()
        data["bully_list"].append(phrase)
        update_db("bully_list", data["bully_list"])
        await update.message.reply_text("<blockquote>✅ Bully စာသားအသစ် ထည့်ပြီးပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

# --- MUTE/UNMUTE ---
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message: return
    user_id = update.message.reply_to_message.from_user.id
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, user_id, ChatPermissions(can_send_messages=False))
        await update.message.reply_text("<blockquote>🔇 Mute လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    except: pass

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message: return
    user_id = update.message.reply_to_message.from_user.id
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, user_id, ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
        await update.message.reply_text("<blockquote>🔊 Mute ဖြည်လိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
    except: pass

# --- MESSAGE MONITOR (Filters & Security) ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    data = get_data()
    text = update.message.text.lower()
    
    # 1. Filters
    filters_dict = data.get("filters", {})
    if text in filters_dict:
        await update.message.reply_text(f"<blockquote>{filters_dict[text]}</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers အစဉ်လိုက် ထည့်မယ်
    app.add_handler(CommandHandler("id", lambda u,c: u.message.reply_text(f"🆔 ID: {u.effective_user.id}")))
    app.add_handler(CommandHandler("addfilter", add_filter))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))
    app.add_handler(CommandHandler("bully", start_bully))
    app.add_handler(CommandHandler("stopbully", stop_bully))
    app.add_handler(CommandHandler("addbully", add_bully_phrase))
    
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_user))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    
    print("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
