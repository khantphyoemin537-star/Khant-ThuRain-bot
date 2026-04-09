import asyncio
import logging
import random
import os
import threading
from datetime import datetime
import pytz
from flask import Flask
from pymongo import MongoClient
from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator

# --- FLASK KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "BoD Sovereign System Active!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION ---
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"
APP_ID = 30765851
APP_HASH = '235b0bc6f03767302dc75763508f7b75'
BOT_TOKEN = "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU"
SPECIFIC_GROUP = -1003580630981
TZ = pytz.timezone('Asia/Yangon')

# --- DATABASE SETUP ---
client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]
filters_col = db["filters"]
allow_col = db["allowed_users"]
groups_col = db["active_groups"]
g_filters_col = db["group_filters"]
admin_tasks_col = db["admin_tasks"]

bot_client = TelegramClient('bot_session', APP_ID, APP_HASH)

# --- UTILS ---
bot_bully_tasks = {}
save_status = False

def bq(text): return f"<blockquote><b>{text}</b></blockquote>"
def owner_tag(): return f"<a href='tg://user?id={OWNER_ID}'>Khant Thu Rain (Dexter Morgan)</a>"

def is_allowed(user_id):
    if user_id == OWNER_ID: return True
    return allow_col.find_one({"user_id": user_id}) is not None

async def check_admin(chat, user_id):
    if user_id == OWNER_ID: return True
    try:
        p = await bot_client(GetParticipantRequest(chat, user_id))
        return isinstance(p.participant, (ChannelParticipantAdmin, ChannelParticipantCreator))
    except: return False

# ==========================================
# 🔵 WELCOME & ACTION LOGIC
# ==========================================

@bot_client.on(events.ChatAction)
async def welcome_goodbye(event):
    chat = await event.get_chat()
    bot_me = await bot_client.get_me()
    bot_mention = f"<a href='tg://user?id={bot_me.id}'>{bot_me.first_name}</a>"

    if event.user_added or event.user_joined:
        if bot_me.id in event.user_ids:
            groups_col.update_one({"chat_id": chat.id}, {"$set": {"title": chat.title}}, upsert=True)
            msg1 = f"ဟိတ် OWNER နဲ့ Admins တို့ မင်းတို့ရဲ့ ဒီ {chat.title} ထဲကို ထည့်သုံးပေးလို့ ကျေးဇူးတင်ပါတယ်! အသုံးလိုကောင်းလိုနိုင်တဲ့ command များယူထားမယ်ဆိုရင် {bot_mention} ရဲ့ Creator {owner_tag()} ရဲ့ Dm (သို့မဟုတ်) @Besties_with_BoD ကိုလာရောက်ပါ!!!"
            await bot_client.send_message(chat.id, bq(msg1), parse_mode='html')
            
            try: members = getattr(chat, 'participants_count', 'Unknown')
            except: members = "Unknown"
            msg2 = f"မင်္ဂလာပါ {chat.title}က သူငယ်ချင်းတို့ မင်းတို့ရဲ့\n{bot_mention}ကို အောက်ပါ Group က ထည့်သုံးထားပါသေးတယ်\n\nGroup Name - {chat.title}\nGroup ID - <code>{chat.id}</code>\nMembers အရေအတွက် - {members}\nBot Creator - {owner_tag()}"
            await bot_client.send_message(SPECIFIC_GROUP, bq(msg2), parse_mode='html')
        else:
            for uid in event.user_ids:
                if uid != bot_me.id:
                    try:
                        u = await bot_client.get_entity(uid)
                        u_mention = f"<a href='tg://user?id={u.id}'>{u.first_name}</a>"
                        await bot_client.send_message(event.chat_id, bq(f"ဟိတ် {u_mention} ... {chat.title} ကနေ ကြိုဆိုလိုက်ပါတယ်!! 🫵😎 စကားဝင်ပြော၊သီချင်းနားထောင်၊ရည်းစားရှာ အပေါင်းအသင်းရှာ ကြိုက်တာလုပ်ဗျ!"), parse_mode='html')
                    except: pass

    elif event.user_left or event.user_kicked:
        try:
            u = await bot_client.get_entity(event.user_id)
            u_mention = f"<a href='tg://user?id={u.id}'>{u.first_name}</a>"
            await bot_client.send_message(event.chat_id, bq(f"ဟုတ် ထွက်သွားလိုက်ပါသေးတယ် {u_mention}! RIP🌾🌾 btw နှင်းဆီပန်းရှာမတွေ့လို့"), parse_mode='html')
        except: pass

# ==========================================
# 🛡️ UTILITY COMMANDS (/b, /sb, /addallow, etc.)
# ==========================================

