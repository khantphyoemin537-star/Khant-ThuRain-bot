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
from telethon import TelegramClient, events, types
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
        # get_permissions ကို သုံးတာက ပိုစိတ်ချရပါတယ်
        permissions = await bot_client.get_permissions(chat_id, user_id)
        return permissions.is_admin
    except:
        return False

# --- TARGET BOT MONITOR & COPYCAT LOGIC ---
@bot_client.on(events.NewMessage())
async def target_bot_shadow(event):
    if event.is_private: return
    
    # Database ထဲမှာ Block ထားတဲ့ Bot ဟုတ်မဟုတ် စစ်မယ်
    target_bot = target_bots_col.find_one({"bot_id": event.sender_id})
    
    if target_bot:
        try:
            # 1. Target Bot ရဲ့ စာကို Copy ကူးပြီး ပြန်ပို့မယ်
            # (Caption ရှိရင် Caption ပါမယ်၊ စာသားဆိုရင် စာသားပါမယ်)
            copy_text = event.text if event.text else ""
            shadow_msg = await event.respond(bq(f"Copying Target: {copy_text}\n\nGroup Chat သန့်ရှင်းအောင် ၄ စက္ကန့်အတွင်း ဖျက်လိုက်ပါပြီ။ 🧹"), parse_mode='html')
            
            # 2. ၄ စက္ကန့် Countdown Animation
            for i in range(3, -1, -1):
                await asyncio.sleep(1)
                if i == 0:
                    # Target Bot ရဲ့စာနဲ့ ငါ့ Bot ရဲ့စာကို ဖျက်မယ်
                    await event.delete()
                    await shadow_msg.delete()
                    break
                await shadow_msg.edit(bq(f"Copying Target: {copy_text}\n\nGroup Chat သန့်ရှင်းအောင် {i} စက္ကန့်အတွင်း ဖျက်လိုက်ပါပြီ။ 🧹"), parse_mode='html')
                
        except Exception as e:
            print(f"Shadow Logic Error: {e}")

# ==========================================
# 🛡️ FILTERS & PROTECTION (BIO/LINK)
# ==========================================

#@bot_client.on ရဲ့ ( ) ထဲမှာ chats parameter ကို ဖြုတ်လိုက်ရင် Bot ရှိသမျှ Group တိုင်းမှာ အလုပ်လုပ်မှာပါ
# --- FILTERS & PROTECTION (BIO/LINK) ---

