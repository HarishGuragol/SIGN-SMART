"""One sqlite table: sessions(phone -> JSON). Simple and fast for a hackathon."""
import json
import secrets
import sqlite3
import threading
import time

from . import config

_lock = threading.RLock()
_conn = sqlite3.connect(config.DATA_DIR / "signsmart.db", check_same_thread=False)
_conn.execute("CREATE TABLE IF NOT EXISTS sessions (phone TEXT PRIMARY KEY, data TEXT NOT NULL)")
_conn.execute("CREATE TABLE IF NOT EXISTS user_profiles (phone TEXT PRIMARY KEY, profile_data TEXT NOT NULL)")
_conn.commit()

# Per-phone locks so two messages from one user never race
_phone_locks = {}


def phone_lock(phone):
    with _lock:
        return _phone_locks.setdefault(phone, threading.Lock())


def save_user_profile(phone, profile_dict):
    """Persist the user's business profile across sessions so we never re-ask."""
    if not profile_dict:
        return
    with _lock:
        existing = get_user_profile(phone)
        existing.update({k: v for k, v in profile_dict.items() if v is not None})
        _conn.execute(
            "INSERT INTO user_profiles(phone, profile_data) VALUES(?, ?) ON CONFLICT(phone) DO UPDATE SET profile_data=excluded.profile_data",
            (phone, json.dumps(existing)),
        )
        _conn.commit()


def get_user_profile(phone):
    """Retrieve persisted profile (income, upfront capacity, etc.) for this phone."""
    with _lock:
        row = _conn.execute("SELECT profile_data FROM user_profiles WHERE phone=?", (phone,)).fetchone()
    return json.loads(row[0]) if row else {}


def new_session(phone):
    # Retain known profile context across sessions / new agreements
    saved_prof = get_user_profile(phone)
    return {
        "phone": phone,
        "token": secrets.token_urlsafe(12),  # used in dashboard + payment links
        "state": "START",
        "lang": "en",
        "files": [],
        "revised_files": [],
        "extracted": None,
        "profile": dict(saved_prof),  # Pre-populate with saved context!
        "has_saved_profile": bool(saved_prof.get("monthly_earnings") or saved_prof.get("stay_months")),
        "must_haves": [],
        "report": None,
        "paid": False,
        "payment_link_id": None,
        "after_pay": None,
        "evidence_deposit": saved_prof.get("evidence_deposit"),
        "negotiation": None,
        "tone": "friendly",
        "owner_phone": None,
        "round": 0,
        "msg_sid": None,
        "msg_status": None,
        "owner_reply": None,
        "revised_extracted": None,
        "evaluation": None,
        "followup_at": None,
        "created_at": time.time(),
    }


def get(phone):
    with _lock:
        row = _conn.execute("SELECT data FROM sessions WHERE phone=?", (phone,)).fetchone()
    return json.loads(row[0]) if row else new_session(phone)


def exists(phone):
    with _lock:
        return _conn.execute("SELECT 1 FROM sessions WHERE phone=?", (phone,)).fetchone() is not None


def save(s):
    with _lock:
        _conn.execute(
            "INSERT INTO sessions(phone, data) VALUES(?, ?) ON CONFLICT(phone) DO UPDATE SET data=excluded.data",
            (s["phone"], json.dumps(s)),
        )
        _conn.commit()


def all_sessions():
    with _lock:
        rows = _conn.execute("SELECT data FROM sessions").fetchall()
    return [json.loads(r[0]) for r in rows]


def find_by_token(token):
    return next((s for s in all_sessions() if s.get("token") == token), None)


def find_by_owner(owner_phone, states):
    """The tenant session currently waiting on this owner, if any."""
    for s in all_sessions():
        if s.get("owner_phone") == owner_phone and s.get("state") in states:
            return s
    return None


def find_by_msg_sid(sid):
    return next((s for s in all_sessions() if s.get("msg_sid") == sid), None)


def due_followups(now):
    return [s for s in all_sessions() if s.get("followup_at") and s["followup_at"] <= now]