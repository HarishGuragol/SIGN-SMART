"""Pine Labs payments — Payment Links API.

PINELABS_MODE=stub  -> local TEST page (/pay/<token>), no money moves, no keys needed.
PINELABS_MODE=upi   -> real UPI QR/deep-link (GPay, PhonePe, Paytm…). No gateway needed.
                       Set UPI_VPA and UPI_PAYEE_NAME in .env.
                       Payment is self-confirmed: user taps "I've paid" in chat.
PINELABS_MODE=live  -> real payment links via Pine Labs' Payment Links API.
                       Needs PINELABS_CLIENT_ID + PINELABS_CLIENT_SECRET in .env.
                       PINELABS_BASE_URL defaults to their UAT host; swap for prod once
                       Pine Labs provides the production URL.
"""
import time
import urllib.parse

import httpx

from . import config

_token_cache = {"value": None, "expires_at": 0}


# ── Pine Labs OAuth token (live mode only) ──────────────────────────────────

def _get_token():
    """Client-credentials token, cached until ~1 min before it expires."""
    now = time.time()
    if _token_cache["value"] and now < _token_cache["expires_at"]:
        return _token_cache["value"]
    r = httpx.post(
        f"{config.PINELABS_BASE_URL}/api/auth/v1/token",
        json={
            "client_id": config.PINELABS_CLIENT_ID,
            "client_secret": config.PINELABS_CLIENT_SECRET,
            "grant_type": "client_credentials",
        },
        headers={"content-type": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    # Pine Labs' docs don't publish the token-response shape for this endpoint.
    # These cover the field names their other SDKs commonly use; print(data)
    # once against a real response and adjust if needed.
    token = data.get("access_token") or data.get("token")
    expires_in = data.get("expires_in", 3000)
    _token_cache.update(value=token, expires_at=now + expires_in - 60)
    return token


def _auth_headers():
    return {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}


# ── UPI deep-link helper ────────────────────────────────────────────────────

def _upi_link(token: str) -> str:
    """
    Build a upi://pay deep-link that any UPI app (GPay, PhonePe, Paytm…)
    can open or scan as a QR code.  We embed the session token in the
    transaction reference (tr) so the QR page can identify the session.
    """
    params = {
        "pa": config.UPI_VPA,
        "pn": config.UPI_PAYEE_NAME,
        "am": str(config.PRICE_RS),
        "cu": "INR",
        "tn": "Sign Smart full pack",
        "tr": token,       # transaction reference — shows up in the bank statement
    }
    return "upi://pay?" + urllib.parse.urlencode(params)


# ── Public API ──────────────────────────────────────────────────────────────

def create_link(s):
    """Return a URL the user should open / scan to pay.

    Stub  → local test page (no real money).
    UPI   → /pay/<token>/upi page with a QR code + deep-link button.
    Live  → Pine Labs payment-link URL.
    """
    mode = config.PINELABS_MODE

    if mode == "stub":
        s["payment_link_id"] = "stub-" + s["token"]
        return f"{config.BASE_URL}/pay/{s['token']}"

    if mode == "upi":
        if not config.UPI_VPA:
            raise RuntimeError("UPI_VPA is not set in .env — cannot create UPI payment link.")
        # No external API call needed; just direct them to the QR page.
        s["payment_link_id"] = "upi-" + s["token"]
        return f"{config.BASE_URL}/pay/{s['token']}/upi"

    # live — Pine Labs Payment Links API
    r = httpx.post(
        f"{config.PINELABS_BASE_URL}/api/pay/v1/payment-links",
        headers=_auth_headers(),
        json={
            "merchant_payment_link_reference": s["token"],
            "payment_link_amount": {"value": config.PRICE_RS * 100, "currency": "INR"},
            "description": "Sign Smart full pack",
            "callback_url": f"{config.BASE_URL}/pay/{s['token']}/confirm",
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    s["payment_link_id"] = data["payment_link_id"]
    return data["payment_link_url"]


def check_status(s):
    """Called when the user taps 'I've paid' (fallback if the webhook hasn't arrived).

    Stub & UPI → instant confirmation so the user is never stuck in demo/live.
    Live       → poll the Pine Labs payment-link status endpoint.
    """
    mode = config.PINELABS_MODE

    if mode in ("stub", "upi"):
        return True

    # live
    link_id = s.get("payment_link_id")
    if not link_id:
        return False
    r = httpx.get(
        f"{config.PINELABS_BASE_URL}/api/pay/v1/payment-links/{link_id}",
        headers=_auth_headers(),
        timeout=30,
    )
    r.raise_for_status()
    # Status field/values aren't documented publicly for this endpoint —
    # confirm against a real response once you have credentials.
    return r.json().get("status", "").upper() in ("PAID", "CAPTURED")


def verify_webhook(body_bytes, headers):
    """Return the session token if this is a genuine Pine Labs 'paid' event, else None.

    UPI and stub modes have no webhook; this only applies to live mode.

    IMPORTANT: Pine Labs' public docs describe the webhook payload shape
    (an ORDER_CAPTURED event) but not how to verify its signature — that's
    on a separate "Signature Verification" page that requires onboarding.
    Until PINELABS_WEBHOOK_SECRET is confirmed and wired in here this
    intentionally rejects every webhook in live mode: trusting an unverified
    payment webhook is worse than not having one, as it lets anyone POST a
    fake "paid" event. Use check_status() via the 'I've paid' button until
    this is filled in.
    """
    if config.PINELABS_MODE != "live" or not config.PINELABS_WEBHOOK_SECRET:
        return None

    import hashlib
    import hmac
    import json

    # Placeholder scheme: HMAC-SHA256 over the raw body, hex digest in
    # X-PineLabs-Signature — CONFIRM against Pine Labs' actual docs before
    # relying on this in production.
    sig = headers.get("x-pinelabs-signature") or headers.get("X-PineLabs-Signature")
    if not sig:
        return None
    expected = hmac.new(
        config.PINELABS_WEBHOOK_SECRET.encode(), body_bytes, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        print("[pinelabs webhook] signature mismatch — rejecting")
        return None

    event = json.loads(body_bytes)
    if event.get("event") != "ORDER_CAPTURED":
        return None
    data = event.get("data", {})
    if data.get("status", "").upper() not in ("CAPTURED", "PAID"):
        return None
    if data.get("amount", {}).get("value") != config.PRICE_RS * 100:
        print(f"[pinelabs webhook] amount mismatch: {data.get('amount')}")
        return None
    return data.get("merchant_payment_link_reference") or data.get("order_id")
