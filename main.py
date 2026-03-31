import asyncio
import logging
import random
from pymongo import MongoClient
from telegram import Update, ChatPermissions
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
TOKEN = "8575371720:AAHR_1fCkRxlALIbhMH0yufXGJiUSQYJyYE"  # Husband သို့မဟုတ် Environment variable သုံးပါ
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0
"
OWNER_ID = 6015356597
SAVE_CHAT_ID = -1003864912245

# ================= DATABASE =================
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]

allow_db = db["allow_users"]
bully_db = db["bully_messages"]
save_db = db["save_chat"]
group_db = db["groups"]

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)

# ================= UTILS =================
def mention(user):
    return f'<a href="tg://user?id={user.id}">{user.full_name}</a>'

def get_allow():
    return [u["user_id"] for u in allow_db.find()]

def get_bully():
    return [u["text"] for u in bully_db.find()]

def get_groups():
    return [g["chat_id"] for g in group_db.find()]

# ================= SAVE CHAT =================
SAVE_MODE = False

async def save_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SAVE_MODE
    SAVE_MODE = True
    await update.message.reply_text("<blockquote>✅ Auto Save: ON</blockquote>", parse_mode=ParseMode.HTML)

async def save_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SAVE_MODE
    SAVE_MODE = False
    await update.message.reply_text("<blockquote>❌ Auto Save: OFF</blockquote>", parse_mode=ParseMode.HTML)

async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if SAVE_MODE and update.effective_chat.id == SAVE_CHAT_ID and update.message.text:
        save_db.insert_one({
            "user_id": update.effective_user.id,
            "text": update.message.text
        })

# ================= ALLOW USERS =================
async def addallow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("<blockquote>Reply user to allow</blockquote>", parse_mode=ParseMode.HTML)
    target = update.message.reply_to_message.from_user
    if allow_db.find_one({"user_id": target.id}):
        return
    allow_db.insert_one({"user_id": target.id, "name": target.full_name})
    await update.message.reply_text(f"<blockquote>{mention(target)} allowed user ဖြစ်သွားပြီ</blockquote>", parse_mode=ParseMode.HTML)

async def allowlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = allow_db.find()
    text = "<blockquote>Allowed Users\n\n"
    for u in users:
        text += f'{mention(type("user",(object,),{"id":u["user_id"],"full_name":u["name"]})())}\n'
    text += "</blockquote>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ================= BULLY =================
async def addbully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if text:
        bully_db.insert_one({"text": text})
        await update.message.reply_text("<blockquote>✅ Bully message saved</blockquote>", parse_mode=ParseMode.HTML)

async def targetbullylist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = save_db.distinct("user_id")
    text = "<blockquote>Bullyခံထားရသူများ\n\n"
    for uid in users:
        text += f'<a href="tg://user?id={uid}">{uid}</a>\n'
    text += "</blockquote>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def bully(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return
    target = update.message.reply_to_message.from_user
    user = update.effective_user

    if target.id == OWNER_ID:
        return await update.message.reply_text("<blockquote>Owner ကို bully မရ</blockquote>", parse_mode=ParseMode.HTML)

    allow = get_allow()
    if target.id in allow and user.id in allow:
        await update.message.reply_text(
            f"<blockquote>ဟိတ်မင်းတို့က {mention(user)} နဲ့ {mention(target)} တဖွဲ့တည်းတွေစည်းလုံးကြ</blockquote>",
            parse_mode=ParseMode.HTML
        )

    msgs = get_bully()
    random.shuffle(msgs)
    msgs = msgs[:5]  # 5 random messages
    for m in msgs:
        await update.message.reply_text(f"<blockquote>{mention(target)}\n{m}</blockquote>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(1)

# ================= GROUP TRACKER & ENTRY =================
async def member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member if update.chat_member else update.my_chat_member
    if not result: return

    chat_id = update.effective_chat.id
    user = result.new_chat_member.user

    # Bot added
    if user.id == context.bot.id:
        if not group_db.find_one({"chat_id": chat_id}):
            group_db.insert_one({"chat_id": chat_id, "title": update.effective_chat.title})
            entry_text = (
                f"<blockquote>ဟိတ်ရို့ /admins မင်းတို့ရဲ့ဒီ {update.effective_chat.title} ကို "
                "ထည့်သွင်းအသုံးပြုပေးတဲ့အတွက် ကျေးဇူး၊ အမ် အသုံးဝင်မယ့် တချို့ကန့်သန့်ထားတဲ့ "
                "bot command တွေသုံးမယ်ဆို @Besties_with_BoD က (မန်းရှင်းနာမည်အပြည့်အစုံ) "
                "သို့ ဆက်သွယ်ပေးပါ။ ဒါက bot command ရှိသူတွေက bot ကို new bully msg တွေသင်ပေးတဲ့နေရာ @rudeword</blockquote>"
            )
            await context.bot.send_message(chat_id, entry_text, parse_mode=ParseMode.HTML)
        return

# ================= BROADCAST =================
async def sendallgp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    text = " ".join(context.args)
    for g in get_groups():
        try:
            await context.bot.send_message(g, f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML)
        except: pass

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(member_update, ChatMemberHandler.ANY_CHAT_MEMBER))

    # Save chat
    app.add_handler(CommandHandler("save_on", save_on))
    app.add_handler(CommandHandler("save_off", save_off))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_message))

    # Allow
    app.add_handler(CommandHandler("addallow", addallow))
    app.add_handler(CommandHandler("allowlist", allowlist))

    # Bully
    app.add_handler(CommandHandler("addbully", addbully))
    app.add_handler(CommandHandler("bully", bully))
    app.add_handler(CommandHandler("targetbullylist", targetbullylist))

    # Broadcast
    app.add_handler(CommandHandler("sendallgp", sendallgp))

    print("🚀 Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
