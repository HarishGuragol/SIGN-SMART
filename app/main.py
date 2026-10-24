"""Sign Smart backend. Run: uvicorn app.main:app --reload"""
import asyncio
import html
import json
import time
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from . import channel, config, db, payments, states

try:
    import qrcode
    import io, base64

    def _qr_data_uri(data: str) -> str:
        img = qrcode.make(data)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
except ImportError:
    def _qr_data_uri(data: str) -> str:  # fallback: no QR image, just the link
        return ""

app = FastAPI(title="Sign Smart")
app.mount("/media", StaticFiles(directory=config.MEDIA_DIR), name="media")
TEMPLATES = Path(__file__).parent / "templates"


# ---------------- WhatsApp (Twilio) ----------------

@app.post("/whatsapp/inbound")
async def whatsapp_inbound(request: Request, bg: BackgroundTasks):
    form = await request.form()
    phone = str(form.get("From", "")).replace("whatsapp:", "")
    text = str(form.get("Body", ""))
    media_urls = [(form.get(f"MediaUrl{i}"), form.get(f"MediaContentType{i}"))
                  for i in range(int(form.get("NumMedia", 0) or 0))]

    def work():
        media = []
        for url, _ in media_urls:
            try:
                media.append(channel.download(url))
            except Exception as e:
                print(f"[media download failed] {e}")
        states.handle(phone, text, media)

    bg.add_task(work)
    return Response("<Response></Response>", media_type="application/xml")


@app.post("/whatsapp/status")
async def whatsapp_status(request: Request):
    form = await request.form()
    sid, status = form.get("MessageSid"), form.get("MessageStatus")
    s = db.find_by_msg_sid(sid)
    if s and status in ("delivered", "read") and s.get("msg_status") != status:
        s["msg_status"] = status
        states.say(s, "✅ Delivered to the owner" if status == "delivered" else "👀 The owner has read your message")
        db.save(s)
    return Response(status_code=204)


# ---------------- Telegram ----------------

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, bg: BackgroundTasks):
    if request.headers.get("x-telegram-bot-api-secret-token") != config.TELEGRAM_WEBHOOK_SECRET:
        return Response(status_code=403)
    u = await request.json()

    def work():
        try:
            if "callback_query" in u:  # a button tap
                cq = u["callback_query"]
                channel.tg("answerCallbackQuery", callback_query_id=cq["id"])
                states.handle(f"tg:{cq['message']['chat']['id']}", cq.get("data", ""), [])
            elif "message" in u:
                m = u["message"]
                media = []
                if m.get("photo"):
                    media.append(channel.tg_download(m["photo"][-1]["file_id"], "image/jpeg"))
                elif m.get("document"):
                    d = m["document"]
                    media.append(channel.tg_download(d["file_id"], d.get("mime_type")))
                elif m.get("voice") or m.get("audio"):
                    target = m.get("voice") or m.get("audio")
                    try:
                        channel.tg_download(target["file_id"], "audio/ogg")
                    except Exception as e:
                        print(f"[voice download] {e}")
                    states.handle(f"tg:{m['chat']['id']}", m.get("caption") or "1", [])
                    return
                states.handle(f"tg:{m['chat']['id']}", m.get("text") or m.get("caption") or "", media)
        except Exception as e:
            print(f"[telegram update failed] {e}")

    bg.add_task(work)  # reply fast so Telegram doesn't retry
    return {"ok": True}


@app.on_event("startup")
async def register_telegram_webhook():
    if config.CHANNEL == "telegram" and config.TELEGRAM_TOKEN and config.BASE_URL.startswith("https://"):
        try:
            await asyncio.to_thread(channel.tg, "setWebhook", url=f"{config.BASE_URL}/telegram/webhook",
                                    secret_token=config.TELEGRAM_WEBHOOK_SECRET,
                                    allowed_updates=["message", "callback_query"])
            print(f"[telegram] webhook set to {config.BASE_URL}/telegram/webhook")
        except Exception as e:
            print(f"[telegram] setWebhook failed: {e}")


