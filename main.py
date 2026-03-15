# Data Storage ထဲမှာ mute_text ထပ်ထည့်ထားပါတယ်
config = {
    "welcome_text": "မင်္ဂလာပါ {name} ရေ... Group မှ ကြိုဆိုပါတယ်ဗျာ။",
    "goodbye_text": "နှုတ်ဆက်ပါတယ် {name} ရေ... နောက်မှပြန်တွေ့ကြမယ်နော်။",
    "ban_text": "မင်္ဂလာပါ {mention} တားမြစ်ထားသောစကားလုံးများပါနေသောကြောင့် စာဖျက်ချလိုက်ပါတယ်။စိတ်မရှိပါနဲ့ဗျ။",
    "mute_text": "မသင့်လျော်သောစာများ/စတေကာများပို့သည့်အတွက် muteလိုက်ပါတယ်။", # ပြင်လို့ရအောင် ထည့်ထားခြင်း
    "reminder_text": "သူငယ်ချင်းတို့ နွေးထွေးမှုအပြည့်နဲ့ခင်မင်စွာစကားပြောနေကြတာကို မြင်ရတာ ကြည်နူးမိပါတယ်ခင်ဗျ။",
    "reminder_interval": 1200, 
    "banned_words": ["badword1", "badword2"] 
}

# --- Reminder On/Off Logic ---
async def reminder_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    interval = config["reminder_interval"]
    
    # ရှိပြီးသား job ကို အရင်ဖျက် (duplicate မဖြစ်အောင်)
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()
        
    context.job_queue.run_repeating(
        send_reminder, 
        interval=interval, 
        first=interval, 
        chat_id=chat_id, 
        name=str(chat_id)
    )
    await update.message.reply_text("🔔 Reminder စနစ်ကို ဖွင့်လိုက်ပါပြီ။")

async def reminder_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    if not current_jobs:
        await update.message.reply_text("🔕 Reminder စနစ်က ပိတ်ထားပြီးသားဖြစ်ပါတယ်။")
        return
        
    for job in current_jobs:
        job.schedule_removal()
    await update.message.reply_text("🔕 Reminder စနစ်ကို ပိတ်လိုက်ပါပြီ။")

# --- Mute Reason ပြင်ဆင်ရန် ---
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        try:
            await context.bot.restrict_chat_member(
                update.effective_chat.id, 
                update.message.reply_to_message.from_user.id, 
                ChatPermissions(can_send_messages=False)
            )
            await update.message.reply_text(config["mute_text"])
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

# --- Command များပေါင်းထည့်ခြင်း ---
# Main block ထဲမှာ အောက်ပါတို့ကို ထပ်ထည့်ပေးပါ
    app.add_handler(CommandHandler("reminderon", reminder_on))
    app.add_handler(CommandHandler("reminderoff", reminder_off))
    app.add_handler(CommandHandler("setmuteword", set_texts)) # set_texts function ကိုပဲ ပြန်သုံးထားပါတယ်
