import asyncio
import logging
import random
import re
from pymongo import MongoClient
from telegram import Update, ChatPermissions, ChatMember
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
    ContextTypes
)

# ================= CONFIG =================
TOKEN = "8575371720:AAHR_1fCkRxlALIbhMH0yufXGJiUSQYJyYE"
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0"
OWNER_ID = 6015356597
SAVE_CHAT_ID = -1003864912245

# ================= DATABASE =================
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]

allow_db = db["allow_users"]
admin_db = db["admin_users"]
bully_db = db["bully_messages"]
save_db = db["save_chat"]
group_db = db["groups"]
filter_db = db["filters"]

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)

# ================= UTILS =================
def mention(user):
    return f'<a href="tg://user?id={user.id}">{user.full_name}</a>'

def owner_mention():
    return f'<a href="tg://user?id={OWNER_ID}">ခန့်သူရိန်</a>'

def get_allow(): return [u["user_id"] for u in allow_db.find()]
def get_admins(): return [u["user_id"] for u in admin_db.find()]
def get_bully(): return [u["text"] for u in bully_db.find()]
def get_groups(): return [g["chat_id"] for g in group_db.find()]

# ================= SAVE CHAT =================
SAVE_MODE = False

async def save_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SAVE_MODE
    SAVE_MODE = True
    await update.message.reply_text("<blockquote> အလိုအလျောက်မှတ်သားခြင်း: ON</blockquote>", parse_mode=ParseMode.HTML)

async def save_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SAVE_MODE
    SAVE_MODE = False
    await update.message.reply_text("<blockquote>အလိုအလျောက်မှတ်သားခြင်း: OFF</blockquote>", parse_mode=ParseMode.HTML)

async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if SAVE_MODE and update.effective_chat.id == SAVE_CHAT_ID and update.message.text:
        save_db.insert_one({
            "user_id": update.effective_user.id,
            "text": update.message.text
        })

# ================= ALLOW / ADMIN =================
async def addallow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: 
        return await update.message.reply_text("<blockquote>Reply user to allow</blockquote>", parse_mode=ParseMode.HTML)
    target = update.message.reply_to_message.from_user
    if allow_db.find_one({"user_id": target.id}): return
    allow_db.insert_one({"user_id": target.id, "name": target.full_name})
    await update.message.reply_text(f"<blockquote>{mention(target)} သူက bot command ကို သုံးလို့ရသွားပြီ</blockquote>", parse_mode=ParseMode.HTML)

async def allowlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = allow_db.find()
    text = "<blockquote>Allowed Users\n\n"
    for u in users:
        text += f'{mention(type("user",(object,),{"id":u["user_id"],"full_name":u["name"]})())}\n'
    text += "</blockquote>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: 
        return await update.message.reply_text("<blockquote>Reply user to add admin</blockquote>", parse_mode=ParseMode.HTML)
    target = update.message.reply_to_message.from_user
    if admin_db.find_one({"user_id": target.id}): return
    admin_db.insert_one({"user_id": target.id, "name": target.full_name})
    await update.message.reply_text(
        f"<blockquote>{mention(target)} ကို {mention(update.effective_user)} က admin ဖြစ်စေလိုက်ပါတယ်။</blockquote>",
        parse_mode=ParseMode.HTML
    )

# ================= BULLY =================
async def addbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if text:
        bully_db.insert_one({"text": text})
        await update.message.reply_text("<blockquote>လိုက်မှတ်ထားလိုက်ပြီ</blockquote>", parse_mode=ParseMode.HTML)

