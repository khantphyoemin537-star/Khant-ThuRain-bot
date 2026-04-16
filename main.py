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

# --- DNS FIX FOR MONGODB ---
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
target_bots_col = db["target_bots"]
replies_col = db["custom_replies"] 
# --- BOT CLIENT SETUP ---
bot_client = TelegramClient('bot_session', APP_ID, APP_HASH)

# --- HELPERS ---
bot_bully_tasks = {}
save_status = False

def bq(text): 
    return f"<blockquote><b>{text}</b></blockquote>"

def owner_tag(): 
    return f"<a href='tg://user?id={OWNER_ID}'>⚚𝘽𝙤𝘿𝙭𝗪𝘆𝗮𝗮𝗾𝗾 𝗭𝘅𝘆𝗳𝗮𝗻𝘇𝘁</a>"

def is_allowed(user_id):
    if user_id == OWNER_ID: return True
    return allow_col.find_one({"user_id": user_id}) is not None

# Unified Admin Checker
async def check_admin(chat_id, user_id):
    if user_id == OWNER_ID: return True
    try:
        permissions = await bot_client.get_permissions(chat_id, user_id)
        return permissions.is_admin
    except:
        return False

# --- IMAGE WELCOME HELPER (အသစ်ထည့်ရန်အပိုင်း) ---
def create_welcome_image(bg_bytes, user_pf_bytes):
    # ၁။ နောက်ခံပုံ (Group PF) ကို ဖွင့်ပြီး Resize လုပ်မယ် (1280x720)
    bg = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
    bg = ImageOps.fit(bg, (1280, 720), centering=(0.5, 0.5))
    
    # ပုံကို ပိုလန်းအောင် နည်းနည်း မှောင်ပေးမယ် (စာသားပေါ်အောင်)
    overlay = Image.new('RGBA', bg.size, (0, 0, 0, 100)) # Black overlay with 100 alpha
    bg = Image.alpha_composite(bg, overlay)

    # ၂။ အသစ်ဝင်လာသူရဲ့ PF ကို ဖွင့်ပြီး လေးထောင့်ပုံစံ Resize လုပ်မယ် (300x300)
    user_pf = Image.open(io.BytesIO(user_pf_bytes)).convert("RGBA")
    user_pf = user_pf.resize((300, 300), Image.Resampling.LANCZOS)
    
    # ၃။ User PF ကို Background ပေါ် တင်မယ် (ဘယ်ဘက်ထောင့်၊ Offset: 50, 210)
    bg.paste(user_pf, (50, 210), user_pf) # 210 is to align vertically with text center
    
    # ၄။ စာသား ထည့်မယ် ("ကြိုဆိုပါတယ် သူငယ်ချင်း")
    draw = ImageDraw.Draw(bg)
    
    # မြန်မာစာသားအတွက် Font လိုအပ်ပါတယ် (Code တည်ရှိရာနေရာမှာ font.ttf ရှိရမယ်)
    # Default font သုံးရင် မြန်မာစာ ပေါ်မှာ မဟုတ်ဘူး။ Chief မှာ font.ttf ရှိရင် အောက်က line ကို သုံးပါ။
    # font = ImageFont.truetype("font.ttf", 80) 
    
    # Chief မှာ font file မရှိသေးရင် ယာယီအားဖြင့် English စာသားနဲ့ပဲ ပြပေးထားမယ်။
    # Chief font file တင်ပြီးရင် အပေါ်က comment ကို ဖွင့်ပြီး သုံးပါ။
    try:
        # သင်တန်းမှာ font.ttf တင်ထားရင် ဒါကိုသုံးပါ
        font = ImageFont.truetype("font.ttf", 80)
        text = "ကြိုဆိုပါတယ် သူငယ်ချင်း"
    except:
        # Font file မရှိရင် default font ကိုသုံးပြီး English လိုပြမယ် (မြန်မာစာ default နဲ့ မရလို့ပါ)
        font = ImageFont.load_default()
        text = "Welcome, Friend!" 
        print("Warning: font.ttf not found. Using default font and English text.")

    # စာသားတည်နေရာ (User PF ရဲ့ ညာဘက်)
    text_position = (400, 320) # X=400 (300 PF + 50 offset + 50 gap), Y=320 (aligned with PF)
    
    # စာသားအရောင် (အဖြူရောင်)
    draw.text(text_position, text, font=font, fill=(255, 255, 255, 255))
    
    # ၅။ နောက်ဆုံးပုံကို Bytes အနေနဲ့ ပြန်ထုတ်ပေးမယ်
    img_byte_arr = io.BytesIO()
    bg.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr.read()

