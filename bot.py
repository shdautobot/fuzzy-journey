import os
import whisper
from transformers import pipeline
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# تحميل الموديلات
whisper_model = whisper.load_model("base")

summarizer = pipeline(
    "summarization",
    model="google/flan-t5-base"
)

user_texts = {}

def split_text(text, max_chars=1000):
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

def smart_summary(text, mode):
    if mode == "points":
        prompt = f"Summarize into bullet points in Arabic:\n{text}"
    elif mode == "detailed":
        prompt = f"Explain in detail in Arabic:\n{text}"
    else:
        prompt = f"Summarize briefly in Arabic:\n{text}"

    result = summarizer(prompt, max_length=200, min_length=50)
    return result[0]['summary_text']

def summarize_long(text, mode):
    parts = split_text(text)
    return "\n".join([smart_summary(p, mode) for p in parts])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎤 أرسل صوت وسأحوله إلى نص + تلخيص 🔥")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    file = None
    if update.message.voice:
        file = await context.bot.get_file(update.message.voice.file_id)
    elif update.message.audio:
        file = await context.bot.get_file(update.message.audio.file_id)
    else:
        return

    await file.download_to_drive("input.ogg")

    os.system("ffmpeg -i input.ogg output.wav -y")

    await update.message.reply_text("⏳ جاري تحويل الصوت...")

    result = whisper_model.transcribe("output.wav")
    text = result["text"]

    user_texts[user_id] = text

    await update.message.reply_text(f"📝 النص:\n\n{text}")

    keyboard = [
        [InlineKeyboardButton("📌 نقاط", callback_data="points")],
        [InlineKeyboardButton("✂️ قصير", callback_data="short")],
        [InlineKeyboardButton("📖 مفصل", callback_data="detailed")]
    ]

    await update.message.reply_text("اختر نوع التلخيص:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    text = user_texts.get(user_id)

    if not text:
        await query.edit_message_text("❌ لا يوجد نص")
        return

    await query.edit_message_text("⏳ جاري التلخيص...")

    summary = summarize_long(text, query.data)

    await query.message.reply_text(f"📄 التلخيص:\n\n{summary}")

def main():
    TOKEN = os.getenv("TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
    app.add_handler(CallbackQueryHandler(handle_summary))

    print("🚀 Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
