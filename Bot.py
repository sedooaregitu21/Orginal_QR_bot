import base64
import os
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

TELEGRAM_BOT_TOKEN = "8883142822:AAEbNh_VPf6KDmqEI4kmMwL4hjmDawSlRGc"
FAYDA_API_KEY = "fayda_303de9ba851cef11142d68c9dfed16375cffb294574f6dcb"
FAYDA_BASE_URL = "https://otp.affiliate.pro.et/api/v1"

# Chapa Secret Key
CHAPA_SECRET_KEY = "CHASECK_TEST-xxxxxxxxxxxxxxxx"

HEADERS = {"x-api-key": FAYDA_API_KEY, "Content-Type": "application/json"}

WAITING_FAN, WAITING_FIN, WAITING_OTP, WAITING_DEPOSIT_AMOUNT = range(4)

# ----------------- Languages & Bank Info -----------------
TEXTS = {
    "am": {
        "welcome": (
            "ሰላም! የFayda ID ሰነድዎን ለማውረድ ወይም ፖይንት ለመሙላት ከታች ያሉትን አማራጮች"
            " ይምረጡ:"
        ),
        "ask_fan": (
            "እባክዎ የFAN ቁጥርዎን (16-ዲጂት) ያስገቡ (ወይም /cancel ብለው"
            " ይሰርዙ):"
        ),
        "ask_fin": "አሁን ደግሞ የFIN ቁጥርዎን (12-ዲጂት) ያስገቡ:",
        "otp_sending": "OTP ወደ ስልክዎ እየተላከ ነው... እባክዎ ትንሽ ይጠብቁ።",
        "otp_prompt": (
            "OTP ({phone}) ቁጥር ላይ ተልኳል። እባክዎ የደረሰዎትን 6-ዲጂት OTP ያስገቡ:"
        ),
        "processing": (
            "መረጃዎ እየተረጋገጠ እና ፒዲኤፍ እየተዘጋጀ ነው... ጥቂት ሰከንዶች ይጠብቁ።"
        ),
        "success": "የእርስዎ Fayda ID በትክክል ወርዷል!",
        "cancel": "ሂደቱ ተቋርጧል።",
        "error_net": "የኔትወርክ ችግር አጋጥሟል። እባክዎ እንደገና ይሞክሩ።",
        "deposit_info": (
            "💳 **የሂሳብ መሙያ (Deposit) አማራጮች:**\n\n1️⃣ **በአውቶማቲክ (Chapa):**"
            " ከታች ያለውን ቁልፍ በመጫን በባንክ ወይም በቴሌብር በቀጥታ በመክፈል ፖይንቶን"
            " በራሱ እንዲሞላ ማድረግ ይችላሉ።\n\n2️⃣ **በማኑዋል (በደረሰኝ):** ገንዘብ ከፍሎ"
            " ስክሪንሾት ማሳየት ይቻላል።\n📱 **ቴሌብር:** 0998703233\n🏦 **ንግድ ባንክ"
            " (CBE):** 1000745390448\n🏦 **አቢሲኒካ (BoA):** 92707617\n🏦 **አማራ"
            " ባንክ:** 9900039885356"
        ),
        "balance_text": "💰 **የእርስዎ ቀሪ ፖይንት:** {points} ፖይንት ይቀርዎታል።",
        "menu_get_id": "🪪 Verify Digital ID",
        "menu_balance": "💰 ባላንስ እይ",
        "menu_deposit": "💳 ፖይንት መሙያ (Deposit)",
        "menu_lang": "🇬🇧 Change to English",
        "ask_deposit_amount": (
            "እባክዎ መሙላት የሚፈልጉትን የብር መጠን (ለምሳሌ: 50 ወይም 100) በቁጥር"
            " ያስገቡ:"
        ),
        "chapa_link_msg": (
            "🔗 **የክፍያ ሊንክዎ ተዘጋጅቷል!**\n\nከታች ባለው ሊንክ ገብተው ክፍያውን ይፈጽሙ:"
            " \n{pay_url}\n\nክፍያውን ሲጨርሱ ፖይንቱ በራሱ ይጨመራል።"
        ),
    },
    "en": {
        "welcome": (
            "Hello! Welcome to Fayda ID Bot. Choose an option below:"
        ),
        "ask_fan": (
            "Please enter your FAN number (16-digits) (or type /cancel):"
        ),
        "ask_fin": "Now enter your FIN number (12-digits):",
        "otp_sending": "Sending OTP to your phone... Please wait.",
        "otp_prompt": (
            "OTP sent to ({phone}). Please enter the 6-digit OTP code:"
        ),
        "processing": "Verifying details and generating PDF... Please wait.",
        "success": "Your Fayda ID has been downloaded successfully!",
        "cancel": "Process cancelled.",
        "error_net": "Network error occurred. Please try again.",
        "deposit_info": (
            "💳 **Deposit Options:**\n\n1️⃣ **Automated (Chapa):** Click the"
            " button below to pay online instantly.\n2️⃣ **Manual:** Transfer"
            " to our accounts and send screenshot.\n📱 **Telebirr:**"
            " 0998703233\n🏦 **CBE:** 1000745390448\n🏦 **Amhara Bank:**"
            " 9900039885356"
        ),
        "balance_text": "💰 **Your Balance:** You have {points} points left.",
        "menu_get_id": "🪪 Verify Digital ID",
        "menu_balance": "💰 Check Balance",
        "menu_deposit": "💳 Deposit / Top-up",
        "menu_lang": "🇪🇹 ወደ አማርኛ ቀይር",
        "ask_deposit_amount": "Please enter the amount in ETB (e.g., 50 or 100):",
        "chapa_link_msg": (
            "🔗 **Your Payment Link:**\n\nPlease click the link below to pay:"
            " \n{pay_url}"
        ),
    },
}