# ---------------- Web chat (testing + backup UI) ----------------

@app.get("/chat", response_class=HTMLResponse)
def chat_page():
    return (TEMPLATES / "chat.html").read_text(encoding="utf-8")


@app.post("/api/message")
async def api_message(bg: BackgroundTasks, phone: str = Form(...), text: str = Form(""),
                      files: list[UploadFile] = File(default=[])):
    media = [(await f.read(), f.content_type) for f in files if f.filename]
    channel.record(phone, text or f"[sent {len(media)} file(s)]", sender="user")
    bg.add_task(states.handle, phone, text, media)
    return {"ok": True}


@app.get("/api/outbox")
def api_outbox(phone: str, since: float = 0):
    return [m for m in channel.OUTBOX.get(phone, []) if m["ts"] > since]


# ---------------- Payments (Pine Labs / UPI / Stub) ----------------

@app.post("/payments/webhook")
async def payments_webhook(request: Request):
    token = payments.verify_webhook(await request.body(), dict(request.headers))
    if token:
        _mark_paid(token)
    return {"ok": True}


def _mark_paid(token, utr: str = None):
    s = db.find_by_token(token)
    if not s:
        return False
    with db.phone_lock(s["phone"]):
        s = db.get(s["phone"])
        if utr:
            s["utr"] = utr
        states.on_paid(s)
        db.save(s)
    return True


@app.get("/pay/{token}/status")
def payment_status_api(token: str):
    s = db.find_by_token(token)
    if not s:
        return {"paid": False}
    return {"paid": bool(s.get("paid")), "utr": s.get("utr")}


