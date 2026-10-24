"""Sending and receiving messages.
  "tg:<chat_id>" -> Telegram bot (numbered menu lines become tap buttons)
  "web:<id>"     -> built-in web chat (/chat)
  "+91..."       -> WhatsApp via Twilio (only if CHANNEL=twilio)
"""
import re
import secrets
import threading
import time
from collections import defaultdict

import httpx

from . import config

OUTBOX = defaultdict(list)
_out_lock = threading.Lock()
MENU_LINE = re.compile(r"^(\d{1,2}) (.{1,60})$")
URL = re.compile(r"(https?://\S+)")


def _split(body, limit=1500):
    if len(body) <= limit:
        return [body]
    parts, cur = [], ""
    for line in body.split("\n"):
        if len(cur) + len(line) + 1 > limit and cur:
            parts.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        parts.append(cur)
    return parts


def record(to, body, media_url=None, sender="bot"):
    with _out_lock:
        OUTBOX[to].append({"from": sender, "body": body, "media": media_url, "ts": time.time()})


def send(to, body, media_url=None, status_callback=None, menu=True):
    """Returns a message id, or None if sending failed (never raises).
    menu=False sends text exactly as is (e.g. a message the user will forward)."""
    if to.startswith("tg:"):
        return _send_telegram(to[3:], body, media_url, menu)
    if config.CHANNEL == "sim" or to.startswith("web:"):
        record(to, body, media_url)
        return "sim-" + secrets.token_hex(4)
    return _send_twilio(to, body, media_url, status_callback)


# ---------------- Telegram ----------------

def tg(method, **payload):
    r = httpx.post(f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/{method}", json=payload, timeout=60)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {data}")
    return data["result"]


def _to_buttons(body):
    """Turn lines like '1 Yes' into tap buttons."""
    keep, rows = [], []
    for line in body.split("\n"):
        m = MENU_LINE.match(line.strip())
        if m:
            rows.append([{"text": m.group(2), "callback_data": m.group(1)}])
        else:
            keep.append(line)
    if "I ACCEPT" in body:
        rows.append([{"text": "✅ I ACCEPT", "callback_data": "I ACCEPT"}])
    for url in URL.findall(body):
        if "/d/" in url:
            rows.insert(0, [{"text": "📊 Open risk dashboard", "url": url}])
        elif "/pay/" in url or "pinelabs" in url.lower():
            rows.insert(0, [{"text": f"💳 Pay ₹{config.PRICE_RS}", "url": url}])
    text = "\n".join(keep).strip() or "Choose:"
    return text, ({"inline_keyboard": rows} if rows else None)


def _md(text):
    """WhatsApp-style *bold* -> Telegram HTML <b>, escaping the rest."""
    t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*([^*\n]+)\*", r"<b>\1</b>", t)
    return re.sub(r"(?<![\w/])_([^_\n]+)_(?![\w/])", r"<i>\1</i>", t)


def _send_telegram(chat_id, body, media_url, menu):
    try:
        text, keyboard = _to_buttons(body) if menu else (body, None)
        if media_url:
            # Check if file exists on disk to upload bytes directly
            filename = media_url.split("/")[-1]
            local_path = config.MEDIA_DIR / filename
            if local_path.exists():
                try:
                    with open(local_path, "rb") as f:
                        files = {"audio": (filename, f.read(), "audio/mp4")}
                        data = {"chat_id": chat_id, "caption": _md(text)[:1000], "parse_mode": "HTML"}
                        r = httpx.post(f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendAudio", data=data, files=files, timeout=60)
                        if r.json().get("ok"):
                            return str(r.json()["result"]["message_id"])
                except Exception as ex:
                    print(f"[telegram direct audio upload fallback] {ex}")

            # Fallback to URL method
            res = tg("sendAudio", chat_id=chat_id, audio=media_url, caption=_md(text)[:1000], parse_mode="HTML")
            return str(res["message_id"])
        mid = None
        chunks = _split(text, 3500)
        for i, chunk in enumerate(chunks):
            payload = {"chat_id": chat_id, "text": _md(chunk) if menu else chunk}
            if menu:
                payload["parse_mode"] = "HTML"
            if keyboard and i == len(chunks) - 1:
                payload["reply_markup"] = keyboard
            mid = str(tg("sendMessage", **payload)["message_id"])
        return mid
    except Exception as e:
        print(f"[telegram send failed to {chat_id}] {e}")
        return None


def tg_download(file_id, mime=None):
    info = tg("getFile", file_id=file_id)
    r = httpx.get(f"https://api.telegram.org/file/bot{config.TELEGRAM_TOKEN}/{info['file_path']}", timeout=60)
    r.raise_for_status()
    if not mime:
        path = info["file_path"].lower()
        mime = "application/pdf" if path.endswith(".pdf") else "image/png" if path.endswith(".png") else "image/jpeg"
    return r.content, mime


# ---------------- WhatsApp (Twilio) ----------------

def _send_twilio(to, body, media_url, status_callback):
    sid = None
    try:
        chunks = _split(body)
        for i, chunk in enumerate(chunks):
            data = {"From": f"whatsapp:{config.TWILIO_FROM}", "To": f"whatsapp:{to}", "Body": chunk}
            if media_url and i == len(chunks) - 1:
                data["MediaUrl"] = media_url
            if status_callback:
                data["StatusCallback"] = status_callback
            r = httpx.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_SID}/Messages.json",
                data=data, auth=(config.TWILIO_SID, config.TWILIO_TOKEN), timeout=30,
            )
            r.raise_for_status()
            sid = r.json()["sid"]
    except Exception as e:
        print(f"[send failed to {to}] {e}")
    return sid


def download(url):
    """Download media a user sent on WhatsApp (Twilio needs basic auth)."""
    r = httpx.get(url, auth=(config.TWILIO_SID, config.TWILIO_TOKEN), follow_redirects=True, timeout=60)
    r.raise_for_status()
    return r.content, r.headers.get("content-type", "application/octet-stream").split(";")[0]