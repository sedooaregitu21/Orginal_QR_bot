"""Telegram bot for the authorized Fayda Verified QR API.
Secrets are read only from Render environment variables.
"""
import base64
import io
import logging
import os
import re
import unicodedata

import requests
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
FAYDA_API_KEY = os.environ.get("FAYDA_API_KEY", "").strip()
BASE_URL = "https://otp.affiliate.pro.et/api/v1"

if not BOT_TOKEN:
    raise SystemExit("Missing BOT_TOKEN environment variable in Render > Environment.")
if not FAYDA_API_KEY:
    raise SystemExit("Missing FAYDA_API_KEY environment variable in Render > Environment.")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
bot = telebot.TeleBot(BOT_TOKEN)
# Temporary only; restart/deploy clears it. Never log these values.
sessions = {}


def clean_text(value):
    value = unicodedata.normalize("NFKC", value or "")
    # Strip zero-width / variation selector characters and surrounding spaces.
    return "".join(ch for ch in value if unicodedata.category(ch) != "Cf").strip()


def main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("🪪 Verify Digital ID"))
    kb.row(KeyboardButton("❌ Cancel"))
    return kb


def consent_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row(KeyboardButton("✅ I agree and continue"))
    kb.row(KeyboardButton("❌ Cancel"))
    return kb


def api_headers():
    return {"x-api-key": FAYDA_API_KEY, "Content-Type": "application/json"}


def api_error_message(response):
    try:
        body = response.json()
        if isinstance(body, dict) and body.get("message"):
            return str(body["message"])[:350]
    except (ValueError, TypeError):
        pass
    return f"The verification service returned HTTP {response.status_code}."


def private_only(message):
    if message.chat.type != "private":
        bot.reply_to(message, "For privacy, please use this bot in a private chat.")
        return False
    return True


