import os
import io
import json
import logging

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")

client = genai.Client(api_key=GEMINI_API_KEY)


async def identify_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if not message or not message.photo:
        return

    status = await message.reply_text("🔍 Card ကို စစ်နေပါတယ်...")

    try:
        # Telegram မှာ အကြီးဆုံး photo size ကိုယူ
        photo = message.photo[-1]
        telegram_file = await context.bot.get_file(photo.file_id)

        image_bytes = await telegram_file.download_as_bytearray()

        prompt = """
Look at this anime character card image and identify the character.

Return ONLY valid JSON in exactly this format:

{
  "character": "Character name",
  "anime": "Anime / manga / game title",
  "confidence": "high"
}

Rules:
- Identify the visible character if possible.
- Give the most likely official character name.
- Give the anime title the character is from.
- If you cannot identify the character reliably, use "Unknown".
- Do not add explanations.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(
                    data=bytes(image_bytes),
                    mime_type="image/jpeg",
                ),
                prompt,
            ],
        )

        text = response.text.strip()

        # ```json ... ``` ဖြစ်ရင် ဖြုတ်
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()

        data = json.loads(text)

        character = data.get("character", "Unknown")
        anime = data.get("anime", "Unknown")
        confidence = data.get("confidence", "unknown")

        if character == "Unknown" and anime == "Unknown":
            result = (
                "❌ Character ကို သေချာမဖော်နိုင်ပါဘူး။\n"
                "ပိုရှင်းတဲ့ Card ပုံတစ်ပုံနဲ့ ထပ်ပို့ကြည့်ပါ။"
            )
        else:
            result = (
                "🎴 <b>Anime Card Found!</b>\n\n"
                f"👤 <b>Character:</b> {character}\n"
                f"📺 <b>Anime:</b> {anime}\n"
                f"🔎 <b>Confidence:</b> {confidence}"
            )

        await status.edit_text(
            result,
            parse_mode="HTML",
        )

    except Exception as e:
        logging.exception("Image recognition error")

        await status.edit_text(
            "❌ ပုံကို စစ်တဲ့အချိန် Error ဖြစ်သွားပါတယ်။\n"
            "ခဏနေရင် ထပ်စမ်းကြည့်ပါ။"
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Anime Card Name Bot\n\n"
        "🎴 Anime Card ပုံကို ဒီ Bot ဆီ Forward ပို့ပါ။\n"
        "Character Name + Anime Name ကို Auto ဖော်ပေးပါမယ်။"
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(filters.COMMAND & filters.Regex(r"^/start$"), start)
    )

    app.add_handler(
        MessageHandler(filters.PHOTO, identify_anime)
    )

    print("🤖 Anime Card Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