@bot_client.on(events.NewMessage())
async def protection_logic(event):
    if event.is_private: return
    
    me = await bot_client.get_me()
    if not event.text or event.sender_id == OWNER_ID or event.sender_id == me.id:
        return

    sender = await event.get_sender()
    text = event.text.strip()
    chat_id = event.chat_id
    sender_id = event.sender_id

    # 1. Harem & Waifu Filter
    if re.search(r'/harem(@\w+)?', text) or re.search(r'/waifu(@\w+)?', text):
        try:
            full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
            mention = f"<a href='tg://user?id={sender_id}'>{full_name}</a>"
            cmd_type = "harem" if "harem" in text.lower() else "waifu"
            
            await event.delete()
            msg_template = "<b>{type} လုပ်သူ-</b> {mention}\nChat သန့်ရှင်းအောင် ဖျက်လိုက်ပါပြီ။"
            warn_msg = await event.respond(bq(msg_template.format(type=cmd_type, mention=mention)), parse_mode='html')
            
            for i in range(9, -1, -1):
                await asyncio.sleep(1)
                if i == 0:
                    await warn_msg.delete()
                    break
                await warn_msg.edit(bq(msg_template.format(type=cmd_type, mention=mention) + f"\n\n{i} စက္ကန့်အတွင်း ပျောက်ကွယ်သွားပါမယ်။"), parse_mode='html')
            return 
        except Exception as e:
            print(f"Harem/Waifu Filter Error: {e}")

    # 2. Bio Keyword Filter
    bio_keywords = ["Bio", "bio", "ဘိုင်အို", "ဘိုင်-အို"]
    if any(key in text for key in bio_keywords):
        is_admin = await check_admin(chat_id, sender_id)
        if not is_admin:
            try:
                await event.delete()
                await event.respond(bq("Bruhh bruhh bioမှာဘာဖြစ်တာလဲ မသိချင်ဘူး ဖျက်လိုက်ပြီ။"), parse_mode='html')
                return 
            except Exception as e:
                print(f"Bio Filter Error: {e}")

        # 3. Link Filter & Auto-Response for Forwarded Media
    urls = re.findall(r'(https?://\S+|www\.\S+)', text)
    
    if urls:
        # --- FORWARDED MESSAGE LOGIC (အသစ်ထည့်ထားသောအပိုင်း) ---
        if event.forward:
            is_admin_user = await check_admin(chat_id, sender_id)
            if is_admin_user:
                text_lower = text.lower()
                # Movie Channel တွေက forward တာဆိုရင် (Keyword စစ်မယ်)
                if any(k in text_lower for k in ["movie", "episode", "season", "ဇာတ်ကား", "ကားသစ်"]):
                    await event.reply(bq("ဘာကားလဲဟ! သူငယ်ချင်းတွေပါ ခေါ်ကြည့်လို့ရတယ်နော်။ 😎🍿"), parse_mode='html')
                
                # Music Bot/Channel က forward တာဆိုရင်
                elif any(k in text_lower for k in ["mp3", "music", "song", "lyrics", "audio", "သီချင်း"]):
                    await event.reply(bq("သီချင်းကောင်းလေးပဲ! ကျန်တဲ့သူတွေလည်း သူပို့တာ နားထောင်ကြည့်ကြဦး။ 🔥🎧"), parse_mode='html')
            return # Forward ဆိုရင် ဒီမှာတင် ရပ်မယ် (Link Filter ထဲ ဆက်မသွားတော့ဘူး)

        # --- NORMAL LINK FILTER (တိုက်ရိုက်ရိုက်ပို့တဲ့ link များအတွက်) ---
        is_admin_user = await check_admin(chat_id, sender_id)
        if is_admin_user:
            full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
            mention = f"<a href='tg://user?id={sender_id}'>{full_name}</a>"
            all_links = "\n".join(urls)
            try:
                await event.delete()
                admin_msg = f"Link ပို့တဲ့သူ- {mention}\nပို့လိုက်တဲ့ Link- {all_links}"
                await event.respond(bq(admin_msg), parse_mode='html')
            except Exception as e:
                print(f"Admin Link Filter Error: {e}")
        else:
            # Member ဆိုရင် Animation နဲ့ ဖျက်မယ်
            try:
                full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
                member_mention = f"<a href='tg://user?id={sender_id}'>{full_name}</a>"
                await event.delete()
                steps = [
                    "ဟိတ်..",
                    f"ဟိတ်.. {member_mention} ဘာ link မှမပို့နဲ့ မရဘူး၊",
                    f"ဟိတ်.. {member_mention} မင်း link ကို ငါဖျက်လိုက်ပြီ🫵"
                ]
                warn_msg = await event.respond(bq(steps[0]), parse_mode='html')
                for step in steps[1:]:
                    await asyncio.sleep(0.5)
                    try: await warn_msg.edit(bq(step), parse_mode='html')
                    except: break
            except Exception as e:
                print(f"Member Link Animation Error: {e}")


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
    mentions = f"<b> {chat_title} ADMINS:</b>\n\n"
    
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

# Target Bot Collection ဆောက်ခြင်း
target_bots_col = db["target_bots"]

# --- BOT DELETE COMMAND ---
@bot_client.on(events.NewMessage(pattern=r'^/delete(?:@\w+)?$'))
async def add_delete_bot(event):
    # Permission: Owner နဲ့ Allow List ပဲ သုံးခွင့်ရှိမယ်
    if not is_allowed(event.sender_id):
        return await event.reply(bq("မင်းမှာ ဒီအမိန့်ပေးပိုင်ခွင့်မရှိဘူး။ လစ်တော့။ "), parse_mode='html')
    
    reply = await event.get_reply_message()
    if reply and reply.sender and reply.sender.bot:
        bot_id = reply.sender_id
        bot_name = escape_html(reply.sender.first_name)
        
        target_bots_col.update_one(
            {"bot_id": bot_id},
            {"$set": {"name": bot_name, "added_by": event.sender_id}},
            upsert=True
        )
        await event.respond(bq(f"{bot_name} ကို Target ထားလိုက်ပြီ! သူပို့သမျှ ငါလိုက်ကူးပြီး ၄ စက္ကန့်အတွင်း အကုန်ရှင်းပစ်မယ်။ 🔥"), parse_mode='html')
    else:
        await event.respond(bq("Target ထားချင်တဲ့ Bot ရဲ့ Message ကို Reply ထောက်ပါ။"), parse_mode='html')

