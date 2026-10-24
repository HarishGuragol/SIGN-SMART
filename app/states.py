"""The conversation: one handler per state. Every bot message ends with numbered options."""
import os
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from . import agents, calc, channel, config, db, payments, voice

LANGS = {"1": "en", "2": "hi", "3": "kn"}
OWNER_WAIT_STATES = ("AWAIT_REPLY", "SELF_SENT", "TYPE_REPLY", "REVISED")
EXT = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}

WELCOME = (
    "Welcome to *Sign Smart* 👋\n"
    "I read agreements and tell you whether to sign, negotiate or walk away.\n\n"
    "Choose your language:\n1 English\n2 हिंदी\n3 ಕನ್ನಡ\n\n"
    "_Your document is used only for this check and deleted after. Guidance, not legal advice._"
)


# ---------------- helpers ----------------

def detect_file_type(data, ctype):
    ctype = (ctype or "").lower()
    if data.startswith(b"%PDF") or "pdf" in ctype:
        return "application/pdf"
    if data.startswith(b"\x89PNG") or "png" in ctype:
        return "image/png"
    if data.startswith(b"RIFF") and b"WEBP" in data[:16]:
        return "image/webp"
    return "image/jpeg"


def say(s, text, media_url=None, translate=True):
    body = agents.translate(text, s.get("lang", "en")) if translate else text
    return channel.send(s["phone"], body, media_url=media_url)


def save_files(s, media, key="files"):
    for data, ctype in media:
        if not data:
            continue
        valid_ctype = detect_file_type(data, ctype)
        ext = EXT.get(valid_ctype, "jpg")
        path = config.UPLOAD_DIR / f"{s['token']}_{key}_{len(s[key])}.{ext}"
        path.write_bytes(data)
        s[key].append([str(path), valid_ctype])


def delete_files(s):
    for path, _ in s.get("files", []) + s.get("revised_files", []):
        try:
            os.remove(path)
        except OSError:
            pass
    s["files"], s["revised_files"] = [], []


def normalize_phone(text):
    digits = re.sub(r"\D", "", text)
    if len(digits) == 10:
        return "+91" + digits
    if len(digits) == 12 and digits.startswith("91"):
        return "+" + digits
    return None


def dashboard_url(s):
    return f"{config.BASE_URL}/d/{s['token']}"


# ---------------- entry point ----------------

def handle(phone, text, media):
    """phone: user id ('tg:..', 'web:..' or '+91..'), text: str, media: list of (bytes, content_type)."""
    text = (text or "").strip()

    # Telegram deep link: the OWNER opened the invite (t.me/<bot>?start=deal_<token>)
    if text.startswith("/start deal_"):
        owner_join(phone, text.split("deal_", 1)[1].strip())
        return

    # Is this the OWNER replying to a message we sent?
    tenant = db.find_by_owner(phone, OWNER_WAIT_STATES)
    if tenant and not (db.exists(phone) and db.get(phone)["state"] not in ("START", "DONE")):
        with db.phone_lock(tenant["phone"]):
            tenant = db.get(tenant["phone"])
            handle_owner(tenant, phone, text, media)
            db.save(tenant)
        return

    with db.phone_lock(phone):
        s = db.get(phone)
        low = text.lower()

        # Handle clean restart commands
        if (low in ("/start", "menu", "restart", "reset") or (s.get("state") == "DONE" and low in ("hi", "hello", "start"))) and not media:
            delete_files(s)
            s = db.new_session(phone)
            channel.send(s["phone"], WELCOME)
            s["state"] = "LANG"
            db.save(s)
            return

        # While waiting for payment, "hi"/"continue" must never unlock the pack by themselves.
        # The backend verifies the payment and advances the flow.
        if s.get("state") == "AWAIT_PAYMENT" and low in (
                "hi", "hello", "hey", "start", "/continue", "continue", "next") and not media:
            verify_payment(s, explicit=False)
            db.save(s)
            return

        # /continue command to smoothly unblock or advance at any point
        if low in ("/continue", "continue", "next"):
            if s.get("state") == "UPSELL":
                ask_send_choice(s)
                db.save(s)
                return
            elif s.get("state") == "SELF_SENT":
                ask_reply_menu(s)
                db.save(s)
                return
            elif s.get("state") == "AWAIT_REPLY":
                say(s, "When the owner replies:\n1 Type what they said\n2 Send the revised agreement\n3 Not yet, remind me later\n4 Owner refused")
                db.save(s)
                return

        # /pay or /unlock command
        if low in ("/pay", "pay", "unlock"):
            s["after_pay"] = "tone"
            start_payment(s)
            db.save(s)
            return

        # If user uploads agreement document directly during START or LANG
        if media and s.get("state") in ("START", "LANG"):
            s["state"] = "COLLECT_DOC"
            if not s.get("lang"):
                s["lang"] = "en"

        # User uploaded a NEW agreement while in a later state (REPORT, DONE, DECIDE, etc.)
        # Reuse their existing profile context without re-asking income questions!
        elif media and s.get("state") not in ("COLLECT_DOC", "REVISED"):
            delete_files(s)
            s["files"] = []
            s["extracted"] = None
            s["report"] = None
            s["evaluation"] = None
            s["negotiation"] = None
            s["round"] = 0
            save_files(s, media)
            say(s, f"📄 Got your new agreement page! Send more pages, or tap below to check it:\n1 Start reading")
            s["state"] = "COLLECT_DOC"
            db.save(s)
            return

        if low == "help" and s["state"] != "START":
            say(s, "Reply with the number of your choice. Reply *menu* to start over.")
            db.save(s)
            return

        handler = HANDLERS.get(s["state"], h_start)
        try:
            handler(s, text, media)
        except Exception as e:
            print(f"[error in {s['state']}] {e}")
            say(s, "Sorry, something went wrong on my side. Please try that again, or reply *menu* to restart.")
        db.save(s)