async def bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    user = update.effective_user

    if target.id == OWNER_ID:
        return await update.message.reply_text("<blockquote>ဟားတိုက်ခံရတော့မယ် Creatorကို bullyလို့မရဘူးညီ🫵</blockquote>", parse_mode=ParseMode.HTML)
    if user.id != OWNER_ID and target.id in get_allow(): 
        await update.message.reply_text(
            f"<blockquote>ဟေ့🫵 မင်းတို့က {mention(user)} နဲ့ {mention(target)} တဖွဲ့တည်းတွေစည်းလုံးကြ</blockquote>",
            parse_mode=ParseMode.HTML
        )

    msgs = get_bully()
    random.shuffle(msgs)
    msgs = msgs[:5]
    for m in msgs:
        await update.message.reply_text(f"<blockquote>{mention(target)}\n{m}</blockquote>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(1)

async def targetbullylist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = save_db.distinct("user_id")
    text = "<blockquote>Bullyခံထားရသူများ\n\n"
    for uid in users:
        text += f'<a href="tg://user?id={uid}">{uid}</a>\n'
    text += "</blockquote>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ================= MEMBER / GROUP =================
async def member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member if update.chat_member else update.my_chat_member
    if not result: return
    chat_id = update.effective_chat.id
    user = result.new_chat_member.user
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status

    # Bot added to group
    if user.id == context.bot.id:
        if not group_db.find_one({"chat_id": chat_id}):
            group_db.insert_one({"chat_id": chat_id, "title": update.effective_chat.title})
            entry_text = (
                f"<blockquote>ဟိတ်ရို့ /admins မင်းတို့ရဲ့ဒီ <b>{update.effective_chat.title}</b> ကို "
                "ထည့်သွင်းအသုံးပြုပေးတဲ့အတွက် ကျေးဇူး၊ အမ် အသုံးဝင်မယ့် တချို့ကန့်သန့်ထားတဲ့ "
                f"bot command တွေသုံးမယ်ဆို @Besties_with_BoD က {owner_mention()} "
                "သို့ ဆက်သွယ်ပေးပါ။ ဒါက bot command ရှိသူတွေက bot ကို new bully msg တွေသင်ပေးတဲ့နေရာ @rudeword</blockquote>"
            )
            await context.bot.send_message(chat_id, entry_text, parse_mode=ParseMode.HTML)
        return

    # Welcome / Goodbye
    if old_status in ["left", "kicked"] and new_status in ["member", "restricted"]:
        await context.bot.send_message(
            chat_id,
            f"<blockquote>ဟိတ် {mention(user)} <b>{update.effective_chat.title}</b>ကနေ ကြိုဆိုလိုက်ပါတယ်၊လွတ်လွတ်လပ်လပ်နဲ့ ပျော်စရာကောင်းတဲ့ရပ်ဝန်းမှာ စိတ်အေးချမ်းမှုရပါစေ!</blockquote>",
            parse_mode=ParseMode.HTML
        )
    elif new_status in ["left", "kicked"]:
        await context.bot.send_message(
            chat_id,
            f"<blockquote>ဟုတ်{mention(user)} ထွက်သွားလိုက်ပါသေးတယ် <b>{update.effective_chat.title}</b>ကို သူပြန်လာပါ့မလား</blockquote>",
            parse_mode=ParseMode.HTML
        )

# ================= FILTER =================
async def addfilter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await update.message.reply_text("<blockquote>Usage: /addfilter keyword reply</blockquote>", parse_mode=ParseMode.HTML)
    keyword = context.args[0].lower()
    reply = " ".join(context.args[1:])
    filter_db.insert_one({"chat_id": update.effective_chat.id, "keyword": keyword, "reply": reply})
    await update.message.reply_text(f"<blockquote>Filter '{keyword}' added</blockquote>", parse_mode=ParseMode.HTML)

async def filter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    f_data = filter_db.find_one({"chat_id": update.effective_chat.id, "keyword": text})
    if f_data:
        await update.message.reply_text(f"<blockquote>{f_data['reply']}</blockquote>", parse_mode=ParseMode.HTML)

# ================= BROADCAST =================
async def sendallgp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    text = " ".join(context.args)
    success, fail = 0, 0
    for g in get_groups():
        try:
            await context.bot.send_message(g, f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML)
            success += 1
        except:
            fail += 1
    await update.message.reply_text(
        f"<blockquote>📢 Broadcast ပြီးဆုံးပါပြီ!\n✅ အောင်မြင်: {success}\n❌ ကျရှုံး: {fail}</blockquote>",
        parse_mode=ParseMode.HTML
    )
# ================= LINK FILTER =================
LINK_REGEX = re.compile(r"(https?://\S+|t\.me/\S+|www\.\S+)")

async def link_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user = update.effective_user
    text = update.message.text
    if user.id == OWNER_ID or user.id in get_admins(): return
    if LINK_REGEX.search(text):
        try: await update.message.delete()
        except: pass
        await update.message.reply_text(
            f"<blockquote>{mention(user)}🫵 ဒီမှာ link ချမရဘူး၊ မင်း link ကို ဖျက်လိုက်ပြီ</blockquote>",
            parse_mode=ParseMode.HTML
        )

# ================= ADMIN ACTIONS =================
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in get_admins() and user.id != OWNER_ID: return
    cmd = update.message.text.split()[0][1:].lower()
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target: return
    chat_id = update.effective_chat.id
    try:
        if cmd == "mute": await context.bot.restrict_chat_member(chat_id, target.id, permissions=ChatPermissions(can_send_messages=False))
        elif cmd == "unmute": await context.bot.restrict_chat_member(chat_id, target.id, permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
        elif cmd == "kick": await context.bot.ban_chat_member(chat_id, target.id); await context.bot.unban_chat_member(chat_id, target.id)
        elif cmd == "ban": await context.bot.ban_chat_member(chat_id, target.id)
        elif cmd == "unban": await context.bot.unban_chat_member(chat_id, target.id)
        await update.message.reply_text(f"<blockquote>{mention(target)} ကို {cmd} လိုက်ပြီ!</blockquote>", parse_mode=ParseMode.HTML)
    except: pass

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(ChatMemberHandler(member_update, ChatMemberHandler.ANY_CHAT_MEMBER))
    
    # Save chat
    app.add_handler(CommandHandler("save_on", save_on))
    app.add_handler(CommandHandler("save_off", save_off))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_message))
    
    # Allow/Admin
    app.add_handler(CommandHandler("addallow", addallow))
    app.add_handler(CommandHandler("allowlist", allowlist))
    app.add_handler(CommandHandler("addadmin", addadmin))
    
    # Bully
    app.add_handler(CommandHandler("addbully", addbully))
    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("targetbullylist", targetbullylist))
    
    # Filter
    app.add_handler(CommandHandler("addfilter", addfilter))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_handler))
    
    # Link
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_filter))
    
    # Broadcast
    app.add_handler(CommandHandler("sendallgp", sendallgp))
    
    # Admin actions
    app.add_handler(CommandHandler(["mute","unmute","kick","ban","unban"], admin_action))
    
    print("🚀 Full Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