def ask_fan(message):
    sessions[message.from_user.id] = {"step": "fan"}
    bot.send_message(
        message.chat.id,
        "Enter the 16-digit FAN for an ID you are authorized to verify. Do not include spaces.",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(commands=["start"])
def start(message):
    if not private_only(message):
        return
    sessions.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        "🪪 Digital ID Verification Bot\n\n"
        "This bot connects to the authorized Fayda Verified QR service. "
        "If you continue, your FAN, FIN and OTP will be sent to that service.\n\n"
        "Use this only for your own ID or when legally authorized. Your ID details, QR and PDF are sensitive. "
        "Use this bot in a private chat and do not forward results without permission.\n\n"
        "Tap Verify Digital ID to begin.",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(func=lambda m: clean_text(m.text) in {"❌ Cancel", "Cancel"}, content_types=["text"])
def cancel(message):
    sessions.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        "Cancelled. Temporary verification details held by this running process were cleared.",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(func=lambda m: clean_text(m.text) in {"🪪 Verify Digital ID", "Verify Digital ID"}, content_types=["text"])
def begin(message):
    if not private_only(message):
        return
    sessions[message.from_user.id] = {"step": "consent"}
    bot.send_message(
        message.chat.id,
        "Before continuing, confirm that you are authorized to verify this ID and agree to send FAN, FIN and OTP to the Fayda Verified QR service.",
        reply_markup=consent_keyboard(),
    )


@bot.message_handler(func=lambda m: clean_text(m.text) in {"✅ I agree and continue", "I agree and continue"}, content_types=["text"])
def agree(message):
    if not private_only(message):
        return
    state = sessions.get(message.from_user.id)
    if not state or state.get("step") != "consent":
        bot.send_message(message.chat.id, "Tap 🪪 Verify Digital ID to start again.", reply_markup=main_keyboard())
        return
    ask_fan(message)


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    if not private_only(message):
        return
    user_id = message.from_user.id
    state = sessions.get(user_id)
    text = clean_text(message.text)

    if not state:
        bot.send_message(message.chat.id, "Tap 🪪 Verify Digital ID to start.", reply_markup=main_keyboard())
        return
    if state.get("step") == "consent":
        bot.send_message(message.chat.id, "Please tap ✅ I agree and continue, or ❌ Cancel.", reply_markup=consent_keyboard())
        return

    if state.get("step") == "fan":
        fan = re.sub(r"\s+", "", text)
        if not re.fullmatch(r"\d{16}", fan):
            bot.reply_to(message, "FAN must contain exactly 16 digits. Please try again.")
            return
        state["fan"] = fan
        state["step"] = "fin"
        bot.send_message(message.chat.id, "Now enter the 12-digit FIN.")
        return

    if state.get("step") == "fin":
        fin = re.sub(r"\s+", "", text)
        if not re.fullmatch(r"\d{12}", fin):
            bot.reply_to(message, "FIN must contain exactly 12 digits. Please try again.")
            return
        state["fin"] = fin
        state["step"] = "sending"
        bot.send_message(message.chat.id, "Requesting an OTP from the registered phone. Please wait...")
        try:
            response = requests.post(
                f"{BASE_URL}/send-otp-verified-qr",
                json={"fanNumber": state["fan"], "finNumber": state["fin"]},
                headers=api_headers(), timeout=60,
            )
            if response.status_code != 200:
                sessions.pop(user_id, None)
                bot.send_message(message.chat.id, "Could not send OTP: " + api_error_message(response) + "\nPlease tap /start to try again.", reply_markup=main_keyboard())
                return
            result = response.json()
            session_token = result.get("session")
            if not session_token:
                raise ValueError("Missing session field")
            state["session"] = session_token
            state["step"] = "otp"
            phone = result.get("phone") or "your registered phone"
            bot.send_message(message.chat.id, f"OTP sent to {phone}.\n\nEnter the 6-digit OTP you received. Never share this code with anyone.")
        except requests.Timeout:
            sessions.pop(user_id, None)
            bot.send_message(message.chat.id, "The OTP request timed out. Please start again later.", reply_markup=main_keyboard())
        except requests.RequestException:
            sessions.pop(user_id, None)
            bot.send_message(message.chat.id, "The verification service could not be reached. Please try again later.", reply_markup=main_keyboard())
        except (ValueError, TypeError):
            sessions.pop(user_id, None)
            bot.send_message(message.chat.id, "The service returned an incomplete response. Please try again later.", reply_markup=main_keyboard())
        return

    if state.get("step") == "otp":
        otp = re.sub(r"\s+", "", text)
        if not re.fullmatch(r"\d{6}", otp):
            bot.reply_to(message, "OTP must contain exactly 6 digits. Please try again.")
            return
        state["step"] = "verifying"
        bot.send_message(message.chat.id, "Verifying OTP. This may take up to 120 seconds; please wait...")
        try:
            response = requests.post(
                f"{BASE_URL}/verify-otp-verified-qr",
                json={"otp": otp, "fanNumber": state["fan"], "finNumber": state["fin"], "session": state["session"]},
                headers=api_headers(), timeout=120,
            )
            if response.status_code != 200:
                bot.send_message(message.chat.id, "Verification failed: " + api_error_message(response) + "\nPlease tap /start to try again.", reply_markup=main_keyboard())
                return
            result = response.json()
            if result.get("success") is not True:
                bot.send_message(message.chat.id, "Verification was not successful. Please start again if needed.", reply_markup=main_keyboard())
                return
            qr_b64 = result.get("verifiedQr")
            pdf_b64 = result.get("pdf")
            remaining = result.get("remainingPoints")
            if qr_b64:
                qr_bytes = base64.b64decode(qr_b64, validate=True)
                bot.send_photo(message.chat.id, io.BytesIO(qr_bytes), caption="Verified QR result. Keep it private.")
            if pdf_b64:
                pdf_bytes = base64.b64decode(pdf_b64, validate=True)
                filename = str(result.get("pdfFilename") or "verified-id.pdf").replace("/", "_").replace("\\", "_")
                bot.send_document(message.chat.id, (filename, io.BytesIO(pdf_bytes)), caption="Verified ID PDF. It contains sensitive personal information; do not forward it without permission.")
            reply = "Verification successful."
            if remaining is not None:
                reply += f"\nService points remaining: {remaining}"
            if not qr_b64 and not pdf_b64:
                reply += "\nThe service did not return a QR image or PDF."
            bot.send_message(message.chat.id, reply, reply_markup=main_keyboard())
        except requests.Timeout:
            bot.send_message(message.chat.id, "Verification timed out. Check the service before retrying, as the request may have completed.", reply_markup=main_keyboard())
        except requests.RequestException:
            bot.send_message(message.chat.id, "The verification service could not be reached. Please try again later.", reply_markup=main_keyboard())
        except (ValueError, TypeError, KeyError):
            bot.send_message(message.chat.id, "The service returned an unexpected result. Please contact the service administrator.", reply_markup=main_keyboard())
        finally:
            sessions.pop(user_id, None)
        return

    bot.send_message(message.chat.id, "Please wait or tap /start to begin again.", reply_markup=main_keyboard())


if __name__ == "__main__":
    logging.info("Digital ID Verification Bot starting.")
    try:
        bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
    except Exception as exc:
        # Do not log user IDs, FAN, FIN, OTP, API keys or response bodies.
        logging.error("Bot stopped with error type: %s", type(exc).__name__)
        raise