# ---------------- start, language, upload ----------------

def h_start(s, text, media):
    channel.send(s["phone"], WELCOME)
    s["state"] = "LANG"


def h_lang(s, text, media):
    if text not in LANGS:
        channel.send(s["phone"], "Please reply 1, 2 or 3.\n1 English\n2 हिंदी\n3 ಕನ್ನಡ")
        return
    s["lang"] = LANGS[text]
    say(s, "Send a photo or PDF of your agreement. For many pages, send several photos.")
    s["state"] = "COLLECT_DOC"


def h_collect_doc(s, text, media):
    if media:
        save_files(s, media)
        say(s, f"Got {len(s['files'])} page(s). Send more pages, or tap below.\n1 Start reading")
        return
    if text == "1" and s["files"]:
        # Guard: drop any stale paths that no longer exist (e.g. after a /start reset)
        s["files"] = [[p, c] for p, c in s["files"] if os.path.exists(p)]
        if not s["files"]:
            say(s, "Please send a photo or PDF of the agreement.")
            return
        say(s, "Reading your agreement… (about 60 seconds)")
        try:
            ex = agents.extract(s["files"])
        except Exception as e:
            print(f"[extract error] {e}")
            say(s, "I had trouble reading that. Please send the photo again or try a clearer image.")
            s["files"] = []
            return
        if not ex.get("readable", True):
            s["files"] = []
            say(s, "I couldn't read that clearly. Please send a sharper photo in good light, or a PDF.")
            return
        s["extracted"] = ex
        say(s, f"I read: *{calc.summary_line(ex)}*.\nIs that right?\n1 Yes\n2 No")
        s["state"] = "CONFIRM_TYPE"
        return
    say(s, "Please send a photo or PDF of the agreement.")


def h_confirm_type(s, text, media):
    if text == "1":
        ask_profile(s, 0)
    elif text == "2":
        say(s, "What is this agreement?\n1 Shop rent\n2 Home rent\n3 Supplier\n4 Loan\n5 Other")
        s["state"] = "FIX_TYPE"
    else:
        say(s, "Please reply 1 (Yes) or 2 (No).")


def h_fix_type(s, text, media):
    kinds = {"1": "shop_rent", "2": "home_rent", "3": "supplier", "4": "loan", "5": "other"}
    if text not in kinds:
        say(s, "Please reply 1 to 5.")
        return
    s["extracted"]["agreement_type"] = kinds[text]
    ask_profile(s, 0)


# ---------------- Risk Profiler questions ----------------

