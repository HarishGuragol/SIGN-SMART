"""All numbers and verdict rules live here, in plain code, never in the LLM."""
import math
import re


def rs(n):
    """Indian-style rupee formatting: 200000 -> ₹2,00,000"""
    if n is None:
        return "-"
    n = int(round(n))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        s = head + "," + tail
    return ("-" if n < 0 else "") + "₹" + s


def parse_amount(text):
    """'1.5L', '1,50,000', '₹150000', '150k' -> 150000. None if no number."""
    t = text.lower().replace(",", "").replace("₹", "").replace("rs", "").strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(lakh|lac|l|k|thousand)?", t)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2)
    if unit in ("lakh", "lac", "l"):
        val *= 100000
    elif unit in ("k", "thousand"):
        val *= 1000
    return int(val)


def summary_line(ex):
    parts = []
    term = ex.get("term_months")
    kind = (ex.get("agreement_type") or "agreement").replace("_", " ")
    if term:
        parts.append(f"{term}-month {kind}" if term % 12 else f"{term // 12}-year {kind}")
    else:
        parts.append(kind)
    if ex.get("monthly_rent"):
        parts.append(f"{rs(ex['monthly_rent'])}/month")
    if ex.get("deposit"):
        parts.append(f"{rs(ex['deposit'])} deposit")
    return ", ".join(parts)


# ---------- Exposure (worst-case money at risk) ----------

def exposure(ex, profile):
    ex = ex or {}
    profile = profile or {}
    rent = ex.get("monthly_rent") or 0
    dep = ex.get("deposit") or 0
    refs = ex.get("clause_refs") or {}
    stay = profile.get("stay_months")
    earn = profile.get("monthly_earnings")
    items = []

    if dep and not ex.get("deposit_refund_days"):
        items.append({"key": "deposit", "label": "Deposit with no refund deadline",
                      "clause": refs.get("deposit"), "amount": dep})

    lock = ex.get("lock_in_months") or 0
    if lock and rent and ex.get("early_exit_full_rent"):
        if stay is not None:
            gap = max(0, lock - stay)
            label = f"Lock-in rent if you leave after {stay} months"
        else:
            gap = lock // 2
            label = "Lock-in rent if you leave halfway"
        if gap:
            items.append({"key": "lock_in", "label": label, "clause": refs.get("lock_in"),
                          "amount": gap * rent})

    pct = ex.get("annual_increase_pct")
    if pct and rent:
        horizon = min(stay or ex.get("term_months") or 36, ex.get("term_months") or 120)
        extra = 0.0
        for y in range(1, math.ceil(horizon / 12)):
            months = min(12, horizon - 12 * y)
            extra += months * rent * ((1 + pct / 100) ** y - 1)
        if extra:
            items.append({"key": "increase", "label": f"Extra rent from {pct}% yearly increase",
                          "clause": refs.get("increase"), "amount": round(extra)})

    if ex.get("late_fee") and not ex.get("late_fee_capped"):
        items.append({"key": "late_fee", "label": "Late fee per late payment, no upper limit",
                      "clause": refs.get("late_fee"), "amount": ex["late_fee"], "per_event": True})

    total = sum(i["amount"] for i in items if not i.get("per_event"))
    months = round(total / earn, 1) if earn else None
    for i in items:
        i["months_of_earnings"] = round(i["amount"] / earn, 1) if earn else None
    return {"items": items, "total": total, "months_of_earnings": months}


# ---------- Must-haves ----------

def risk_level(score):
    """Returns level name, badge class, colors, and plain-English explanation."""
    if score is None:
        score = 50
    if score <= 35:
        return {
            "score": score,
            "level": "Low Risk",
            "badge": "low",
            "color": "#0F4A2D",
            "bg": "#E3F3EA",
            "summary": "Fair and balanced terms. Standard legal protections in place.",
            "action": "Safe to sign with minimal adjustments."
        }
    elif score <= 65:
        return {
            "score": score,
            "level": "Moderate Risk",
            "badge": "medium",
            "color": "#7A2E0B",
            "bg": "#FDEBD3",
            "summary": "Several one-sided clauses found (such as deposit refund delays or notice terms).",
            "action": "Negotiation recommended to protect your rights before signing."
        }
    else:
        return {
            "score": score,
            "level": "High Risk",
            "badge": "high",
            "color": "#8A1C10",
            "bg": "#FDE4E1",
            "summary": "Severe financial exposure or heavily one-sided clauses (e.g. lock-in penalty or non-refundable deposit).",
            "action": "Do NOT sign as-is. Negotiate essential must-haves or walk away."
        }


