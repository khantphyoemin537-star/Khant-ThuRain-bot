import asyncio
import re
import os
import logging
from pymongo import MongoClient
from telegram import Update, ChatPermissions
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
ADMIN_GROUP_ID = -1003806830045
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
    await update.message.reply_text("<blockquote>မင်းမှာ BoD's Wyaaqq Zxyfanzt bot Command သုံးခွင့်မရှိသေးဘူး🫵 @Besties_with_BoD ကိုလာပြီးယူလို့ရတယ်</blockquote>", parse_mode=ParseMode.HTML)
    return False

async def is_tg_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid == OWNER_ID: return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, uid)
        return member.status in ['administrator', 'creator']
    except: return False

# --- MEMBER HANDLER (Bot Entry & Member Join/Leave) ---
async def member_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return
    
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title
    user = result.new_chat_member.user
    
    was_member = result.old_chat_member.status in ["left", "kicked", "both_left"]
    is_member = result.new_chat_member.status in ["member", "administrator", "creator"]

    if was_member and is_member:
        if user.id == context.bot.id:
            marked = get_list("marked_groups")
            if chat_id not in marked:
                marked.append(chat_id)
                set_list("marked_groups", marked)
            
            admin_msg = (
                "👋 <b>Bot ကို ယူသုံးထားပါတယ်</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"<b>Group Name:</b> {chat_title}\n"
                f"<b>🆔 Group ID:</b> <code>{chat_id}</code>\n"
                "<b>No Link</b>"
            )
            try:
                await context.bot.send_message(ADMIN_GROUP_ID, admin_msg, parse_mode=ParseMode.HTML)
            except: pass

            owner_mention = f'<a href="tg://user?id={OWNER_ID}">ခန့်သူရိန်</a>'
            await context.bot.send_message(
                chat_id, 
                f"<blockquote>ဟိတ်ရို့ /admins မင်းတို့ရဲ့ဒီ group <b>{chat_title}</b> ကို ထည့်သွင်းအသုံးပြုပေးတဲ့အတွက် ကျေးဇူး၊ အမ် အသုံးဝင်မယ့် တချို့ကန့်သန့်ထားတဲ့ bot command တွေသုံးမယ်ဆို @Besties_with_BoD က OWNER user id ကို {owner_mention} ဆီကိုလာဆက်သွယ်ပေးပါ။ဒါက bot command ရှိသူတွေက botကိုnew bully msgတွေသင်ပေးတဲ့နေရာ @rudeword</blockquote>",
                parse_mode=ParseMode.HTML
            )
        else:
            mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
            await context.bot.send_message(chat_id, f"<blockquote>ဟိတ် {mention}! {chat_title} ကနေ ကြိုဆိုပါတယ်!</blockquote>", parse_mode=ParseMode.HTML)
    
    elif not was_member and not is_member:
        if user.id == context.bot.id:
            db.filters.delete_many({"chat_id": chat_id})
        else:
            mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
            await context.bot.send_message(chat_id, f"<blockquote>{mention} ထွက်သွားပါပြီ။ သွားတော့ ဝေးရာဆီ!</blockquote>", parse_mode=ParseMode.HTML)

# --- OWNER & ALLOW COMMANDS ---

