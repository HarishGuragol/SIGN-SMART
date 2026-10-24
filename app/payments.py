"""Pine Labs payments.
PINELABS_MODE=stub -> local TEST page (/pay/<token>), no money moves.
PINELABS_MODE=live -> fill in the 3 TODOs from Pine Labs' payment-link docs."""
from . import config


def create_link(s):
    if config.PINELABS_MODE == "stub":
        s["payment_link_id"] = "stub-" + s["token"]
        return f"{config.BASE_URL}/pay/{s['token']}"
    # TODO (live): call Pine Labs "create payment link" with:
    #   amount = config.PRICE_RS * 100 (paise, check their docs), currency INR,
    #   reference / order id = s["token"]  (so the webhook can find the session),
    #   description = "Sign Smart full pack",
    #   callback / webhook URL = f"{config.BASE_URL}/payments/webhook"
    # Save their link id in s["payment_link_id"] and return the payment URL.
    raise NotImplementedError("Add the Pine Labs payment-link API call here")


def check_status(s):
    """Used when the user taps 'I've paid' in case the webhook hasn't arrived."""
    if config.PINELABS_MODE == "stub":
        return bool(s.get("paid"))
    # TODO (live): query Pine Labs for s["payment_link_id"] and return True if paid.
    raise NotImplementedError


def verify_webhook(body_bytes, headers):
    """Return the session token if this is a genuine 'paid' event, else None."""
    if config.PINELABS_MODE == "stub":
        return None
    # TODO (live): verify Pine Labs' signature, check status == paid and amount == PRICE_RS,
    # and return the reference (our token).
    raise NotImplementedError