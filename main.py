import asyncio
import logging
import random
import os
import threading
import re
from datetime import datetime
import pytz
from flask import Flask
from pymongo import MongoClient
from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import (
    ChannelParticipantAdmin, 
    ChannelParticipantCreator, 
    ChannelParticipantsAdmins
)
from html import escape as escape_html

# --- DNS FIX FOR MONGODB (Image 1 Error Fix) ---
try:
    import dns.resolver
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1']
except:
    pass

# --- FLASK KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "BoDx Sovereign System Active!"
def run_flask(): 
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION ---
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"
APP_ID = 30765851
APP_HASH = '235b0bc6f03767302dc75763508f7b75'
BOT_TOKEN = "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU"
SPECIFIC_GROUP = -1003580630981 # Log group
TARGET_CHAT_ID = -1003806830045 # Main group for filters
TZ = pytz.timezone('Asia/Yangon')

# --- DATABASE SETUP ---
client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]
filters_col = db["filters"]
allow_col = db["allowed_users"]
groups_col = db["active_groups"]
admin_tasks_col = db["admin_tasks"]

# --- BOT CLIENT SETUP ---
bot_client = TelegramClient('bot_session', APP_ID, APP_HASH)

# --- HELPERS ---
bot_bully_tasks = {}
save_status = False

def bq(text): 
    return f"<blockquote><b>{text}</b></blockquote>"

def owner_tag(): 
    return f"<a href='tg://user?id={OWNER_ID}'>Khant Thu Rain (Dexter Morgan)</a>"

def is_allowed(user_id):
    if user_id == OWNER_ID: return True
    return allow_col.find_one({"user_id": user_id}) is not None

# Unified Admin Checker
async def check_admin(chat_id, user_id):
    if user_id == OWNER_ID: return True
    try:
        # chat_id သို့မဟုတ် entity ကို လက်ခံနိုင်ရန်
        admins = await bot_client.get_participants(chat_id, filter=ChannelParticipantsAdmins)
        return any(admin.id == user_id for admin in admins)
    except: return False

# ==========================================
# 🛡️ FILTERS & PROTECTION (BIO/LINK)
# ==========================================

@bot_client.on(events.NewMessage(chats=TARGET_CHAT_ID))
async def protection_logic(event):
    if not event.text or event.sender_id == OWNER_ID: return
    
    sender = await event.get_sender()
    text = event.text.strip()
    
    # 1. Bio Keyword Filter
    if text in ["Bio", "ဘိုင်အို", "ဘိုင်-အို"]:
        if not await check_admin(event.chat_id, event.sender_id):
            await event.delete()
            return await event.respond(bq("Bruhh bruhh bioမှာဘာဖြစ်တာလဲ မသိချင်ပါဘူး စာကိုဖျက်လိုက်ပြီ။နောက်တစ်ခါ bioရင် ဒီလိုဖြစ်မယ် 🤰🫃"), parse_mode='html')

    # 2. Link Filter
    urls = re.findall(r'(https?://\S+|www\.\S+)', text)
    if urls:
        if await check_admin(event.chat_id, event.sender_id):
            full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
            mention = f"<a href='tg://user?id={sender.id}'>{full_name}</a>"
            all_links = "\n".join(urls)
            reason = text
            for u in urls: reason = reason.replace(u, "")
            
            await event.delete()
            admin_msg = f"Linkပို့တဲ့သူ- {mention}\nသူပို့တဲ့Link- {all_links}\nReason - {escape_html(reason.strip() or 'No message')}"
            await event.respond(bq(admin_msg), parse_mode='html')
        else:
            await event.delete()
            await event.respond(bq("ဘာ link မှမပို့နဲ့ မရဘူး၊မင်းlinkကို ငါဖျက်လိုက်ပြီ🫵"), parse_mode='html')

# ==========================================
# 🔵 WELCOME & ACTION LOGIC
# ==========================================