async def addallow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    target_id = None
    if context.args: target_id = int(context.args[0])
    elif update.message.reply_to_message: target_id = update.message.reply_to_message.from_user.id
    
    if target_id:
        allowed = get_list("allow")
        if target_id not in allowed:
            allowed.append(target_id)
            set_list("allow", allowed)
            await update.message.reply_text(f"<blockquote>✅ User: <code>{target_id}</code> ကို Bot Command သုံးခွင့်ပေးလိုက်ပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("<blockquote>အင်းဒီကောင်က ပါမစ်ရပြီးသား</blockquote>", parse_mode=ParseMode.HTML)

async def addallowlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    allowed = get_list("allow")
    text = "<b>📜 Allowed Users List:</b>\n\n"
    for uid in allowed:
        try:
            user = await context.bot.get_chat(uid)
            text += f"• <a href='tg://user?id={uid}'>{user.full_name}</a> (<code>{uid}</code>)\n"
        except: text += f"• User ID: <code>{uid}</code>\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# --- ADMIN ACTIONS ---

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_tg_admin(update, context): return
    cmd = update.message.text.split()[0][1:].lower()
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text("<blockquote>Reply ပြန်ပြီး command သုံးပါ။</blockquote>", parse_mode=ParseMode.HTML)

    try:
        if cmd == "mute":
            await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=False))
            await update.message.reply_text("<blockquote>မဟုတ်တာတွေပြောလို့ mute လိုက်ပြီ!</blockquote>", parse_mode=ParseMode.HTML)
        elif cmd == "unmute":
            await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True))
            await update.message.reply_text("<blockquote>လိမ္မာသွားလို့ unmute ပေးလိုက်ပြီ!</blockquote>", parse_mode=ParseMode.HTML)
        elif cmd == "kick":
            await context.bot.unban_chat_member(update.effective_chat.id, target.id)
            await update.message.reply_text("<blockquote>အလိုက်တသိ ထွက်မသွားလို့ kick လိုက်ပြီ!</blockquote>", parse_mode=ParseMode.HTML)
        elif cmd == "ban":
            await context.bot.ban_chat_member(update.effective_chat.id, target.id)
            await update.message.reply_text("<blockquote>ဆက်နေခွင့်မပေးသင့်တော့လို့ ban လိုက်ပြီ!</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e: await update.message.reply_text(f"Error: {e}")

# --- BULLY & FILTER & MAIN HANDLER ---

async def bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allow(update): return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return await update.message.reply_text("<blockquote>Reply ပြန်ပြီး ဆော်ပါ။</blockquote>", parse_mode=ParseMode.HTML)
    chat_id = update.effective_chat.id
    words = get_list("bully")
    if not words: return await update.message.reply_text("<blockquote>Bully list အလွတ်ဖြစ်နေသည်။</blockquote>", parse_mode=ParseMode.HTML)
    if chat_id in bully_tasks: 
        stop_events[chat_id].set()
        bully_tasks[chat_id].cancel()
    stop_events[chat_id] = asyncio.Event()
    mention = f'<a href="tg://user?id={target.id}">{target.full_name}</a>'
    async def loop():
        try:
            while not stop_events[chat_id].is_set():
                for w in words:
                    if stop_events[chat_id].is_set(): break
                    await context.bot.send_message(chat_id, f"<blockquote>{mention} {w}</blockquote>", parse_mode=ParseMode.HTML)
                    await asyncio.sleep(3.5)
        except: pass
    bully_tasks[chat_id] = asyncio.create_task(loop())
    await update.message.reply_text(f"<blockquote>🔥 {target.full_name} ကို ဟိတ်ကောင်ငါ့messageတွေခိုးcopyစမ်း!😜</blockquote>", parse_mode=ParseMode.HTML)

async def main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    chat_id, uid, text = update.effective_chat.id, update.effective_user.id, (update.message.text or update.message.caption)
    
    # 🔗 LINK DETECTION LOGIC (Delete & Reply)
    if text and re.search(LINK_REGEX, text):
        # Admin မဟုတ်ရင် ဖျက်မယ်
        if not await is_tg_admin(update, context):
            try:
                await update.message.delete()
                mention = f'<a href="tg://user?id={uid}">{update.effective_user.full_name}</a>'
                await context.bot.send_message(
                    chat_id, 
                    f"<blockquote>ဟိတ် {mention}! Group ထဲမှာ Link ချခွင့်မရှိပါဘူး။ မင်းပို့တဲ့ Link ကို ဖျက်လိုက်ပါပြီ။ 🚫</blockquote>",
                    parse_mode=ParseMode.HTML
                )
            except: pass
            return

    # Auto Save logic
    if chat_id == SAVE_CHAT and get_bool("save") and (uid == OWNER_ID or uid in get_list("allow")):
        if text:
            bully_list = get_list("bully")
            if text not in bully_list:
                bully_list.append(text)
                set_list("bully", bully_list)
                await update.message.reply_text(f"<blockquote>မှတ်သားထားပါတယ်: {text}</blockquote>", parse_mode=ParseMode.HTML)
                return

    if text:
        f_data = db.filters.find_one({"chat_id": chat_id, "keyword": text.lower()})
        if f_data: await update.message.reply_text(f"<blockquote>{f_data['reply']}</blockquote>", parse_mode=ParseMode.HTML)

# --- (ကျန်တဲ့ sendallgp, help_command, stopbully logic များ) ---

async def stopbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_allow(update): return
    chat_id = update.effective_chat.id
    if chat_id in stop_events:
        stop_events[chat_id].set()
        await update.message.reply_text("<blockquote>မင်းကရပ်ခိုင်းလို့သာငါကဆက်ဘူလီချင်သေးတာ😁</blockquote>", parse_mode=ParseMode.HTML)

async def sendallgp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    msg = update.message.reply_to_message
    if not msg: return await update.message.reply_text("<blockquote>စာကို Reply ပြန်ပါ။</blockquote>", parse_mode=ParseMode.HTML)
    marked = get_list("marked_groups")
    count = 0
    for gid in marked:
        try:
            await context.bot.copy_message(chat_id=gid, from_chat_id=update.effective_chat.id, message_id=msg.message_id)
            count += 1
            await asyncio.sleep(0.2)
        except: pass
    await update.message.reply_text(f"<blockquote>📢 Group {count} ခုကို ပို့ပြီးပါပြီ။</blockquote>", parse_mode=ParseMode.HTML)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "<b>🔥 Young Master Bot Help Menu</b>\n\n"
        "<b>👑 Owner:</b> <code>/addallow</code>, <code>/addallowlist</code>, <code>/sendallgp</code>\n"
        "<b>⚔️ Admin:</b> <code>/mute</code>, <code>/unmute</code>, <code>/kick</code>, <code>/ban</code>, <code>/addfilter</code>\n"
        "<b> Bully:</b> <code>/bully</code>, <code>/stopbully</code>, <code>/save_on/off</code>"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(member_update_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addallow", addallow))
    app.add_handler(CommandHandler("addallowlist", addallowlist))
    app.add_handler(CommandHandler(["mute", "unmute", "kick", "ban"], admin_action))
    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("stopbully", stopbully))
    app.add_handler(CommandHandler("sendallgp", sendallgp))
    app.add_handler(CommandHandler("save_on", lambda u,c: set_bool("save", True) or u.message.reply_text("<blockquote>✅ Auto Save: ON</blockquote>", parse_mode=ParseMode.HTML)))
    app.add_handler(CommandHandler("save_off", lambda u,c: set_bool("save", False) or u.message.reply_text("<blockquote>❌ Auto Save: OFF</blockquote>", parse_mode=ParseMode.HTML)))
    
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND, main_handler))
    
    print("🚀 Young Master ThuRain V26 Running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__": main()

