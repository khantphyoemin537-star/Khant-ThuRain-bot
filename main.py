import logging
import asyncio
import random
import os
from pymongo import MongoClient
from flask import Flask
from threading import Thread
from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes
)

# --- Keep Alive ---
app_flask = Flask('')
@app_flask.route('/')
def home():
    return "Bot is Alive!"

def run():
    port = int(os.environ.get("PORT", 7860))
    app_flask.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURATION ---
TOKEN = "YOUR_BOT_TOKEN_HERE"
OWNER_ID = 6015356597
MONGO_URI = "YOUR_MONGO_URI_HERE"

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
                "စောက်ရူး... မင်းရဲ့ ဦးနှောက်က သုတ်ပိုးတွေနဲ့ပဲ ပြည့်နေတာလား",   
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
"ဒီemotနဲ့မင်းကိုbullyနေတာ🤪"
            ],
            "registered_groups": [],
            "filters": {},
            "settings": {"antilink": False}
        }
        collection.insert_one(data)
    return data

def update_db(key, value):
    collection.update_one({"_id": "config"}, {"$set": {key: value}})

# --- IS ADMIN CHECK ---
async def is_admin(update: Update):
    data = get_data()
    if update.effective_user.id in data["allowed_users"]:
        return True
    await update.message.reply_text("❌ မင်းမှာ bot သုံးခွင့်မရှိသေးဘူး။", quote=True)
    return False

# --- WELCOME & GOODBYE ---
async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    for member in update.message.new_chat_members:
        mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
        await update.message.reply_text(f"ဟိတ် {mention}! <b>{chat.title}</b> မှ ကြိုဆိုလိုက်ပါတယ်!", parse_mode=ParseMode.HTML, quote=True)
        data = get_data()
        if chat.id not in data["registered_groups"]:
            data["registered_groups"].append(chat.id)
            update_db("registered_groups", data["registered_groups"])

async def goodbye_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.message.left_chat_member
    if member:
        mention = f'<a href="tg://user?id={member.id}">{member.first_name}</a>'
        await update.message.reply_text(f"{mention} ထွက်သွားပါပြီ။ <b>{update.effective_chat.title}</b>", parse_mode=ParseMode.HTML, quote=True)

# --- FILTERS ---
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if len(context.args) < 2:
        return await update.message.reply_text("သုံးနည်း: /addfilter [keyword] [response]", quote=True)
    keyword, reply = context.args[0].lower(), " ".join(context.args[1:])
    data = get_data()
    filters_dict = data.get("filters", {})
    filters_dict[keyword] = reply
    update_db("filters", filters_dict)
    await update.message.reply_text(f"✅ Filter ထည့်ပြီးပါပြီ: {keyword}", quote=True)

# --- BULLY LOOP ---
async def start_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply someone နှင့် /bully သုံးပါ", quote=True)
    
    target = update.message.reply_to_message.from_user
    mention = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
    job_name = f"bully_{update.effective_chat.id}_{target.id}"
    
    for job in context.job_queue.get_jobs_by_name(job_name):
        job.schedule_removal()
    
    await update.message.reply_text(f"😎 Bully start: {mention}", parse_mode=ParseMode.HTML, quote=True)
    data = get_data()
    bully_list = data["bully_list"]
    index = 0

    async def bully_loop(ctx):
        nonlocal index
        if index >= len(bully_list): index = 0
        phrase = bully_list[index]
        index += 1
        try:
            await ctx.bot.send_message(update.effective_chat.id, f"{mention} {phrase}", parse_mode=ParseMode.HTML)
        except: pass

    context.job_queue.run_repeating(bully_loop, interval=3, name=job_name)

async def stop_bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    jobs = [job for job in context.job_queue.jobs() if "bully_" in job.name and str(update.effective_chat.id) in job.name]
    if not jobs: return await update.message.reply_text("❌ Bully loop မတွေ့ပါ", quote=True)
    for j in jobs: j.schedule_removal()
    await update.message.reply_text("✅ Bully loop ရပ်လိုက်ပါပြီ", quote=True)

async def add_bully_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    phrase = " ".join(context.args)
    if not phrase: return await update.message.reply_text("❌ Phrase ထည့်ပါ", quote=True)
    data = get_data()
    data["bully_list"].append(phrase)
    update_db("bully_list", data["bully_list"])
    await update.message.reply_text("✅ Bully စာသားအသစ်ထည့်ပြီးပါပြီ။", quote=True)

