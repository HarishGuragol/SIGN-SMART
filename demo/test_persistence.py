"""Test specifically that in the same chat, when user uploads a new agreement,
the income/profile details are NEVER re-asked and context is completely reused.
"""
import sys
import time
import httpx

BASE = "http://localhost:8000"
PHONE = f"web:persist_{int(time.time())}"
since = 0.0

def send(text="", file=None):
    global since
    files = None
    if file:
        files = {"files": (file.split("/")[-1], open(file, "rb"), "application/pdf")}
    httpx.post(f"{BASE}/api/message", data={"phone": PHONE, "text": text}, files=files, timeout=30)
    print(f"\n>>> USER: {text or file}")
    time.sleep(1)
    msgs = httpx.get(f"{BASE}/api/outbox", params={"phone": PHONE, "since": since}, timeout=30).json()
    for m in msgs:
        since = max(since, m["ts"])
        print("BOT:", (m.get("text") or m.get("body") or "")[:400])

print(f"Testing persistence for phone: {PHONE}")

# Agreement 1: Initial onboarding
send("hi")
send("1") # English
send("", "demo/original_agreement.pdf")
time.sleep(2)
send("1") # Start reading
time.sleep(12)
send("1") # Yes, terms are correct

# Q1: Upfront limit -> Answer option 2 (₹1,80,000)
send("2")
# Q2: Stay duration -> Answer option 2 (1 to 2 years)
send("2")
# Must haves: Keep
send("1")
time.sleep(10)
print("\n--- Agreement 1 Report Received! ---")

# Now user uploads a SECOND agreement in the EXACT SAME CHAT!
print("\n=== UPLOADING NEW AGREEMENT IN SAME CHAT ===")
send("", "demo/revised_agreement.pdf")
time.sleep(2)
send("1") # Start reading
time.sleep(12)
send("1") # Yes, terms are correct

# CHECK: Does the bot ask for deposit/income/stay duration again?!
# Or does it reuse the saved profile context and jump straight to must-haves / report?!
time.sleep(3)
msgs = httpx.get(f"{BASE}/api/outbox", params={"phone": PHONE, "since": since}, timeout=30).json()
for m in msgs:
    print("BOT (New Agreement):", (m.get("text") or m.get("body") or ""))
