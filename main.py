import io
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
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ==========================================
# 🌐 DNS FIX FOR MONGODB
# ==========================================
try:
    import dns.resolver
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1']
except: pass

# ==========================================
# 🌐 FLASK KEEP-ALIVE (Render အတွက် Port 10000 ပြင်ထားသည်)
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "BoDx Sovereign System Active!"

def run_flask(): 
    # Render သည် default အားဖြင့် port 10000 ကို အသုံးပြုသည်
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"
APP_ID = 30765851
APP_HASH = '235b0bc6f03767302dc75763508f7b75'
BOT_TOKEN = "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU"
SPECIFIC_GROUP = -1003580630981 # Log group / Target Image Group
TARGET_GROUP_ID = -1003580630981 # Main group for filters
TZ = pytz.timezone('Asia/Yangon')

# ==========================================
# 🗄️ DATABASE SETUP
# ==========================================
client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]
filters_col = db["custom_filters"]
allow_col = db["allowed_users"]
groups_col = db["active_groups"]
admin_tasks_col = db["admin_tasks"]

# --- BOT CLIENT SETUP ---
bot_client = TelegramClient('bot_session', APP_ID, APP_HASH)

# ==========================================
# 🛠️ HELPERS
# ==========================================
bot_bully_tasks = {}
save_status = False
sticker_spam_data = {}

def bq(text): return f"<blockquote><b>{text}</b></blockquote>"
def owner_tag(): return f"<a href='tg://user?id={OWNER_ID}'>⚚𝘽𝙤𝘿𝙭𝗪𝘆𝗮𝗮𝗾𝗾 𝗭𝘅𝘆𝗳𝗮𝗻𝘇𝘁</a>"

def is_allowed(user_id):
    if user_id == OWNER_ID: return True
    return allow_col.find_one({"user_id": user_id}) is not None

async def check_admin(chat_id, user_id):
    if user_id == OWNER_ID: return True
    try:
        permissions = await bot_client.get_permissions(chat_id, user_id)
        return permissions.is_admin
    except: return False

def create_welcome_image(bg_bytes, user_pf_bytes):
    bg = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
    bg = ImageOps.fit(bg, (1280, 720), centering=(0.5, 0.5))
    overlay = Image.new('RGBA', bg.size, (0, 0, 0, 100))
    bg = Image.alpha_composite(bg, overlay)
    
    user_pf = Image.open(io.BytesIO(user_pf_bytes)).convert("RGBA")
    user_pf = user_pf.resize((300, 300), Image.Resampling.LANCZOS)
    bg.paste(user_pf, (50, 210), user_pf)
    
    draw = ImageDraw.Draw(bg)
    try:
        font = ImageFont.truetype("font.ttf", 80)
        text = "ကြိုဆိုပါတယ် သူငယ်ချင်း"
    except:
        font = ImageFont.load_default()
        text = "Welcome, Friend!" 
    
    draw.text((400, 320), text, font=font, fill=(255, 255, 255, 255))
    img_byte_arr = io.BytesIO()
    bg.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr.read()

# ==========================================
# 🛡️ EVENT HANDLERS
# ==========================================

#  [B] Welcome & Goodbye
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
                        
                        target_group_entity = await bot_client.get_entity(SPECIFIC_GROUP)
                        bg_bytes = await bot_client.download_profile_photo(target_group_entity, file=bytes)
                        user_pf_bytes = await bot_client.download_profile_photo(u, file=bytes)
                        
                        if bg_bytes and user_pf_bytes:
                            final_img_bytes = await asyncio.get_event_loop().run_in_executor(
                                None, create_welcome_image, bg_bytes, user_pf_bytes
                            )
                            caption_msg = f"ဟိတ် {u_mention} ... {safe_title} ကနေ ကြိုဆိုလိုက်ပါတယ်!!🤍စကားဝင်ပြော၊သီချင်းနားထောင်၊ရည်းစားရှာ အပေါင်းအသင်းရှာ ကြိုက်တာလုပ်!"
                            await bot_client.send_file(event.chat_id, file=io.BytesIO(final_img_bytes), caption=bq(caption_msg), parse_mode='html', force_document=False)
                        else:
                            await bot_client.send_message(event.chat_id, bq(f"ဟိတ် {u_mention} ... {safe_title} ကနေ ကြိုဆိုလိုက်ပါတယ်!!🤍စကားဝင်ပြော၊သီချင်းနားထောင်၊ရည်းစားရှာ အပေါင်းအသင်းရှာ ကြိုက်တာလုပ်!"), parse_mode='html')
                    except Exception as e: print(f"Welcome Image Error: {e}")

    elif event.user_left or event.user_kicked:
        try:
            u = await bot_client.get_entity(event.user_id)
            u_mention = f"<a href='tg://user?id={u.id}'>{escape_html(u.first_name)}</a>"
            await bot_client.send_message(event.chat_id, bq(f"ထွက်သွားလိုက်ပါသေးတယ် {u_mention}!!"), parse_mode='html')
        except: pass

