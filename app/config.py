import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def env(key, default=None):
    v = os.getenv(key)
    return v if v not in (None, "") else default


BASE_URL = env("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")

# Channel: "telegram" (demo channel), "sim" = built-in web chat only, "twilio" = WhatsApp via Twilio
CHANNEL = env("CHANNEL", "sim")
TELEGRAM_TOKEN = env("TELEGRAM_TOKEN")
TELEGRAM_WEBHOOK_SECRET = env("TELEGRAM_WEBHOOK_SECRET", "change-me-to-a-random-string")
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", "YourBot")  # without @
TWILIO_SID = env("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = env("TWILIO_AUTH_TOKEN")
TWILIO_FROM = env("TWILIO_WHATSAPP_FROM", "+14155238886")  # Twilio sandbox number

# LLM
MOCK_LLM = env("MOCK_LLM", "1") == "1"
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
LLM_MODEL = env("LLM_MODEL", "claude-sonnet-5-5")
AGENT_BACKEND = env("AGENT_BACKEND", "agenticorg")  # "agenticorg" (default) or "llm"
AGENTICORG_URL = env("AGENTICORG_URL")
AGENTICORG_API_KEY = env("AGENTICORG_API_KEY")
AGENTICORG_COMPANY_ID = env("AGENTICORG_COMPANY_ID")  # required by the SDK when running agents by type

# Payments
PINELABS_MODE = env("PINELABS_MODE", "stub")  # "stub" (fake test page) | "upi" (real GPay/UPI QR, self-confirmed) | "live" (Pine Labs API)
PRICE_RS = int(env("PRICE_RS", "49"))
PINELABS_BASE_URL = env("PINELABS_BASE_URL", "https://pluraluat.v2.pinepg.in")  # UAT default; swap for prod when Pine Labs gives it
PINELABS_CLIENT_ID = env("PINELABS_CLIENT_ID")
PINELABS_CLIENT_SECRET = env("PINELABS_CLIENT_SECRET")
PINELABS_WEBHOOK_SECRET = env("PINELABS_WEBHOOK_SECRET")  # set once Pine Labs confirms their signature scheme — see payments.py

# UPI QR payment (PINELABS_MODE=upi) — a real upi://pay deep link any UPI
# app (GPay, PhonePe, Paytm...) can scan/open. No gateway, so "paid" is
# self-confirmed by tapping "I've paid" in chat, same as every other mode.
UPI_VPA = env("UPI_VPA")            # your UPI ID, e.g. yourname@okaxis
UPI_PAYEE_NAME = env("UPI_PAYEE_NAME", "Sign Smart")

# Voice
ELEVENLABS_API_KEY = env("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = env("ELEVENLABS_VOICE_ID")
ELEVENLABS_MODEL = env("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# Follow-up reminder delay (short for the demo)
REMINDER_SECONDS = int(env("REMINDER_SECONDS", "120"))
MAX_ROUNDS = int(env("MAX_ROUNDS", "2"))

DATA_DIR = Path(env("DATA_DIR", "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
MEDIA_DIR = DATA_DIR / "media"
for d in (DATA_DIR, UPLOAD_DIR, MEDIA_DIR):
    d.mkdir(parents=True, exist_ok=True)