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

# HTML Parse mode ကို default အဖြစ်ကြိုသတ်မှတ်ခြင်း
bot_client = TelegramClient('bot_session', APP_ID, APP_HASH)
bot_client.parse_mode = 'html'

# --- UTILS ---
bot_bully_tasks = {}
save_status = False

def bq(text): return f"<blockquote><b>{text}</b></blockquote>"
def owner_tag(): return f"<a href='tg://user?id={OWNER_ID}'>Khant Thu Rain (Dexter Morgan)</a>"

# HTML tag error မတက်စေရန် နာမည်များကို filter လုပ်ပေးမည့် function
def escape_html(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") if text else ""

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
    bot_mention = f"<a href='tg://user?id={bot_me.id}'>{escape_html(bot_me.first_name)}</a>"
    safe_title = escape_html(chat.title)

    if event.user_added or event.user_joined:
        if bot_me.id in event.user_ids:
            groups_col.update_one({"chat_id": chat.id}, {"$set": {"title": chat.title}}, upsert=True)
            msg1 = f"ဟိတ် OWNER နဲ့ Admins တို့ မင်းတို့ရဲ့ ဒီ {safe_title} ထဲကို ထည့်သုံးပေးလို့ ကျေးဇူးတင်ပါတယ်! အသုံးလိုကောင်းလိုနိုင်တဲ့ command များယူထားမယ်ဆိုရင် {bot_mention} ရဲ့ Creator {owner_tag()} ရဲ့ Dm (သို့မဟုတ်) @Besties_with_BoD ကိုလာရောက်ပါ!!!"
            await bot_client.send_message(chat.id, bq(msg1))
            
            try: members = getattr(chat, 'participants_count', 'Unknown')
            except: members = "Unknown"
            msg2 = f"မင်္ဂလာပါ {safe_title}က သူငယ်ချင်းတို့ မင်းတို့ရဲ့\n{bot_mention}ကို အောက်ပါ Group က ထည့်သုံးထားပါသေးတယ်\n\nGroup Name - {safe_title}\nGroup ID - <code>{chat.id}</code>\nMembers အရေအတွက် - {members}\nBot Creator - {owner_tag()}"
            await bot_client.send_message(SPECIFIC_GROUP, bq(msg2))
        else:
            for uid in event.user_ids:
                if uid != bot_me.id:
                    try:
                        u = await bot_client.get_entity(uid)
                        u_mention = f"<a href='tg://user?id={u.id}'>{escape_html(u.first_name)}</a>"
                        await bot_client.send_message(event.chat_id, bq(f"ဟိတ် {u_mention} ... {safe_title} ကနေ ကြိုဆိုလိုက်ပါတယ်!! 🫵😎 စကားဝင်ပြော၊သီချင်းနားထောင်၊ရည်းစားရှာ အပေါင်းအသင်းရှာ ကြိုက်တာလုပ်!"))
                    except: pass

    elif event.user_left or event.user_kicked:
        try:
            u = await bot_client.get_entity(event.user_id)
            u_mention = f"<a href='tg://user?id={u.id}'>{escape_html(u.first_name)}</a>"
            await bot_client.send_message(event.chat_id, bq(f"ဟုတ် ထွက်သွားလိုက်ပါသေးတယ် {u_mention}!သူ့အစားပိုကောင်းတဲ့သူကိုရှာပြီး ခင်မင်ပေးလိုက်!!!"))
        except: pass

# ==========================================
# 🛡️ UTILITY COMMANDS
# ==========================================

@bot_client.on(events.NewMessage(pattern=r'^/cmd(?:@\w+)?$'))
async def show_commands(event):
    cmd_msg = """<b>🛡️ BoDx Sovereign System Commands:</b>

<u>👮‍♂️ Admin & Owner Commands:</u>
• <code>/adm &lt;message&gt;</code> - Group Admin အားလုံးကို Mention ခေါ်ပေးမည်။
• <code>/mute</code> - Reply ထောက်ပြီး User ကို Mute မည်။
• <code>/unmute</code> - Reply ထောက်ပြီး User ကို Unmute မည်။
• <code>/done</code> - နေ့စဉ် Admin Task ပြီးကြောင်း မှတ်သားမည် (၁ နာရီတစ်ခါ သတိပေးခြင်း ရပ်မည်)။

<u>🤖 Bot Bully (Allowed Users Only):</u>
• <code>/b</code> - Reply ထောက်ပြီး Bot မှ Auto Bully စမည်။
• <code>/sb</code> - Bot Bully ရပ်မည်။

<u>⚙️ System Commands (Owner Only):</u>
• <code>/saveon</code> - Message များကို Filter အဖြစ် စတင်မှတ်သားမည်။
• <code>/saveoff</code> - Message မှတ်သားခြင်း ရပ်မည်။
• <code>/addallow</code> - Reply ထောက်ပြီး Bully သုံးခွင့်ပြုမည်။
• <code>/allowlist</code> - ခွင့်ပြုထားသူများစာရင်း ကြည့်မည်။
• <code>/send &lt;message&gt;</code> - Group အားလုံးသို့ Broadcast ပို့မည်။

• <code>/cmd</code> - Command list ကို ပြမည်။"""
    await event.respond(bq(cmd_msg))

@bot_client.on(events.NewMessage(pattern=r'^/saveon(?:@\w+)?$'))
async def save_on(event):
    global save_status
    if event.sender_id != OWNER_ID: return
    save_status = True
    await event.reply(bq("Save Mode ON ✅ (စာတွေလိုက်မှတ်နေပါပြီ)"))

@bot_client.on(events.NewMessage(pattern=r'^/saveoff(?:@\w+)?$'))
async def save_off(event):
    global save_status
    if event.sender_id != OWNER_ID: return
    save_status = False
    await event.reply(bq("Save Mode OFF 🛑 (စာမှတ်ခြင်း ရပ်လိုက်ပါပြီ)"))

@bot_client.on(events.NewMessage())
async def save_messages(event):
    global save_status
    if save_status and event.text and not event.text.startswith('/'):
        filters_col.update_one({"text": event.text}, {"$set": {"text": event.text}}, upsert=True)

@bot_client.on(events.NewMessage(pattern=r'^/b(?:@\w+)?$'))
async def bot_bully(event):
    if not is_allowed(event.sender_id): return
    reply = await event.get_reply_message()
    if not reply: return
    if reply.sender_id == OWNER_ID:
        return await event.respond(bq("ဟားတိုက်ခံရတော့မယ်၊မင်းမှာ Creator ကို bully ခွင့်မရှိဘူးညီ 🫵😎"))

    chat_id = event.chat_id
    bot_bully_tasks[chat_id] = True
    t = reply.sender
    mention = f"<a href='tg://user?id={t.id}'>{escape_html(t.first_name)}</a>"
    while bot_bully_tasks.get(chat_id):
        words = [w.get("text") for w in list(filters_col.find()) if w.get("text")]
        if words:
            try: await bot_client.send_message(chat_id, bq(f"{mention} {random.choice(words)}"), reply_to=reply.id)
            except: break
        await asyncio.sleep(0.8)

@bot_client.on(events.NewMessage(pattern=r'^/sb(?:@\w+)?$'))
async def stop_bot_bully(event):
    if not is_allowed(event.sender_id): return
    bot_bully_tasks[event.chat_id] = False
    await event.reply(bq("အခုနားဆိုလို့နားလိုက်မယ်၊စောက်ချိုးမပြေရင်ထပ်ဆဲပေးမယ်"))

@bot_client.on(events.NewMessage(pattern=r'^/addallow(?:@\w+)?$'))
async def add_allow(event):
    if event.sender_id != OWNER_ID: return
    reply = await event.get_reply_message()
    if reply:
        allow_col.update_one({"user_id": reply.sender_id}, {"$set": {"name": reply.sender.first_name}}, upsert=True)
        await event.reply(bq(f"{escape_html(reply.sender.first_name)} ကို Allow List ထည့်ပြီးပါပြီ! ✅"))

@bot_client.on(events.NewMessage(pattern=r'^/allowlist(?:@\w+)?$'))
async def allow_list(event):
    if event.sender_id != OWNER_ID: return
    users = list(allow_col.find())
    msg = "<b>✅ Allowed Users List:</b>\n" + "\n".join([f"• <a href='tg://user?id={u['user_id']}'>{escape_html(u['name'])}</a>" for u in users]) if users else "Allow List မှာ မရှိသေးပါ။"
    await event.reply(bq(msg))

@bot_client.on(events.NewMessage(pattern=r'^/send(?:@\w+)?\s+(.*)'))
async def broadcast(event):
    if event.sender_id != OWNER_ID: return
    text = event.pattern_match.group(1)
    success = 0
    for g in groups_col.find():
        try:
            await bot_client.send_message(g['chat_id'], bq(text))
            success += 1
        except: pass
    await event.respond(bq(f"ငါ မင်းပို့ခိုင်းတဲ့messageတွေကို သေချာပို့ပေးလိုက်ပြီ! 📢\nပို့ဆောင်ပြီးစီးသော Group အရေအတွက်: {success}"))

# ==========================================
# 🛡️ SYSTEM PROTECTION (ADMIN TOOLS)
# ==========================================

# Anti-Slash (Chat Cleaner) - ပြီးပြည့်စုံစွာ Fix ထားသည်
@bot_client.on(events.NewMessage())
async def anti_slash(event):
    if event.sender and event.sender.bot: 
        return 
        
    text = event.text
    if text and text.startswith('/'):
        # @bot_name ပါလာခဲ့လျှင် ဖယ်ရှားပြီး မူရင်း command ကိုသာ စစ်ဆေးမည်
        base_cmd = text.split()[0].split('@')[0]
        exclude = ['/b', '/sb', '/adm', '/done', '/saveon', '/saveoff', '/send', '/addallow', '/allowlist', '/addfilter', '/mute', '/unmute', '/cmd']
        
        if base_cmd not in exclude:
            await asyncio.sleep(1.5)
            try:
                u = await event.get_sender()
                safe_name = escape_html(u.first_name)
                await event.delete()
                msg = await event.respond(
                    bq(f"<a href='tg://user?id={u.id}'>{safe_name}</a> ဟိတ် chat သန့်ရှင်းအောင် ငါမင်းတို့ /နဲ့စတဲ့ message တွေဖျက်ပေးလိုက်တယ်")
                )
                await asyncio.sleep(10)
                await msg.delete()
            except Exception as e:
                print(f"Anti-Slash Error: {e}")

# ADM Command 
@bot_client.on(events.NewMessage(pattern=r'^/adm(?:@\w+)?(?:\s+(.*))?'))
async def admin_mention(event):
    if event.is_private:
        return await event.respond(bq("ဒီ Command က Group ထဲမှာပဲ သုံးလို့ရပါတယ် Chief!"))

    if not await check_admin(event.chat_id, event.sender_id): 
        return

    text = event.pattern_match.group(1) if event.pattern_match.group(1) else "Attention Admins!"
    
    mentions = f"<b>🛡️ {escape_html(event.chat.title)} ADMINS:</b>\n\n"
    found_admin = False
    
    try:
        async for user in bot_client.iter_participants(event.chat_id, filter=ChannelParticipantAdmin):
            if not user.bot:
                found_admin = True
                name = escape_html(user.first_name) if user.first_name else "Admin"
                mentions += f"• <a href='tg://user?id={user.id}'>{name}</a>\n"
        
        if not found_admin:
            return await event.respond(bq("Admin စာရင်း ဆွဲမထုတ်နိုင်ပါဘူး။ငါ့ကို Admin Permission ပေးထားဖို့ လိုပါတယ်။"))

        full_msg = f"{mentions}\n💬 <b>Message:</b> {escape_html(text)}"
        await event.respond(bq(full_msg))
        
    except Exception as e:
        await event.respond(bq(f"Error fetching admins: {e}"))
    
@bot_client.on(events.NewMessage(pattern=r'^/mute(?:@\w+)?$'))
async def mute_user(event):
    if not await check_admin(event.chat_id, event.sender_id): return
    reply = await event.get_reply_message()
    if reply:
        try:
            await bot_client.edit_permissions(event.chat_id, reply.sender_id, until_date=None, send_messages=False)
            await event.respond(bq(f"<a href='tg://user?id={reply.sender_id}'>{escape_html(reply.sender.first_name)}</a> ကို Mute လိုက်ပါပြီ!"))
        except Exception as e: 
            await event.respond(bq(f"Error: {e}"))

@bot_client.on(events.NewMessage(pattern=r'^/unmute(?:@\w+)?$'))
async def unmute_user(event):
    if not await check_admin(event.chat_id, event.sender_id): return
    reply = await event.get_reply_message()
    if reply:
        try:
            await bot_client.edit_permissions(event.chat_id, reply.sender_id, until_date=None, send_messages=True)
            await event.respond(bq(f"<a href='tg://user?id={reply.sender_id}'>{escape_html(reply.sender.first_name)}</a> စာပြန်ပို့!Unmute လုပ်ပြီးပြီ!"))
        except Exception as e: 
            await event.respond(bq(f"Error: {e}"))

# 4. Hourly Admin Task (/done)
@bot_client.on(events.NewMessage(pattern=r'^/done(?:@\w+)?$'))
async def admin_done(event):
    if not await check_admin(event.chat_id, event.sender_id): return
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    admin_tasks_col.update_one({"chat_id": event.chat_id}, {"$set": {"last_done": today}}, upsert=True)
    u = await event.get_sender()
    await event.respond(bq(f"<a href='tg://user?id={u.id}'>{escape_html(u.first_name)}</a> ဟုတ်ပြီ သတိပေးတာကို ဒီနေ့အတွက် ရပ်လိုက်ပြီ"))

# Group တစ်ခု Error တက်ရင် Loop မရပ်အောင် try..except ဖြင့် ကာကွယ်ထားသည်
async def hourly_reminder():
    await asyncio.sleep(15) # Bot ပွင့်ပြီး ခဏစောင့်မည်
    while True:
        today = datetime.now(TZ).strftime("%Y-%m-%d")
        for g in groups_col.find():
            try:
                task = admin_tasks_col.find_one({"chat_id": g['chat_id']})
                if not task or task.get("last_done") != today:
                    mentions = ""
                    async for admin in bot_client.iter_participants(g['chat_id'], filter=ChannelParticipantAdmin):
                        if not admin.bot: mentions += f"<a href='tg://user?id={admin.id}'>{escape_html(admin.first_name)}</a> "
                    msg = f"{mentions}\n\nပြီးဒီနေ့ မင်းလူ 5ယောက်ထည့်ပေးရမယ်၊မထည့်ရသေးရင် ထည့်ပေးပါအုံး၊Group ရဲ့ နေ့စဉ် active ဖြစ်မှုနဲ့ member ဝင်ရောက်နှုန်းပိုများဖို့က မင်းတို့လက်ထဲမှာ မူတည်နေတာကြောင့် ကြိုးစားပေးပါ။🤍 လူထည့်ပြီးရင် Admin တစ်ယောက်ယောက် ငါ့ကို /done လို့ reply ထောက်ပြီးပြော ဒါဆိုဒီနေ့အတွက် သတိပေးတာရပ်လိုက်မယ်🫵"
                    await bot_client.send_message(g['chat_id'], bq(msg))
            except Exception as e:
                print(f"Reminder Loop Error for group {g.get('chat_id')}: {e}")
                
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
