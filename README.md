# Sedoo Verified QR

Standalone Telegram bot for the **Fayda Verified QR 2** two-OTP flow only.

## Security and privacy
- Use this only for a person's own Fayda ID with their informed consent.
- The bot sends the QR and PDF only to the Telegram account that started the request.
- Do not ask users to send FANs or OTPs to an administrator.
- Do not add logging of message bodies or API payloads.
- API key is read from the server environment and must never be committed to GitHub.
- This starter stores FAN and the short-lived API session in SQLite while a verification is active. It clears them after success/failure/cancel. Use a protected persistent disk or managed database for deployment; restrict access to the database file.
- The service fee of 15 ETB is separate from the provider's 1-point charge on successful final verification.
- Payment approval is manual in this starter. It does not claim to integrate with a payment gateway.

## Required environment variables
- `BOT_TOKEN`: Telegram bot token
- `FAYDA_API_KEY`: provider API key
- `ADMIN_ID`: your Telegram numeric user ID
- `PAYMENT_INSTRUCTIONS`: optional payment instructions shown to users
- `DB_PATH`: optional SQLite path

Never paste tokens, API keys, FANs, or OTPs into public chats or GitHub.

## Run locally
```bash
python -m venv .venv
# activate the environment
pip install -r requirements.txt
export BOT_TOKEN="..."
export FAYDA_API_KEY="..."
export ADMIN_ID="123456789"
export PAYMENT_INSTRUCTIONS="Payment instructions..."
python bot.py
```

## Admin payment approval
After the user sends a receipt/reference, the bot forwards that proof to the configured admin account and sends the user's Telegram ID. The admin approves using:
```text
/approve 123456789
```
Only the configured `ADMIN_ID` can approve.

## Render deployment
Create a **Background Worker** from your GitHub repository:
- Build command: `pip install -r requirements.txt`
- Start command: `python bot.py`
- Add the environment variables above in Render's Environment settings.
- Attach persistent storage and set `DB_PATH` to a file on that disk if your Render plan supports it. Without persistent storage, bot state may be lost after a restart.

## API endpoints used
- `POST /send-otp-verified-qr2`
- `POST /verify-otp-verified-qr2`
- `POST /verify-otp-verified-qr2-final`

The API key is sent in the `x-api-key` header. The bot does not call the one-OTP Verified QR endpoints.

## Important API response note
The integration guide supplied for this project identifies `verifiedQr` and a PDF base64 value, but the exact PDF response property name may differ. This starter checks `pdf` and `verifiedQrPdf`. If your provider uses another exact property name, update the `pdf_value = ...` line in `bot.py` to match the official response schema. Test with a non-production/sandbox account if available before accepting payments.