@bot_client.on(events.NewMessage(pattern=r'^[/.]filter\s+(.*)'))
async def add_filter(event):
    if event.chat_id != TARGET_GROUP_ID: return
    
    if not await check_admin(event.chat_id, event.sender_id): return

    input_str = event.pattern_match.group(1).split(None, 1)
    keyword = input_str[0].lower()
    reply = await event.get_reply_message()

    if reply:
        media = None
        m_type = None
        
        # Sticker, Photo, Video တွေကို media reference နဲ့ပဲ ယူမယ်
        if reply.sticker:
            media = reply.media
            m_type = "sticker"
        elif reply.photo:
            media = reply.media
            m_type = "photo"
        elif reply.video:
            media = reply.media
            m_type = "video"
        elif reply.text:
            media = reply.text
            m_type = "text"

        if media:
            filters_col.update_one(
                {"chat_id": event.chat_id, "keyword": keyword},
                {"$set": {"content": media, "type": m_type}}, 
                upsert=True
            )
            await event.reply(bq(f"အိုကေ! '{keyword}' အတွက် {m_type} filter မှတ်လိုက်ပြီ ✅"), parse_mode='html')
    
    elif len(input_str) > 1:
        filters_col.update_one(
            {"chat_id": event.chat_id, "keyword": keyword},
            {"$set": {"content": input_str[1], "type": "text"}}, 
            upsert=True
        )
        await event.reply(bq(f"အိုကေ! '{keyword}' ဆိုရင် '{input_str[1]}' လို့ ပြန်ပေးမယ်။ ✅"), parse_mode='html')

@bot_client.on(events.NewMessage(pattern=r'^[/.]id'))
async def get_user_id(event):
    reply = await event.get_reply_message()
    
    if reply:
        target_id = reply.sender_id
        user = await reply.get_sender()
        name = escape_html(user.first_name) if user else "User"
        msg = f"👤 <b>Name:</b> {name}\n🆔 <b>User ID:</b> <code>{target_id}</code>"
    else:
        target_id = event.sender_id
        msg = f"🆔 <b>Your ID:</b> <code>{target_id}</code>"
    
    await event.respond(bq(msg), parse_mode='html')

@bot_client.on(events.NewMessage(pattern=r'^[/.]gid'))
async def get_group_id(event):
    if event.is_private:
        return await event.respond(bq("ဒါက Private Chat မို့လို့ Group ID မရှိပါဘူး!"), parse_mode='html')
    
    chat_id = event.chat_id
    chat_title = escape_html(event.chat.title)
    
    msg = f"📍 <b>Group:</b> {chat_title}\n🌐 <b>Chat ID:</b> <code>{chat_id}</code>"
    await event.respond(bq(msg), parse_mode='html')

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

# [A] VC Service Listener (Started/Ended)
@bot_client.on(events.ChatAction)
async def vc_service_listener(event):
    if event.is_private: return
    if event.action_message:
        if isinstance(event.action_message.action, types.MessageActionGroupCallStarted):
            try: await event.action_message.delete()
            except: pass
            await bot_client.send_message(event.chat_id, bq("ဟုတ် သီချင်းနားထောင်တာ (or) စကားပြောဖို့အတွက် Voice Chat စလိုက်ပါသေးတယ် 🎧"), parse_mode='html')
        elif isinstance(event.action_message.action, types.MessageActionGroupCallEnded):
            try: await event.action_message.delete()
            except: pass
            await bot_client.send_message(event.chat_id, bq("Voice Chat ပြီးဆုံးသွားပါပြီ!! 💔"), parse_mode='html')