@bot_client.on(events.NewMessage(pattern=r'^[/.]reply'))
async def add_custom_reply(event):
    if event.chat_id != -1003580630981: return
    if not await is_allowed(event.sender_id): return

    reply_to = await event.get_reply_message()
    if not reply_to:
        return await event.respond(bq("အသုံးပြုပုံ- သင်ပြန်စေချင်တဲ့စာကို Reply ထောက်ပြီး <code>/reply keyword</code> လို့ ရိုက်ပါဗျ။"), parse_mode='html')

    # Command ရဲ့နောက်က Keyword ကိုယူမယ် (ဥပမာ- /reply hi ဆိုရင် 'hi' ကိုယူမယ်)
    args = event.text.split(maxsplit=1)
    if len(args) < 2:
        return await event.respond(bq("Keyword ထည့်ပေးဖို့ လိုပါတယ် Chief!"), parse_mode='html')
    
    keyword = args[1].lower()
    
    # ပြန်ပို့ရမယ့်စာသား (Reply ထောက်ထားတဲ့စာက Text ဒါမှမဟုတ် Caption ကိုယူမယ်)
    response_text = reply_to.text if reply_to.text else ""
    
    # Database ထဲ သိမ်းမယ် (ရှိပြီးသားဆိုရင် Update လုပ်မယ်)
    replies_col.update_one(
        {"keyword": keyword},
        {"$set": {"response": response_text}},
        upsert=True
    )
    
    await event.respond(bq(f"အခုကစပြီး <code>{keyword}</code> လို့ ပို့ရင် အဲ့ဒီစာကို ပြန်ပို့ပေးပါမယ်။ ✅"), parse_mode='html')

@bot_client.on(events.NewMessage())
async def custom_reply_listener(event):
    # သတ်မှတ်ထားတဲ့ Group မဟုတ်ရင် ကျော်မယ်
    if event.chat_id != -1003580630981 or event.is_private or not event.text:
        return

    me = await bot_client.get_me()
    if event.sender_id == me.id: return # Bot အချင်းချင်း loop မပတ်အောင်

    # ပို့လိုက်တဲ့စာကို database ထဲမှာ ရှာမယ်
    user_text = event.text.lower().strip()
    entry = replies_col.find_one({"keyword": user_text})

    if entry:
        try:
            # စာကို Reply ပြန်တဲ့ပုံစံမျိုးနဲ့ ပို့ပေးမယ်
            await event.reply(entry["response"])
        except Exception as e:
            print(f"Reply Error: {e}")