def profile_questions(s):
    """Minimal, high-impact dynamic questions based on agreement type (max 1-2 questions)."""
    ex = s["extracted"] or {}
    atype = ex.get("agreement_type", "shop_rent")
    dep = ex.get("deposit")
    rent = ex.get("monthly_rent")
    lock_in = ex.get("lock_in_months")
    loan_amt = ex.get("loan_amount")
    qs = []

    if atype in ("shop_rent", "home_rent"):
        # Q1: Upfront deposit capacity if deposit exists
        if dep:
            opts = [(f"{calc.rs(dep)} is fine", dep)]
            if rent and dep > (rent * 3):
                opts.append((f"{calc.rs(int(dep * 0.6))} (Lower deposit)", int(dep * 0.6)))
            opts.append(("Type an amount", "TYPE"))
            opts.append(("Skip", None))
            qs.append({
                "key": "upfront_limit",
                "q": f"The deposit is {calc.rs(dep)}. What is the maximum you can pay upfront?",
                "opts": opts
            })
        # Q2: Planned stay duration
        qs.append({
            "key": "stay_months",
            "q": f"The agreement specifies {lock_in or 11}-month lock-in. How long do you plan to stay?",
            "opts": [("Under 1 year", 9), ("1 to 2 years", 24), ("3+ years", 48), ("Skip", None)]
        })

    elif atype == "loan":
        # Q1: Monthly earnings context
        qs.append({
            "key": "monthly_earnings",
            "q": "Roughly what are your monthly net business earnings?",
            "opts": [("Under ₹30,000", 20000), ("₹30,000 to ₹60,000", 45000), ("Over ₹60,000", 80000), ("Skip", None)]
        })
        # Q2: Max EMI affordability
        qs.append({
            "key": "upfront_limit",
            "q": "What is the maximum monthly EMI you can comfortably afford?",
            "opts": [("₹5,000 / month", 5000), ("₹10,000 / month", 10000), ("Type an amount", "TYPE"), ("Skip", None)]
        })

    elif atype == "supplier":
        # Q1: Payment/Credit terms
        qs.append({
            "key": "stay_months",
            "q": "What credit payment window do you need for vendor orders?",
            "opts": [("15 days credit", 15), ("30 days credit", 30), ("45 days credit", 45), ("Skip", None)]
        })

    else:
        # Generic single question for other contracts
        qs.append({
            "key": "stay_months",
            "q": "How long do you plan to be committed to this agreement?",
            "opts": [("Under 1 year", 9), ("1 to 3 years", 24), ("Long term (3+ yrs)", 48), ("Skip", None)]
        })

    return qs[:2]  # Strict maximum of 2 dynamic questions


def _mark_answered(s, key):
    """Remember that the user already answered (or skipped) this question, so it's never re-asked."""
    ans = s["profile"].setdefault("_answered", [])
    if key not in ans:
        ans.append(key)


def ask_profile(s, i):
    # Check if we already have the user's business profile in context (from this or previous agreements)
    prof = s.get("profile") or {}
    has_context = bool(prof.get("_answered") or prof.get("monthly_earnings")
                       or prof.get("stay_months") or prof.get("upfront_limit"))
    if has_context and s.get("state") not in ("PROFILE", "TYPE_AMOUNT"):
        lines = ["🧠 *Profile Context Found*"]
        if prof.get("monthly_earnings"):
            lines.append(f"• Net earnings: ₹{prof['monthly_earnings']:,}/mo")
        if prof.get("stay_months"):
            lines.append(f"• Planned tenure: {prof['stay_months']} months")
        if prof.get("upfront_limit"):
            lines.append(f"• Max upfront capacity: ₹{prof['upfront_limit']:,}")
        lines.append("\n✅ Using your saved details. (Reply *menu* to start over.)")
        say(s, "\n".join(lines))
        propose_must_haves(s)
        return

    qs = profile_questions(s)
    if i >= len(qs):
        db.save_user_profile(s["phone"], s["profile"])
        propose_must_haves(s)
        return
    q = qs[i]
    menu = "\n".join(f"{n + 1} {label}" for n, (label, _) in enumerate(q["opts"]))
    say(s, f"{q['q']}\n{menu}")
    s["pq"] = i
    s["state"] = "PROFILE"


def h_confirm_saved_profile(s, text, media):
    if text == "1":
        propose_must_haves(s)
    elif text == "2":
        s["profile"] = {}
        ask_profile(s, 0)
    else:
        say(s, "1 Use saved profile for this agreement\n2 Update my details")


def h_profile(s, text, media):
    q = profile_questions(s)[s["pq"]]
    if not text.isdigit() or not (1 <= int(text) <= len(q["opts"])):
        say(s, f"Please reply 1 to {len(q['opts'])}.")
        return
    val = q["opts"][int(text) - 1][1]
    if val == "TYPE":
        say(s, "Type the amount, e.g. 1.5 lakh or 150000.")
        s["state"] = "TYPE_AMOUNT"
        return
    s["profile"][q["key"]] = val
    _mark_answered(s, q["key"])
    db.save_user_profile(s["phone"], s["profile"])
    ask_profile(s, s["pq"] + 1)