# 🛡️ 3. FILTERS & PROTECTION
@bot_client.on(events.NewMessage())
async def protection_logic(event):
    if event.is_private: return
    me = await bot_client.get_me()
    if not event.text or event.sender_id == OWNER_ID or event.sender_id == me.id: return

    sender = await event.get_sender()
    text = event.text.strip()
    chat_id = event.chat_id
    sender_id = event.sender_id

    # Harem & Waifu Filter
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
        except: pass

    # Bio Keyword Filter
    bio_keywords = ["Bio", "bio", "ဘိုင်အို", "ဘိုင်-အို", "ဘိုင်-O"]
    if any(key in text for key in bio_keywords):
        if not await check_admin(chat_id, sender_id):
            try:
                await event.delete()
                await event.respond(bq("Bruhh bruhh bioမှာဘာဖြစ်တာလဲ မသိချင်ဘူး ဖျက်လိုက်ပြီ။"), parse_mode='html')
                return 
            except: pass

    # Link Filter
    urls = re.findall(r'(https?://\S+|www\.\S+)', text)
    if urls:
        if event.forward:
            if await check_admin(chat_id, sender_id):
                text_lower = text.lower()
                if any(k in text_lower for k in ["movie", "episode", "season", "ဇာတ်ကား", "ကားသစ်"]):
                    await event.reply(bq("ဘာကားလဲဟ! သူငယ်ချင်းတွေပါ ခေါ်ကြည့်လို့ရတယ်နော်။ 😎🍿"), parse_mode='html')
                elif any(k in text_lower for k in ["mp3", "music", "song", "lyrics", "audio", "သီချင်း"]):
                    await event.reply(bq("သီချင်းကောင်းလေးပဲ! ကျန်တဲ့သူတွေလည်း သူပို့တာ နားထောင်ကြည့်ကြဦး။ 🔥🎧"), parse_mode='html')
            return 

        if await check_admin(chat_id, sender_id):
            full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
            mention = f"<a href='tg://user?id={sender_id}'>{full_name}</a>"
            all_links = "\n".join(urls)
            try:
                await event.delete()
                await event.respond(bq(f"Link ပို့လိုက်တဲ့ Admin ချောချောလေး - {mention}\nသူပို့လိုက်တဲ့ Link- {all_links}"), parse_mode='html')
            except: pass
        else:
            try:
                full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
                member_mention = f"<a href='tg://user?id={sender_id}'>{full_name}</a>"
                await event.delete()
                steps = ["ဟိတ်..", f"ဟိတ်.. {member_mention} ဘာ link မှမပို့နဲ့ မရဘူး၊", f"ဟိတ်.. {member_mention} မင်း link ကို ငါဖျက်လိုက်ပြီ🫵"]
                warn_msg = await event.respond(bq(steps[0]), parse_mode='html')
                for step in steps[1:]:
                    await asyncio.sleep(1)
                    try: await warn_msg.edit(bq(step), parse_mode='html')
                    except: break
            except: pass

@bot_client.on(events.NewMessage)
async def sticker_spam_filter(event):
    if not event.sticker or event.is_private:
        return
    
    me = await bot_client.get_me()
    if event.sender_id == me.id or event.sender_id == OWNER_ID:
        return

    sender_id = event.sender_id
    now = datetime.now()

    if sender_id not in sticker_spam_data:
        sticker_spam_data[sender_id] = {"count": 1, "last_time": now}
        return

    last_time = sticker_spam_data[sender_id]["last_time"]
    time_diff = (now - last_time).total_seconds()

    if time_diff <= 2.0:
        sticker_spam_data[sender_id]["count"] += 1
    else:
        sticker_spam_data[sender_id]["count"] = 1
        sticker_spam_data[sender_id]["last_time"] = now
        return

    if sticker_spam_data[sender_id]["count"] >= 2:
        try:
            sender = await event.get_sender()
            name = escape_html(sender.first_name)
            mention = f"<a href='tg://user?id={sender_id}'>{name}</a>"
            
            warning_msg = f"{mention} ဟာ stkတွေ အဲ့လို မspamပါနဲ့၊ ပြန်ဖျက်အုံး "
            await event.respond(bq(warning_msg), parse_mode='html')
            
            sticker_spam_data[sender_id]["count"] = 0 
        except Exception as e:
            print(f"Sticker Spam Error: {e}")

