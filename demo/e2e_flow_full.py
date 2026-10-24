"""End-to-end demo flow matching the exact 12-box user workflow.
Usage: python demo/e2e_flow_full.py [phone]
"""
import sys
import time
import httpx

BASE = "http://localhost:8000"
PHONE = sys.argv[1] if len(sys.argv) > 1 else f"web:flowdemo"
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
    # 1. 'Namaskara', picks language
    ("hi", None),
    ("1", None),

    # 2. Uploads agreement (photo or PDF)
    ("", "demo/original_agreement.pdf"),

    # 3. 'I read 3-yr shop rent, 35k/mo, 3L deposit. Is that right?'
    ("1", None),

    # 4. Answers 1-2 profile traps
    ("1", None),     # confirm type: yes
    ("2", None),     # upfront limit: ₹1,80,000 (lower deposit)
    ("2", None),     # tenure stay: 1 to 2 years

    # 5. 'I check 3-4 must-haves for you'
    ("1", None),     # keep must-haves

    # 6. Opens risk dashboard link (dashboard link received)
    # 7. Get 1 free message for top risk
    ("1", None),     # Help me negotiate
    ("150000", None),# market benchmark nearby

    # 8. Unlocks full pack 49
    ("1", None),     # unlock
    ("1", None),     # I've paid (or webhook)

    # 9. Pick tone, message sent to owner
    ("2", None),     # firm tone
    ("2", None),     # I'll forward it myself
    ("1", None),     # Yes, sent

    # 10. Owner replies or bot follows up
    ("2", None),     # Send revised agreement

    # 11. Document revised: re-enter audit
    ("", "demo/revised_agreement.pdf"),
    ("1", None),     # Check it
    ("1", None),     # Draft round 2
    ("2", None),     # I'll forward round 2 myself
    ("1", None),     # Yes, sent round 2
    ("1", None),     # Type what they said
    ("Owner agreed to cap late fee at 2000 per month and keep 30 day refund", None),

    # 12. Types 'I ACCEPT' or walks away -> Deal close summary in chat
    ("I ACCEPT", None)
]

for text, f in STEPS:
    send(text, f)

print(f"\nCompleted 12-stage workflow for {PHONE}!")