def h_type_amount(s, text, media):
    amt = calc.parse_amount(text)
    if not amt:
        say(s, "Please type an amount, e.g. 150000 or 1.5 lakh.")
        return
    s["profile"]["upfront_limit"] = amt
    _mark_answered(s, "upfront_limit")
    db.save_user_profile(s["phone"], s["profile"])
    ask_profile(s, s["pq"] + 1)


def propose_must_haves(s):
    s["must_haves"] = calc.default_must_haves(s["extracted"], s["profile"])
    if not s["must_haves"]:
        run_report(s)
        return
    lines = "\n".join(f"✅ {m['label']}" for m in s["must_haves"])
    say(s, f"To protect you, I'll check for:\n{lines}\n\n1 Keep these\n2 Change something")
    s["state"] = "MUSTHAVES"


def h_musthaves(s, text, media):
    if text == "1":
        run_report(s)
    elif text == "2":
        say(s, "Type what you'd change, e.g. 'a 24-month lock-in is fine'.")
        s["state"] = "MH_EDIT"
    else:
        say(s, "Please reply 1 or 2.")


def h_mh_edit(s, text, media):
    s["must_have_note"] = text
    run_report(s)


# ---------------- report, voice, dashboard ----------------

def run_report(s):
    ex, profile = s["extracted"], s["profile"]
    say(s, "Analyzing agreement clauses and computing risk exposure…")
    exp = calc.exposure(ex, profile)
    prof = agents.risk_profile(ex, profile, s["must_haves"], exp, s.get("must_have_note"))
    checks = calc.check_must_haves(s["must_haves"], ex)
    verdict = calc.report_verdict(checks, prof.get("risks", []))
    score = calc.derive_score(prof, checks, exp, profile)  # rule-based, not the agent's raw number
    lvl = calc.risk_level(score)

    s["report"] = {**prof, "overall_score": score, "verdict": verdict, "exposure": exp, "checks": checks,
                   "what_if_total": calc.what_if(ex, profile, profile.get("upfront_limit"),
                                                 profile.get("stay_months"))}

    # Clean chat summary — full risk details live on the dashboard
    lines = [
        f"📋 *Agreement Check Complete*",
        f"",
        f"• *Verdict:* *{verdict}*",
        f"• *Risk Score:* *{score}/100* ({lvl['level']})",
    ]
    if exp.get("total"):
        worst = f"• *Money at Risk:* *{calc.rs(exp['total'])}*"
        if exp.get("months_of_earnings"):
            worst += f" (≈ {exp['months_of_earnings']} months of earnings)"
        lines.append(worst)

    dash_url = dashboard_url(s)
    lines.extend([
        f"",
        f"📊 *Full Breakdown on Dashboard:*",
        f"Clause analysis, risk charts & what-if numbers have been compiled into your private dashboard:",
        f"{dash_url}",
        f"",
        f"1 Help me negotiate",
        f"2 Ask a question",
        f"3 🔊 Play voice summary",
    ])
    say(s, "\n".join(lines))

    try:
        script = agents.voice_script(s["report"], profile, s["lang"])
        url = voice.tts(script)
        if url:
            say(s, "🔊 Here is your spoken risk summary:", media_url=url)
    except Exception as e:
        print(f"[voice skipped] {e}")

    s["state"] = "REPORT"


def h_report(s, text, media):
    if text == "1":
        say(s, "Do you know what similar places nearby pay as deposit? It makes your request stronger.\n"
               "Type the amount, or 0 to skip.")
        s["state"] = "EVIDENCE"
    elif text == "2":
        say(s, "Type your question about the agreement.")
        s["state"] = "ASK_Q"
    elif text == "3":
        script = agents.voice_script(s["report"], s["profile"], s["lang"])
        url = voice.tts(script)
        if url:
            say(s, "🔊 Spoken risk summary:", media_url=url)
        else:
            say(s, script)
        say(s, "1 Help me negotiate\n2 Ask a question\n3 🔊 Play voice summary again")
    else:
        say(s, "1 Help me negotiate\n2 Ask a question\n3 🔊 Play voice summary")


def h_ask_q(s, text, media):
    say(s, agents.answer(s["extracted"], s["report"], text, s["lang"]), translate=False)
    say(s, "1 Help me negotiate\n2 Ask another question")
    s["state"] = "REPORT"


# ---------------- negotiation (free first, then upsell) ----------------

def unmet_labels(s):
    ev = s.get("evaluation")
    checks = ev["checks"] if ev else s["report"]["checks"]
    return [c["label"] for c in checks if not c["met"]]