# 🎯 4. GROUP SPECIFIC RULES
@bot_client.on(events.NewMessage())
async def group_specific_rules(event):
    if event.is_private: return
    me = await bot_client.get_me()
    if not event.text or event.sender_id == OWNER_ID or event.sender_id == me.id: return

    text = event.text.strip()
    text_lower = text.lower()
    chat_id = event.chat_id
    sender = await event.get_sender()
    sender_id = event.sender_id
    
    if chat_id == SPECIFIC_GROUP:
        chat_title = escape_html(event.chat.title)
        keywords = ["ဂေ့", "ဂစ်", "ကတ်ဂေ့", "ကဒ်ဂေ့"]
        if re.search(r'^[/,.](harem|gift|check)', text_lower) or any(k in text_lower for k in keywords):
            full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
            user_mention = f"<a href='tg://user?id={sender_id}'>{full_name}</a>"
            msg = f"ဟိတ်... {user_mention} !! <b>{chat_title}</b> ထဲမှာ Character Catcher Bot ကို ကဒ်ကောက်ဖို့ပဲ ရတော့မယ်။ကျန်တဲ့ Giftပေးတာ,Haremတာ,Checkတာတွေအတွက် သီးသန့် Group Chat တစ်ခု ဖွင့်ပေးထားပါတယ်၊အဲ့ထဲမှာ စိတ်ကြိုက် ကဒ်ဂေ့၊ဟာရမ်း၊ချက်ခ်လုပ်ကြပါ သူငယ်ချင်းတို့🤍 သီးသန့် Group Mention Link - https://t.me/catchbot_gift_harem_check_only"
            try: await event.reply(bq(msg), parse_mode='html', link_preview=False)
            except: pass
            return 

@bot_client.on(events.NewMessage(pattern=r'^/play(?:\s+(.*))?'))
async def play_response(event):
    if event.is_private: return
    song_title = event.pattern_match.group(1)
    if not song_title: return 
    sender = await event.get_sender()
    full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
    mention = f"<a href='tg://user?id={event.sender_id}'>{full_name}</a>"
    response = f"<b>Song Title</b>- {escape_html(song_title)}\n<b>သီချင်းဖွင့်တဲ့သူ</b>- {mention}\nစနားထောင်လို့ရပါပြီ။\nMusic botကို ပိတ်ဖို့လည်း မမေ့ပါနဲ့🤍"
    await event.respond(bq(response), parse_mode='html')

@bot_client.on(events.NewMessage(pattern=r'^/addallow(?:@\w+)?$'))
async def add_allow(event):
    if event.sender_id != OWNER_ID: return
    reply = await event.get_reply_message()
    if reply:
        allow_col.update_one({"user_id": reply.sender_id}, {"$set": {"name": reply.sender.first_name}}, upsert=True)
        await event.reply(bq(f"{escape_html(reply.sender.first_name)} ကို Allow List ထည့်ပြီးပါပြီ! ✅"), parse_mode='html')
    else: await event.reply(bq("Allow ပေးချင်တဲ့သူကို Reply ထောက်ပြီးမှ Command ရိုက်"), parse_mode='html')

@bot_client.on(events.NewMessage(pattern=r'^/allowlist(?:@\w+)?$'))
async def allow_list(event):
    if event.sender_id != OWNER_ID: return
    users = list(allow_col.find())
    if users:
        msg = "<b>✅ Allowed Users List:</b>\n\n"
        for u in users: msg += f"• <a href='tg://user?id={u.get('user_id')}'>{escape_html(u.get('name', 'Unknown'))}</a> (<code>{u.get('user_id')}</code>)\n"
    else: msg = "Allow List မှာ မရှိသေးပါ။"
    await event.reply(bq(msg), parse_mode='html')

