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

TELEGRAM_BOT_TOKEN = "8883142822:AAF6raw8CDotC403sP_OGH6pUxkPU0sRBRc"
FAYDA_API_KEY = "fayda_303de9ba851cef11142d68c9dfed16375cffb294574f6dcb"
FAYDA_BASE_URL = "https://otp.affiliate.pro.et/api/v1"

HEADERS = {"x-api-key": FAYDA_API_KEY, "Content-Type": "application/json"}

WAITING_FAN, WAITING_FIN, WAITING_OTP = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "ሰላም! የFayda ID ሰነድዎን ለማውረድ እባክዎ የFAN (16-ዲጂት) ቁጥርዎን ያስገቡ:"
  )
  return WAITING_FAN


async def get_fan(update: Update, context: ContextTypes.DEFAULT_TYPE):
  fan = update.message.text.strip().replace(" ", "")
  context.user_data["fan"] = fan
  await update.message.reply_text("አሁን ደግሞ የFIN (12-ዲጂት) ቁጥርዎን ያስገቡ:")
  return WAITING_FIN


async def get_fin(update: Update, context: ContextTypes.DEFAULT_TYPE):
  fin = update.message.text.strip().replace(" ", "")
  context.user_data["fin"] = fin
  fan = context.user_data["fan"]
  await update.message.reply_text(
      "OTP ወደ ስልክዎ እየተላከ ነው... እባክዎ ትንሽ ይጠብቁ።"
  )

  try:
    response = requests.post(
        f"{FAYDA_BASE_URL}/send-otp-verified-qr",
        json={"fanNumber": fan, "finNumber": fin},
        headers=HEADERS,
        timeout=60,
    )
    res_data = response.json()

    if response.status_code == 200 and "session" in res_data:
      context.user_data["session"] = res_data["session"]
      masked_phone = res_data.get("phone", "ስልክ ቁጥር")
      await update.message.reply_text(
          f"OTP ({masked_phone}) ቁጥር ላይ ተልኳል። እባክዎ የደረሰዎትን 6-ዲጂት"
          " OTP ያስገቡ:"
      )
      return WAITING_OTP
    else:
      msg = res_data.get("message", "OTP መላክ አልተቻለም።")
      await update.message.reply_text(
          f"ስህተት ተከሰቷል: {msg}\n\nእንደገና ለመሞከር /start ይበሉ።"
      )
      return ConversationHandler.END

  except Exception:
    await update.message.reply_text("የኔትወርክ ችግር አጋጥሟል። እባክዎ እንደገና ይሞክሩ።")
    return ConversationHandler.END


async def get_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
  otp = update.message.text.strip().replace(" ", "")
  if len(otp) != 6 or not otp.isdigit():
    await update.message.reply_text("እባክዎ ትክክለኛ የ6-ዲጂት OTP ብቻ ያስገቡ:")
    return WAITING_OTP

  fan = context.user_data["fan"]
  fin = context.user_data["fin"]
  session = context.user_data["session"]

  await update.message.reply_text(
      "መረጃዎ እየተረጋገጠ እና ፒዲኤፍ እየተዘጋጀ ነው... ጥቂት ሰከንዶች ይጠብቁ።"
  )

  try:
    response = requests.post(
        f"{FAYDA_BASE_URL}/verify-otp-verified-qr",
        json={
            "otp": otp,
            "fanNumber": fan,
            "finNumber": fin,
            "session": session,
        },
        headers=HEADERS,
        timeout=120,
    )
    res_data = response.json()

    if response.status_code == 200 and res_data.get("success"):
      pdf_bytes = base64.b64decode(res_data["pdf"])
      pdf_filename = res_data.get("pdfFilename", "Fayda_ID.pdf")

      await update.message.reply_document(
          document=pdf_bytes,
          filename=pdf_filename,
          caption="የእርስዎ Fayda ID በትክክል ወርዷል!",
      )
      return ConversationHandler.END
    else:
      msg = res_data.get("message", "ማረጋገጥ አልተቻለም።")
      await update.message.reply_text(
          f"ስህተት ተከሰቷል: {msg}\n\nእንደገና ለመሞከር /start ይበሉ።"
      )
      return ConversationHandler.END

  except Exception:
    await update.message.reply_text(
        "ፋይሉን በማውረድ ላይ ችግር ተከሰተ። እባክዎ እንደገና ይሞክሩ።"
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text("ሂደቱ ተቋርጧል።")
  return ConversationHandler.END


def main():
  app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

  conv_handler = ConversationHandler(
      entry_points=[CommandHandler("start", start)],
      states={
          WAITING_FAN: [
              MessageHandler(filters.TEXT & ~filters.COMMAND, get_fan)
          ],
          WAITING_FIN: [
              MessageHandler(filters.TEXT & ~filters.COMMAND, get_fin)
          ],
          WAITING_OTP: [
              MessageHandler(filters.TEXT & ~filters.COMMAND, get_otp)
          ],
      },
      fallbacks=[CommandHandler("cancel", cancel)],
  )

  app.add_handler(conv_handler)
  print("Bot is running...")
  app.run_polling()


if __name__ == "__main__":
  main()