def build_negotiation(s, paid):
    evidence = {"deposit_nearby": s["evidence_deposit"]} if s.get("evidence_deposit") else None
    neg = agents.negotiate(s["extracted"], s["report"].get("risks", []), s["must_haves"], evidence,
                           s["tone"], s["lang"], s["round"] + 1, unmet_labels(s),
                           max_asks=3 if paid else 1)
    s["negotiation"] = neg
    return neg


def h_evidence(s, text, media):
    amt = calc.parse_amount(text)
    s["evidence_deposit"] = amt if amt else None
    neg = build_negotiation(s, paid=False)
    say(s, "Here's a message for the owner about your biggest risk:")
    channel.send(s["phone"], neg["message"], menu=False)
    say(s, f"Want the full pack? All risky clauses with fallback offers, tone choice, and a check of the "
           f"owner's reply against your must-haves. ₹{config.PRICE_RS}, one time.\n\n"
           f"1 Unlock for ₹{config.PRICE_RS}\n2 Continue with this message")
    s["state"] = "UPSELL"


def h_upsell(s, text, media):
    if text == "1":
        s["after_pay"] = "tone"
        start_payment(s)
    elif text == "2":
        ask_send_choice(s)
    else:
        say(s, "Please reply 1 or 2.")


def start_payment(s):
    link = payments.create_link(s)
    mode_name = "UPI / GPay" if config.PINELABS_MODE == "upi" else "test mode"
    say(s, f"💳 *Unlock Full Negotiation Pack (₹{config.PRICE_RS})*\n\n"
           f"Pay via {mode_name} using this secure link:\n{link}\n\n"
           f"Once paid, tap below:\n1 I've paid\n2 Skip, continue free")
    s["state"] = "AWAIT_PAYMENT"


def verify_payment(s, explicit=True):
    """Advance the flow only if the backend confirms payment.

    explicit=True  -> user tapped "I've paid": poll the gateway (payments.check_status).
    explicit=False -> user just typed hi/continue: never unlock; payment is confirmed by the
                      backend (webhook / confirm page calling on_paid), so just remind them.
    """
    if explicit and payments.check_status(s):
        on_paid(s)
    else:
        say(s, "I haven't received your payment yet. Please complete it using the link above, "
               "and I'll continue automatically once it's confirmed.\n1 I've paid\n2 Skip, continue free")


def h_await_payment(s, text, media):
    if text == "1":
        verify_payment(s)
    elif text == "2":
        if s.get("after_pay") == "eval":
            ask_decide_free(s)
        else:
            ask_send_choice(s)
    else:
        say(s, "1 I've paid\n2 Skip, continue free")


def on_paid(s):
    """Called from the payment webhook, confirm page, or after 'I've paid'."""
    if s.get("paid") and s.get("state") != "AWAIT_PAYMENT":
        return  # already processed (duplicate webhook / confirm page reload)
    s["paid"] = True
    say(s, "Payment received ✅ Thank you! Your full negotiation pack is unlocked.")
    if s.get("after_pay") == "eval":
        evaluate(s)
    else:
        say(s, "Pick a tone for your message:\n1 Friendly\n2 Firm\n3 Formal")
        s["state"] = "TONE"


def h_tone(s, text, media):
    tones = {"1": "friendly", "2": "firm", "3": "formal"}
    if text not in tones:
        say(s, "Please reply 1, 2 or 3.")
        return
    s["tone"] = tones[text]
    neg = build_negotiation(s, paid=True)
    rows = "\n".join(f"• {a['topic']} (Clause {a['clause']}): now {a['now']} → ask {a['ask']}, "
                     f"fallback {a['fallback']}" for a in neg["asks"])
    say(s, f"Your negotiation plan:\n{rows}")
    say(s, "Your message for the owner:")
    channel.send(s["phone"], neg["message"], menu=False)
    ask_send_choice(s)


# ---------------- sending to the owner ----------------

def is_tg(s):
    return s["phone"].startswith("tg:")


def owner_label(s):
    o = s.get("owner_phone") or ""
    return "the owner" if o.startswith("tg:") else o


def owner_intro(s):
    sender = "a Sign Smart user" if s["phone"].startswith(("web:", "tg:")) else s["phone"]
    return (f"Namaskara. This message is sent on behalf of {sender} via Sign Smart, "
            f"about the agreement you shared. Your reply here will be shared with them.\n\n")


def ask_send_choice(s):
    if s.get("owner_phone"):
        extra = f" ({owner_label(s)})"
    elif is_tg(s):
        extra = " (I'll give you an invite link for the owner)"
    else:
        extra = " (I'll need the owner's WhatsApp number)"
    say(s, f"How do you want to send it?\n1 Send it for me{extra}\n2 I'll forward it myself")
    s["state"] = "SEND_CHOICE"