@bot_client.on(events.NewMessage(pattern=r'^/send(?:@\w+)?\s+(.*)'))
async def broadcast(event):
    if event.sender_id != OWNER_ID: return
    text = event.pattern_match.group(1)
    if not text: return await event.respond(bq("ပို့မယ့်စာသား ထည့်ပါဦး​ဗျ"))
    success = 0
    for g in list(groups_col.find()):
        try:
            await bot_client.send_message(g['chat_id'], bq(text), parse_mode='html')
            success += 1
        except: pass
    await event.respond(bq(f"ငါ မင်းပို့ခိုင်းတဲ့ Message တွေကို သေချာပို့ပေးလိုက်ပြီ! 📢\nပို့ဆောင်ပြီးစီးသော Group အရေအတွက်: {success}"), parse_mode='html')

@bot_client.on(events.NewMessage(pattern=r'^[/.]show'))
async def show_commands(event):
    features = (
        "🤖 <b>BoDx Sovereign Bot Features:</b>\n"
        "• <b>Welcome Image:</b> အဖွဲ့ဝင်သစ်တွေကို Profile ပါတဲ့ ပုံနဲ့ ကြိုဆိုခြင်း\n"
        "• <b>Anti-Spam:</b> Sticker 2 ခု 1 စက္ကန့်အတွင်း ပို့ရင် သတိပေးခြင်း\n"
        "• <b>Filters:</b> Link, Bio, Harem/Waifu Command တွေ သန့်ရှင်းရေးလုပ်ခြင်း\n"
        "• <b>VC Monitor:</b> Voice Chat စတာနဲ့ ပြီးတာကို အသိပေးခြင်း\n\n"
    )
    admin_cmds = (
        "🛠 <b>Admin Commands:</b>\n"
        "• <code>/adm [text]</code> - Admin အကုန်လုံးကို Tag ခေါ်ပြီး စာပို့ခြင်း\n"
        "• <code>/mute</code> / <code>/unmute</code> - စာပို့ခွင့် ပိတ်/ဖွင့်ခြင်း\n"
        "• <code>/play [name]</code> - သီချင်းဖွင့်ကြောင်း အလှပြစာသားပို့ခြင်း\n"
        "• <code>/id</code> / <code>/gid</code> - User သို့မဟုတ် Group ရဲ့ ID ကို ကြည့်ခြင်း\n\n"
    )
    allowed_only = (
        "🌟 <b>Allowed Users Only:</b>\n"
        "• <code>/b</code> - တစ်ဖက်လူကို ခေါင်းမဖော်နိုင်အောင် ဆဲခိုင်းခြင်း (Bully)\n"
        "• <code>/sb</code> - Bully လုပ်နေတာကို ရပ်ခိုင်းခြင်း\n"
        "• <code>/delete [id]</code> - Target Bot ကို ၂ စက္ကန့်အတွင်း ဖျက်ခိုင်းခြင်း\n"
    )

    full_msg = features + admin_cmds + allowed_only
    await event.respond(bq(full_msg), parse_mode='html')

# 🎯 FILTER WATCHER (အောက်ဆုံးမှာထားပါ)
@bot_client.on(events.NewMessage())
async def group_filter_watcher(event):
    if event.chat_id != TARGET_GROUP_ID or not event.text: 
        return
    
    me = await bot_client.get_me()
    if event.sender_id == me.id: 
        return

    user_msg = event.text.lower().strip()
    all_filters = filters_col.find({"chat_id": event.chat_id})
    
    for item in all_filters:
        keyword = item["keyword"].lower().strip()
        
        is_match = False
        if user_msg == keyword: 
            is_match = True
        elif f" {keyword} " in f" {user_msg} ": 
            is_match = True
        elif user_msg.startswith(f"{keyword} "): 
            is_match = True
        elif user_msg.endswith(f" {keyword}"): 
            is_match = True

        if is_match:
            content = item["content"]
            m_type = item["type"]
            try:
                if m_type == "text":
                    await event.reply(content)
                else:
                    await event.reply(file=content)
                break
            except Exception as e:
                print(f"Filter Response Error: {e}")

# ==========================================
# 🚀 EXECUTION
# ==========================================
async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ BoDx Sovereign System Online!")
    await bot_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