@bot_client.on(events.ChatAction)
async def welcome_goodbye(event):
    chat = await event.get_chat()
    bot_me = await bot_client.get_me()
    bot_mention = f"<a href='tg://user?id={bot_me.id}'>{escape_html(bot_me.first_name)}</a>"
    safe_title = escape_html(chat.title)

    if event.user_added or event.user_joined:
        if bot_me.id in event.user_ids:
            groups_col.update_one({"chat_id": chat.id}, {"$set": {"title": chat.title}}, upsert=True)
            msg1 = f"ဟိတ် OWNER နဲ့ Admins တို့ မင်းတို့ရဲ့ ဒီ {safe_title} ထဲကို ထည့်သုံးပေးလို့ ကျေးဇူးတင်ပါတယ်! အသုံးလိုကောင်းလိုနိုင်တဲ့ command များယူထားမယ်ဆိုရင် {bot_mention} ရဲ့ Creator {owner_tag()} ရဲ့ Dm (သို့မဟုတ်) @Besties_with_BoD ကိုလာရောက်ပါ!!!"
            await bot_client.send_message(chat.id, bq(msg1), parse_mode='html')
            
            try: members = getattr(chat, 'participants_count', 'Unknown')
            except: members = "Unknown"
            msg2 = f"မင်္ဂလာပါ {safe_title}က သူငယ်ချင်းတို့ မင်းတို့ရဲ့\n{bot_mention}ကို အောက်ပါ Group က ထည့်သုံးထားပါသေးတယ်\n\nGroup Name - {safe_title}\nGroup ID - <code>{chat.id}</code>\nMembers အရေအတွက် - {members}\nBot Creator - {owner_tag()}"
            await bot_client.send_message(SPECIFIC_GROUP, bq(msg2), parse_mode='html')
        else:
            for uid in event.user_ids:
                if uid != bot_me.id:
                    try:
                        u = await bot_client.get_entity(uid)
                        u_mention = f"<a href='tg://user?id={u.id}'>{escape_html(u.first_name)}</a>"
                        await bot_client.send_message(event.chat_id, bq(f"ဟိတ် {u_mention} ... {safe_title} ကနေ ကြိုဆိုလိုက်ပါတယ်!! 🫵😎 စကားဝင်ပြော၊သီချင်းနားထောင်၊ရည်းစားရှာ အပေါင်းအသင်းရှာ ကြိုက်တာလုပ်!"), parse_mode='html')
                    except: pass

    elif event.user_left or event.user_kicked:
        try:
            u = await bot_client.get_entity(event.user_id)
            u_mention = f"<a href='tg://user?id={u.id}'>{escape_html(u.first_name)}</a>"
            await bot_client.send_message(event.chat_id, bq(f"ဟုတ် ထွက်သွားလိုက်ပါသေးတယ် {u_mention}!သူ့အစားပိုကောင်းတဲ့သူကိုရှာပြီး ခင်မင်ပေးလိုက်!!!"), parse_mode='html')
        except: pass

# ==========================================
# 👮‍♂️ ADMIN COMMANDS (/adm, /done, /mute)
# ==========================================

@bot_client.on(events.NewMessage(pattern=r'^/adm(?:@\w+)?(?:\s+(.*))?'))
async def admin_mention(event):
    if event.is_private or not await check_admin(event.chat_id, event.sender_id): return
    
    input_text = event.pattern_match.group(1) or "Attention Admins!"
    chat_title = escape_html(event.chat.title)
    mentions = f"<b>🛡️ {chat_title} ADMINS:</b>\n\n"
    
    try:
        admins = await bot_client.get_participants(event.chat_id, filter=ChannelParticipantsAdmins)
        for user in admins:
            if not user.bot:
                name = escape_html(user.first_name) or "Admin"
                mentions += f"• <a href='tg://user?id={user.id}'>{name}</a>\n"
        
        await event.respond(bq(f"{mentions}\n💬 <b>Message:</b> {escape_html(input_text)}"), parse_mode='html')
    except Exception as e:
        await event.respond(bq(f"Error: {e}"), parse_mode='html')