def h_send_choice(s, text, media):
    if text == "1":
        if s.get("owner_phone"):
            confirm_send(s)
        elif is_tg(s):
            # Telegram bots can't message someone first: the owner opens an invite link.
            link = f"https://t.me/{config.TELEGRAM_BOT_USERNAME}?start=deal_{s['token']}"
            say(s, "Forward this invite to the owner on WhatsApp or SMS. When they open it, "
                   "I'll deliver your approved message to them:")
            channel.send(s["phone"], "Namaskara, I've sent you a message about the agreement through "
                                     f"Sign Smart. Please open this link to read it and reply:\n{link}", menu=False)
            say(s, "Waiting for the owner to open the link…\n1 Cancel, I'll forward the message myself")
            s["state"] = "AWAIT_OWNER_JOIN"
        else:
            say(s, "What's the owner's WhatsApp number? (e.g. 9845012345)")
            s["state"] = "AWAIT_OWNER_NO"
    elif text == "2":
        say(s, "Copy and forward this message to the owner:")
        channel.send(s["phone"], s["negotiation"]["message"], menu=False)
        say(s, "Did you send it?\n1 Yes, sent\n2 Not yet")
        s["round"] += 1
        s["state"] = "SELF_SENT"
    else:
        say(s, "Please reply 1 or 2.")


def h_owner_no(s, text, media):
    num = normalize_phone(text)
    if not num:
        say(s, "That doesn't look like a phone number. Please type the 10-digit number.")
        return
    s["owner_phone"] = num
    confirm_send(s)


def h_await_owner_join(s, text, media):
    if text == "1":
        s["state"] = "SEND_CHOICE"
        h_send_choice(s, "2", media)
    else:
        say(s, "Still waiting for the owner to open your invite link.\n1 Cancel, I'll forward the message myself")


def owner_join(owner_id, token):
    """Owner tapped Start on the invite link: link them to the tenant and deliver the approved message."""
    found = db.find_by_token(token)
    if not found or found.get("state") != "AWAIT_OWNER_JOIN":
        channel.send(owner_id, "This link has expired. Please ask the sender for a new one.", menu=False)
        return
    with db.phone_lock(found["phone"]):
        s = db.get(found["phone"])
        s["owner_phone"] = owner_id
        sid = channel.send(owner_id, owner_intro(s) + s["negotiation"]["message"], menu=False)
        s["msg_sid"], s["msg_status"] = sid, "delivered"
        s["round"] += 1
        say(s, "✅ The owner opened your invite and has received your message. I'll tell you when they reply.")
        ask_reply_menu(s)
        db.save(s)


def confirm_send(s):
    change = "" if s["owner_phone"].startswith("tg:") else "\n2 Change number"
    say(s, f"I'll send your message to *{owner_label(s)}* on your behalf. Confirm?\n1 Yes, send{change}")
    s["state"] = "CONFIRM_SEND"


def h_confirm_send(s, text, media):
    if text == "2":
        say(s, "What's the owner's WhatsApp number?")
        s["state"] = "AWAIT_OWNER_NO"
        return
    if text != "1":
        confirm_send(s)
        return
    sid = channel.send(s["owner_phone"], owner_intro(s) + s["negotiation"]["message"],
                       status_callback=f"{config.BASE_URL}/whatsapp/status", menu=False)
    if not sid:
        say(s, "I couldn't deliver it (in the test sandbox the owner must join first). "
               "You can forward it yourself instead.\n1 Try again\n2 I'll forward it myself")
        s["state"] = "SEND_CHOICE"
        return
    s["msg_sid"], s["msg_status"] = sid, "sent"
    s["round"] += 1
    sent_at = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%I:%M %p")
    say(s, f"✅ Sent to the owner at {sent_at}. I'll tell you when they reply.")
    ask_reply_menu(s)


def h_self_sent(s, text, media):
    if text == "1":
        ask_reply_menu(s)
    else:
        say(s, "No problem. Reply 1 once you've sent it.\n1 Yes, sent")


def ask_reply_menu(s):
    say(s, "When the owner replies:\n1 Type what they said\n2 Send the revised agreement\n"
           "3 Not yet, remind me later\n4 Owner refused")
    s["state"] = "AWAIT_REPLY"


