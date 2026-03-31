import asyncio
import re
import os
import logging
import random
from pymongo import MongoClient
from telegram import Update, ChatPermissions, ChatMember
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    ChatMemberHandler
)

# --- LOGGING SETUP ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION ---
TOKEN = "8575371720:AAHR_1fCkRxlALIbhMH0yufXGJiUSQYJyYE" 
OWNER_ID = 6015356597
ADMIN_GROUP_ID = -1003580630981
SAVE_CHAT = -1003864912245  
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"
LINK_REGEX = r"(https?://|t\.me|telegram\.me|www\.)"

# --- DATABASE CONNECTION ---
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
bully_tasks = {} 
stop_events = {} 

# --- DB HELPERS ---
def get_list(name):
    data = db.settings.find_one({"_id": name})
    return data["data"] if data and "data" in data else []

def set_list(name, data):
    db.settings.update_one({"_id": name}, {"$set": {"data": data}}, upsert=True)

def get_bool(name):
    data = db.settings.find_one({"_id": name})
    return data.get("data", False) if data else False

def set_bool(name, val):
    db.settings.update_one({"_id": name}, {"$set": {"data": val}}, upsert=True)

# --- PERMISSIONS ---
async def is_allow(update: Update):
    uid = update.effective_user.id
    if uid == OWNER_ID or uid in get_list("allow"): return True
    await update.message.reply_text("<blockquote>မင်းမှာ BoDxBrotherhood_of_Dexter bot Command သုံးခွင့်မရှိသေးဘူး🫵 @Besties_with_BoD ကိုလာပြီးယူလို့ရတယ်</blockquote>", parse_mode=ParseMode.HTML)
    return False

async def is_tg_ban_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid == OWNER_ID: return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, uid)
        return member.status in ['administrator', 'creator']
    except: return False

# --- MEMBER HANDLER (Greetings & Auto Mark) ---
async def member_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member if update.chat_member else update.my_chat_member
    if not result: return
    
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title
    user = result.new_chat_member.user
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status

    # 1. Bot Presence (Auto Registration)
    if user.id == context.bot.id:
        if new_status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
            marked = get_list("marked_groups")
            if chat_id not in marked:
                marked.append(chat_id)
                set_list("marked_groups", marked)
                
                admin_msg = f"👋 <b>ကိုခန့်သူရိန်ဗျ @Wyaaqq_Zxyfanzt ကျနော်တို့ BoD_Brotherhood_of_Dexter Bot ကို ယူသုံးထားပါတယ်</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>Group Name:</b> {chat_title}\n<b>🆔 Group Id:</b> <code>{chat_id}</code>"
                try: await context.bot.send_message(ADMIN_GROUP_ID, admin_msg, parse_mode=ParseMode.HTML)
                except: pass
                
                owner_m = f'<a href="tg://user?id={OWNER_ID}">ခန့်သူရိန်</a>'
                await context.bot.send_message(chat_id, f"<blockquote>ဟိတ်ရို့ /admins မင်းတို့ရဲ့ဒီ group <b>{chat_title}</b> ကို ထည့်သွင်းအသုံးပြုပေးတဲ့အတွက် ကျေးဇူး၊ အမ် အသုံးဝင်မယ့် တချို့ကန့်သန့်ထားတဲ့ bot command တွေသုံးမယ်ဆို @Besties_with_BoD က OWNER {owner_m} ဆီကိုလာဆက်သွယ်ပေးပါ။ဒါက bot command ရှိသူတွေက botကိုnew bully msgတွေသင်ပေးတဲ့နေရာ @rudeword</blockquote>", parse_mode=ParseMode.HTML)
        elif new_status in [ChatMember.LEFT, ChatMember.KICKED]:
            marked = get_list("marked_groups")
            if chat_id in marked:
                marked.remove(chat_id)
                set_list("marked_groups", marked)
            db.filters.delete_many({"chat_id": chat_id})

    # 2. User Welcome/Goodbye
    else:
        mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
        if old_status in [ChatMember.LEFT, ChatMember.KICKED] and new_status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
            await context.bot.send_message(chat_id, f"<blockquote>ဟိတ် {mention}! {chat_title} ကနေ ကြိုဆိုလိုက်ပါတယ်!🫵 စကားအေးဆေးဝင်​ပြောလို့ရတယ်၊လူတွေမို့လူတွေကိုဖော်ရွေတယ်၊တစ်ဦးနှင့်တစ်ဦး အတတ်နိုင်ဆုံး လေးစားသမှုနဲ့ ​​​ပြောဆိုကြ</blockquote>", parse_mode=ParseMode.HTML)
        elif old_status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR] and new_status in [ChatMember.LEFT, ChatMember.KICKED]:
            await context.bot.send_message(chat_id, f"<blockquote>{mention} ထွက်သွားပါပြီ။ သွားတော့ ဝေးရာဆီ!</blockquote>", parse_mode=ParseMode.HTML)