@bot_client.on(events.NewMessage(pattern=r'^/done(?:@\w+)?$'))
async def admin_done(event):
    if not await check_admin(event.chat_id, event.sender_id): return
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    admin_tasks_col.update_one({"chat_id": event.chat_id}, {"$set": {"last_done": today}}, upsert=True)
    u = await event.get_sender()
    name = escape_html(u.first_name) or "Chief"
    await event.respond(bq(f"<a href='tg://user?id={u.id}'>{name}</a> ဟုတ်ပြီ သတိပေးတာကို ဒီနေ့အတွက် ရပ်လိုက်ပြီ"), parse_mode='html')

@bot_client.on(events.NewMessage(pattern=r'^/mute(?:@\w+)?$'))
async def mute_user(event):
    if not await check_admin(event.chat_id, event.sender_id): return
    reply = await event.get_reply_message()
    if reply:
        try:
            await bot_client.edit_permissions(event.chat_id, reply.sender_id, send_messages=False)
            await event.respond(bq(f"<a href='tg://user?id={reply.sender_id}'>{escape_html(reply.sender.first_name)}</a> ကို Mute လိုက်ပါပြီ!"), parse_mode='html')
        except Exception as e: await event.respond(bq(f"Error: {e}"), parse_mode='html')

@bot_client.on(events.NewMessage(pattern=r'^/unmute(?:@\w+)?$'))
async def unmute_user(event):
    if not await check_admin(event.chat_id, event.sender_id): return
    reply = await event.get_reply_message()
    if reply:
        try:
            await bot_client.edit_permissions(event.chat_id, reply.sender_id, send_messages=True)
            await event.respond(bq(f"<a href='tg://user?id={reply.sender_id}'>{escape_html(reply.sender.first_name)}</a> စာပြန်ပို့!Unmute လုပ်ပြီးပြီ!"), parse_mode='html')
        except Exception as e: await event.respond(bq(f"Error: {e}"), parse_mode='html')

# ==========================================
# 🤖 BULLY & SYSTEM
# ==========================================

@bot_client.on(events.NewMessage(pattern=r'^/b(?:@\w+)?$'))
async def bot_bully(event):
    if not is_allowed(event.sender_id): return
    reply = await event.get_reply_message()
    if not reply: return
    if reply.sender_id == OWNER_ID:
        return await event.respond(bq("ဟားတိုက်ခံရတော့မယ်၊မင်းမှာ Creator ကို bully ခွင့်မရှိဘူးညီ 🫵😎"), parse_mode='html')

    chat_id = event.chat_id
    bot_bully_tasks[chat_id] = True
    t = await reply.get_sender()
    mention = f"<a href='tg://user?id={t.id}'>{escape_html(t.first_name)}</a>"
    while bot_bully_tasks.get(chat_id):
        words = [w.get("text") for w in filters_col.find() if w.get("text")]
        if words:
            try: await bot_client.send_message(chat_id, bq(f"{mention} {random.choice(words)}"), reply_to=reply.id, parse_mode='html')
            except: break
        await asyncio.sleep(0.4)

@bot_client.on(events.NewMessage(pattern=r'^/sb(?:@\w+)?$'))
async def stop_bot_bully(event):
    if not is_allowed(event.sender_id): return
    bot_bully_tasks[event.chat_id] = False
    await event.reply(bq("အခုနားဆိုလို့နားလိုက်မယ်၊စောက်ချိုးမပြေရင်ထပ်ဆဲပေးမယ်"), parse_mode='html')
