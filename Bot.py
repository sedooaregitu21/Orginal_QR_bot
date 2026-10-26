# ============================================================
# DIGITAL ID VERIFICATION BOT — ALL-IN-ONE FILE
#
# The Verified QR integration guide is included below as comments,
# followed by the runnable Telegram bot code.
# Before running: fill BOT_TOKEN and FAYDA_API_KEY in the code section.
# Keep both values secret. Install packages in Pydroid 3:
#     pip install pyTelegramBotAPI requests
# ============================================================
# INCLUDED VERIFIED QR INTEGRATION GUIDE
# # Verified QR — Integration Guide
#
# This product verifies a National ID with **FAN and FIN**, using **one OTP**. A successful verify returns the identity as JSON, the signed Fayda QR, and a PDF.
#
# **Base URL:** `https://otp.affiliate.pro.et/api/v1`  
# **Auth:** `x-api-key: your_fayda_api_key` on every request
#
# This is a separate API. Do not use `/send-otp`, `/verify-otp`, `/verify-otp-json`, `/send-otp-pass`, `/verify-otp-pass`, or the Verified QR 2 endpoints for this product.
#
# ---
#
# ## What you get
#
# | | |
# |---|---|
# | Send | `POST /send-otp-verified-qr` — OTP to the registered phone |
# | Verify | `POST /verify-otp-verified-qr` — JSON profile, verified QR, and PDF |
# | Cost | **1 point**, deducted only after a successful verify |
# | Remaining points | `remainingPoints` in the JSON body and `X-Remaining-Points` header |
#
# ---
#
# ## Flow
#
# ```
# Client sends FAN + FIN
#   → POST /send-otp-verified-qr
#   → store session with that FAN and FIN
#   → OTP is sent to the masked phone
#
# Client sends OTP
#   → POST /verify-otp-verified-qr with { otp, fanNumber, finNumber, session }
#   → if 200:
#         read data
#         decode verifiedQr and pdf from base64
#         read remainingPoints
#   → if error:
#         show message from JSON
# ```
#
# Store `session`, `fanNumber`, and `finNumber` together. Pass `session` back exactly as returned. Do not parse or modify it.
#
# ---
#
# ## Authentication
#
# Every request must include your API key.
#
# 1. **Header (recommended)**  
#    `x-api-key: your_fayda_api_key`
#
# 2. **Query parameter**  
#    `?apiKey=your_fayda_api_key`
#
# Keep the key on your server. Never put it in a browser, mini-app, or mobile client.
#
# ---
#
# ## 1. Send OTP
#
# ```
# POST /api/v1/send-otp-verified-qr
# Content-Type: application/json
# x-api-key: YOUR_KEY
# ```
#
# ```json
# {
#   "fanNumber": "1234567890123456",
#   "finNumber": "123456789012"
# }
# ```
#
# | Field | Type | Required | Description |
# |---|---|---|---|
# | `fanNumber` | string | yes | 16-digit FAN. Spaces are stripped. |
# | `finNumber` | string | yes | 12-digit FIN. Spaces are stripped. |
#
# Success (`200`):
#
# ```json
# {
#   "session": "opaque-string-store-as-is",
#   "phone": "******7890",
#   "otpMethod": "vqr"
# }
# ```
#
# | Field | Description |
# |---|---|
# | `session` | Opaque token. Store as-is and send it unchanged to verify. |
# | `phone` | Masked mobile number the OTP was sent to. |
# | `otpMethod` | Always `vqr` on this endpoint. |
#
# Send OTP does not deduct a point. If the account has 0 points, this call returns `402`.
#
# ---
#
# ## 2. Verify OTP
#
# ```
# POST /api/v1/verify-otp-verified-qr
# Content-Type: application/json
# x-api-key: YOUR_KEY
# ```
#
# ```json
# {
#   "otp": "123456",
#   "fanNumber": "1234567890123456",
#   "finNumber": "123456789012",
#   "session": "opaque-string-from-step-1"
# }
# ```
#
# | Field | Type | Required | Description |
# |---|---|---|---|
# | `otp` | string | yes | 6-digit code from SMS. |
# | `fanNumber` | string | yes | Same 16-digit FAN from step 1. |
# | `finNumber` | string | yes | Same 12-digit FIN from step 1. |
# | `session` | string | yes | Exact `session` from step 1. |
#
# Allow **60–120 seconds** timeout. Verification can take several seconds.
#
# Success (`200`):
#
# ```json
# {
#   "success": true,
#   "otpMethod": "vqr",
#   "remainingPoints": 496,
#   "data": {
#     "fanNumber": "1234567890123456",
#     "fin": "123456789012",
#     "name": {
#       "amharic": "...",
#       "english": "..."
#     },
#     "dateOfBirth": {
#       "ethiopian": "01/05/1988",
#       "gregorian": "1988-05-09"
#     },
#     "gender": {
#       "amharic": "...",
#       "english": "Male"
#     },
#     "nationality": {
#       "amharic": "ኢትዮጵያዊ",
#       "english": "Ethiopian"
#     },
#     "phone": "0912345678",
#     "address": {
#       "city": { "amharic": "...", "english": "..." },
#       "subCity": { "amharic": "...", "english": "..." },
#       "woreda": { "amharic": "...", "english": "..." }
#     },
#     "issueDate": {
#       "ethiopian": "...",
#       "gregorian": "..."
#     },
#     "expiryDate": {
#       "ethiopian": "...",
#       "gregorian": "..."
#     },
#     "photo": "base64",
#     "qrCode": "base64"
#   },
#   "verifiedQr": "base64-png",
#   "pdf": "base64-pdf-bytes",
#   "pdfFilename": "Fayda-Original-Full-Name-1234567890123456.pdf",
#   "pdfMimeType": "application/pdf"
# }
# ```
#
# Also returned as a header: `X-Remaining-Points: 496`
#
# | Field | Description |
# |---|---|
# | `remainingPoints` | Account balance after this request (1 point deducted). |
# | `data` | Identity profile, including photo and QR. |
# | `verifiedQr` | Signed Fayda identity QR as a base64 PNG. |
# | `pdf` | ID PDF as base64. Decode and save as a `.pdf` file. |
# | `pdfFilename` | Suggested filename. |
# | `pdfMimeType` | Always `application/pdf`. |
#
# Use `response.json()` on this endpoint. Success is JSON, not raw PDF bytes.
#
# To write the files in Node:
#
# ```javascript
# fs.writeFileSync('verified-qr.png', Buffer.from(verifiedQr, 'base64'));
# fs.writeFileSync(pdfFilename, Buffer.from(pdf, 'base64'));
# ```
#
# In Python:
#
# ```python
# Path('verified-qr.png').write_bytes(base64.b64decode(verified_qr))
# Path(filename).write_bytes(base64.b64decode(pdf))
# ```
#
# Error (`400` / `401` / `402` / `429` / `500`):
#
# ```json
# {
#   "success": false,
#   "message": "Human-readable error"
# }
# ```
#
# ---
#
# ## 3. Check remaining points (optional)
#
# ```
# GET /api/v1/balance
# x-api-key: YOUR_KEY
# ```
#
# Success (`200`):
#
# ```json
# {
#   "success": true,
#   "username": "your-username",
#   "email": "you@example.com",
#   "points": 496,
#   "status": "active"
# }
# ```
#
# | `status` | Meaning |
# |---|---|
# | `active` | More than 10 points. |
# | `low` | 1–10 points. |
# | `depleted` | 0 points. Further send and verify calls return `402`. |
#
# ---
#
# ## Billing
#
# - Send OTP: **free** (still requires at least 1 point on the account)
# - Successful verify: **1 point**
# - Failed verify (wrong OTP, expired session, validation error): **no charge**
#
# ---
#
# ## Node.js (Axios)
#
# ```javascript
# const fs = require('fs');
# const axios = require('axios');
#
# const BASE_URL = 'https://otp.affiliate.pro.et/api/v1';
# const API_KEY = process.env.FAYDA_API_KEY;
#
# function faydaHeaders() {
#   return {
#     'Content-Type': 'application/json',
#     'x-api-key': API_KEY,
#   };
# }
#
# async function sendVerifiedQr(fanNumber, finNumber) {
#   const res = await axios.post(
#     `${BASE_URL}/send-otp-verified-qr`,
#     { fanNumber, finNumber },
#     { headers: faydaHeaders(), timeout: 60000 }
#   );
#   return res.data; // { session, phone, otpMethod }
# }
#
# async function verifyVerifiedQr({ otp, fanNumber, finNumber, session }) {
#   const res = await axios.post(
#     `${BASE_URL}/verify-otp-verified-qr`,
#     { otp, fanNumber, finNumber, session },
#     { headers: faydaHeaders(), timeout: 120000 }
#   );
#
#   const { remainingPoints, data, verifiedQr, pdf, pdfFilename } = res.data;
#   if (verifiedQr) {
#     fs.writeFileSync('verified-qr.png', Buffer.from(verifiedQr, 'base64'));
#   }
#   fs.writeFileSync(pdfFilename || 'fayda.pdf', Buffer.from(pdf, 'base64'));
#   return { remainingPoints, data, pdfFilename };
# }
# ```
#
# ---
#
# ## Python (requests)
#
# ```python
# import base64
# import os
# from pathlib import Path
#
# import requests
#
# BASE_URL = "https://otp.affiliate.pro.et/api/v1"
# API_KEY = os.environ["FAYDA_API_KEY"]
# HEADERS = {"x-api-key": API_KEY, "Content-Type": "application/json"}
#
#
# def send_verified_qr(fan_number, fin_number):
#     res = requests.post(
#         f"{BASE_URL}/send-otp-verified-qr",
#         json={"fanNumber": fan_number, "finNumber": fin_number},
#         headers=HEADERS,
#         timeout=60,
#     )
#     res.raise_for_status()
#     body = res.json()
#     return body["session"], body["phone"]
#
#
# def verify_verified_qr(otp, fan_number, fin_number, session):
#     res = requests.post(
#         f"{BASE_URL}/verify-otp-verified-qr",
#         json={
#             "otp": otp,
#             "fanNumber": fan_number,
#             "finNumber": fin_number,
#             "session": session,
#         },
#         headers=HEADERS,
#         timeout=120,
#     )
#     res.raise_for_status()
#     body = res.json()
#     if body.get("verifiedQr"):
#         Path("verified-qr.png").write_bytes(base64.b64decode(body["verifiedQr"]))
#     filename = body.get("pdfFilename") or "fayda.pdf"
#     Path(filename).write_bytes(base64.b64decode(body["pdf"]))
#     return {
#         "remaining_points": body["remainingPoints"],
#         "data": body["data"],
#         "pdf_filename": filename,
#     }
# ```
#
# ---
#
# ## Checklist
#
# 1. Call `/send-otp-verified-qr` and `/verify-otp-verified-qr` only.
# 2. Send **FAN and FIN on both steps**.
# 3. Parse the verify body as JSON.
# 4. Read identity from `data`.
# 5. Decode `verifiedQr` as a PNG and `pdf` as a PDF.
# 6. Read remaining points from `remainingPoints` (also in `X-Remaining-Points`).
# 7. Keep `session` per request and send it back unchanged.
# 8. Allow about 60–120 seconds timeout on verify.
# 9. Keep the API key on the server only.
#
# ---
#
# ## Common errors
#
# | Message / status | Meaning |
# |---|---|
# | `401` Invalid API key | Wrong or missing `x-api-key`. |
# | `402` Insufficient points | Recharge the API account. |
# | `400` `fanNumber is required` / must be 16 digits | Missing or malformed FAN. |
# | `400` `finNumber is required` / must be 12 digits | Missing or malformed FIN. |
# | `400` `otp is required` / must be 6 digits | Missing or malformed OTP. |
# | `400` `session is required` | Session missing. |
# | `400` Incorrect OTP. Please try again. | Wrong code. |
# | `400` OTP session expired. Please request a new OTP. | Session timed out. Call send again. |
# | `429` Too many requests | Slow down and retry later. Limit is 60 requests per minute. |
# | `Could not send OTP. Please try again.` | Send failed. Retry send. |
# | `Could not verify OTP. Please try again.` | Verify failed. You may need a new OTP. |
# | Timeout | Increase the client timeout on verify. |