# --- ADMIN ACTIONS (Protection Included) ---
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_tg_ban_admin(update, context):
        return await update.message.reply_text("<blockquote>မင်းမှာ ဒီ command သုံးဖို့ permission မရှိဘူး 🚫</blockquote>", parse_mode=ParseMode.HTML)
    
    cmd = update.message.text.split()[0][1:].lower()
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text("<blockquote>Reply ပြန်ပြီး command သုံးပါ။</blockquote>", parse_mode=ParseMode.HTML)
    
    chat_id, executor_id = update.effective_chat.id, update.effective_user.id
    try:
        t_mem = await context.bot.get_chat_member(chat_id, target.id)
        e_mem = await context.bot.get_chat_member(chat_id, executor_id)

        if t_mem.status in ['administrator', 'creator'] and executor_id != OWNER_ID:
            return await update.message.reply_text("<blockquote>Admin အချင်းချင်း လုပ်ပိုင်ခွင့်မရှိပါ! 🚫</blockquote>", parse_mode=ParseMode.HTML)

        if cmd == "mute":
            await context.bot.restrict_chat_member(chat_id, target.id, permissions=ChatPermissions(can_send_messages=False))
            await update.message.reply_text(f"<blockquote>{target.full_name} ကို မဟုတ်တာတွေပြောလို့ mute လိုက်ပြီ!</blockquote>", parse_mode=ParseMode.HTML)
        elif cmd == "unmute":
            await context.bot.restrict_chat_member(chat_id, target.id, permissions=ChatPermissions(can_send_messages=True, can_send_photos=True, can_send_videos=True, can_send_audios=True, can_send_documents=True, can_send_other_messages=True, can_add_web_page_previews=True, can_invite_users=True))
            await update.message.reply_text(f"<blockquote>ဟိတ် {target.full_name}! မဟုတ်တာမပြောဖို့ကိုဆင်ခြင်ပါ၊နောက်ဆို တန်း ban မယ်!</blockquote>", parse_mode=ParseMode.HTML)
        elif cmd == "kick":
            await context.bot.unban_chat_member(chat_id, target.id)
            await update.message.reply_text("<blockquote>အလိုက်တသိ ထွက်မသွားလို့ kick လိုက်ပြီ!</blockquote>", parse_mode=ParseMode.HTML)
        elif cmd == "ban":
            if not e_mem.can_restrict_members: return await update.message.reply_text("<blockquote>မင်းမှာ ban ပိုင်ခွင့် permission မရှိဘူး! 🚫</blockquote>", parse_mode=ParseMode.HTML)
            await context.bot.ban_chat_member(chat_id, target.id)
            await update.message.reply_text("<blockquote>ဆက်နေခွင့်မပေးသင့်တော့လို့ ban လိုက်ပြီ!</blockquote>", parse_mode=ParseMode.HTML)
        elif cmd == "addadmin":
            if e_mem.status != 'creator' and executor_id != OWNER_ID:
                return await update.message.reply_text("<blockquote>Owner သာလျှင် Admin ခန့်နိုင်သည်။</blockquote>", parse_mode=ParseMode.HTML)
            await context.bot.promote_chat_member(chat_id, target.id, can_delete_messages=True, can_restrict_members=True, can_invite_users=True, can_pin_messages=True, can_manage_video_chats=True)
            await update.message.reply_text(f"<blockquote>{target.full_name} ကို Admin ပေးလိုက်ပါပြီ! Group ကို တိုးတက်အောင်စွမ်းဆောင်ပါ🫵</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e: await update.message.reply_text(f"<blockquote>Error: {e}</blockquote>", parse_mode=ParseMode.HTML)

# --- BULLY & BROADCAST ---
async def bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allow(update): return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text("<blockquote>Reply ပြန်ပြီး လိုးသတ်။</blockquote>", parse_mode=ParseMode.HTML)
    
    if target.id == OWNER_ID or target.id in get_list("allow"):
        return await update.message.reply_text("<blockquote>ဟိတ်မင်းတို့က တစ်ဖွဲ့တည်းတွေ စည်းလုံးကြစမ်း! 🫵</blockquote>", parse_mode=ParseMode.HTML)

    chat_id, words = update.effective_chat.id, get_list("bully")
    if not words: return await update.message.reply_text("<blockquote>Bully list အလွတ်ဖြစ်နေသည်။</blockquote>", parse_mode=ParseMode.HTML)
    
    if chat_id in bully_tasks: 
        stop_events[chat_id].set()
        bully_tasks[chat_id].cancel()
    
    stop_events[chat_id] = asyncio.Event()
    mention = f'<a href="tg://user?id={target.id}">{target.full_name}</a>'
    
    # Statistics
    stats = (db.settings.find_one({"_id": "bully_stats"}) or {"data": {}}).get("data", {})
    stats[str(target.id)] = stats.get(str(target.id), 0) + 1
    db.settings.update_one({"_id": "bully_stats"}, {"$set": {"data": stats}}, upsert=True)

    async def loop():
        try:
            while not stop_events[chat_id].is_set():
                pool = words.copy()
                random.shuffle(pool)
                for _ in range(5):
                    if not pool or stop_events[chat_id].is_set(): break
                    await context.bot.send_message(chat_id, f"<blockquote>{mention} {pool.pop()}</blockquote>", parse_mode=ParseMode.HTML)
                    await asyncio.sleep(0.5)
                await asyncio.sleep(4)
        except: pass
    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(f"<blockquote>🔥 {target.full_name} ကို ဟိတ်ကောင် မင်းကိုအသေလိုးပြီ!🫵</blockquote>", parse_mode=ParseMode.HTML)

async def sendallgp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message: return await update.message.reply_text("<blockquote>Broadcast လုပ်မယ့် message ကို Reply ပြန်ပါ။</blockquote>", parse_mode=ParseMode.HTML)
    
    msg, groups = update.message.reply_to_message, get_list("marked_groups")
    count, fail = 0, 0
    status_msg = await update.message.reply_text("<blockquote>🚀 Broadcast စတင်နေပြီ...</blockquote>", parse_mode=ParseMode.HTML)
    
    for gid in groups:
        try:
            await context.bot.copy_message(chat_id=gid, from_chat_id=update.effective_chat.id, message_id=msg.message_id)
            count += 1
            await asyncio.sleep(0.3)
        except: fail += 1
    await status_msg.edit_text(f"<blockquote>🚀 Broadcast ပြီးပါပြီ!\n✅ အောင်မြင်: {count}\n❌ ကျရှုံး: {fail}</blockquote>", parse_mode=ParseMode.HTML)

# --- MAIN HANDLER (Filters & Save) ---
async def main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    chat_id, uid, text = update.effective_chat.id, update.effective_user.id, (update.message.text or update.message.caption)
    
    if text and not text.startswith('/'):
        f_data = db.filters.find_one({"chat_id": chat_id, "keyword": text.lower()})
        if f_data: await update.message.reply_text(f"<blockquote>{f_data['reply']}</blockquote>", parse_mode=ParseMode.HTML)
        
        if chat_id == SAVE_CHAT and get_bool("save") and (uid == OWNER_ID or uid in get_list("allow")):
            bully_list = get_list("bully")
            if text not in bully_list:
                bully_list.append(text)
                set_list("bully", bully_list)
                await context.bot.send_message(chat_id, f"<blockquote>Bully text (1)ကြောင်း ပေါင်းထည့်ထားသေးတယ် အခုဆိုရင် Bully Text စုစုပေါင်း ({len(bully_list)})ရှိနေပြီ မလုံလောက်သေးဘူး</blockquote>", parse_mode=ParseMode.HTML)

# --- SYSTEM COMMANDS ---
async def allowlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    allowed = get_list("allow")
    owner_m, bot_m = f'<a href="tg://user?id={OWNER_ID}">ခန့်သူရိန်</a>', f'<a href="tg://user?id={context.bot.id}">ThuRain</a>'
    res = f"<blockquote>ဟုတ် {owner_m} က {bot_m} ရဲ့ command တွေကို သူတို့ကိုသုံးခွင့်ပေးထားပါသေးတယ်:</blockquote>\n"
    for u_id in allowed: res += f"• <a href='tg://user?id={u_id}'>{u_id}</a>\n"
    await update.message.reply_text(res, parse_mode=ParseMode.HTML)

async def bullylist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    stats = (db.settings.find_one({"_id": "bully_stats"}) or {"data": {}}).get("data", {})
    res = "<blockquote>ဒီကောင်တွေ bullyထားခံရတယ်:</blockquote>\n"
    for uid, count in stats.items(): res += f"• <code>{uid}</code> - {count} ကြိမ်\n"
    await update.message.reply_text(res, parse_mode=ParseMode.HTML)

async def savelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    await update.message.reply_text(f"<blockquote>bullyစာသားစုစုပေါင်း ({len(get_list('bully'))})ကို သိမ်းထားပြီးပြီ။ထပ်ထည့်ရင်လည်း ထပ်ထည့်မယ်</blockquote>", parse_mode=ParseMode.HTML)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(member_update_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(ChatMemberHandler(member_update_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("stopbully", lambda u,c: stop_events[u.effective_chat.id].set() or u.message.reply_text("<blockquote>ရပ်လိုက်ပြီ!</blockquote>", parse_mode=ParseMode.HTML) if u.effective_chat.id in stop_events else None))
    app.add_handler(CommandHandler(["mute", "unmute", "kick", "ban", "addadmin"], admin_action))
    app.add_handler(CommandHandler("sendallgp", sendallgp))
    app.add_handler(CommandHandler("allowlist", allowlist))
    app.add_handler(CommandHandler("bullylist", bullylist))
    app.add_handler(CommandHandler("savelist", savelist))
    app.add_handler(CommandHandler("markgp", lambda u,c: u.message.reply_text("<blockquote>ဒီ Group က BoDနဲ့အတူကာကွယ်ပေးထားပြီးသားပါ</blockquote>", parse_mode=ParseMode.HTML)))
    app.add_handler(CommandHandler("save_on", lambda u,c: set_bool("save", True) or u.message.reply_text("<blockquote>✅ Auto Save: ON</blockquote>", parse_mode=ParseMode.HTML)))
    app.add_handler(CommandHandler("save_off", lambda u,c: set_bool("save", False) or u.message.reply_text("<blockquote>❌ Auto Save: OFF</blockquote>", parse_mode=ParseMode.HTML)))
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION), main_handler))
    app.run_polling()

if __name__ == "__main__": main()