# ==========================================
# 🎯 GROUP SPECIFIC RULES (-1003580630981 & -1003806830045)
# ==========================================
@bot_client.on(events.NewMessage())
async def group_specific_rules(event):
    if event.is_private: return
    
    me = await bot_client.get_me()
    if not event.text or event.sender_id == OWNER_ID or event.sender_id == me.id:
        return

    text = event.text.strip()
    text_lower = text.lower()
    chat_id = event.chat_id
    sender = await event.get_sender()
    sender_id = event.sender_id
    
        # --- 1. SPECIFIC GROUP (-1003580630981) LOGIC ---
    if chat_id == -1003580630981:
        chat = await event.get_chat()
        chat_title = escape_html(chat.title)
        keywords = ["ဂေ့", "ဂစ်", "ကတ်ဂေ့", "ကဒ်ဂေ့"]
        cmd_pattern = r'^[/,.](harem|gift|check)' 
        is_match = False
        
        if re.search(cmd_pattern, text_lower) or any(k in text_lower for k in keywords):
            is_match = True
            
        if is_match:
            full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
            user_mention = f"<a href='tg://user?id={sender_id}'>{full_name}</a>"
            msg = f"ဟိတ်... {user_mention} !! <b>{chat_title}</b> ထဲမှာ Character Catcher Bot ကို ကဒ်ကောက်ဖို့ပဲ ရတော့မယ်။ကျန်တဲ့ Giftပေးတာ,Haremတာ,Checkတာတွေအတွက် သီးသန့် Group Chat တစ်ခု ဖွင့်ပေးထားပါတယ်၊အဲ့ထဲမှာ စိတ်ကြိုက် ကဒ်ဂေ့၊ဟာရမ်း၊ချက်ခ်လုပ်ကြပါ သူငယ်ချင်းတို့🤍 သီးသန့် Group Mention Link - https://t.me/catchbot_gift_harem_check_only"
            try:
                # await event.delete()  <-- ဒီကောင်ကို ဖျက်လိုက် (သို့) comment ပိတ်လိုက်ပါ
                # event.reply ကို သုံးပြီး သူပို့တဲ့စာကို reply ပြန်ပေးလိုက်မယ်
                await event.reply(bq(msg), parse_mode='html', link_preview=False)
            except Exception as e: 
                print(f"Group 1 Error: {e}")
            return 


    #     # --- 2. MAIN GROUP (-1003806830045) LOGIC ---
    if chat_id == -1003806830045:
        # ၁။ ပို့လိုက်တဲ့စာက Command (/ or .) မဟုတ်ဘူး၊ ကိန်းဂဏန်းလည်း မဟုတ်ဘူးဆိုရင်
        if not re.match(r'^[/.\d]', text):
            
            # --- Admin/Owner သီးသန့် /ok Reply စစ်ဆေးခြင်း ---
            # စာကို reply ထောက်ထားခြင်း ရှိ/မရှိ စစ်မယ်
            reply = await event.get_reply_message()
            
            if reply:
                # Reply ပြန်တဲ့သူက Admin ဟုတ်မဟုတ် စစ်မယ်
                is_admin_reply = await check_admin(event.chat_id, event.sender_id)
                
                # အကယ်၍ Admin/Owner က /ok လို့ reply ပြန်လိုက်တာဆိုရင် မဖျက်ဘဲ ကျော်သွားမယ်
                if is_admin_reply and event.text.strip().lower() == "/ok":
                    # အဲ့ဒီ /ok ဆိုတဲ့စာကိုပါ ပြန်ဖျက်ပေးရမယ် (အမြင်သန့်အောင်)
                    try: await event.delete()
                    except: pass
                    return # Logic ကို ဒီမှာတင် ရပ်လိုက်မယ် (မူရင်းစာ မပျက်တော့ဘူး)
            # -----------------------------------------------

            # Admin က /ok လို့ Reply မပြန်ထားတဲ့ စာတွေဆိုရင်တော့ ပုံမှန်အတိုင်း ဖျက်မယ်
            full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
            user_mention = f"<a href='tg://user?id={sender_id}'>{full_name}</a>"
            msg = f"{user_mention} ဟယ်လို သူငယ်ချင်း ဒီထဲမှာက တခြားစာတွေစကားတွေပြောမရဘူးနော်၊ ပြောမယ်ဆို @Besties_with_BoD ကိုသွားပေး"
            
            try:
                await event.delete() 
                await event.respond(bq(msg), parse_mode='html')
            except Exception as e: 
                print(f"Group 2 Error: {e}")
            return 