@bot_client.on(events.NewMessage(pattern=r'^/addallow(?:@\w+)?$'))
async def add_allow(event):
    # Owner တစ်ဦးတည်းသာ သုံးခွင့်ရှိသည်
    if event.sender_id != OWNER_ID: return
    
    reply = await event.get_reply_message()
    if reply:
        # Database ထဲသို့ သိမ်းဆည်းခြင်း
        allow_col.update_one(
            {"user_id": reply.sender_id}, 
            {"$set": {"name": reply.sender.first_name}}, 
            upsert=True
        )
        name = escape_html(reply.sender.first_name)
        await event.reply(bq(f"{name} ကို Allow List ထည့်ပြီးပါပြီ! ✅"), parse_mode='html')
    else:
        await event.reply(bq("Allow ပေးချင်တဲ့သူကို Reply ထောက်ပြီးမှ Command ရိုက်ပါ Chief!"), parse_mode='html')
@bot_client.on(events.NewMessage(pattern=r'^/allowlist(?:@\w+)?$'))
async def allow_list(event):
    # Owner တစ်ဦးတည်းသာ သုံးခွင့်ရှိသည်
    if event.sender_id != OWNER_ID: return
    
    users = list(allow_col.find())
    if users:
        msg = "<b>✅ Allowed Users List:</b>\n\n"
        for u in users:
            name = escape_html(u.get('name', 'Unknown'))
            user_id = u.get('user_id')
            msg += f"• <a href='tg://user?id={user_id}'>{name}</a> (<code>{user_id}</code>)\n"
    else:
        msg = "Allow List မှာ မရှိသေးပါ။"
        
    await event.reply(bq(msg), parse_mode='html')

@bot_client.on(events.NewMessage(pattern=r'^/send(?:@\w+)?\s+(.*)'))
async def broadcast(event):
    if event.sender_id != OWNER_ID: return
    text = event.pattern_match.group(1)
    success = 0
    for g in groups_col.find():
        try:
            await bot_client.send_message(g['chat_id'], bq(text), parse_mode='html')
            success += 1
        except: pass
    await event.respond(bq(f"ငါ မင်းပို့ခိုင်းတဲ့messageတွေကို သေချာပို့ပေးလိုက်ပြီ! 📢\nပို့ဆောင်ပြီးစီးသော Group အရေအတွက်: {success}"), parse_mode='html')

# ==========================================
# 🚀 STARTUP & REMINDER
# ==========================================

async def hourly_reminder():
    await asyncio.sleep(30)
    while True:
        today = datetime.now(TZ).strftime("%Y-%m-%d")
        for g in groups_col.find():
            try:
                task = admin_tasks_col.find_one({"chat_id": g['chat_id']})
                if not task or task.get("last_done") != today:
                    mentions = ""
                    async for admin in bot_client.iter_participants(g['chat_id'], filter=ChannelParticipantsAdmins):
                        if not admin.bot: mentions += f"<a href='tg://user?id={admin.id}'>{escape_html(admin.first_name)}</a> "
                    msg = f"{mentions}\n\nပြီးဒီနေ့ မင်းလူ 5ယောက်ထည့်ပေးရမယ်၊မထည့်ရသေးရင် ထည့်ပေးပါအုံး၊Group ရဲ့ နေ့စဉ် active ဖြစ်မှုနဲ့ member ဝင်ရောက်နှုန်းပိုများဖို့က မင်းတို့လက်ထဲမှာ မူတည်နေတာကြောင့် ကြိုးစားပေးပါ။🤍 လူထည့်ပြီးရင် Admin တစ်ယောက်ယောက် ငါ့ကို /done လို့ reply ထောက်ပြီးပြော ဒါဆိုဒီနေ့အတွက် သတိပေးတာရပ်လိုက်မယ်🫵"
                    await bot_client.send_message(g['chat_id'], bq(msg), parse_mode='html')
            except: pass
        await asyncio.sleep(3600)

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ BoDx Sovereign System Online!")
    asyncio.create_task(hourly_reminder())
    await bot_client.run_until_disconnected()

if __name__ == "__main__":
    try: asyncio.run(main())
    except: pass
