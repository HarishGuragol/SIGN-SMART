"""End-to-end demo flow test against the local server. Usage: python demo/e2e_test.py [phone]"""
import sys
import time

import httpx

BASE = "http://localhost:8000"
PHONE = sys.argv[1] if len(sys.argv) > 1 else f"web:e2e{int(time.time()) % 100000}"
since = 0.0


def send(text="", file=None):
    files = None
    if file:
        files = {"files": (file.split("/")[-1], open(file, "rb"), "application/pdf")}
    httpx.post(f"{BASE}/api/message", data={"phone": PHONE, "text": text}, files=files, timeout=30)
    print(f"\n>>> USER: {text or file}")
    wait_replies()


def wait_replies(max_wait=150, quiet=6):
    global since
    start, last = time.time(), time.time()
    while time.time() - start < max_wait:
        time.sleep(1.5)
        msgs = httpx.get(f"{BASE}/api/outbox", params={"phone": PHONE, "since": since}, timeout=30).json()
        for m in msgs:
            since = max(since, m["ts"])
            print("BOT:", (m.get("text") or m.get("body") or str(m))[:600])
            last = time.time()
        if time.time() - last > quiet and time.time() - start > 4:
            return


STEPS = [
    ("hi", None), ("1", None),
    ("", "demo/original_agreement.pdf"), ("1", None), ("1", None),
    ("2", None), ("2", None),           # lower deposit, stay 1-2 years
    ("1", None),                        # keep must-haves
    ("1", None), ("150000", None),      # negotiate, nearby deposit
    ("1", None), ("1", None),           # unlock, I've paid
    ("2", None),                        # firm tone
    ("2", None), ("1", None),           # forward myself, sent
    ("2", None), ("", "demo/revised_agreement.pdf"), ("1", None),  # revised agreement, check
    ("1", None),                        # draft round 2
    ("I ACCEPT", None),                 # Step 12: Accept deal close summary
]
for text, f in STEPS:
    send(text, f)
print("\nDone. Dashboard token page: check /stats")
