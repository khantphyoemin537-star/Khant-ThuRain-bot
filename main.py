import logging
import asyncio
import random
import os
from pymongo import MongoClient
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes
)

# --- Keep Alive ---
app_flask = Flask('')
@app_flask.route('/')
def home(): return "Bot is Alive!"
def run():
    port = int(os.environ.get("PORT", 7860))
    app_flask.run(host='0.0.0.0', port=port)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURATION ---
TOKEN = "8575371720:AAHjBOXArgOAtBUqPY_8xnZjQe-w4Dk4uRc"
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"
TARGET_CHAT_ID = -1003864912245 

client = MongoClient(MONGO_URI)
db = client['bully_bot_db']
collection = db['bot_data']

def get_data():
    data = collection.find_one({"_id": "config"})
    if not data:
        data = {
            "_id": "config",
            "allowed_users": [OWNER_ID],
            "bully_list": ["မင်းရုပ်က error တစ်ခုပဲ", "ဟိတ်ကောင် ​စောက်ရူး", "မင်းရုပ်က error တစ်ခုပဲ",   
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
"ဒီemojiနဲ့မင်းကိုbullyနေတာ🤪",],
            "autosave": False,
            "registered_groups": [],
            "filters": {}
        }
        collection.insert_one(data)
    return data

def update_db(key, value):
    collection.update_one({"_id": "config"}, {"$set": {key: value}})

# --- PERMISSION CHECK ---
async def is_admin(update: Update):
    data = get_data()
    if update.effective_user.id in data["allowed_users"]:
        return True
    await update.message.reply_text("<blockquote>ညီမင်းမှာ သုံးခွင့်မရှိဘူး၊သုံးမယ်ဆို @Besties_with_BoD ကိုလာတောင်း🫵</blockquote>", parse_mode=ParseMode.HTML)
    return False

# --- WELCOME & GOODBYE ---
async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    for member in update.message.new_chat_members:
        mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
        await update.message.reply_text(f"ဟိတ် {mention}! <b>{chat.title}</b> မှ ကြိုဆိုလိုက်ပါတယ်!", parse_mode=ParseMode.HTML)
        data = get_data()
        if chat.id not in data.get("registered_groups", []):
            groups = data.get("registered_groups", [])
            groups.append(chat.id)
            update_db("registered_groups", groups)

async def goodbye_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.message.left_chat_member
    if member:
        mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
        await update.message.reply_text(f"ဟုတ် {mention} ထွက်သွားပါပြီ။ <b>{update.effective_chat.title}</b>", parse_mode=ParseMode.HTML)

# --- BROADCAST COMMAND ---
async def send_all_gp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not context.args:
        return await update.message.reply_text("စာသားထည့်ပါ: /sendallgp [message]")
    
    msg = " ".join(context.args)
    data = get_data()
    gps = data.get("registered_groups", [])
    
    count = 0
    for gid in gps:
        try:
            await context.bot.send_message(gid, msg)
            count += 1
        except: continue
    await update.message.reply_text(f"✅ Group {count} ခုကို စာပို့ပြီးပါပြီ။")

# --- AUTO SAVE & FILTERS ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    data = get_data()

    filters_dict = data.get("filters", {})
    if text.lower() in filters_dict:
        await update.message.reply_text(filters_dict[text.lower()])

    if chat_id == TARGET_CHAT_ID and data.get("autosave", False):
        if user_id in data["allowed_users"]:
            if text not in data["bully_list"]:
                data["bully_list"].append(text)
                update_db("bully_list", data["bully_list"])

# --- COMMAND HANDLERS ---
async def add_allowed_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message:
        return await update.message.reply_text("ပါမစ်ပေးမည့်သူကို Reply ပြန်ပြီး /addallow သုံးပါ။")
    
    target_id = update.message.reply_to_message.from_user.id
    data = get_data()
    allowed = data.get("allowed_users", [])
    if target_id not in allowed:
        allowed.append(target_id)
        update_db("allowed_users", allowed)
        await update.message.reply_text(f"✅ User {target_id} ကို Bot သုံးခွင့် ပေးလိုက်ပါပြီ။")

async def autosave_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    update_db("autosave", True)
    await update.message.reply_text("✅ Auto-save ကို ဖွင့် လိုက်ပါပြီ။")

async def autosave_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    update_db("autosave", False)
    await update.message.reply_text("❌ Auto-save ကို ပိတ်လိုက်ပါပြီ။")

async def start_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply someone နှင့် /bully သုံးပါ")
    
    target = update.message.reply_to_message.from_user
    mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
    chat_id = update.effective_chat.id
    job_name = f"bully_{chat_id}"

    for job in context.job_queue.get_jobs_by_name(job_name): job.schedule_removal()
    
    await update.message.reply_text(f"😎 Bully start: {mention}", parse_mode=ParseMode.HTML)
    data = get_data()
    bully_list = data["bully_list"]

    async def bully_loop(ctx):
        phrase = random.choice(bully_list)
        try: await ctx.bot.send_message(chat_id, f"{mention} {phrase}", parse_mode=ParseMode.HTML)
        except: pass

    context.job_queue.run_repeating(bully_loop, interval=3, name=job_name)

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    job_name = f"bully_{update.effective_chat.id}"
    for j in context.job_queue.get_jobs_by_name(job_name): j.schedule_removal()
    await update.message.reply_text("✅ Bully loop ရပ်လိုက်ပါပြီ")

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Register Commands
    app.add_handler(CommandHandler("addallow", add_allowed_user))
    app.add_handler(CommandHandler("sendallgp", send_all_gp))
    app.add_handler(CommandHandler("autosave_on", autosave_on))
    app.add_handler(CommandHandler("autosave_off", autosave_off))
    app.add_handler(CommandHandler("bully", start_bully))
    app.add_handler(CommandHandler("stopbully", stop_bully))
    app.add_handler(CommandHandler("myid", lambda u,c: u.message.reply_text(f"🆔 ID: {u.effective_user.id}")))
    
    # Handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_user))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    
    print("Bot is starting with /addallow and /sendallgp...")
    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()