def h_await_reply(s, text, media):
    if text == "1":
        say(s, "Type what the owner said.")
        s["state"] = "TYPE_REPLY"
    elif text == "2":
        say(s, "Send the revised agreement photos or PDF, then reply 1.")
        s["revised_files"] = []
        s["state"] = "REVISED"
    elif text == "3":
        s["followup_at"] = time.time() + config.REMINDER_SECONDS
        say(s, "OK, I'll check with you later.")
    elif text == "4":
        walk_away(s)
    else:
        ask_reply_menu(s)


def h_type_reply(s, text, media):
    s["owner_reply"] = text
    evaluate_entry(s)


def h_revised(s, text, media):
    if media:
        save_files(s, media, key="revised_files")
        say(s, f"Got {len(s['revised_files'])} page(s). Send more, or tap below.\n1 Check it")
        return
    if text == "1" and s["revised_files"]:
        say(s, "Reading the revised agreement…")
        s["revised_extracted"] = agents.extract(s["revised_files"])
        s["owner_reply"] = None
        evaluate_entry(s)
        return
    say(s, "Please send the revised agreement, then reply 1.")


def handle_owner(tenant, owner_phone, text, media):
    """The owner replied to our bot: relay it to the tenant."""
    if media:
        save_files(tenant, media, key="revised_files")
        tenant["revised_extracted"] = agents.extract(tenant["revised_files"])
        shown = "a revised agreement"
    else:
        shown = f"\"{text}\""
    tenant["owner_reply"] = text or None
    tenant["followup_at"] = None
    channel.send(owner_phone, "Thank you. Your reply has been shared.")
    say(tenant, f"📩 The owner replied: {shown}\n\n1 Check it against my must-haves\n2 I'll decide myself")
    tenant["state"] = "OWNER_REPLIED"


def h_owner_replied(s, text, media):
    if text == "1":
        evaluate_entry(s)
    else:
        ask_decide_free(s)


# ---------------- evaluation and decision ----------------

def evaluate_entry(s):
    if s["paid"]:
        evaluate(s)
        return
    s["after_pay"] = "eval"
    say(s, f"Checking the owner's reply against your must-haves is part of the full pack "
           f"(₹{config.PRICE_RS}).\n1 Unlock for ₹{config.PRICE_RS}\n2 Skip, I'll decide myself")
    s["state"] = "EVAL_GATE"


def h_eval_gate(s, text, media):
    if text == "1":
        start_payment(s)
    else:
        ask_decide_free(s)


def evaluate(s):
    say(s, "Comparing with agreement terms…")
    base_terms = (s.get("evaluation") or {}).get("terms") or s["extracted"]
    upd = agents.evaluate_terms(base_terms, s.get("owner_reply"), s.get("revised_extracted"))
    if s.get("owner_reply") and re.search(r"cap.*late fee|late fee.*cap|cap.*fee", s["owner_reply"], re.I):
        upd["late_fee_capped"] = True
    terms = calc.merge_terms(base_terms, s.get("revised_extracted"))
    terms = calc.merge_terms(terms, upd)
    checks = calc.check_must_haves(s["must_haves"], terms)
    new_risks = upd.get("new_risks", [])
    verdict = calc.eval_verdict(checks, new_risks, upd.get("refused"))
    before = s["report"]["exposure"]["total"]
    after = calc.exposure(terms, s["profile"])["total"]
    s["evaluation"] = {"checks": checks, "new_risks": new_risks, "verdict": verdict,
                       "terms": terms, "exposure_before": before, "exposure_after": after,
                       "concessions": upd.get("concessions", [])}

    lines = ["Compared with the original:"]
    for c in checks:
        lines.append(f"{'✅' if c['met'] else '❌'} {c['label']} (now: {c['now']})")
    for r in new_risks:
        lines.append(f"⚠️ New: {r['title']} (Clause {r.get('clause', '?')})")
    lines.append(f"Money at risk: {calc.rs(before)} → {calc.rs(after)}")
    unmet = sum(1 for c in checks if not c["met"])

    if verdict == "ACCEPT":
        lines.append("\n*ACCEPT recommended.* All your must-haves are met.\n"
                     "The final decision is yours. Type *I ACCEPT* to confirm.\n3 Walk away")
    elif verdict == "REJECT":
        lines.append("\n*WALK AWAY recommended.* The owner refused your must-haves.\n"
                     "2 Accept anyway\n3 Walk away")
    else:
        lines.append(f"\n*COUNTER recommended:* {unmet} must-have(s) unmet, {len(new_risks)} new risk(s).")
        if s["round"] < config.MAX_ROUNDS:
            lines.append("1 Draft round 2\n2 Accept anyway\n3 Walk away")
        else:
            lines.append("That was the last round.\n2 Accept anyway\n3 Walk away")
    say(s, "\n".join(lines))
    s["state"] = "DECIDE"


