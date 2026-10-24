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


# ---------------- Payments (Pine Labs) ----------------

@app.post("/payments/webhook")
async def payments_webhook(request: Request):
    token = payments.verify_webhook(await request.body(), dict(request.headers))
    if token:
        _mark_paid(token)
    return {"ok": True}


def _mark_paid(token):
    s = db.find_by_token(token)
    if not s:
        return False
    with db.phone_lock(s["phone"]):
        s = db.get(s["phone"])
        states.on_paid(s)
        db.save(s)
    return True


@app.get("/pay/{token}", response_class=HTMLResponse)
def stub_pay_page(token: str):
    if config.PINELABS_MODE != "stub" or not db.find_by_token(token):
        return HTMLResponse("Not found", status_code=404)
    return f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Test payment</title></head><body style="font-family:system-ui;max-width:420px;margin:40px auto;padding:16px">
<p style="background:#FDEBD3;padding:12px;border-radius:8px"><b>TEST MODE.</b> No real money moves.
Replace with the Pine Labs checkout (PINELABS_MODE=live).</p>
<h2>Sign Smart full pack</h2><p>Amount: <b>₹{config.PRICE_RS}</b></p>
<form method="post" action="/pay/{html.escape(token)}/confirm">
<button style="width:100%;height:52px;font-size:18px;border-radius:12px;border:0;background:#F08A24">Pay ₹{config.PRICE_RS} (test)</button>
</form></body></html>"""


@app.post("/pay/{token}/confirm", response_class=HTMLResponse)
def stub_pay_confirm(token: str):
    if config.PINELABS_MODE != "stub":
        return HTMLResponse("Not found", status_code=404)
    ok = _mark_paid(token)
    return "<p style='font-family:system-ui;padding:24px'>Payment done ✅ Go back to the chat.</p>" if ok else "Not found"


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