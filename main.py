import asyncio
import logging
import random
import os
import threading
from flask import Flask
from pymongo import MongoClient
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator, ChatBannedRights

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

SESSION_STRING = """1BVtsOIMBu7QJHcoVUPy95A99dxNDlyYLtqKA2Z3aBVZb1rzF1E4cgbeku73GsFjKib11Xn7vzVsOA8nnSHllfWiqRfISBV6ssv2m7D6GlmwbrhH2UqT4Q51b2QMHJ5QslNknLYJR8IniGn3V9VqTESqMmIXOCwMbJuMyRctSUcjvnRclJvyjeGwtDsJAYNU1aoy7BxCyHaPtULAUkd2JV5N5j3WM1iSgpK_a2COST9jN8n320FgS0ieVGCinMlrxXIIAyvj-ccn4o2gbQU2K8WQCvKVnenvUYNu0WVOuUIbTRUpQoE7oxkbFdHdVOLR3jflyL100Ynvjx_bBxrstmqvOP6lOkHA="""

# --- DATABASE SETUP ---
client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]
filters_col = db["filters"]          # kill/b စာသားများ
allow_col = db["allowed_users"]      # /b သုံးခွင့်ရသူများ
groups_col = db["active_groups"]     # Broadcast အတွက်
g_filters_col = db["group_filters"]  # /addfilter အတွက်

# --- CLIENTS ---
user_client = TelegramClient(StringSession(SESSION_STRING.strip()), APP_ID, APP_HASH) if SESSION_STRING else None
bot_client = TelegramClient('bot_session', APP_ID, APP_HASH)

# --- UTILS ---
kill_tasks = {}
bot_bully_tasks = {}
save_status = False

def bq(text): return f"<blockquote><b>{text}</b></blockquote>"
def owner_tag(): return f"<a href='tg://user?id={OWNER_ID}'>Khant Thu Rain (Dexter Morgan)</a>"

def is_allowed(user_id):
    if user_id == OWNER_ID: return True
    return allow_col.find_one({"user_id": user_id}) is not None

async def check_ban_perm(chat, user_id):
    if user_id == OWNER_ID: return True
    try:
        p = await bot_client(GetParticipantRequest(chat, user_id))
        if isinstance(p.participant, ChannelParticipantCreator): return True
        if isinstance(p.participant, ChannelParticipantAdmin): return p.participant.admin_rights.ban_users
    except: pass
    return False

# ==========================================
# 🔴 USERBOT LOGIC (/kill, /unkill)
# ==========================================
@user_client.on(events.NewMessage(pattern='/kill', outgoing=True))
async def kill_handler(event):
    reply = await event.get_reply_message()
    if not reply: return
    chat_id = event.chat_id
    kill_tasks[chat_id] = True
    await event.delete()
    while kill_tasks.get(chat_id):
        words = [w.get("text") for w in list(filters_col.find()) if w.get("text")]
        if words:
            try: await user_client.send_message(chat_id, bq(random.choice(words)), reply_to=reply.id, parse_mode='html')
            except: break
        await asyncio.sleep(0.5)

@user_client.on(events.NewMessage(pattern='/unkill', outgoing=True))
async def unkill_handler(event):
    kill_tasks[event.chat_id] = False
    await event.edit("အားတိုင်းထပ်ထပ်လိုးမယ်ဖာသည်မသား 😎")
    await asyncio.sleep(2); await event.delete()

# ==========================================
# 🔵 BOT LOGIC
# ==========================================

# 1. Welcome / Goodbye & Bot Added Logic
@bot_client.on(events.ChatAction)
async def welcome_goodbye(event):
    chat = await event.get_chat()
    bot_me = await bot_client.get_me()
    bot_mention = f"<a href='tg://user?id={bot_me.id}'>{bot_me.first_name}</a>"

    if event.user_added or event.user_joined:
        if bot_me.id in event.user_ids:
            # Bot အသစ်အထည့်ခံရချိန်
            groups_col.update_one({"chat_id": chat.id}, {"$set": {"title": chat.title}}, upsert=True)
            msg1 = f"ဟိတ် OWNER နဲ့ Admins တို့ မင်းတို့ရဲ့ ဒီ {chat.title} ထဲကို ထည့်သုံးပေးလို့ ကျေးဇူးတင်ပါတယ်!အသုံးလိုကောင်းလိုနိုင်တဲ့ command များယူထားမယ်ဆိုရင် {bot_mention} ရဲ့ Creator {owner_tag()} ရဲ့ Dm (သို့မဟုတ်) @Besties_with_BoD ကိုလာရောက်ပါ!!!"
            await bot_client.send_message(chat.id, bq(msg1), parse_mode='html')
            
            # Specific Group (-1003580630981) သို့ သတင်းပို့ခြင်း
            try: members = getattr(chat, 'participants_count', 'Unknown')
            except: members = "Unknown"
            msg2 = f"မင်္ဂလာပါ {chat.title}က သူငယ်ချင်းတို့ မင်းတို့ရဲ့\n{bot_mention}ကို အောက်ပါ Group က ထည့်သုံးထားပါသေးတယ်\n\nGroup Name - {chat.title}\nGroup ID - <code>{chat.id}</code>\nMembers အရေအတွက် - {members}\nBot Creator - {owner_tag()}"
            await bot_client.send_message(SPECIFIC_GROUP, bq(msg2), parse_mode='html')
        else:
            # User ဝင်လာချိန် Welcome
            for uid in event.user_ids:
                if uid != bot_me.id:
                    try:
                        u = await bot_client.get_entity(uid)
                        u_mention = f"<a href='tg://user?id={u.id}'>{u.first_name}</a>"
                        await bot_client.send_message(event.chat_id, bq(f"ဟိတ် {u_mention} ... {chat.title} ကနေ ကြိုဆိုလိုက်ပါတယ်!! 🫵😎 စကားဝင်ပြော၊သီးချင်းနားထောင်၊ရည်းစားရှာ အပေါင်းအသင်းရှာ ကြိုက်တာလုပ်ဗျ!"), parse_mode='html')
                    except: pass

    elif event.user_left or event.user_kicked:
        try:
            u = await bot_client.get_entity(event.user_id)
            u_mention = f"<a href='tg://user?id={u.id}'>{u.first_name}</a>"
            await bot_client.send_message(event.chat_id, bq(f"ဟုတ် ထွက်သွားလိုက်ပါသေးတယ် {u_mention}! RIP🌾🌾 btw နှင်းဆီပန်းရှာမတွေ့လို့"), parse_mode='html')
        except: pass