# --- STOP DELETE COMMAND ---
@bot_client.on(events.NewMessage(pattern=r'^/undelete(?:@\w+)?$'))
async def remove_delete_bot(event):
    if not await check_admin(event.chat_id, event.sender_id): return
    
    reply = await event.get_reply_message()
    if reply and reply.sender:
        target_bots_col.delete_one({"bot_id": reply.sender_id})
        await event.respond(bq("ဒီ Bot ရဲ့စာတွေကို မဖျက်တော့ဘူးနော်။ ✅"), parse_mode='html')
# ==========================================
# 🎵 VC START/END DETECTION (BOTS & SERVICE)
# ==========================================

# စောင့်ကြည့်မယ့် Music Bot များ၏ ID (ဥပမာ - Rose, Cheems, etc.)
# Chief group ထဲက music bot ID တွေကို ဒီမှာ ထည့်ပါ
MUSIC_BOT_IDS = [
    123456789, # Rose Bot ID (Example)
    987654321  # Cheems Bot ID (Example)
]

# VC Start/End အတွက် ရှာဖွေမည့် Keyword များ
VC_START_KEYWORDS = [
    "voice chat started", "video chat started", 
    "vc started", "music started"
]
VC_END_KEYWORDS = [
    "voice chat ended", "video chat ended", 
    "vc ended", "music stopped", "thanks for the vibes"
]

@bot_client.on(events.NewMessage())
async def vc_detection_listener(event):
    if event.is_private: return
    
    # 1. Telegram Service Message (White Message) ကို စစ်ဆေးခြင်း
    if event.action:
        # ChatActionGroupCallStarted -> VC စတင်ခြင်း
        if isinstance(event.action, types.MessageActionGroupCallStarted):
            await event.respond(
                bq("ဟုတ် သီချင်းနားထောင်တာ (or) စကားပြောဖို့အတွက် Voice Chat စလိုက်ပါသေးတယ်"), 
                parse_mode='html'
            )
        # ChatActionGroupCallEnded -> VC ပြီးဆုံးခြင်း
        elif isinstance(event.action, types.MessageActionGroupCallEnded):
            await event.respond(
                bq("Voice Chat ပြီးဆုံးသွားပါပြီ!!"), 
                parse_mode='html'
            )
        return # Service message ဆိုရင် ဒီမှာ တင်ရပ်မယ်

    # 2. တခြား Music Bot တွေရဲ့ စာသားကို စောင့်ကြည့်ခြင်း
    if event.sender_id in MUSIC_BOT_IDS and event.text:
        text_lower = event.text.lower()
        
        # VC Start Keyword ပါသလား စစ်မယ်
        if any(keyword in text_lower for keyword in VC_START_KEYWORDS):
            # Music bot ရဲ့ စာကို reply ပြန်ပြီး အသိပေးမယ်
            await event.reply(
                bq("ဟုတ် Voice Chat စလိုက်ပါသေးတယ် "), 
                parse_mode='html'
            )
            
        # VC End Keyword ပါသလား စစ်မယ်
        elif any(keyword in text_lower for keyword in VC_END_KEYWORDS):
            # Music bot ရဲ့ စာကို reply ပြန်ပြီး အသိပေးမယ်
            await event.reply(
                bq("Voice Chat ပိတ်လိုက်ပါသေးတယ်!! 💔"), 
                parse_mode='html'
            )

# Play Command Protection/Response
@bot_client.on(events.NewMessage(pattern=r'^/play(?:\s+(.*))?'))
async def play_response(event):
    # Private chat ဆိုရင် ကျော်မယ်
    if event.is_private: return
    
    song_title = event.pattern_match.group(1)
    if not song_title:
        return # သီချင်းနာမည် မပါရင် ဘာမှမလုပ်ဘူး

    sender = await event.get_sender()
    sender_id = event.sender_id
    full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
    mention = f"<a href='tg://user?id={sender_id}'>{full_name}</a>"

    response = (
        f"<b>Song Title</b>- {escape_html(song_title)}\n"
        f"<b>သီချင်းဖွင့်တဲ့သူ</b>- {mention}\n"
        f"စနားထောင်လို့ရပါပြီ။\n"
        f"Music ကို ပိတ်ဖို့လည်း မမေ့ပါနဲ့🤍"
    )
    
    await event.respond(bq(response), parse_mode='html')

# ==========================================
# 🤖 BULLY & SYSTEM
# ==========================================