# 1. Save Mode (စာမှတ်ခြင်း)
@bot_client.on(events.NewMessage(pattern=r'^/saveon$'))
async def save_on(event):
    global save_status
    if event.sender_id != OWNER_ID: return
    save_status = True
    await event.reply(bq("Save Mode ON ✅ (စာတွေလိုက်မှတ်နေပါပြီ)"), parse_mode='html')

@bot_client.on(events.NewMessage(pattern=r'^/saveoff$'))
async def save_off(event):
    global save_status
    if event.sender_id != OWNER_ID: return
    save_status = False
    await event.reply(bq("Save Mode OFF 🛑 (စာမှတ်ခြင်း ရပ်လိုက်ပါပြီ)"), parse_mode='html')

@bot_client.on(events.NewMessage())
async def save_messages(event):
    global save_status
    if save_status and event.text and not event.text.startswith('/'):
        filters_col.update_one({"text": event.text}, {"$set": {"text": event.text}}, upsert=True)

# 2. Bot Bully (/b & /sb) with Owner Protection
@bot_client.on(events.NewMessage(pattern=r'^/b$'))
async def bot_bully(event):
    if not is_allowed(event.sender_id): return
    reply = await event.get_reply_message()
    if not reply: return
    if reply.sender_id == OWNER_ID:
        return await event.respond(bq("ဟားတိုက်ခံရတော့မယ်၊မင်းမှာ Creator ကို bully ခွင့်မရှိဘူးညီ 🫵😎"), parse_mode='html')

    chat_id = event.chat_id
    bot_bully_tasks[chat_id] = True
    t = reply.sender
    mention = f"<a href='tg://user?id={t.id}'>{t.first_name}</a>"
    while bot_bully_tasks.get(chat_id):
        words = [w.get("text") for w in list(filters_col.find()) if w.get("text")]
        if words:
            try: await bot_client.send_message(chat_id, bq(f"{mention} {random.choice(words)}"), reply_to=reply.id, parse_mode='html')
            except: break
        await asyncio.sleep(0.8)

@bot_client.on(events.NewMessage(pattern=r'^/sb$'))
async def stop_bot_bully(event):
    if not is_allowed(event.sender_id): return
    bot_bully_tasks[event.chat_id] = False
    await event.reply(bq("Bot Bully Stopped! 🛑"), parse_mode='html')

# 3. Allow List (/addallow, /allowlist)
@bot_client.on(events.NewMessage(pattern=r'^/addallow$'))
async def add_allow(event):
    if event.sender_id != OWNER_ID: return
    reply = await event.get_reply_message()
    if reply:
        allow_col.update_one({"user_id": reply.sender_id}, {"$set": {"name": reply.sender.first_name}}, upsert=True)
        await event.reply(bq(f"{reply.sender.first_name} ကို Allow List ထည့်ပြီးပါပြီ! ✅"), parse_mode='html')

@bot_client.on(events.NewMessage(pattern=r'^/allowlist$'))
async def allow_list(event):
    if event.sender_id != OWNER_ID: return
    users = list(allow_col.find())
    msg = "<b>✅ Allowed Users List:</b>\n" + "\n".join([f"• <a href='tg://user?id={u['user_id']}'>{u['name']}</a>" for u in users]) if users else "Allow List မှာ မရှိသေးပါ။"
    await event.reply(bq(msg), parse_mode='html')

# 4. Broadcast (/send) with success count
@bot_client.on(events.NewMessage(pattern=r'^/send\s+(.*)'))
async def broadcast(event):
    if event.sender_id != OWNER_ID: return
    text = event.pattern_match.group(1)
    success = 0
    for g in groups_col.find():
        try:
            await bot_client.send_message(g['chat_id'], bq(text), parse_mode='html')
            success += 1
        except: pass
    await event.respond(bq(f"Broadcast အောင်မြင်ပါသည်! 📢\nပို့ဆောင်ပြီးစီးသော Group အရေအတွက်: {success}"), parse_mode='html')

# ==========================================
# 🛡️ SYSTEM PROTECTION (ADMIN TOOLS)
# ==========================================

# 1. Anti-Slash (Cleaner)
@bot_client.on(events.NewMessage())
async def anti_slash(event):
    exclude = ['/b', '/sb', '/adm', '/done', '/saveon', '/saveoff', '/send', '/addallow', '/allowlist', '/addfilter', '/mute', '/unmute']
    if event.text and event.text.startswith('/') and not any(event.text.startswith(x) for x in exclude):
        await asyncio.sleep(2)
        try:
            u = await event.get_sender()
            await event.delete()
            msg = await event.respond(bq(f"<a href='tg://user?id={u.id}'>{u.first_name}</a> ဟိတ် chat သန့်ရှင်းအောင် ငါမင်းတို့ /နဲ့စတဲ့ message တွေဖျက်ပေးလိုက်တယ်"))
            await asyncio.sleep(5)
            await msg.delete()
        except: pass