# ============================================================
# RUNNABLE TELEGRAM BOT CODE
# ============================================================
import base64
import io
import re
import time

import requests
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Keep these secrets private. Never send them in chat or publish this file.
BOT_TOKEN='8883142822:AAF6raw8CDotC403sP_OGH6pUxkPU0sRBRc'
FAYDA_API_KEY='fayda_303de9ba851cef11142d68c9dfed16375cffb294574f6dcb'

BASE_URL = "https://otp.affiliate.pro.et/api/v1"
bot = telebot.TeleBot(BOT_TOKEN)

# Temporary in-memory state only. It is cleared if the program stops.
sessions = {}
last_request_time = {}


def api_headers():
    return {
        "x-api-key": FAYDA_API_KEY,
        "Content-Type": "application/json",
    }


def private_chat_only(message):
    return message.chat.type == "private"


def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🪪 Verify Digital ID"))
    keyboard.add(KeyboardButton("❌ Cancel"))
    return keyboard


def safe_api_error(response):
    try:
        body = response.json()
        return body.get("message", "The verification service returned an error.")
    except (ValueError, AttributeError):
        return "The verification service returned an unexpected response."


@bot.message_handler(commands=["start"])
def start(message):
    if not private_chat_only(message):
        bot.reply_to(message, "For privacy, please use this bot in a private chat.")
        return

    bot.send_message(
        message.chat.id,
        "🪪 Digital ID Verification Bot\n\n"
        "This bot connects to the authorized Verified QR service.\n"
        "Your FAN, FIN, and OTP will be sent to that service to verify your ID. "
        "Only continue if you consent and are authorized to use this service.\n\n"
        "For your privacy, use this bot only in a private chat. "
        "Do not send your details to anyone else.\n\n"
        "Tap Verify Digital ID to begin.",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(func=lambda m: (m.text or "").strip() in {"❌ Cancel", "Cancel"})
def cancel(message):
    sessions.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        "Cancelled. Temporary verification details were cleared from the bot's memory.",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(func=lambda m: (m.text or "").strip() in {"🪪 Verify Digital ID", "Verify Digital ID"})
def begin(message):
    if not private_chat_only(message):
        bot.reply_to(message, "For privacy, please use this bot in a private chat.")
        return

    sessions[message.from_user.id] = {"step": "fan"}
    bot.send_message(
        message.chat.id,
        "Before continuing, confirm that you have permission to verify this ID "
        "and agree to send the details to the Verified QR service.\n\n"
        "Enter the 16-digit FAN. Do not include spaces.",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    if not private_chat_only(message):
        return

    user_id = message.from_user.id
    state = sessions.get(user_id)

    if not state:
        bot.send_message(
            message.chat.id,
            "Tap 🪪 Verify Digital ID to start.",
            reply_markup=main_keyboard(),
        )
        return

    text = (message.text or "").strip()

    if state["step"] == "fan":
        fan = re.sub(r"\s+", "", text)
        if not re.fullmatch(r"\d{16}", fan):
            bot.reply_to(message, "FAN must contain exactly 16 digits. Please try again.")
            return
        state["fan"] = fan
        state["step"] = "fin"
        bot.send_message(message.chat.id, "Now enter the 12-digit FIN.")
        return

    if state["step"] == "fin":
        fin = re.sub(r"\s+", "", text)
        if not re.fullmatch(r"\d{12}", fin):
            bot.reply_to(message, "FIN must contain exactly 12 digits. Please try again.")
            return

        state["fin"] = fin
        state["step"] = "sending"
        bot.send_message(
            message.chat.id,
            "Requesting an OTP from the registered phone. Please wait...",
        )

        try:
            response = requests.post(
                f"{BASE_URL}/send-otp-verified-qr",
                json={"fanNumber": state["fan"], "finNumber": state["fin"]},
                headers=api_headers(),
                timeout=60,
            )
            if response.status_code != 200:
                sessions.pop(user_id, None)
                bot.send_message(
                    message.chat.id,
                    "Could not send OTP: " + safe_api_error(response)
                    + "\nPlease try again later with /start.",
                    reply_markup=main_keyboard(),
                )
                return

            result = response.json()
            state["session"] = result["session"]
            state["step"] = "otp"
            masked_phone = result.get("phone", "your registered phone")
            bot.send_message(
                message.chat.id,
                f"OTP sent to {masked_phone}.\n\n"
                "Enter the 6-digit OTP you received. Never share this code with anyone.",
            )
        except requests.RequestException:
            sessions.pop(user_id, None)
            bot.send_message(
                message.chat.id,
                "The verification service could not be reached. Please try again later.",
                reply_markup=main_keyboard(),
            )
        except (ValueError, KeyError):
            sessions.pop(user_id, None)
            bot.send_message(
                message.chat.id,
                "The service response was incomplete. Please try again later.",
                reply_markup=main_keyboard(),
            )
        return

    if state["step"] == "otp":
        otp = re.sub(r"\s+", "", text)
        if not re.fullmatch(r"\d{6}", otp):
            bot.reply_to(message, "OTP must contain exactly 6 digits. Please try again.")
            return

        state["step"] = "verifying"
        bot.send_message(
            message.chat.id,
            "Verifying OTP. This may take up to 120 seconds; please wait...",
        )

        try:
            response = requests.post(
                f"{BASE_URL}/verify-otp-verified-qr",
                json={
                    "otp": otp,
                    "fanNumber": state["fan"],
                    "finNumber": state["fin"],
                    "session": state["session"],
                },
                headers=api_headers(),
                timeout=120,
            )

            if response.status_code != 200:
                sessions.pop(user_id, None)
                bot.send_message(
                    message.chat.id,
                    "Verification failed: " + safe_api_error(response)
                    + "\nPlease start again with /start if you need a new OTP.",
                    reply_markup=main_keyboard(),
                )
                return

            result = response.json()
            if not result.get("success", False):
                sessions.pop(user_id, None)
                bot.send_message(
                    message.chat.id,
                    "Verification was not successful. Please try again later.",
                    reply_markup=main_keyboard(),
                )
                return

            verified_qr = result.get("verifiedQr")
            pdf_b64 = result.get("pdf")
            remaining = result.get("remainingPoints")

            # Do not send the full identity profile back as chat text.
            if verified_qr:
                qr_bytes = base64.b64decode(verified_qr)
                bot.send_photo(
                    message.chat.id,
                    io.BytesIO(qr_bytes),
                    caption="Verified QR result. Keep it private.",
                )

            if pdf_b64:
                pdf_bytes = base64.b64decode(pdf_b64)
                pdf_name = result.get("pdfFilename") or "verified-id.pdf"
                # Avoid trusting a server-provided path as a filesystem path.
                pdf_name = pdf_name.replace("/", "_").replace("\\", "_")
                bot.send_document(
                    message.chat.id,
                    (pdf_name, io.BytesIO(pdf_bytes)),
                    caption="Verified ID PDF. This contains sensitive personal information; do not forward it without permission.",
                )

            message_text = "Verification successful."
            if remaining is not None:
                message_text += f"\nService points remaining: {remaining}"
            if not verified_qr and not pdf_b64:
                message_text += "\nThe service did not return a QR image or PDF."
            bot.send_message(
                message.chat.id,
                message_text,
                reply_markup=main_keyboard(),
            )

        except requests.Timeout:
            bot.send_message(
                message.chat.id,
                "Verification timed out. Check the service before retrying, as the request may have completed.",
                reply_markup=main_keyboard(),
            )
        except requests.RequestException:
            bot.send_message(
                message.chat.id,
                "The verification service could not be reached. Please try again later.",
                reply_markup=main_keyboard(),
            )
        except (ValueError, KeyError, TypeError):
            bot.send_message(
                message.chat.id,
                "The service returned an unexpected result. Please contact the service administrator.",
                reply_markup=main_keyboard(),
            )
        finally:
            # Do not keep FAN, FIN, or the OTP session in memory after verification.
            sessions.pop(user_id, None)
        return

    bot.send_message(message.chat.id, "Please wait or tap /start to begin again.")


if __name__ == "__main__":
    if "PASTE_TELEGRAM_BOT_TOKEN_HERE" in BOT_TOKEN:
        raise SystemExit("Set BOT_TOKEN in bot.py before running.")
    if "PASTE_FAYDA_API_KEY_HERE" in FAYDA_API_KEY:
        raise SystemExit("Set FAYDA_API_KEY in bot.py before running.")
    print("Digital ID Verification Bot is running...")
    print("Open Telegram, send /start, then tap Verify Digital ID.")
    try:
        bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
    except Exception as exc:
        # Print diagnostic details to the local Pydroid console only.
        # Never print BOT_TOKEN or FAYDA_API_KEY.
        print(f"Bot stopped with error: {type(exc).__name__}: {exc}")
        raise