# ==========================================
# --- TARGET BOT MONITOR & COPYCAT LOGIC ---
@bot_client.on(events.NewMessage())
async def target_bot_shadow(event):
    if event.is_private or not event.text: return
    
    me = await bot_client.get_me()
    
    # ၁။ ကိုယ့် Bot ပို့တဲ့စာ ဒါမှမဟုတ် Owner ပို့တဲ့စာဆိုရင် ကျော်မယ်
    if event.sender_id == me.id or event.sender_id == OWNER_ID:
        return

    # ၂။ ဒီနေရာမှာ အခုပေးတဲ့ code ကို ထည့်ရမှာပါ (Database ကနေ Target စစ်တာ)
    target_bot = target_bots_col.find_one({
        "$or": [
            {"bot_id": event.sender_id},       # Integer အနေနဲ့ စစ်မယ်
            {"bot_id": str(event.sender_id)}  # String အနေနဲ့ပါ ထပ်စစ်မယ်
        ]
    })
    
    # ၃။ အကယ်၍ Target Bot ဟုတ်ခဲ့ရင် ကျန်တဲ့ Logic တွေ ဆက်လုပ်မယ်
    if target_bot:
        try:
            copy_text = event.text
            shadow_msg = await event.respond(
                bq(f"Copying Target: {copy_text}\n\nGroup Chat သန့်ရှင်းအောင် ၄ စက္ကန့်အတွင်း ဖျက်လိုက်ပါပြီ။"), 
                parse_mode='html'
            )
            
            for i in range(3, -1, -1):
                await asyncio.sleep(1)
                if i == 0:
                    try:
                        await event.delete() # Target Bot ရဲ့စာကို ဖျက်မယ်
                        await shadow_msg.delete() # ကိုယ့်စာကို ပြန်ဖျက်မယ်
                    except: pass
                    break
                
                try:
                    await shadow_msg.edit(
                        bq(f"Copying Target: {copy_text}\n\nGroup Chat သန့်ရှင်းအောင် {i} စက္ကန့်အတွင်း ဖျက်လိုက်ပါပြီ။"), 
                        parse_mode='html'
                    )
                except: break
        except Exception as e:
            print(f"Shadow Logic Error: {e}")




# ==========================================
# 🛡️ FILTERS & PROTECTION (BIO/LINK)
# ==========================================
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
        if event.forward:
            is_admin_user = await check_admin(chat_id, sender_id)
            if is_admin_user:
                text_lower = text.lower()
                if any(k in text_lower for k in ["movie", "episode", "season", "ဇာတ်ကား", "ကားသစ်"]):
                    await event.reply(bq("ဘာကားလဲဟ! သူငယ်ချင်းတွေပါ ခေါ်ကြည့်လို့ရတယ်နော်။ 😎🍿"), parse_mode='html')
                elif any(k in text_lower for k in ["mp3", "music", "song", "lyrics", "audio", "သီချင်း"]):
                    await event.reply(bq("သီချင်းကောင်းလေးပဲ! ကျန်တဲ့သူတွေလည်း သူပို့တာ နားထောင်ကြည့်ကြဦး။ 🔥🎧"), parse_mode='html')
            return 

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
                    await asyncio.sleep(1)
                    try: await warn_msg.edit(bq(step), parse_mode='html')
                    except: break
            except Exception as e:
                print(f"Member Link Animation Error: {e}")

# ==========================================
# 🔵 WELCOME & ACTION LOGIC (IMAGE-BASED)
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
                    # အသစ်ဝင်လာတဲ့သူကို Image နဲ့ ကြိုဆိုမယ့် Logic (အသစ်ထည့်ရန်အပိုင်း)
                    try:
                        u = await bot_client.get_entity(uid)
                        u_mention = f"<a href='tg://user?id={u.id}'>{escape_html(u.first_name)}</a>"
                        
                        # ၁။ Group Profile Picture ကို Download လုပ်မယ်
                        bg_bytes = await bot_client.download_profile_photo(chat, file=bytes)
                        # ၂။ အသစ်ဝင်လာသူရဲ့ Profile Picture ကို Download လုပ်မယ်
                        user_pf_bytes = await bot_client.download_profile_photo(u, file=bytes)
                        
                        # ၃။ ပုံဖန်တီးမည့် Helper Function ကို ခေါ်မယ်
                        # Default ပုံတွေ သုံးဖို့ bytes မရရင် ကျော်မယ် (try-except)
                        if bg_bytes and user_pf_bytes:
                            # Run in executor to not block asyncio
                            final_img_bytes = await asyncio.get_event_loop().run_in_executor(
                                None, create_welcome_image, bg_bytes, user_pf_bytes
                            )
                            
                            # ၄။ ပုံကို Caption နဲ့အတူ ပို့မယ် (Animation ဖြုတ်လိုက်သည်)
                            caption_msg = f"ဟိတ် {u_mention} ... {safe_title} ကနေ ကြိုဆိုလိုက်ပါတယ်!! 🫵😎 စကားဝင်ပြော၊သီချင်းနားထောင်၊ရည်းစားရှာ အပေါင်းအသင်းရှာ ကြိုက်တာလုပ်!"
                            await bot_client.send_file(
                                event.chat_id, 
                                file=io.BytesIO(final_img_bytes), 
                                caption=bq(caption_msg), 
                                parse_mode='html'
                            )
                        else:
                            # PF မရှိရင် ပုံမှန်စာပဲ ပို့မယ်
                            await bot_client.send_message(
                                event.chat_id, 
                                bq(f"ဟိတ် {u_mention} ... {safe_title} ကနေ ကြိုဆိုလိုက်ပါတယ်!! 🫵😎 စကားဝင်ပြော၊သီချင်းနားထောင်၊ရည်းစားရှာ အပေါင်းအသင်းရှာ ကြိုက်တာလုပ်!"), 
                                parse_mode='html'
                            )
                            
                    except Exception as e: 
                        print(f"Welcome Image Error: {e}")

    elif event.user_left or event.user_kicked:
        try:
            u = await bot_client.get_entity(event.user_id)
            u_mention = f"<a href='tg://user?id={u.id}'>{escape_html(u.first_name)}</a>"
            await bot_client.send_message(event.chat_id, bq(f"ဟုတ် ထွက်သွားလိုက်ပါသေးတယ် {u_mention}!!"), parse_mode='html')
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
    except Exception as e: await event.respond(bq(f"Error: {e}"), parse_mode='html')

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

