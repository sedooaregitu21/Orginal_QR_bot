import os
import re
import time
import base64
import logging
import sqlite3
from io import BytesIO
from datetime import datetime, timedelta, timezone

import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------------- Configuration ----------------
BOT_TOKEN = os.environ["BOT_TOKEN"]
FAYDA_API_KEY = os.environ["FAYDA_API_KEY"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
API_BASE = "https://otp.affiliate.pro.et/api/v1"
PAYMENT_INSTRUCTIONS = os.getenv(
    "PAYMENT_INSTRUCTIONS",
    "Payment instructions have not been configured yet. Please contact the bot administrator."
)
DB_PATH = os.getenv("DB_PATH", "sedoo_verified_qr.db")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
logging.basicConfig(level=logging.INFO)
# Do not log message bodies, FANs, OTPs, API keys, or API response bodies.

TEXT = {
    "am": {
        "choose": "🌐 ቋንቋ ይምረጡ፦",
        "welcome": "እንኳን ወደ Sedoo Verified QR በደህና መጡ።\n\nይህ አገልግሎት የራስዎን Fayda ID ለማረጋገጥ ብቻ ነው።",
        "consent": "የራሴን Fayda ID እጠቀማለሁ፣ ለማረጋገጥም ፈቃድ እሰጣለሁ ብለው ያረጋግጡ።",
        "agree": "✅ እስማማለሁ",
        "pay": "የአገልግሎቱ ክፍያ 15 ብር ነው።\n\n{} \n\nክፍያዎን ካደረጉ በኋላ የክፍያ ማረጋገጫ ይላኩ። አስተዳዳሪው ካጸደቀው በኋላ ይቀጥላሉ።",
        "proof": "የክፍያ ማረጋገጫውን (ደረሰኝ/ማጣቀሻ) እንደ መልዕክት ወይም ፎቶ ይላኩ።",
        "pending": "የክፍያ ማረጋገጫዎ ተልኳል። አስተዳዳሪው ሲያጸድቅ ይቀጥሉ።",
        "approved": "ክፍያዎ ተፈቅዷል። የ16 አሃዝ FAN ቁጥርዎን ያስገቡ።",
        "fanbad": "FAN ቁጥሩ 16 አሃዝ መሆን አለበት። እንደገና ያስገቡ።",
        "otp1": "የመጀመሪያው OTP ወደ ተመዘገበው ስልክ ተልኳል። ኮዱን እዚህ ያስገቡ።",
        "otp2": "የመጀመሪያው ማረጋገጫ ተሳክቷል። ሁለተኛው OTP ተልኳል። በ10 ደቂቃ ውስጥ ያስገቡ።",
        "done": "ማረጋገጫው ተሳክቷል። QR እና PDF እዚህ ተልከዋል።",
        "restart": "ሂደቱ አልቋል ወይም ጊዜው አልፏል። /start በመጫን እንደገና ይጀምሩ።",
        "error": "ማረጋገጫው አልተሳካም። መረጃውን ያረጋግጡና /start ይጫኑ።",
        "wait": "እባክዎ አስተዳዳሪው ክፍያዎን እስኪያጸድቅ ይጠብቁ።",
        "help": "ይህ ቦት የFayda Verified QR 2 ባለሁለት OTP ሂደትን ብቻ ይጠቀማል። /start ይጫኑ።",
    },
    "en": {
        "choose": "🌐 Choose your language:",
        "welcome": "Welcome to Sedoo Verified QR.\n\nUse this service only to verify your own Fayda ID.",
        "consent": "Confirm that this is your own Fayda ID and that you authorize this verification.",
        "agree": "✅ I agree",
        "pay": "The service fee is 15 ETB.\n\n{}\n\nAfter paying, send your payment proof. Processing continues after admin approval.",
        "proof": "Send your payment receipt/reference as a message or photo.",
        "pending": "Payment proof received. Please wait for admin approval.",
        "approved": "Payment approved. Enter your 16-digit FAN.",
        "fanbad": "FAN must contain exactly 16 digits. Please try again.",
        "otp1": "The first OTP was sent to your registered phone. Enter it here.",
        "otp2": "First verification succeeded. The second OTP was sent. Enter it within 10 minutes.",
        "done": "Verification succeeded. Your QR and PDF are attached here.",
        "restart": "The process ended or expired. Send /start to begin again.",
        "error": "Verification failed. Check your details and send /start to try again.",
        "wait": "Please wait until an administrator approves your payment.",
        "help": "This bot uses only the two-OTP Fayda Verified QR 2 flow. Send /start.",
    },
    "om": {
        "choose": "🌐 Afaan keessan filadhaa:",
        "welcome": "Baga gara Sedoo Verified QR dhuftan.\n\nFayda ID keessan dhuunfaa qofa mirkaneessuuf fayyadamaa.",
        "consent": "Fayda ID kun kan keessan ta'uu fi mirkaneessuuf hayyama kennuu keessan mirkaneessaa.",
        "agree": "✅ Nan walii gala",
        "pay": "Kaffaltiin tajaajilaa 15 ETB dha.\n\n{}\n\nErga kaffaltanii booda ragaa kaffaltii ergaa. Bulchaan erga mirkaneesseen booda itti fufa.",
        "proof": "Ragaa kaffaltii (receipt/reference) akka ergaa yookaan suuraa ergaa.",
        "pending": "Ragaan kaffaltii keessanii fudhatameera. Mirkaneessa bulchaa eeggadhaa.",
        "approved": "Kaffaltiin mirkanaa'eera. FAN lakkoofsa dijitii 16 qabu galchaa.",
        "fanbad": "FAN dijitii 16 qabaachuu qaba. Irra deebi'aa galchaa.",
        "otp1": "OTP jalqabaa gara bilbila galmaa'eetti ergameera. Asitti galchaa.",
        "otp2": "Mirkaneessi jalqabaa milkaa'eera. OTP lammaffaan ergameera. Daqiiqaa 10 keessatti galchaa.",
        "done": "Mirkaneessi milkaa'eera. QR fi PDF keessan asitti ergameera.",
        "restart": "Adeemsi xumurame yookaan yeroo isaa darbe. /start ergaa.",
        "error": "Mirkaneessi hin milkoofne. Odeeffannoo keessan ilaalaa; /start ergaa.",
        "wait": "Maaloo hanga bulchaan kaffaltii keessan mirkaneessutti eeggadhaa.",
        "help": "Botichi adeemsa Fayda Verified QR 2 OTP lama qabu qofa fayyadama. /start ergaa.",
    },
}

def db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            lang TEXT NOT NULL DEFAULT 'am',
            state TEXT NOT NULL DEFAULT 'language',
            paid INTEGER NOT NULL DEFAULT 0,
            fan TEXT,
            session TEXT,
            step2_expires REAL
        )""")

def get_user(uid):
    with db() as c:
        row = c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
        if not row:
            c.execute("INSERT INTO users(user_id) VALUES(?)", (uid,))
            row = c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
        return dict(row)

def update(uid, **fields):
    allowed = {"lang", "state", "paid", "fan", "session", "step2_expires"}
    fields = {k:v for k,v in fields.items() if k in allowed}
    if not fields:
        return
    sql = ", ".join(f"{k}=?" for k in fields)
    with db() as c:
        c.execute(f"UPDATE users SET {sql} WHERE user_id=?", (*fields.values(), uid))

def clear_transaction(uid, keep_paid=True):
    user = get_user(uid)
    update(uid, state="ready" if keep_paid and user["paid"] else "payment",
           fan=None, session=None, step2_expires=None)

def t(uid, key):
    return TEXT.get(get_user(uid)["lang"], TEXT["am"])[key]

def api_post(path, payload, timeout):
    headers = {"x-api-key": FAYDA_API_KEY, "Content-Type": "application/json"}
    return requests.post(API_BASE + path, json=payload, headers=headers, timeout=timeout)

def extract_data(resp):
    try:
        obj = resp.json()
    except Exception:
        raise RuntimeError("Invalid API response")
    if not resp.ok:
        code = resp.status_code
        if code == 401: raise RuntimeError("API_KEY")
        if code == 402: raise RuntimeError("POINTS")
        if code == 429: raise RuntimeError("RATE_LIMIT")
        raise RuntimeError("API_ERROR")
    # Accept common API wrappers without assuming identity field names.
    return obj.get("data", obj)

def b64_file(value):
    if not isinstance(value, str):
        raise ValueError("Missing file")
    if value.startswith("data:") and "," in value:
        value = value.split(",", 1)[1]
    return base64.b64decode(value, validate=False)

def safe_error(uid, exc):
    code = str(exc)
    if code == "API_KEY":
        bot.send_message(uid, "Service configuration error. Please contact the administrator.")
    elif code == "POINTS":
        bot.send_message(uid, "The verification provider account has insufficient points. Please contact the administrator.")
    elif code == "RATE_LIMIT":
        bot.send_message(uid, "Too many attempts. Please wait and try later.")
    else:
        bot.send_message(uid, t(uid, "error"))

@bot.message_handler(commands=["start", "help"])
def start(message):
    uid = message.from_user.id
    update(uid, state="language", fan=None, session=None, step2_expires=None)
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("አማርኛ", callback_data="lang:am"),
           InlineKeyboardButton("English", callback_data="lang:en"),
           InlineKeyboardButton("Afaan Oromoo", callback_data="lang:om"))
    bot.send_message(uid, TEXT["am"]["choose"], reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("lang:"))
def language(c):
    uid = c.from_user.id
    lang = c.data.split(":", 1)[1]
    if lang not in TEXT: lang = "am"
    update(uid, lang=lang, state="consent")
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t(uid, "agree"), callback_data="consent:yes"))
    bot.answer_callback_query(c.id)
    bot.send_message(uid, t(uid, "welcome") + "\n\n" + t(uid, "consent"), reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "consent:yes")
def consent(c):
    uid = c.from_user.id
    update(uid, state="payment")
    bot.answer_callback_query(c.id)
    bot.send_message(uid, t(uid, "pay").format(PAYMENT_INSTRUCTIONS))
    bot.send_message(uid, t(uid, "proof"))

@bot.message_handler(content_types=["text", "photo"], func=lambda m: get_user(m.from_user.id)["state"] == "payment")
def payment_proof(message):
    uid = message.from_user.id
    if uid == ADMIN_ID:
        bot.send_message(uid, "Admin: use /approve USER_ID to approve a payment.")
        return
    try:
        bot.forward_message(ADMIN_ID, uid, message.message_id)
        bot.send_message(ADMIN_ID, f"Payment proof received from Telegram user ID: {uid}\nApprove with /approve {uid}")
        bot.send_message(uid, t(uid, "pending"))
    except Exception:
        bot.send_message(uid, "Could not submit proof. Please contact the administrator.")

@bot.message_handler(commands=["approve"])
def approve(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        bot.reply_to(message, "Usage: /approve USER_ID")
        return
    uid = int(parts[1])
    get_user(uid)
    update(uid, paid=1, state="ready")
    bot.send_message(uid, t(uid, "approved"))
    bot.reply_to(message, "Payment approved.")

@bot.message_handler(commands=["cancel"])
def cancel(message):
    uid = message.from_user.id
    clear_transaction(uid)
    bot.send_message(uid, t(uid, "restart"))

@bot.message_handler(func=lambda m: get_user(m.from_user.id)["state"] in ("ready", "fan", "otp1", "otp2"))
def handle_flow(message):
    uid = message.from_user.id
    user = get_user(uid)
    value = (message.text or "").strip()

    if not user["paid"]:
        bot.send_message(uid, t(uid, "wait"))
        return

    if user["state"] in ("ready", "fan"):
        fan = re.sub(r"\s+", "", value)
        if not re.fullmatch(r"\d{16}", fan):
            bot.send_message(uid, t(uid, "fanbad"))
            return
        update(uid, fan=fan, state="sending")
        try:
            resp = api_post("/send-otp-verified-qr2", {"fanNumber": fan}, 60)
            data = extract_data(resp)
            session = data.get("session")
            if not session:
                raise RuntimeError("API_ERROR")
            update(uid, session=str(session), state="otp1")
            bot.send_message(uid, t(uid, "otp1"))
        except Exception as e:
            clear_transaction(uid)
            safe_error(uid, e)
        return

    if user["state"] == "otp1":
        otp = re.sub(r"\s+", "", value)
        if not re.fullmatch(r"\d{4,8}", otp):
            bot.send_message(uid, "Enter the OTP digits only.")
            return
        update(uid, state="verifying1")
        try:
            user = get_user(uid)
            resp = api_post("/verify-otp-verified-qr2",
                            {"otp": otp, "fanNumber": user["fan"], "session": user["session"]}, 120)
            data = extract_data(resp)
            new_session = data.get("session")
            if not new_session:
                raise RuntimeError("API_ERROR")
            update(uid, session=str(new_session), state="otp2",
                   step2_expires=time.time() + 600)
            bot.send_message(uid, t(uid, "otp2"))
        except Exception as e:
            clear_transaction(uid)
            safe_error(uid, e)
        return

    if user["state"] == "otp2":
        if not user["step2_expires"] or time.time() > user["step2_expires"]:
            clear_transaction(uid)
            bot.send_message(uid, t(uid, "restart"))
            return
        otp = re.sub(r"\s+", "", value)
        if not re.fullmatch(r"\d{4,8}", otp):
            bot.send_message(uid, "Enter the OTP digits only.")
            return
        update(uid, state="verifying2")
        try:
            user = get_user(uid)
            resp = api_post("/verify-otp-verified-qr2-final",
                            {"otp": otp, "fanNumber": user["fan"], "session": user["session"]}, 120)
            data = extract_data(resp)

            qr_value = data.get("verifiedQr")
            pdf_value = data.get("pdf") or data.get("verifiedQrPdf")
            pdf_name = data.get("pdfFilename") or data.get("filename") or "Fayda-Verified-QR.pdf"

            if not qr_value or not pdf_value:
                raise RuntimeError("API_ERROR")

            qr_bytes = b64_file(qr_value)
            pdf_bytes = b64_file(pdf_value)

            # Send only to the Telegram account that initiated this transaction.
            bot.send_document(uid, BytesIO(qr_bytes), visible_file_name="Fayda-Verified-QR.png")
            bot.send_document(uid, BytesIO(pdf_bytes), visible_file_name=os.path.basename(str(pdf_name)))
            bot.send_message(uid, t(uid, "done"))
            clear_transaction(uid)
        except Exception as e:
            clear_transaction(uid)
            safe_error(uid, e)

@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.send_message(message.chat.id, t(message.from_user.id, "help"))

if __name__ == "__main__":
    init_db()
    if not all([BOT_TOKEN, FAYDA_API_KEY, ADMIN_ID]):
        raise RuntimeError("Set BOT_TOKEN, FAYDA_API_KEY and ADMIN_ID environment variables.")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
