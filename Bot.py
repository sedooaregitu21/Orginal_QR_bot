import base64
import os
import sqlite3
import requests
from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
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

ADMIN_CHAT_ID = 8609938129

HEADERS = {"x-api-key": FAYDA_API_KEY, "Content-Type": "application/json"}

WAITING_FAN, WAITING_FIN, WAITING_OTP, WAITING_POINT_AMOUNT = range(4)


# ----------------- Database Setup -----------------
def init_db():
  conn = sqlite3.connect("bot_database.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            points INTEGER DEFAULT 0
        )
    """)
  conn.commit()
  conn.close()


init_db()


def add_user_points(user_id: int, points_to_add: int):
  conn = sqlite3.connect("bot_database.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT OR IGNORE INTO users (user_id, points) VALUES (?, 0)", (user_id,)
  )
  cursor.execute(
      "UPDATE users SET points = points + ? WHERE user_id = ?",
      (points_to_add, user_id),
  )
  conn.commit()
  cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
  res = cursor.fetchone()
  conn.close()
  return res[0] if res else 0


def get_user_points(user_id: int):
  conn = sqlite3.connect("bot_database.db")
  cursor = conn.cursor()
  cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
  res = cursor.fetchone()
  conn.close()
  return res[0] if res else 0


# ----------------- Texts & Menus -----------------
TEXTS = {
    "am": {
        "welcome": (
            "👋 ሰላም! የFayda ID ሰነድዎን ለማውረድ ወይም ፖይንት ለመሙላት ከታች ያሉትን"
            " አማራጮች ይምረጡ 👇"
        ),
        "ask_fan": (
            "🆔 እባክዎ የFAN ቁጥርዎን (16-ዲጂት) ያስገቡ (ወይም /cancel ብለው"
            " ይሰርዙ):"
        ),
        "ask_fin": "🔢 አሁን ደግሞ የFIN ቁጥርዎን (12-ዲጂት) ያስገቡ:",
        "otp_sending": "⏳ OTP ወደ ስልክዎ እየተላከ ነው... እባክዎ ትንሽ ይጠብቁ።",
        "otp_prompt": (
            "📱 OTP ({phone}) ቁጥር ላይ ተልኳል። እባክዎ የደረሰዎትን 6-ዲጂት OTP"
            " ያስገቡ:"
        ),
        "processing": "⚙️ መረጃዎ እየተረጋገጠ እና ፒዲኤፍ እየተዘጋጀ ነው... ጥቂት ሰከንዶች ይጠብቁ።",
        "success": "✅ የእርስዎ Fayda ID በትክክል ወርዷል!",
        "cancel": "❌ ሂደቱ ተቋርጧል።",
        "error_net": "⚠️ የኔትወርክ ችግር አጋጥሟል። እባክዎ እንደገና ይሞክሩ።",
        "deposit_info": (
            "💳 **የሂሳብ መሙያ (Deposit) የባንክ አካውንቶች:**\n\nፖይንት ለመሙላት ከታች"
            " ባሉት የባንክ አካውንቶች ገንዘብ ከፍሎ የደረሰኝ ስክሪንሾት (Screenshot)"
            " ይላኩ 📸\n\n📱 **ቴሌብር (Telebirr):** `0998703233`\n🏦 **ንግድ ባንክ"
            " (CBE):** `1000745390448`\n🏦 **አቢሲኒካ ባንክ (BoA):**"
            " `92707617`\n🏦 **አማራ ባንክ (Amhara Bank):**"
            " `9900039885356`\n\n👇 **ክፍያውን ከፈጸሙ በኋላ የደረሰኝ ፎቶ (Screenshot)"
            " በቀጥታ ወደዚህ ቦት ይላኩ!**"
        ),
        "receipt_received": (
            "📩 **የክፍያ ማረጋገጫ ደርሷል!**\n\nአድሚኑ እስኪያረጋግጠው ⏳ ትንሽ"
            " ይጠብቁ። ማረጋገጫ ሲሰጥ ፖይንቱ በራስ ሰር ይሞላልዎታል።"
        ),
        "balance_text": "💰 **የእርስዎ ቀሪ ፖይንት:** {points} ፖይንት ይቀርዎታል።",
        "menu_get_id": "🪪 Get PDF",
        "menu_balance": "⭐ My points",
        "menu_deposit": "💳 Buy points",
        "menu_support": "💬 Support",
        "menu_lang": "🇪🇹 አማርኛ",
    },
    "en": {
        "welcome": (
            "👋 Hello! Welcome to Fayda ID Bot. Choose an option below 👇"
        ),
        "ask_fan": (
            "🆔 Please enter your FAN number (16-digits) (or type /cancel):"
        ),
        "ask_fin": "🔢 Now enter your FIN number (12-digits):",
        "otp_sending": "⏳ Sending OTP to your phone... Please wait.",
        "otp_prompt": (
            "📱 OTP sent to ({phone}). Please enter the 6-digit OTP code:"
        ),
        "processing": "⚙️ Verifying details and generating PDF... Please wait.",
        "success": "✅ Your Fayda ID has been downloaded successfully!",
        "cancel": "❌ Process cancelled.",
        "error_net": "⚠️ Network error occurred. Please try again.",
        "deposit_info": (
            "💳 **Deposit / Bank Accounts:**\n\nTo top up points, transfer money"
            " to any account below and send the screenshot 📸\n\n📱 **Telebirr:**"
            " `0998703233`\n🏦 **CBE:** `1000745390448`\n🏦 **BoA:**"
            " `92707617`\n🏦 **Amhara Bank:** `9900039885356`\n\n👇 **Send your"
            " payment screenshot directly to this bot!**"
        ),
        "receipt_received": (
            "📩 **Receipt Received!**\n\nPlease wait ⏳ while the admin"
            " verifies your payment. Your points will be added soon."
        ),
        "balance_text": "💰 **Your Balance:** You have {points} points left.",
        "menu_get_id": "🪪 Get PDF",
        "menu_balance": "⭐ My points",
        "menu_deposit": "💳 Buy points",
        "menu_support": "💬 Support",
        "menu_lang": "🇬🇧 English",
    },
}


def get_lang(context: ContextTypes.DEFAULT_TYPE):
  return context.user_data.get("lang", "am")


def get_main_keyboard(lang="am"):
  t = TEXTS[lang]
  return ReplyKeyboardMarkup(
      [
          [KeyboardButton(t["menu_get_id"]), KeyboardButton(t["menu_balance"])],
          [KeyboardButton(t["menu_deposit"]), KeyboardButton(t["menu_support"])],
          [KeyboardButton(t["menu_lang"])],
      ],
      resize_keyboard=True,
  )


# ----------------- Start & Main Menu -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  context.user_data.setdefault("lang", "am")
  lang = get_lang(context)
  t = TEXTS[lang]
  reply_markup = get_main_keyboard(lang)

  if update.message:
    await update.message.reply_text(
        t["welcome"], reply_markup=reply_markup, parse_mode="Markdown"
    )


async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  text = update.message.text
  lang = get_lang(context)

  if "አማርኛ" in text or "English" in text or "Change" in text:
    context.user_data["lang"] = "en" if lang == "am" else "am"
    await start(update, context)
  elif "Get PDF" in text or "Verify" in text:
    return await start_cmd(update, context)
  elif "My points" in text or "ባላንስ" in text:
    user_id = update.effective_user.id
    points = get_user_points(user_id)
    t = TEXTS[lang]
    await update.message.reply_text(
        t["balance_text"].format(points=points), parse_mode="Markdown"
    )
  elif "Buy points" in text or "ፖይንት" in text:
    t = TEXTS[lang]
    await update.message.reply_text(t["deposit_info"], parse_mode="Markdown")
  elif "Support" in text:
    await update.message.reply_text(
        "💬 ጥያቄ ካሎት አድሚኑን በውስጥ መስመር ያነጋግሩ።"
    )


# ----------------- Screenshot Receipt Handler -----------------
async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user = update.effective_user
  lang = get_lang(context)
  t = TEXTS[lang]

  if not update.message.photo:
    return

  photo_file = update.message.photo[-1].file_id

  from telegram import InlineKeyboardButton, InlineKeyboardMarkup

  admin_kb = InlineKeyboardMarkup([
      [
          InlineKeyboardButton(
              "✅ አጽድቅ (Approve)", callback_data=f"approve_{user.id}"
          ),
          InlineKeyboardButton(
              "❌ ውድቅ አድርግ (Reject)", callback_data=f"reject_{user.id}"
          ),
      ]
  ])

  user_points = get_user_points(user.id)

  try:
    await context.bot.send_photo(
        chat_id=ADMIN_CHAT_ID,
        photo=photo_file,
        caption=(
            f"📥 **አዲስ የክፍያ ስክሪንሾት ደርሷል!**\n\n👤 ስም: {user.full_name}\n🆔"
            f" ዩዘር ID: `{user.id}`\n🔗 ዩዘርናም: @{user.username or 'None'}\n💰"
            f" አሁን ያለው ፖይንት: `{user_points}` ፖይንት"
        ),
        reply_markup=admin_kb,
        parse_mode="Markdown",
    )
    await update.message.reply_text(t["receipt_received"], parse_mode="Markdown")
  except Exception as e:
    print(f"Error sending to admin: {e}")
    await update.message.reply_text(
        "⚠️ ስክሪንሾቱን ወደ አድሚን መላክ አልተቻለም። እባክዎ ቆይተው እንደገና ይሞክሩ።"
    )


# ----------------- Admin Action Handlers -----------------
async def admin_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  query = update.callback_query
  await query.answer()
  data = query.data

  if data.startswith("approve_"):
    target_user_id = int(data.split("_")[1])
    context.user_data["pending_approve_user"] = target_user_id

    await query.message.reply_text(
        "✍️ እባክዎ ለዚህ ተጠቃሚ መሙላት የሚፈልጉትን የ**ፖይንት መጠን** (ቁጥር ብቻ"
        " አድርገው) በጽሑፍ ይላኩልን (ለምሳሌ: 50 ወይም 100):",
        parse_mode="Markdown",
    )
    return WAITING_POINT_AMOUNT

  elif data.startswith("reject_"):
    target_user_id = int(data.split("_")[1])
    try:
      await context.bot.send_message(
          chat_id=target_user_id,
          text=(
              "❌ **የክፍያዎ ደረሰኝ ውድቅ ተደርጓል!**\n\nእባክዎ ትክክለኛ የክፍያ ደረሰኝ"
              " መላክዎን ያረጋግጡ ወይም አድሚኑን ያነጋግሩ።"
          ),
          parse_mode="Markdown",
      )
      await query.edit_message_caption(
          caption=query.message.caption
          + "\n\n❌ **[ሁኔታ: ውድቅ ተደርጓል (Rejected)]**",
          reply_markup=None,
      )
    except Exception:
      await query.message.reply_text("⚠️ ተጠቃሚው መልክቱን ማግኘት አልቻለም።")


async def save_approved_points(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  text_input = update.message.text.strip()
  if not text_input.isdigit():
    await update.message.reply_text(
        "⚠️ እባክዎ ትክክለኛ የፖይንት መጠን በቁጥር ብቻ (ለምሳሌ: 50) ያስገቡ:"
    )
    return WAITING_POINT_AMOUNT

  points_to_add = int(text_input)
  target_user_id = context.user_data.get("pending_approve_user")

  if not target_user_id:
    await update.message.reply_text(
        "⚠️ ስህተት ተፈጥሯል (User ID አልተገኘም)። እባክዎ እንደገና ይሞክሩ።"
    )
    return ConversationHandler.END

  new_total = add_user_points(target_user_id, points_to_add)

  try:
    await context.bot.send_message(
        chat_id=target_user_id,
        text=(
            f"🎉 **እንኳን ደስ አለዎት!**\n\nክፍያዎ በአድሚኑ ጸድቋል ✅\n➕ **የተጨመረልዎ"
            f" ፖይንት:** {points_to_add}\n💰 **ጠቅላላ ቀሪ ፖይንትዎ:** {new_total}"
            " ፖይንት"
        ),
        parse_mode="Markdown",
    )
    await update.message.reply_text(
        f"✅ ተጠቃሚው (ID: `{target_user_id}`) ৳{points_to_add} ፖይንት በተሳካ ሁኔታ"
        f" ተሞልቶለታል! (አጠቃላይ ባላንስ: {new_total})",
        parse_mode="Markdown",
    )
  except Exception:
    await update.message.reply_text(
        "⚠️ ፖይንቱ ተመዝግቧል ግን ለተጠቃሚው ማሳወቅ አልተቻለም።"
    )

  context.user_data.pop("pending_approve_user", None)
  return ConversationHandler.END


# ----------------- ID Download Conversation -----------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
  context.user_data.setdefault("lang", "am")
  lang = get_lang(context)
  await update.message.reply_text(
      TEXTS[lang]["ask_fan"], reply_markup=ReplyKeyboardRemove()
  )
  return WAITING_FAN


async def get_fan(update: Update, context: ContextTypes.DEFAULT_TYPE):
  lang = get_lang(context)
  text = update.message.text.strip()

  if text.startswith("/") or text in [
      "🪪 Get PDF",
      "💳 Buy points",
      "⭐ My points",
      "💬 Support",
  ]:
    return WAITING_FAN

  fan = text.replace(" ", "")
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
      lang = get_lang(context)
      await update.message.reply_text(
          f"❌ ስህተት ተከሰቷል: {msg}", reply_markup=get_main_keyboard(lang)
      )
      return ConversationHandler.END

  except Exception:
    lang = get_lang(context)
    await update.message.reply_text(
        t["error_net"], reply_markup=get_main_keyboard(lang)
    )
    return ConversationHandler.END


async def get_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
  lang = get_lang(context)
  t = TEXTS[lang]
  otp = update.message.text.strip().replace(" ", "")
  if len(otp) != 6 or not otp.isdigit():
    await update.message.reply_text("⚠️ እባክዎ ትክክለኛ የ6-ዲጂት OTP ያስገቡ:")
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
      filename = res_data.get("pdfFilename", "Fayda_ID.pdf")

      await update.message.reply_document(
          document=pdf_bytes,
          filename=filename,
          caption=t["success"],
          reply_markup=get_main_keyboard(lang),
      )
      return ConversationHandler.END
    else:
      msg = res_data.get("message", "ማረጋገጥ አልተቻለም።")
      await update.message.reply_text(
          f"❌ ስህተት: {msg}", reply_markup=get_main_keyboard(lang)
      )
      return ConversationHandler.END

  except Exception:
    await update.message.reply_text(
        "⚠️ ፋይል በማውረድ ላይ ችግር ተፈጥሯል መረጋገጥ አልቻለም።",
        reply_markup=get_main_keyboard(lang),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
  lang = get_lang(context)
  await update.message.reply_text(
      TEXTS[lang]["cancel"], reply_markup=get_main_keyboard(lang)
  )
  return ConversationHandler.END


def main():
  app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

  admin_point_conv = ConversationHandler(
      entry_points=[
          CallbackQueryHandler(admin_callback_handler, pattern="^approve_")
      ],
      states={
          WAITING_POINT_AMOUNT: [
              MessageHandler(filters.TEXT & ~filters.COMMAND, save_approved_points)
          ],
      },
      fallbacks=[CommandHandler("cancel", cancel)],
  )

  id_conv_handler = ConversationHandler(
      entry_points=[
          CommandHandler("start", start_cmd),
          MessageHandler(filters.Regex("^(🪪 Get PDF)$"), start_cmd),
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
      },
      fallbacks=[
          CommandHandler("start", start),
          CommandHandler("cancel", cancel),
      ],
  )

  app.add_handler(admin_point_conv)
  app.add_handler(id_conv_handler)
  app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^reject_"))
  app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
  app.add_handler(
      MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_menu)
  )
  app.add_handler(CommandHandler("start", start))

  print("Bot with Reply Keyboard is running...")
  app.run_polling()


if __name__ == "__main__":
  main()