# --- BOT DELETE COMMAND ---
@bot_client.on(events.NewMessage(pattern=r'^/delete(?:@\w+)?$'))
async def add_delete_bot(event):
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
# --- VC DETECTION LOGIC (SERVICE & BOT DETECTION) ---

# ၁။ Service Message တွေကို ဖမ်းဖို့ (Group Call Started/Ended)
@bot_client.on(events.ChatAction)
async def vc_service_listener(event):
    if event.is_private: return
    
    # Voice Chat စလိုက်တဲ့အခါ
    if event.action_message and isinstance(event.action_message.action, types.MessageActionGroupCallStarted):
        await event.respond(bq("ဟုတ် သီချင်းနားထောင်တာ (or) စကားပြောဖို့အတွက် Voice Chat စလိုက်ပါသေးတယ် 🎧"), parse_mode='html')
    
    # Voice Chat ပိတ်လိုက်တဲ့အခါ
    elif event.action_message and isinstance(event.action_message.action, types.MessageActionGroupCallEnded):
        await event.respond(bq("Voice Chat ပြီးဆုံးသွားပါပြီ!! 💔"), parse_mode='html')

# ၂။ Music Bot တွေရဲ့ စာသားကို ဖမ်းဖို့
@bot_client.on(events.NewMessage())
async def vc_text_listener(event):
    if event.is_private or not event.text: return
    
    MUSIC_BOT_IDS = [7428895701, 987654321]
    VC_START_KEYWORDS = ["voice chat started", "video chat started", "vc started", "music started"]
    VC_END_KEYWORDS = ["voice chat ended", "video chat ended", "vc ended", "music stopped", "thanks for the vibes"]

    if event.sender_id in MUSIC_BOT_IDS:
        text_lower = event.text.lower()
        if any(kw in text_lower for kw in VC_START_KEYWORDS):
            await event.reply(bq("ဟုတ် Voice Chat စလိုက်ပါသေးတယ် 🎶"), parse_mode='html')
        elif any(kw in text_lower for kw in VC_END_KEYWORDS):
            await event.reply(bq("Voice Chat ပိတ်လိုက်ပါသေးတယ်!! 🥀"), parse_mode='html')


# Play Command Protection/Response
@bot_client.on(events.NewMessage(pattern=r'^/play(?:\s+(.*))?'))
async def play_response(event):
    if event.is_private: return
    song_title = event.pattern_match.group(1)
    if not song_title: return 

    sender = await event.get_sender()
    sender_id = event.sender_id
    full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
    mention = f"<a href='tg://user?id={sender_id}'>{full_name}</a>"

    response = f"<b>Song Title</b>- {escape_html(song_title)}\n<b>သီချင်းဖွင့်တဲ့သူ</b>- {mention}\nစနားထောင်လို့ရပါပြီ။\nMusic ကို ပိတ်ဖို့လည်း မမေ့ပါနဲ့🤍"
    await event.respond(bq(response), parse_mode='html')

