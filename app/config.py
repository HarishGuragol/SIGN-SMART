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

# ---------------- Communication Channels ----------------
# "telegram" = live Telegram bot, "sim" = built-in web chat, "twilio" = WhatsApp
CHANNEL = env("CHANNEL", "telegram")
TELEGRAM_TOKEN = env("TELEGRAM_TOKEN")
TELEGRAM_WEBHOOK_SECRET = env("TELEGRAM_WEBHOOK_SECRET", "change-me-to-a-random-string")
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", "SignSmart_Help_bot")

TWILIO_SID = env("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = env("TWILIO_AUTH_TOKEN")
TWILIO_FROM = env("TWILIO_WHATSAPP_FROM", "+14155238886")

# ---------------- AI Engine (Google Gemini) ----------------
MOCK_LLM = env("MOCK_LLM", "0") == "1"
AGENT_BACKEND = env("AGENT_BACKEND", "gemini")
GEMINI_API_KEY = env("GEMINI_API_KEY")
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_EMBED_MODEL = env("GEMINI_EMBED_MODEL", "gemini-embedding-001")

# ---------------- Payments & UPI ----------------
PINELABS_MODE = env("PINELABS_MODE", "upi")  # "upi" (real UPI QR/intent) | "stub" | "live"
PRICE_RS = int(env("PRICE_RS", "49"))
PINELABS_BASE_URL = env("PINELABS_BASE_URL", "https://pluraluat.v2.pinepg.in")
PINELABS_CLIENT_ID = env("PINELABS_CLIENT_ID")
PINELABS_CLIENT_SECRET = env("PINELABS_CLIENT_SECRET")
PINELABS_WEBHOOK_SECRET = env("PINELABS_WEBHOOK_SECRET")

UPI_VPA = env("UPI_VPA")
UPI_PAYEE_NAME = env("UPI_PAYEE_NAME", "Sign Smart")

# ---------------- Voice (ElevenLabs Multilingual) ----------------
ELEVENLABS_API_KEY = env("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = env("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
ELEVENLABS_MODEL = env("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# ---------------- Follow-up Reminders & Limits ----------------
REMINDER_SECONDS = int(env("REMINDER_SECONDS", "120"))
MAX_ROUNDS = int(env("MAX_ROUNDS", "2"))

# ---------------- Storage Paths ----------------
DATA_DIR = Path(env("DATA_DIR", "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
MEDIA_DIR = DATA_DIR / "media"
for d in (DATA_DIR, UPLOAD_DIR, MEDIA_DIR):
    d.mkdir(parents=True, exist_ok=True)
