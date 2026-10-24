import html
import re
import subprocess
from pathlib import Path
import httpx

OUT_DIR = Path("/Users/harishguragol/Downloads/signsmart/flowchart_screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PHONE = "web:flowdemo"

r = httpx.get(f"http://localhost:8000/api/outbox?phone={PHONE}")
msgs = r.json()

OPT_LINE = re.compile(r"^(\d{1,2})\s+(.{1,80})$")
URL_RE = re.compile(r"(https?://\S+)")

def render_step(step_msgs, step_num, step_title, what_powers_it):
    html_parts = []
    for m in step_msgs:
        sender = m.get("from", "bot")
        body = m.get("body", "")
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

# Map each of the 12 boxes from user flowchart
flowchart_steps = [
    # Box 1
    ("01_Namaskara_Picks_Language.png", msgs[0:4], "1",
     "'Namaskara', picks language",
     "Twelve / ElevenLabs + language_translator agent (Sonnet fallback)"),

    # Box 2
    ("02_Uploads_Agreement.png", msgs[4:6], "2",
     "Uploads agreement (photo or PDF)",
     "agreement_extractor agent"),

    # Box 3
    ("03_I_Read_3yr_Shop_Rent_Confirm.png", msgs[6:9], "3",
     "'I read 3-yr shop rent, 35k/mo, 3L deposit. Is that right?'",
     "Fixed extraction correction UI"),

    # Box 4
    ("04_Answers_1_to_2_Profile_Traps.png", msgs[9:14], "4",
     "Answers 1–2 profile traps (stay intent & deposit limit)",
     "Rule-first form report: constraints"),

    # Box 5
    ("05_Check_3_to_4_Must_Haves.png", msgs[14:16], "5",
     "'I check 3–4 must-haves for you'",
     "Transition report: must-haves formulate"),

    # Box 6
    ("06_Risk_Audit_Verdict_Exposure.png", msgs[16:18], "6",
     "Risk Audit Verdict & Exposure (₹7,20,000 at risk · WALK AWAY)",
     "agreement_risk_profiler agent + calculated monetary exposure"),

    # Box 7
    ("08_Get_1_Free_Message_For_Top_Risk.png", msgs[18:24], "7",
     "Get 1 free message for top risk",
     "agreement_negotiator agent"),

    # Box 8
    ("09_Unlocks_Unlock_Full_Pack_49.png", msgs[23:26], "8",
     "'Unlocks unlock full pack 49'",
     "Pine Labs PL-link webhook & UPI deep link"),

    # Box 9
    ("11_Pick_Tone_Message_Sent_To_Owner.png", msgs[26:34], "9",
     "Pick tone, message sent to owner (full 3-ask plan)",
     "Owner approval: delivery status & fallback matrix"),

    # Box 10
    ("12_Owner_Replies_Or_Bot_Follows_Up.png", msgs[34:41], "10",
     "Owner replies, or bot follows up",
     "Reply relay + reminder mechanism"),

    # Box 11
    ("13_Document_Revised_ReEnter_Audit.png", msgs[41:48], "11",
     "Document revised: re-enter audit",
     "agreement_evaluator agent: audit view (concessions vs new 15% rent hike)"),

    # Box 12
    ("14_Types_I_ACCEPT_Deal_Close_Summary.png", msgs[48:], "12",
     "Types 'I ACCEPT' or walks away",
     "Deal close summary with locked terms in chat"),
]

for fname, s_msgs, num, title, powered in flowchart_steps:
    h = render_step(s_msgs, num, title, powered)
    take_snap(h, fname)

# Capture Box 6 Dashboard link & Box 8 GPay Checkout Modal
token = "vnCevjjmF_BdHQRL"
take_url(f"http://localhost:8000/d/{token}", "07_Opens_Risk_Dashboard_Page.png", w=1200, h=950)
take_url(f"http://localhost:8000/pay/{token}/upi", "10_PineLabs_UPI_GPay_Checkout_Modal.png", w=440, h=880)

print("\n🎉 Created all 14 flowchart screenshots in flowchart_screenshots/")