# 2. Add Filter & Auto Reply (Specific Group Only)
@bot_client.on(events.NewMessage(pattern=r'^/addfilter\s+(.+?)\s+(.+)', chats=[SPECIFIC_GROUP]))
async def add_filter(event):
    if not is_allowed(event.sender_id): return
    trigger = event.pattern_match.group(1).lower()
    reply = event.pattern_match.group(2)
    g_filters_col.update_one({"trigger": trigger}, {"$set": {"reply": reply}}, upsert=True)
    await event.reply(bq(f"Filter added: '{trigger}' -> '{reply}' ✅"), parse_mode='html')

@bot_client.on(events.NewMessage(chats=[SPECIFIC_GROUP]))
async def filter_reply(event):
    if event.text and not event.text.startswith('/'):
        text = event.text.lower()
        for f in g_filters_col.find():
            if f['trigger'] in text:
                await event.reply(bq(f['reply']), parse_mode='html')
                break

# 3. Save On / Save Off (All Groups)
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

# 4. Bot Bully (/b & /sb)
@bot_client.on(events.NewMessage(pattern=r'^/b$'))
async def bot_bully(event):
    if not is_allowed(event.sender_id): return
    reply = await event.get_reply_message()
    if not reply: return
    chat_id = event.chat_id
    bot_bully_tasks[chat_id] = True
    t = reply.sender
    t_mention = f"<a href='tg://user?id={t.id}'>{t.first_name}</a>" if t else "Target"
    
    while bot_bully_tasks.get(chat_id):
        words = [w.get("text") for w in list(filters_col.find()) if w.get("text")]
        if words:
            try: await bot_client.send_message(chat_id, bq(f"{t_mention} {random.choice(words)}"), reply_to=reply.id, parse_mode='html')
            except: break
        await asyncio.sleep(0.8)

@bot_client.on(events.NewMessage(pattern=r'^/sb$'))
async def stop_bot_bully(event):
    if not is_allowed(event.sender_id): return
    bot_bully_tasks[event.chat_id] = False
    await event.reply(bq("Bot Bully Stopped! 🛑"), parse_mode='html')

# 5. Allow List & Send Broadcast
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

@bot_client.on(events.NewMessage(pattern=r'^/send\s+(.*)'))
async def broadcast(event):
    if event.sender_id != OWNER_ID: return
    text = event.pattern_match.group(1)
    for g in groups_col.find():
        try: await bot_client.send_message(g['chat_id'], bq(text), parse_mode='html')
        except: pass
    await event.reply(bq("Broadcast အောင်မြင်ပါသည်! 📢"), parse_mode='html')

# 6. Admin Tools (Mute / Unmute)
@bot_client.on(events.NewMessage(pattern=r'^/mute$'))
async def mute_user(event):
    if not await check_ban_perm(event.chat, event.sender_id): return await event.reply(bq("Ban Permission မရှိလို့ Mute လုပ်ခွင့်မရှိပါ! ❌"), parse_mode='html')
    reply = await event.get_reply_message()
    if reply:
        try:
            await bot_client.edit_permissions(event.chat_id, reply.sender_id, ChatBannedRights(until_date=None, send_messages=True))
            await event.reply(bq(f"<a href='tg://user?id={reply.sender_id}'>{reply.sender.first_name}</a> ကို Mute လိုက်ပါပြီ! 🔇"), parse_mode='html')
        except Exception as e: await event.reply(bq(f"Error: {e}"), parse_mode='html')

@bot_client.on(events.NewMessage(pattern=r'^/unmute$'))
async def unmute_user(event):
    if not await check_ban_perm(event.chat, event.sender_id): return await event.reply(bq("Ban Permission မရှိလို့ Unmute လုပ်ခွင့်မရှိပါ! ❌"), parse_mode='html')
    reply = await event.get_reply_message()
    if reply:
        try:
            await bot_client.edit_permissions(event.chat_id, reply.sender_id, ChatBannedRights(until_date=None, send_messages=False))
            await event.reply(bq(f"<a href='tg://user?id={reply.sender_id}'>{reply.sender.first_name}</a> ကို Unmute ပြုလုပ်ပြီးပါပြီ! 🔊"), parse_mode='html')
        except Exception as e: await event.reply(bq(f"Error: {e}"), parse_mode='html')

# ==========================================
# 🚀 SYSTEM STARTUP
# ==========================================
async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    if user_client:
        print("Connecting User Client...")
        await user_client.start()
        print("✅ Userbot is Running!")
        
    print("Connecting Bot Client...")
    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ Bot is Running!")
    
    await asyncio.gather(
        user_client.run_until_disconnected() if user_client else asyncio.sleep(0),
        bot_client.run_until_disconnected()
    )

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