# 2. Admin Mention (/adm)
@bot_client.on(events.NewMessage(pattern=r'^/adm\s+(.*)'))
async def admin_mention(event):
    if not await check_admin(event.chat_id, event.sender_id): return
    text = event.pattern_match.group(1)
    mentions = "<b>🛡️ ADMINS LIST:</b>\n"
    async for user in bot_client.iter_participants(event.chat_id, filter=ChannelParticipantAdmin):
        if not user.bot: mentions += f"• <a href='tg://user?id={user.id}'>{user.first_name}</a>\n"
    await event.respond(bq(f"{mentions}\n💬 Admin Message: {text}"), parse_mode='html')

# Mute / Unmute command နေရာမှာ ဒါလေးနဲ့ အစားထိုးပါ
@bot_client.on(events.NewMessage(pattern=r'^/mute$'))
async def mute_user(event):
    if not await check_admin(event.chat_id, event.sender_id): return
    reply = await event.get_reply_message()
    if reply:
        try:
            # တိတိကျကျ specify လုပ်ပြီး mute တာပါ
            await bot_client.edit_permissions(
                event.chat_id, 
                reply.sender_id, 
                until_date=None, 
                send_messages=False
            )
            await event.respond(bq(f"<a href='tg://user?id={reply.sender_id}'>{reply.sender.first_name}</a> ကို Mute လိုက်ပါပြီ! 🔇"), parse_mode='html')
        except Exception as e: 
            await event.respond(bq(f"Error: {e}"))

@bot_client.on(events.NewMessage(pattern=r'^/unmute$'))
async def unmute_user(event):
    if not await check_admin(event.chat_id, event.sender_id): return
    reply = await event.get_reply_message()
    if reply:
        try:
            # Right အားလုံးကို True ပြန်ပေးပြီး unmute တာပါ
            await bot_client.edit_permissions(
                event.chat_id, 
                reply.sender_id, 
                until_date=None, 
                send_messages=True
            )
            await event.respond(bq(f"<a href='tg://user?id={reply.sender_id}'>{reply.sender.first_name}</a> ကို Unmute ပြုလုပ်ပြီးပါပြီ! 🔊"), parse_mode='html')
        except Exception as e: 
            await event.respond(bq(f"Error: {e}"))

# 4. Hourly Admin Task (/done)
@bot_client.on(events.NewMessage(pattern=r'^/done$'))
async def admin_done(event):
    if not await check_admin(event.chat_id, event.sender_id): return
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    admin_tasks_col.update_one({"chat_id": event.chat_id}, {"$set": {"last_done": today}}, upsert=True)
    u = await event.get_sender()
    await event.respond(bq(f"<a href='tg://user?id={u.id}'>{u.first_name}</a> ဟုတ်ပြီ သတိပေးတာကို ဒီနေ့အတွက် ရပ်လိုက်ပြီ"), parse_mode='html')

async def hourly_reminder():
    while True:
        today = datetime.now(TZ).strftime("%Y-%m-%d")
        for g in groups_col.find():
            task = admin_tasks_col.find_one({"chat_id": g['chat_id']})
            if not task or task.get("last_done") != today:
                mentions = ""
                async for admin in bot_client.iter_participants(g['chat_id'], filter=ChannelParticipantAdmin):
                    if not admin.bot: mentions += f"<a href='tg://user?id={admin.id}'>{admin.first_name}</a> "
                msg = f"{mentions}\n\nပြီးဒီနေ့ မင်းလူ 5ယောက်ထည့်ပေးရမယ်၊မထည့်ရသေးရင် ထည့်ပေးပါအုံး၊Group ရဲ့ နေ့စဉ် active ဖြစ်မှုနဲ့ member ဝင်ရောက်နှုန်းပိုများဖို့က မင်းတို့လက်ထဲမှာ မူတည်နေတာကြောင့် ကြိုးစားပေးပါ။🤍 လူထည့်ပြီးရင် Admin တစ်ယောက်ယောက် ငါ့ကို /done လို့ reply ထောက်ပြီးပြော ဒါဆိုဒီနေ့အတွက် သတိပေးတာရပ်လိုက်မယ်🫵"
                try: await bot_client.send_message(g['chat_id'], bq(msg), parse_mode='html')
                except: pass
        await asyncio.sleep(3600)

# ==========================================
# 🚀 SYSTEM STARTUP
# ==========================================
async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ BoDx Sovereign System Online!")
    asyncio.create_task(hourly_reminder())
    await bot_client.run_until_disconnected()

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