def get_lang(context: ContextTypes.DEFAULT_TYPE):
  return context.user_data.get("lang", "am")


# ----------------- Start & Main Menu -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  context.user_data.setdefault("lang", "am")
  lang = get_lang(context)
  t = TEXTS[lang]

  keyboard = [
      [
          InlineKeyboardButton(t["menu_get_id"], callback_data="btn_get_id"),
          InlineKeyboardButton(t["menu_deposit"], callback_data="btn_deposit"),
      ],
      [
          InlineKeyboardButton(t["menu_balance"], callback_data="btn_balance"),
          InlineKeyboardButton(t["menu_lang"], callback_data="btn_toggle_lang"),
      ],
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)

  if update.message:
    await update.message.reply_text(t["welcome"], reply_markup=reply_markup)
  elif update.callback_query:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(t["welcome"], reply_markup=reply_markup)


# ----------------- Button Handlers -----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  data = query.data
  lang = get_lang(context)
  t = TEXTS[lang]

  if data == "btn_toggle_lang":
    context.user_data["lang"] = "en" if lang == "am" else "am"
    await start(update, context)

  elif data == "btn_deposit":
    keyboard = [
        [
            InlineKeyboardButton(
                "💳 በባንክ/ቴሌብር በሊንክ ክፈል (Chapa)",
                callback_data="btn_chapa_pay",
            )
        ],
        [InlineKeyboardButton("🔙 ወደ ዋናው ምናሌ", callback_data="btn_home")],
    ]
    await query.edit_message_text(
        t["deposit_info"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  elif data == "btn_chapa_pay":
    await query.message.reply_text(t["ask_deposit_amount"])
    return WAITING_DEPOSIT_AMOUNT

  elif data == "btn_balance":
    try:
      res = requests.get(f"{FAYDA_BASE_URL}/balance", headers=HEADERS, timeout=10)
      if res.status_code == 200:
        data_res = res.json()
        points = data_res.get("balance", data_res.get("points", "N/A"))
        msg = t["balance_text"].format(points=points)
      else:
        msg = "ባላንስ ማምጣት አልተቻለም።"
    except Exception:
      msg = "የኔትወርክ ችግር አጋጥሟል።"

    keyboard = [[InlineKeyboardButton("🔙 ወደ ዋናው ምናሌ", callback_data="btn_home")]]
    await query.edit_message_text(
        msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )

  elif data == "btn_home":
    await start(update, context)

  elif data == "btn_get_id":
    await query.message.reply_text(t["ask_fan"])
    return WAITING_FAN

  return ConversationHandler.END


# ----------------- Chapa Link Generator -----------------
async def create_chapa_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
  lang = get_lang(context)
  t = TEXTS[lang]
  text_input = update.message.text.strip()

  if not text_input.isdigit():
    await update.message.reply_text("እባክዎ ትክክለኛ የብር መጠን በቁጥር ብቻ ያስገቡ:")
    return WAITING_DEPOSIT_AMOUNT

  amount = int(text_input)
  user_id = update.effective_user.id
  tx_ref = f"tx-fayda-{user_id}-{os.urandom(4).hex()}"

  chapa_url = "https://api.chapa.co/v1/transaction/initialize"
  headers = {
      "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
      "Content-Type": "application/json",
  }
  payload = {
      "amount": str(amount),
      "currency": "ETB",
      "email": f"user_{user_id}@bot.et",
      "first_name": update.effective_user.first_name or "User",
      "tx_ref": tx_ref,
      "callback_url": "https://webhook.site/test",
  }

  try:
    response = requests.post(
        chapa_url, json=payload, headers=headers, timeout=30
    )
    res_data = response.json()

    if response.status_code == 200 and res_data.get("status") == "success":
      checkout_url = res_data["data"]["checkout_url"]
      await update.message.reply_text(
          t["chapa_link_msg"].format(pay_url=checkout_url),
          parse_mode="Markdown",
      )
    else:
      await update.message.reply_text(
          "የክፍያ ሊንክ ማመንጨት አልተቻለም። እባክዎ ቆይተው እንደገና ይሞክሩ።"
      )
  except Exception:
    await update.message.reply_text("የኔትወርክ ስህተት አጋጥሟል።")

  return ConversationHandler.END


# ----------------- ID Download Conversation -----------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
  context.user_data.setdefault("lang", "am")
  lang = get_lang(context)
  await update.message.reply_text(TEXTS[lang]["ask_fan"])
  return WAITING_FAN


async def get_fan(update: Update, context: ContextTypes.DEFAULT_TYPE):
  lang = get_lang(context)
  fan = update.message.text.strip().replace(" ", "")
  context.user_data["fan"] = fan
  await update.message.reply_text(TEXTS[lang]["ask_fin"])
  return WAITING_FIN


async def get_fin(update: Update, context: ContextTypes.DEFAULT_TYPE):
  lang = get_lang(context)
  t = TEXTS[lang]
  fin = update.message.text.strip().replace(" ", "")
  context.user_data["fin"] = fin
  fan = context.user_data["fan"]

  await update.message.reply_text(t["otp_sending"])

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
          t["otp_prompt"].format(phone=masked_phone)
      )
      return WAITING_OTP
    else:
      msg = res_data.get("message", "OTP መላክ አልተቻለም።")
      await update.message.reply_text(
          f"ስህተት ተከሰቷል: {msg}\n\nእንደገና ለመሞከር /start ይበሉ።"
      )
      return ConversationHandler.END

  except Exception:
    await update.message.reply_text(t["error_net"])
    return ConversationHandler.END


async def get_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
  lang = get_lang(context)
  t = TEXTS[lang]
  otp = update.message.text.strip().replace(" ", "")
  if len(otp) != 6 or not otp.isdigit():
    await update.message.reply_text("እባክዎ ትክክለኛ የ6-ዲጂት OTP ብቻ ያስገቡ:")
    return WAITING_OTP

  fan = context.user_data["fan"]
  fin = context.user_data["fin"]
  session = context.user_data["session"]

  await update.message.reply_text(t["processing"])

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
          document=pdf_bytes, filename=pdf_filename, caption=t["success"]
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
  lang = get_lang(context)
  await update.message.reply_text(TEXTS[lang]["cancel"])
  return ConversationHandler.END


def main():
  app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

  conv_handler = ConversationHandler(
      entry_points=[
          CommandHandler("start", start_cmd),
          CallbackQueryHandler(button_handler, pattern="^btn_get_id$"),
          CallbackQueryHandler(button_handler, pattern="^btn_chapa_pay$"),
      ],
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
          WAITING_DEPOSIT_AMOUNT: [
              MessageHandler(filters.TEXT & ~filters.COMMAND, create_chapa_link)
          ],
      },
      fallbacks=[
          CommandHandler("start", start),
          CommandHandler("cancel", cancel),
      ],
  )

  app.add_handler(conv_handler)
  app.add_handler(CallbackQueryHandler(button_handler))
  app.add_handler(CommandHandler("start", start))

  print("Bot is running...")
  app.run_polling()


if __name__ == "__main__":
  main()