def derive_score(prof, checks, exp, profile):
    """Risk score from the actual agreement, used when the agent gives no valid number
    (so the score never falls back to one fixed value)."""
    weights = {"high": 12, "medium": 6, "low": 2}
    score = 10 + sum(weights.get((r.get("severity") or "").lower(), 4) for r in prof.get("risks", []))
    score += 4 * sum(1 for c in checks if not c["met"])
    earn = (profile or {}).get("monthly_earnings")
    if earn and exp.get("total"):
        score += min(20, int(exp["total"] / earn * 2))
    elif exp.get("total"):
        score += min(15, int(exp["total"] / 50000))
    return max(5, min(97, score))


def default_must_haves(ex, profile):
    ex = ex or {}
    profile = profile or {}
    mh = []
    dep = ex.get("deposit")
    if dep:
        limit = profile.get("upfront_limit") or dep
        mh.append({"key": "deposit_max", "label": f"Deposit at most {rs(limit)}", "limit": limit})
        mh.append({"key": "refund_days_max", "label": "Deposit refunded within 30 days of leaving", "limit": 30})
    lock = ex.get("lock_in_months")
    if lock:
        limit = profile.get("stay_months") or 11
        if lock > limit:
            mh.append({"key": "lock_in_max", "label": f"Lock-in no longer than {limit} months", "limit": limit})
    pct = ex.get("annual_increase_pct")
    if pct and pct > 5:
        mh.append({"key": "increase_max", "label": "Rent increase at most 5% a year", "limit": 5})
    if ex.get("late_fee") and not ex.get("late_fee_capped"):
        mh.append({"key": "late_fee_capped", "label": "Late fee has an upper limit", "limit": True})
    return mh


def check_must_haves(must_haves, terms):
    """terms = merged agreement terms. Returns list of {label, met, now}."""
    out = []
    for m in must_haves:
        k, lim = m["key"], m["limit"]
        if k == "deposit_max":
            v = terms.get("deposit")
            met, now = (v is not None and v <= lim), rs(v)
        elif k == "refund_days_max":
            v = terms.get("deposit_refund_days")
            met, now = (v is not None and v <= lim), (f"{v} days" if v else "no deadline")
        elif k == "lock_in_max":
            v = terms.get("lock_in_months")
            met, now = (not v or v <= lim), (f"{v} months" if v else "none")
        elif k == "increase_max":
            v = terms.get("annual_increase_pct") or 0
            met, now = (v <= lim), f"{v}% a year"
        elif k == "late_fee_capped":
            met, now = bool(terms.get("late_fee_capped")), ("capped" if terms.get("late_fee_capped") else "no cap")
        else:
            met, now = False, "?"
        out.append({"key": k, "label": m["label"], "met": met, "now": now})
    return out


def report_verdict(checks, risks):
    """SIGN if all must-haves met and no high risk; WALK AWAY if 3+ high risks; else NEGOTIATE."""
    high = [r for r in risks if (r.get("severity") or "").lower() == "high"]
    if all(c["met"] for c in checks) and not high:
        return "SIGN"
    if len(high) >= 3 and sum(1 for c in checks if not c["met"]) >= 3:
        return "WALK AWAY"
    return "NEGOTIATE"


def merge_terms(original, update):
    merged = dict(original or {})
    for k, v in (update or {}).items():
        if v is not None and k in ("deposit", "deposit_refund_days", "lock_in_months",
                                   "annual_increase_pct", "monthly_rent", "late_fee", "late_fee_capped",
                                   "early_exit_full_rent"):
            merged[k] = v
    return merged


def eval_verdict(checks, new_risks, refused):
    """Fixed rules shown to judges."""
    if refused:
        return "REJECT"
    high_new = [r for r in new_risks if (r.get("severity") or "").lower() == "high"]
    if all(c["met"] for c in checks) and not high_new:
        return "ACCEPT"
    return "COUNTER"


def what_if(ex, profile, deposit=None, lock_in=None):
    """Exposure if the owner agreed to the user's limits (for the dashboard)."""
    alt = dict(ex)
    if deposit is not None:
        alt["deposit"] = deposit
    alt["deposit_refund_days"] = 30
    if lock_in is not None:
        alt["lock_in_months"] = lock_in
    return exposure(alt, profile)["total"]