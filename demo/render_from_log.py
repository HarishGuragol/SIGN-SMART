import html
import re
import subprocess
from pathlib import Path

OUT_DIR = Path("/Users/harishguragol/Downloads/signsmart/final_submission_screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = Path("/Users/harishguragol/.gemini/antigravity/brain/88fbadee-3ad0-4896-b01a-5fb41b61848b/.system_generated/tasks/task-366.log")
lines = LOG_PATH.read_text(encoding="utf-8").splitlines()

# Parse distinct conversation turns
raw_turns = []
cur_sender = None
cur_lines = []

for l in lines:
    if l.startswith(">>> USER:"):
        if cur_sender and cur_lines:
            raw_turns.append((cur_sender, "\n".join(cur_lines).strip()))
            cur_lines = []
        cur_sender = "user"
        cur_lines.append(l[len(">>> USER:"):].strip())
    elif l.startswith("BOT:"):
        b_txt = l[len("BOT:"):].strip()
        # In e2e test log, the bot echoes user text sometimes, or gives messages
        if cur_sender == "bot":
            cur_lines.append(b_txt)
        else:
            if cur_sender and cur_lines:
                raw_turns.append((cur_sender, "\n".join(cur_lines).strip()))
                cur_lines = []
            cur_sender = "bot"
            cur_lines.append(b_txt)

if cur_sender and cur_lines:
    raw_turns.append((cur_sender, "\n".join(cur_lines).strip()))

# Filter out duplicate echoes if any
clean_turns = []
for s, text in raw_turns:
    # clean up
    text = text.strip()
    if not text:
        continue
    # In task-366 output, BOT repeats the short user command on the first line (e.g. 'BOT: 1', 'BOT: hi')
    if s == "bot" and len(clean_turns) > 0 and clean_turns[-1][0] == "user":
        user_prev = clean_turns[-1][1].strip()
        lines_b = text.split("\n")
        if lines_b[0].strip() == user_prev and len(lines_b) > 1:
            text = "\n".join(lines_b[1:]).strip()
    clean_turns.append((s, text))

print(f"Clean turns parsed: {len(clean_turns)}")
for i, (s, t) in enumerate(clean_turns):
    print(f"{i:02d}: [{s}] {t.split(chr(10))[0][:65]}")

OPT_LINE = re.compile(r"^(\d{1,2})\s+(.{1,80})$")
URL_RE = re.compile(r"(https?://\S+)")

def render_step_html(step_msgs, step_num, step_title, what_powers_it):
    html_parts = []
    for sender, body in step_msgs:
        is_user = sender == "user"
        lines = body.split("\n")
        opt_lines, text_lines, link_lines = [], [], []
        for l in lines:
            trimmed = l.strip()
            mo = OPT_LINE.match(trimmed)
            if mo and not URL_RE.search(trimmed):
                opt_lines.append(mo.group(2))
                continue
            if URL_RE.search(trimmed) and URL_RE.sub("", trimmed).strip() == "":
                link_lines.append(trimmed)
                continue
            text_lines.append(l)

        text = "\n".join(text_lines).strip()
        formatted = html.escape(text).replace("\n", "<br/>")
        formatted = re.sub(r"\*([^*\n]+)\*", r"<b>\1</b>", formatted)
        formatted = re.sub(r"_([^_\n]+)_", r"<i>\1</i>", formatted)

        bubble_class = "user" if is_user else "bot"
        html_parts.append(f"""
        <div class="row {bubble_class}">
          <div class="bubble">{formatted}</div>
        </div>
        """)
        if opt_lines and not is_user:
            btns = "".join([f'<span class="btn">{html.escape(o)}</span>' for o in opt_lines])
            html_parts.append(f'<div class="options">{btns}</div>')
        if link_lines and not is_user:
            links = "".join([f'<a class="linkbtn" href="{html.escape(lk)}" target="_blank">🔗 Open Link: {html.escape(lk)}</a>' for lk in link_lines])
            html_parts.append(f'<div class="links">{links}</div>')

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #0B1120;
  color: #F8FAFC;
  margin: 0;
  padding: 24px;
  display: flex;
  justify-content: center;
}}
.container {{
  max-width: 680px;
  width: 100%;
  background: #0F172A;
  border: 1px solid #1E293B;
  border-radius: 20px;
  padding: 24px 28px;
  box-shadow: 0 16px 36px rgba(0,0,0,0.5);
}}
.header {{
  padding: 6px 0 18px;
  border-bottom: 1px solid #1E293B;
  margin-bottom: 22px;
}}
.badge {{
  display: inline-block;
  background: #0369A1;
  color: #E0F2FE;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}}
.header h1 {{ margin: 0 0 6px; font-size: 20px; color: #38BDF8; font-weight: 700; }}
.header p {{ margin: 0; color: #94A3B8; font-size: 13px; }}
.header p b {{ color: #F1F5F9; }}
.row {{
  display: flex;
  margin-bottom: 14px;
}}
.row.bot {{ justify-content: flex-start; }}
.row.user {{ justify-content: flex-end; }}
.bubble {{
  max-width: 86%;
  padding: 12px 16px;
  border-radius: 18px;
  font-size: 14px;
  line-height: 1.55;
  word-wrap: break-word;
}}
.row.bot .bubble {{
  background: #1E293B;
  color: #F1F5F9;
  border-bottom-left-radius: 4px;
  border: 1px solid #334155;
}}
.row.user .bubble {{
  background: #2563EB;
  color: #FFFFFF;
  border-bottom-right-radius: 4px;
  font-weight: 500;
}}
.options {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: -4px 0 14px 6px;
}}
.btn {{
  background: #1E293B;
  color: #38BDF8;
  padding: 7px 14px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid #38BDF8;
}}
.links {{
  margin: -4px 0 14px 6px;
}}
.linkbtn {{
  display: inline-block;
  background: #0284C7;
  color: #FFFFFF;
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
  margin-bottom: 4px;
}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="badge">Flowchart Step {step_num} of 12</div>
    <h1>{html.escape(step_title)}</h1>
    <p>What powers it: <b>{html.escape(what_powers_it)}</b></p>
  </div>
  {"".join(html_parts)}
</div>
</body>
</html>"""

def take_snap(html_str, filename, w=900, h=1050):
    tmp = OUT_DIR / f"{filename}.html"
    tmp.write_text(html_str, encoding="utf-8")
    out = OUT_DIR / filename
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless", "--disable-gpu", "--user-data-dir=/tmp/chromedata",
        f"--window-size={w},{h}", f"--screenshot={out}", f"file://{tmp}"
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tmp.unlink(missing_ok=True)
    print(f"📸 {filename}")

def take_url(url, filename, w=1200, h=950):
    out = OUT_DIR / filename
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless", "--disable-gpu", "--user-data-dir=/tmp/chromedata",
        f"--window-size={w},{h}", f"--screenshot={out}", url
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"📸 {filename}")

# Mapping clean_turns to the 12 boxes:
flowchart_steps = [
    # Box 1: 'Namaskara', picks language
    ("01_Namaskara_Picks_Language.png", clean_turns[0:4], "1",
     "'Namaskara', picks language",
     "Twelve / ElevenLabs + language_translator agent (Sonnet fallback)"),

    # Box 2: Uploads agreement (photo or PDF)
    ("02_Uploads_Agreement.png", clean_turns[4:6], "2",
     "Uploads agreement (photo or PDF)",
     "agreement_extractor agent"),

    # Box 3: 'I read 3-yr shop rent, 35k/mo, 3L deposit. Is that right?'
    ("03_I_Read_3yr_Shop_Rent_Confirm.png", clean_turns[6:9], "3",
     "'I read 3-yr shop rent, 35k/mo, 3L deposit. Is that right?'",
     "Fixed extraction correction UI"),

    # Box 4: Answers 1-2 profile traps
    ("04_Answers_1_to_2_Profile_Traps.png", clean_turns[9:14], "4",
     "Answers 1–2 profile traps (stay intent & deposit limit)",
     "Rule-first form report: constraints"),

    # Box 5: 'I check 3-4 must-haves for you'
    ("05_Check_3_to_4_Must_Haves.png", clean_turns[14:16], "5",
     "'I check 3–4 must-haves for you'",
     "Transition report: must-haves formulate"),

    # Box 6: Risk audit verdict & exposure
    ("06_Risk_Audit_Verdict_Exposure.png", clean_turns[16:18], "6",
     "Risk Audit Verdict & Exposure (₹7,20,000 at risk · WALK AWAY)",
     "agreement_risk_profiler agent + calculated monetary exposure"),

    # Box 7: Get 1 free message for top risk
    ("08_Get_1_Free_Message_For_Top_Risk.png", clean_turns[18:22], "7",
     "Get 1 free message for top risk",
     "agreement_negotiator agent"),

    # Box 8: 'Unlocks unlock full pack 49'
    ("09_Unlocks_Unlock_Full_Pack_49.png", clean_turns[21:25], "8",
     "'Unlocks unlock full pack 49'",
     "Pine Labs PL-link webhook & UPI deep link"),

    # Box 9: Pick tone, message sent to owner
    ("11_Pick_Tone_Message_Sent_To_Owner.png", clean_turns[25:31], "9",
     "Pick tone, message sent to owner (full 3-ask plan)",
     "Owner approval: delivery status & fallback matrix"),

    # Box 10: Owner replies, or bot follows up
    ("12_Owner_Replies_Or_Bot_Follows_Up.png", clean_turns[31:36], "10",
     "Owner replies, or bot follows up",
     "Reply relay + reminder mechanism"),

    # Box 11: Document revised: re-enter audit
    ("13_Document_Revised_ReEnter_Audit.png", clean_turns[36:40], "11",
     "Document revised: re-enter audit",
     "agreement_evaluator agent: audit view (concessions vs new 15% rent hike)"),

    # Box 12: Types 'I ACCEPT' or walks away
    ("14_Types_I_ACCEPT_Deal_Close_Summary.png", clean_turns[40:], "12",
     "Types 'I ACCEPT' or walks away",
     "Deal close summary with locked terms in chat"),
]

for fname, s_msgs, num, title, powered in flowchart_steps:
    h = render_step_html(s_msgs, num, title, powered)
    take_snap(h, fname)

token = "vnCevjjmF_BdHQRL"
take_url(f"http://localhost:8000/d/{token}", "07_Opens_Risk_Dashboard_Page.png", w=1200, h=950)
take_url(f"http://localhost:8000/pay/{token}/upi", "10_PineLabs_UPI_GPay_Checkout_Modal.png", w=440, h=880)

print("\n🎉 Re-rendered all 14 flowchart screenshots from persistent log into final_submission_screenshots/!")