# ==========================================
# 🤖 BULLY & SYSTEM
# ==========================================
@bot_client.on(events.NewMessage(pattern=r'^/b(?:@\w+)?$'))
async def bot_bully(event):
    if not is_allowed(event.sender_id):
        return await event.reply(bq("မင်းမှာ ဒီ Command ကို သုံးပိုင်ခွင့်မရှိဘူး။သုံးခွင့်နဲ့အသုံးပြုနည်းများအတွက် @Besties_with_BoDကိုလာ "), parse_mode='html')
    
    reply = await event.get_reply_message()
    if not reply:
        return await event.respond(bq("ဘယ်ကောင့်ကို ခေါင်းမဖော်နိုင်အောင် ဆဲပေးရမလဲ၊Replyပြန်လိုက် "))

    chat_id = event.chat_id
    t = await reply.get_sender()
    if not t: return

    target_id = t.id
    if target_id == OWNER_ID:
        target_id = event.sender_id
        t = await event.get_sender()
        await event.respond(bq("ဟိတ်ကောင်🫵😎 Creatorကိုများ ဆဲခိုင်းတယ်ပေါ့။ မင်းကိုပဲ ပြန်ကျွေးမယ်။ ခံလိုက်တော့! 🔥"))
    else:
        await event.respond(bq(f"<a href='tg://user?id={target_id}'>{escape_html(t.first_name)}</a>"))

    bot_bully_tasks[chat_id] = True
    mention = f"<a href='tg://user?id={target_id}'>{escape_html(t.first_name)}</a>"
    words = [w.get("text") for w in filters_col.find() if w.get("text")]
    
    if not words: return await event.respond(bq("DB မှာ စာလုံးမရှိသေးဘူး Chief!"))

    send_count = 0
    while bot_bully_tasks.get(chat_id):
        try: 
            await bot_client.send_message(chat_id, bq(f"{mention} {random.choice(words)}"), reply_to=reply.id if target_id != event.sender_id else event.id, parse_mode='html')
            send_count += 1
            if send_count >= 8: 
                await asyncio.sleep(1)
                send_count = 0 
            else: await asyncio.sleep(0.4) 
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
    if event.sender_id != OWNER_ID: return
    reply = await event.get_reply_message()
    if reply:
        allow_col.update_one({"user_id": reply.sender_id}, {"$set": {"name": reply.sender.first_name}}, upsert=True)
        name = escape_html(reply.sender.first_name)
        await event.reply(bq(f"{name} ကို Allow List ထည့်ပြီးပါပြီ! ✅"), parse_mode='html')
    else: await event.reply(bq("Allow ပေးချင်တဲ့သူကို Reply ထောက်ပြီးမှ Command ရိုက်"), parse_mode='html')

@bot_client.on(events.NewMessage(pattern=r'^/allowlist(?:@\w+)?$'))
async def allow_list(event):
    if event.sender_id != OWNER_ID: return
    users = list(allow_col.find())
    if users:
        msg = "<b>✅ Allowed Users List:</b>\n\n"
        for u in users:
            name = escape_html(u.get('name', 'Unknown'))
            user_id = u.get('user_id')
            msg += f"• <a href='tg://user?id={user_id}'>{name}</a> (<code>{user_id}</code>)\n"
    else: msg = "Allow List မှာ မရှိသေးပါ။"
    await event.reply(bq(msg), parse_mode='html')

@bot_client.on(events.NewMessage(pattern=r'^/send(?:@\w+)?\s+(.*)'))
async def broadcast(event):
    if event.sender_id != OWNER_ID: return
    text = event.pattern_match.group(1)
    if not text: return await event.respond(bq("ပို့မယ့်စာသား ထည့်ပါဦး Chief!"))

    success = 0
    all_groups = list(groups_col.find())
    for g in all_groups:
        try:
            await bot_client.send_message(g['chat_id'], bq(text), parse_mode='html')
            success += 107
        except Exception as e: pass
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
                    msg = f"{mentions}\n\nမင်းလူ 5 ယောက်ထည့်ပေးဖို့ မမေ့နဲ့ဦး! ပြီးရင် /done လို့ ပြောပါ🫵"
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