def ask_decide_free(s):
    say(s, "The decision is yours. Type *I ACCEPT* to accept.\n3 Walk away")
    s["state"] = "DECIDE"


def h_decide(s, text, media):
    ev = s.get("evaluation")
    if "i accept" in text.lower():
        final_summary(s)
    elif text == "1" and ev and ev["verdict"] == "COUNTER" and s["round"] < config.MAX_ROUNDS:
        neg = build_negotiation(s, paid=True)
        say(s, "Round 2 message (asks only what's still open):")
        channel.send(s["phone"], neg["message"], menu=False)
        ask_send_choice(s)
    elif text == "2":
        gaps = [f"Not met: {c['label']} (now: {c['now']})" for c in (ev["checks"] if ev else []) if not c["met"]]
        gaps += [f"New risk: {r['title']}" for r in (ev["new_risks"] if ev else [])]
        detail = ("You'd be accepting with:\n" + "\n".join(f"• {g}" for g in gaps)) if gaps else ""
        say(s, f"{detail}\nType *I ACCEPT* to confirm.")
    elif text == "3":
        walk_away(s)
    else:
        say(s, "Type *I ACCEPT* to accept.\n3 Walk away")


def final_summary(s):
    ev = s.get("evaluation")
    terms = ev["terms"] if ev else s["extracted"]
    lines = ["✅ *You accepted.* Final terms:"]
    if terms.get("deposit"):
        lines.append(f"• Deposit: {calc.rs(terms['deposit'])}")
    lines.append(f"• Deposit refund: {str(terms['deposit_refund_days']) + ' days' if terms.get('deposit_refund_days') else 'no deadline'}")
    if terms.get("lock_in_months"):
        lines.append(f"• Lock-in: {terms['lock_in_months']} months")
    if terms.get("annual_increase_pct"):
        lines.append(f"• Rent increase: {terms['annual_increase_pct']}% a year")
    if terms.get("late_fee_capped"):
        lines.append("• Late fee: Capped (reasonable limit agreed)")
    unclear = (s.get("report") or {}).get("unclear", [])
    if unclear:
        lines.append("\nConfirm before signing: " + "; ".join(f"{u['title']} (Clause {u['clause']})" for u in unclear))
    lines.append("\nMake sure the signed copy matches these terms. Guidance, not legal advice.")
    say(s, "\n".join(lines))
    finish(s)


def walk_away(s):
    say(s, "Nothing is signed. Here's a polite message you can send the owner if you like:")
    channel.send(s["phone"], "Thank you for your time. I won't be going ahead with the agreement as it is. "
                             "Happy to talk again if the terms can change.", menu=False)
    finish(s)


def finish(s):
    s["state"] = "DONE"
    s["followup_at"] = None
    delete_files(s)
    say(s, "Reply *menu* to check another agreement. Know another shop owner? Share Sign Smart with them 🙏")


def h_done(s, text, media):
    say(s, "Reply *menu* to check another agreement.")


def send_followup(s):
    s["followup_at"] = None
    say(s, "Has the owner replied?\n1 Yes, I'll type it\n2 Yes, revised agreement\n3 Not yet\n4 Owner refused")
    s["state"] = "AWAIT_REPLY"


HANDLERS = {
    "START": h_start, "LANG": h_lang, "COLLECT_DOC": h_collect_doc, "CONFIRM_TYPE": h_confirm_type,
    "FIX_TYPE": h_fix_type, "CONFIRM_SAVED_PROFILE": h_confirm_saved_profile,
    "PROFILE": h_profile, "TYPE_AMOUNT": h_type_amount,
    "MUSTHAVES": h_musthaves, "MH_EDIT": h_mh_edit, "REPORT": h_report, "ASK_Q": h_ask_q,
    "EVIDENCE": h_evidence, "UPSELL": h_upsell, "AWAIT_PAYMENT": h_await_payment, "TONE": h_tone,
    "SEND_CHOICE": h_send_choice, "AWAIT_OWNER_NO": h_owner_no, "AWAIT_OWNER_JOIN": h_await_owner_join,
    "CONFIRM_SEND": h_confirm_send, "SELF_SENT": h_self_sent, "AWAIT_REPLY": h_await_reply,
    "TYPE_REPLY": h_type_reply, "REVISED": h_revised, "OWNER_REPLIED": h_owner_replied,
    "EVAL_GATE": h_eval_gate, "DECIDE": h_decide, "DONE": h_done,
}