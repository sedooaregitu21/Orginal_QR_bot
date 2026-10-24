import base64
import os
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# ----------------- CONFIGURATION -----------------
TELEGRAM_BOT_TOKEN = os.environ.get("8883142822:AAEj0gXg9gmwJMfjb8yFxEsUTXY182kgZ5U")
FAYDA_API_KEY = os.environ.get("FAYDA_API_KEY")
FAYDA_BASE_URL = "https://otp.affiliate.pro.et/api/v1"

# Conversation States
WAITING_FAN, WAITING_FIN, WAITING_OTP = range(3)

HEADERS = {
    "x-api-key": FAYDA_API_KEY,
    "Content-Type": "application/json"
}

# ----------------- BOT HANDLERS -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ሰላም! እንኳን ወደ Fayda Verification Bot በደህና መጡ።\n\n"
        "እባክዎ የ16-ዲጂት FAN ቁጥርዎን ያስገቡ፦"
    )
    return WAITING_FAN

async def get_fan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fan = update.message.text.strip().replace(" ", "")
    if len(fan) != 16 or not fan.isdigit():
        await update.message.reply_text("እባክዎ ትክክለኛ የ16-ዲጂት FAN ቁጥር ያስገቡ፦")
        return WAITING_FAN

    context.user_data["fan"] = fan
    await update.message.reply_text("አመሰግናለሁ! አሁን ደግሞ የ12-ዲጂት FIN ቁጥርዎን ያስገቡ፦")
    return WAITING_FIN

async def get_fin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fin = update.message.text.strip().replace(" ", "")
    if len(fin) != 12 or not fin.isdigit():
        await update.message.reply_text("እባክዎ ትክክለኛ የ12-ዲጂት FIN ቁጥር ያስገቡ፦")
        return WAITING_FIN

    context.user_data["fin"] = fin
    fan = context.user_data["fan"]

    await update.message.reply_text("OTP ወደ ስልክዎ እየተላከ ነው... እባክዎ ይጠብቁ።")

    try:
        response = requests.post(
            f"{FAYDA_BASE_URL}/send-otp-verified-qr",
            json={"fanNumber": fan, "finNumber": fin},
            headers=HEADERS,
            timeout=60
        )
        res_data = response.json()

        if response.status_code == 200 and "session" in res_data:
            context.user_data["session"] = res_data["session"]
            phone_masked = res_data.get("phone", "ስልክዎ")
            await update.message.reply_text(
                f"የማረጋገጫ OTP ኮድ ወደ {phone_masked} ተልኳል።\n\n"
                "እባክዎ በስልክዎ የደረሰዎትን የ6-ዲጂት OTP ኮድ ያስገቡ፦"
            )
            return WAITING_OTP
        else:
            msg = res_data.get("message", "OTP መላክ አልተቻለም።")
            await update.message.reply_text(f"ስህተት ተከሰቷል፦ {msg}\n\nእንደገና ለመሞከር /start ይበሉ።")
            return ConversationHandler.END

    except Exception:
        await update.message.reply_text("ከሲስተሙ ጋር መገናኘት አልተቻለም። እባክዎ ቆይተው ይሞክሩ።")
        return ConversationHandler.END

async def get_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text.strip().replace(" ", "")
    if len(otp) != 6 or not otp.isdigit():
        await update.message.reply_text("እባክዎ ትክክለኛ የ6-ዲጂት OTP ያስገቡ፦")
        return WAITING_OTP

    fan = context.user_data["fan"]
    fin = context.user_data["fin"]
    session = context.user_data["session"]

    await update.message.reply_text("መረጃዎ እየተረጋገጠ ነው... ጥቂት ሰከንዶች ይጠብቁ።")

    try:
        response = requests.post(
            f"{FAYDA_BASE_URL}/verify-otp-verified-qr",
            json={"otp": otp, "fanNumber": fan, "finNumber": fin, "session": session},
            headers=HEADERS,
            timeout=120
        )
        res_data = response.json()

        if response.status_code == 200 and res_data.get("success"):
            pdf_bytes = base64.b64decode(res_data["pdf"])
            pdf_filename = res_data.get("pdfFilename", "Fayda_ID.pdf")

            await update.message.reply_document(
                document=pdf_bytes,
                filename=pdf_filename,
                caption="የእርስዎ የFayda ID ሰነድ በስኬት ወርዷል!"
            )

            if res_data.get("verifiedQr"):
                qr_bytes = base64.b64decode(res_data["verifiedQr"])
                await update.message.reply_photo(
                    photo=qr_bytes,
                    caption="የእርስዎ Verified Fayda QR Code"
                )

            await update.message.reply_text("አገልግሎታችንን ስለተጠቀሙ አመሰግናለሁ! ሌላ ለማውረድ /start ይበሉ።")
            return ConversationHandler.END

        else:
            msg = res_data.get("message", "ማረጋገጥ አልተቻለም።")
            await update.message.reply_text(f"ስህተት ተከሰቷል፦ {msg}\n\nእንደገና ለመሞከር /start ይበሉ።")
            return ConversationHandler.END

    except Exception:
        await update.message.reply_text("ፋይሉን በማውረድ ላይ ችግር ተከሰተ። እባክዎ እንደገና ይሞክሩ።")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ሂደቱ ተቋርጧል። እንደገና ለመጀመር /start ይበሉ።")
    return ConversationHandler.END

def main():
    if not TELEGRAM_BOT_TOKEN or not FAYDA_API_KEY:
        print("ERROR: Environment variables are missing!")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fan)],
            WAITING_FIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fin)],
            WAITING_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_otp)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