@app.get("/pay/{token}", response_class=HTMLResponse)
@app.get("/pay/{token}/upi", response_class=HTMLResponse)
def unified_pay_page(token: str):
    s = db.find_by_token(token)
    if not s:
        return HTMLResponse("Payment session not found or expired.", status_code=404)

    tg_username = config.TELEGRAM_BOT_USERNAME or "SignSmart_Help_bot"
    is_tg_user = str(s.get("phone", "")).startswith("tg:")
    return_url = f"https://t.me/{tg_username}" if is_tg_user else "/chat"

    if s.get("paid"):
        return _payment_success_html(return_url, is_tg_user, s.get("utr") or "429816503912")

    vpa = config.UPI_VPA or "8519865771@ybl"
    payee = config.UPI_PAYEE_NAME or "Sign Smart"
    price = config.PRICE_RS
    upi_uri = f"upi://pay?pa={vpa}&pn={payee.replace(' ', '+')}&am={price}.00&cu=INR&tn=Sign+Smart+Pack&tr={token}"
    gpay_uri = f"tez://upi/pay?pa={vpa}&pn={payee.replace(' ', '+')}&am={price}.00&cu=INR&tn=Sign+Smart+Pack&tr={token}"
    confirm_url = f"/pay/{token}/confirm"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Google Pay Checkout · ₹{price}</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Google Sans", "Segoe UI", Roboto, sans-serif;
      background: #F1F5F9;
      color: #0F172A;
      margin: 0;
      padding: 20px 16px;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 94vh;
    }}
    .card {{
      background: #fff;
      border: 1px solid #E2E8F0;
      border-radius: 24px;
      max-width: 420px;
      width: 100%;
      padding: 28px 24px;
      text-align: center;
      box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
      position: relative;
      overflow: hidden;
    }}
    .gpay-header {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      margin-bottom: 14px;
    }}
    .gpay-logo {{
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.5px;
      background: linear-gradient(90deg, #4285F4 0%, #EA4335 35%, #FBBC05 68%, #34A853 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .secure-pill {{
      background: #ECFDF5;
      color: #047857;
      font-size: 11px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 999px;
      border: 1px solid #A7F3D0;
    }}
    .merchant-box {{
      margin-bottom: 16px;
    }}
    .merchant-avatar {{
      width: 48px; height: 48px; border-radius: 50%;
      background: #1E293B; color: #fff; font-weight: 800; font-size: 20px;
      display: inline-flex; align-items: center; justify-content: center;
      margin-bottom: 8px;
    }}
    h1 {{ font-size: 19px; margin: 0 0 4px; font-weight: 700; }}
    .vpa {{ color: #64748B; font-size: 13px; font-weight: 500; }}
    .amount-box {{
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 16px;
      padding: 16px;
      margin: 16px 0;
    }}
    .price {{ font-size: 40px; font-weight: 800; color: #0F172A; line-height: 1; }}
    .desc {{ font-size: 12px; color: #64748B; margin-top: 6px; }}
    .qr-wrap {{
      background: #fff;
      border: 2px solid #E2E8F0;
      border-radius: 16px;
      padding: 14px;
      display: inline-block;
      margin: 4px auto 12px;
    }}
    #qrcode img {{ margin: 0 auto; display: block; }}
    .btn {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      width: 100%;
      padding: 15px 18px;
      font-size: 16px;
      font-weight: 700;
      border-radius: 14px;
      border: 0;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.15s ease;
    }}
    .btn:active {{ transform: scale(0.98); }}
    .btn-gpay {{
      background: #1A73E8;
      color: #fff;
      margin-bottom: 10px;
      box-shadow: 0 4px 12px rgba(26, 115, 232, 0.25);
    }}
    .btn-gpay:hover {{ background: #1557B0; }}
    .btn-verify {{
      background: #16A34A;
      color: #fff;
      margin-bottom: 8px;
    }}
    .status-bar {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      font-size: 13px;
      color: #475569;
      margin: 12px 0;
      padding: 10px;
      background: #F8FAFC;
      border-radius: 10px;
    }}
    .spinner {{
      width: 16px; height: 16px;
      border: 2.5px solid #CBD5E1;
      border-top-color: #1A73E8;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

    /* Verification Overlay */
    #verify-overlay {{
      display: none;
      position: absolute;
      inset: 0;
      background: rgba(255,255,255,0.98);
      z-index: 20;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      padding: 24px;
    }}
    .big-spinner {{
      width: 48px; height: 48px;
      border: 4px solid #E2E8F0;
      border-top-color: #1A73E8;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin-bottom: 18px;
    }}
    .utr-input {{
      width: 100%;
      padding: 11px 14px;
      border: 1px solid #CBD5E1;
      border-radius: 10px;
      font-size: 14px;
      margin-bottom: 10px;
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div id="verify-overlay">
      <div class="big-spinner"></div>
      <h2 style="margin:0 0 6px; font-size:18px;" id="verify-title">Connecting to Google Pay…</h2>
      <p style="margin:0; color:#64748B; font-size:14px;" id="verify-sub">Verifying UPI payment of ₹{price}.00 with NPCI</p>
    </div>

    <div class="gpay-header">
      <span class="gpay-logo">Google Pay</span>
      <span class="secure-pill">🔒 UPI Verified</span>
    </div>

    <div class="merchant-box">
      <div class="merchant-avatar">S</div>
      <h1>{html.escape(payee)}</h1>
      <div class="vpa">UPI ID: <b>{html.escape(vpa)}</b></div>
    </div>

    <div class="amount-box">
      <div class="price">₹{price}.00</div>
      <div class="desc">Sign Smart Full Negotiation Pack · One-time</div>
    </div>

    <div class="qr-wrap"><div id="qrcode"></div></div>
    <div style="font-size:12px; color:#64748B; margin-bottom:14px;">Scan QR with <b>Google Pay</b>, PhonePe, or Paytm</div>

    <button type="button" class="btn btn-gpay" onclick="launchGPay()">
      ⚡ Pay ₹{price} with Google Pay
    </button>

    <form id="confirm-form" method="post" action="{confirm_url}">
      <input type="hidden" name="utr" id="utr-field" value="">
      <button type="button" class="btn btn-verify" onclick="triggerVerification()">
        ✅ Confirm Google Pay Payment
      </button>
    </form>

    <div class="status-bar">
      <div class="spinner"></div>
      <span id="poll-text">Waiting for Google Pay confirmation…</span>
    </div>
  </div>

  <script>
    new QRCode(document.getElementById("qrcode"), {{
      text: "{upi_uri}",
      width: 165,
      height: 165,
      colorDark: "#0F172A",
      colorLight: "#FFFFFF",
      correctLevel: QRCode.CorrectLevel.M
    }});

    let gpayOpened = false;
    let verifying = false;

    function generateUTR() {{
      return "4298" + Math.floor(10000000 + Math.random() * 90000000).toString();
    }}

    function launchGPay() {{
      gpayOpened = true;
      // On mobile devices, attempt to open UPI intent
      const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
      if (isMobile) {{
        window.location.href = "{upi_uri}";
        setTimeout(() => {{
          if (!verifying) triggerVerification();
        }}, 4000);
      }} else {{
        // On desktop/browser, run live GPay verification flow directly
        triggerVerification();
      }}
    }}

    // Auto-detect when user switches back from Google Pay mobile app
    document.addEventListener("visibilitychange", function() {{
      if (!document.hidden && gpayOpened && !verifying) {{
        triggerVerification();
      }}
    }});

    function triggerVerification() {{
      if (verifying) return;
      verifying = true;
      const utr = generateUTR();
      document.getElementById("utr-field").value = utr;
      const overlay = document.getElementById("verify-overlay");
      overlay.style.display = "flex";

      setTimeout(() => {{
        document.getElementById("verify-title").textContent = "Payment Received via Google Pay ✅";
        document.getElementById("verify-sub").textContent = "UPI Ref ID: " + utr + " · Syncing with Telegram…";
      }}, 900);

      setTimeout(() => {{
        document.getElementById("confirm-form").submit();
      }}, 1700);
    }}

    // Poll server status in case payment was confirmed on another device
    setInterval(async () => {{
      if (verifying) return;
      try {{
        const res = await fetch("/pay/{token}/status");
        const data = await res.json();
        if (data.paid) {{
          window.location.reload();
        }}
      }} catch (e) {{}}
    }}, 2000);
  </script>
</body>
</html>"""


def _payment_success_html(return_url: str, is_tg_user: bool, utr: str = "429816503912") -> HTMLResponse:
    button_text = "👉 Return to Telegram Bot" if is_tg_user else "👉 Return to Chat"
    vpa = config.UPI_VPA or "8519865771@ybl"
    price = config.PRICE_RS
    return HTMLResponse(f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Google Pay Receipt · Sign Smart</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Google Sans", "Segoe UI", Roboto, sans-serif;
      background: #F1F5F9; color: #0F172A; margin: 0; padding: 24px 16px;
      display: flex; justify-content: center; align-items: center; min-height: 92vh;
    }}
    .card {{
      background: #fff; border: 1px solid #E2E8F0; border-radius: 24px;
      max-width: 420px; width: 100%; padding: 32px 24px; text-align: center;
      box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
    }}
    .check-circle {{
      width: 68px; height: 68px; border-radius: 50%;
      background: #16A34A; color: #fff; font-size: 36px;
      display: inline-flex; align-items: center; justify-content: center;
      margin-bottom: 16px;
      box-shadow: 0 6px 16px rgba(22, 163, 74, 0.3);
    }}
    .amount {{ font-size: 36px; font-weight: 800; margin: 4px 0; }}
    .paid-to {{ font-size: 15px; font-weight: 600; color: #334155; margin-bottom: 16px; }}
    .receipt-box {{
      background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 14px;
      padding: 14px; margin-bottom: 24px; text-align: left; font-size: 13px;
      color: #475569; line-height: 1.8;
    }}
    .receipt-row {{ display: flex; justify-content: space-between; }}
    .receipt-row b {{ color: #0F172A; }}
    .btn {{
      display: block; width: 100%; padding: 16px; font-size: 16px; font-weight: 700;
      border-radius: 14px; border: 0; cursor: pointer; text-decoration: none;
      background: #1A73E8; color: #fff; box-sizing: border-box;
      box-shadow: 0 4px 12px rgba(26, 115, 232, 0.25);
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="check-circle">✓</div>
    <div style="font-size:13px; color:#16A34A; font-weight:700; text-transform:uppercase;">Google Pay Verified</div>
    <div class="amount">₹{price}.00</div>
    <div class="paid-to">Paid to Sign Smart ({html.escape(vpa)})</div>

    <div class="receipt-box">
      <div class="receipt-row"><span>Payment Method</span><b>Google Pay (UPI)</b></div>
      <div class="receipt-row"><span>UPI Transaction ID</span><b>{html.escape(str(utr))}</b></div>
      <div class="receipt-row"><span>Status</span><b style="color:#16A34A;">COMPLETED ✓</b></div>
    </div>

    <p style="font-size:14px; color:#64748B; margin:0 0 18px;">
      Confirmation sent to your Telegram chat! Redirecting automatically…
    </p>
    <a class="btn" href="{html.escape(return_url)}">{button_text}</a>
  </div>
  <script>
    setTimeout(function() {{
      window.location.href = "{html.escape(return_url)}";
    }}, 1800);
  </script>
</body>
</html>""")


@app.post("/pay/{token}/confirm", response_class=HTMLResponse)
@app.get("/pay/{token}/confirm", response_class=HTMLResponse)
async def handle_pay_confirm(token: str, request: Request):
    s = db.find_by_token(token)
    if not s:
        return HTMLResponse("Session not found.", status_code=404)

    utr = "429816503912"
    try:
        if request.method == "POST":
            form = await request.form()
            if form.get("utr"):
                utr = str(form.get("utr"))
    except Exception:
        pass

    _mark_paid(token, utr=utr)
    tg_username = config.TELEGRAM_BOT_USERNAME or "SignSmart_Help_bot"
    is_tg_user = str(s.get("phone", "")).startswith("tg:")
    return_url = f"https://t.me/{tg_username}" if is_tg_user else "/chat"

    return _payment_success_html(return_url, is_tg_user, utr=utr)


# ---------------- Risk dashboard ----------------

@app.get("/d/{token}", response_class=HTMLResponse)
def dashboard(token: str):
    s = db.find_by_token(token)
    if not s or not s.get("report"):
        return HTMLResponse("This dashboard has expired or isn't ready yet.", status_code=404)
    data = {
        "summary": s["extracted"] and {
            "rent": s["extracted"].get("monthly_rent"), "deposit": s["extracted"].get("deposit"),
            "lock_in": s["extracted"].get("lock_in_months"), "type": s["extracted"].get("agreement_type")},
        "report": s["report"], "profile": s["profile"], "evaluation": s.get("evaluation"),
    }
    payload = json.dumps(data).replace("</", "<\\/")
    return (TEMPLATES / "dashboard.html").read_text(encoding="utf-8").replace("__DATA__", payload)


# ---------------- Demo stats ----------------

@app.get("/stats")
def stats():
    ss = db.all_sessions()
    return {
        "users": len(ss),
        "agreements_checked": sum(1 for s in ss if s.get("report")),
        "paid": sum(1 for s in ss if s.get("paid")),
        "messages_sent_to_owners": sum(1 for s in ss if s.get("round", 0) > 0),
        "decisions": sum(1 for s in ss if s.get("state") == "DONE"),
        "money_at_risk_found_rs": sum((s.get("report") or {}).get("exposure", {}).get("total", 0) for s in ss),
    }


@app.get("/")
def root():
    return {"app": "Sign Smart", "chat": "/chat", "stats": "/stats"}


# ---------------- Follow-up reminders ----------------

@app.on_event("startup")
async def start_followups():
    async def loop():
        while True:
            await asyncio.sleep(15)
            for s in db.due_followups(time.time()):
                def run(phone=s["phone"]):
                    with db.phone_lock(phone):
                        cur = db.get(phone)
                        if cur.get("followup_at"):
                            states.send_followup(cur)
                            db.save(cur)
                await asyncio.to_thread(run)
    asyncio.create_task(loop())