# --- MUTE / UNMUTE ---
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message: return await update.message.reply_text("❌ Reply someone လုပ်ပါ", quote=True)
    user_id = update.message.reply_to_message.from_user.id
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, user_id, ChatPermissions(can_send_messages=False))
        await update.message.reply_text("🔇 Mute လုပ်ပြီးပါပြီ", quote=True)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}", quote=True)

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if not update.message.reply_to_message: return await update.message.reply_text("❌ Reply someone လုပ်ပါ", quote=True)
    user_id = update.message.reply_to_message.from_user.id
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, user_id, 
            ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
        )
        await update.message.reply_text("✅ Mute ဖြေပြီးပါပြီ", quote=True)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}", quote=True)

# --- MESSAGE MONITOR ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    data = get_data()
    text = update.message.text.lower()
    filters_dict = data.get("filters", {})
    if text in filters_dict:
        await update.message.reply_text(filters_dict[text], quote=True)

# --- ADD ALLOWED USER ---
async def add_allowed_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("❌ သုံးနိုင်မယ့်သူက Owner ပဲဖြစ်ရမယ်။", quote=True)
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply someone with /addallow", quote=True)
    
    try:
        target_id = update.message.reply_to_message.from_user.id
        data = get_data()
        if target_id not in data["allowed_users"]:
            data["allowed_users"].append(target_id)
            update_db("allowed_users", data["allowed_users"])
            await update.message.reply_text(f"✅ User {target_id} ကို allow လုပ်ပြီးပါပြီ။ သူက /bully, /stopbully, /addbully သုံးလို့ရပါပြီ။", quote=True)
        else:
            await update.message.reply_text("❌ သူက 이미 allowed user ဖြစ်ပြီးသားပါ။", quote=True)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}", quote=True)

# --- ID COMMANDS ---
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Your ID: {update.effective_user.id}", quote=True)

async def gpid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💬 Chat ID: {update.effective_chat.id}", quote=True)

async def id_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return await update.message.reply_text("❌ Reply someone လုပ်ပါ", quote=True)
    user_id = update.message.reply_to_message.from_user.id
    await update.message.reply_text(f"🆔 Replied User ID: {user_id}", quote=True)

# --- SEND TO ALL GROUPS ---
async def send_all_gp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return await update.message.reply_text("❌ Owner only command", quote=True)
    text = " ".join(context.args)
    if not text: return await update.message.reply_text("❌ စာသားထည့်ပါ", quote=True)
    data = get_data()
    for chat_id in data["registered_groups"]:
        try:
            await context.bot.send_message(chat_id, text)
        except: pass
    await update.message.reply_text("✅ စာပို့ပြီးပါပြီ", quote=True)

# --- HELP COMMAND ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📌 **Bot Commands List**

**General:**
/myid - ကိုယ့် ID ရှာဖို့
/gpid - ဒီ Chat ID ရှာဖို့
/id - Reply လုပ်ပြီး User ID ရှာဖို့

**Admin / Owner Only:**
/addallow - Reply someone လုပ်ပြီး allowed user ထည့်
/sendallgp [text] - စာတိုင်း registered groups အားလုံးသို့ ပို့

**Filters:**
/addfilter [keyword] [response] - Filter ထည့်

**Mute / Unmute:**
/mute - Reply someone လုပ်ပြီး mute
/unmute - Reply someone လုပ်ပြီး unmute

**Bully:**
/bully - Reply someone လုပ်ပြီး bully စတင်
/stopbully - Bully loop ရပ်
/addbully [phrase] - Bully စာသားအသစ်ထည့်
"""
    try:
        await context.bot.send_message(chat_id=update.effective_user.id, text=help_text, parse_mode=ParseMode.MARKDOWN)
        if update.effective_chat.type != "private":
            await update.message.reply_text("✅ Check your DM for bot commands list!", quote=True)
    except:
        await update.message.reply_text("❌ Can't send DM. Start bot first.", quote=True)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Command Handlers
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("gpid", gpid))
    app.add_handler(CommandHandler("id", id_reply))
    app.add_handler(CommandHandler("addallow", add_allowed_user))
    app.add_handler(CommandHandler("sendallgp", send_all_gp))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addfilter", add_filter))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))
    app.add_handler(CommandHandler("bully", start_bully))
    app.add_handler(CommandHandler("stopbully", stop_bully))
    app.add_handler(CommandHandler("addbully", add_bully_phrase))
    
    # Message Handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_user))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    
    print("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