# Bully လုပ်နေတဲ့ status ကိုမှတ်ဖို့ list/dict တစ်ခု ကြိုဆောက်ထားပါ (Code ရဲ့ အပေါ်ဆုံးနားမှာ)
bot_bully_tasks = {}

@bot_client.on(events.NewMessage(pattern=r'^/b(?:@\w+)?$'))
async def bot_bully(event):
    # 1. Permission Check (Allow List ထဲပါမှ သုံးရမယ်)
    if not is_allowed(event.sender_id):
        return await event.reply(bq("မင်းမှာ ဒီ Command ကို သုံးပိုင်ခွင့်မရှိဘူး။သုံးခွင့်နဲ့အသုံးပြုနည်းများအတွက် @Besties_with_BoDကိုလာ "), parse_mode='html')
    
    reply = await event.get_reply_message()
    if not reply:
        return await event.respond(bq("ဘယ်ကောင့်ကို ခေါင်းမဖော်နိုင်အောင် ဆဲပေးရမလဲ၊Replyပြန်လိုက် "))

    chat_id = event.chat_id
    t = await reply.get_sender()
    if not t: return

    # 2. Owner Protection (Owner ကို လာဆဲရင် ဆဲတဲ့ကောင်ကို ပြန်ဆဲမယ်)
    target_id = t.id
    if target_id == OWNER_ID:
        # ဆဲခိုင်းတဲ့ကောင်ကို Target ပြန်ပြောင်းမယ်
        target_id = event.sender_id
        t = await event.get_sender()
        await event.respond(bq("ဟိတ်ကောင်🫵😎 Creatorကိုများ ဆဲခိုင်းတယ်ပေါ့။ မင်းကိုပဲ ပြန်ကျွေးမယ်။ ခံလိုက်တော့! 🔥"))
    else:
        await event.respond(bq(f"<a href='tg://user?id={target_id}'>{escape_html(t.first_name)}</a> 🫵😎 "))

    # Bully Logic
    bot_bully_tasks[chat_id] = True
    mention = f"<a href='tg://user?id={target_id}'>{escape_html(t.first_name)}</a>"
    words = [w.get("text") for w in filters_col.find() if w.get("text")]
    
    if not words:
        return await event.respond(bq("DB မှာ စာလုံးမရှိသေးဘူး Chief!"))

    send_count = 0
    while bot_bully_tasks.get(chat_id):
        try: 
            await bot_client.send_message(
                chat_id, 
                bq(f"{mention} {random.choice(words)}"), 
                reply_to=reply.id if target_id != event.sender_id else event.id, 
                parse_mode='html'
            )
            send_count += 1
            
            # စာအရှိန်မြှင့်ထားတယ် (၁၀ စောင်ပို့မှ ၁ စက္ကန့်နားမယ်)
            if send_count >= 10: 
                await asyncio.sleep(1)
                send_count = 0 
            else:
                await asyncio.sleep(0.01) # အလွန်မြန်တဲ့ အရှိန်
                
        except Exception as e:
            print(f"Bully Error: {e}")
            bot_bully_tasks[chat_id] = False
            break


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
    
    # ပို့မယ့်စာသားကို group(1) ကနေ ယူမယ်
    text = event.pattern_match.group(1)
    if not text:
        return await event.respond(bq("ပို့မယ့်စာသား ထည့်ပါဦး Chief!"))

    success = 0
    # Database ထဲက အုပ်စုအားလုံးကို find() နဲ့ ဆွဲထုတ်မယ်
    all_groups = list(groups_col.find())
    
    for g in all_groups:
        try:
            # Database ထဲက chat_id ကိုသုံးပြီး ပို့မယ်
            await bot_client.send_message(g['chat_id'], bq(text), parse_mode='html')
            success += 100 # Success count ကို တစ်ခါပို့တိုင်း ၁ တိုးမယ်
        except Exception as e:
            print(f"Error sending to {g['chat_id']}: {e}")
            pass
            
    await event.respond(bq(f"ငါ မင်းပို့ခိုင်းတဲ့ Message တွေကို သေချာပို့ပေးလိုက်ပြီ! 📢\nပို့ဆောင်ပြီးစီးသော Group အရေအတွက်: {success}"), parse_mode='html')

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
        await asyncio.sleep(72000)

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ BoDx Sovereign System Online!")
    asyncio.create_task(hourly_reminder())
    await bot_client.run_until_disconnected()

if __name__ == "__main__":
    try: asyncio.run(main())
    except: pass
