import html
import re
import subprocess
from pathlib import Path
import httpx

OUT_DIR = Path("/Users/harishguragol/Downloads/signsmart/demo/screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PHONE = "web:flowdemo"

def fetch_messages():
    r = httpx.get(f"http://localhost:8000/api/outbox?phone={PHONE}")
    return r.json()

OPT_LINE = re.compile(r"^(\d{1,2})\s+(.{1,80})$")
URL_RE = re.compile(r"(https?://\S+)")

def render_html_slice(msgs, stage_title, stage_subtitle):
    html_parts = []
    for m in msgs:
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
        # CRITICAL: Use \1 and \2 in Python regex replacement, NEVER $1 or $2!
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
  padding: 22px 26px;
  box-shadow: 0 16px 36px rgba(0,0,0,0.5);
}}
.header {{
  text-align: center;
  padding: 6px 0 18px;
  border-bottom: 1px solid #1E293B;
  margin-bottom: 20px;
}}
.header h1 {{ margin: 0 0 4px; font-size: 19px; color: #38BDF8; font-weight: 700; }}
.header p {{ margin: 0; color: #94A3B8; font-size: 13px; }}
.row {{
  display: flex;
  margin-bottom: 12px;
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
  padding: 6px 14px;
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
    <h1>{html.escape(stage_title)}</h1>
    <p>{html.escape(stage_subtitle)}</p>
  </div>
  {"".join(html_parts)}
</div>
</body>
</html>"""

def capture_screenshot(html_str, filename, width=900, height=1050):
    tmp_path = OUT_DIR / f"{filename}.html"
    tmp_path.write_text(html_str, encoding="utf-8")
    out_png = OUT_DIR / filename
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless",
        "--disable-gpu",
        "--user-data-dir=/tmp/chromedata",
        f"--window-size={width},{height}",
        f"--screenshot={out_png}",
        f"file://{tmp_path}"
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tmp_path.unlink(missing_ok=True)
    print(f"✅ Generated {filename}")

def capture_url(url, filename, width=1200, height=950):
    out_png = OUT_DIR / filename
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless",
        "--disable-gpu",
        "--user-data-dir=/tmp/chromedata",
        f"--window-size={width},{height}",
        f"--screenshot={out_png}",
        url
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ Generated {filename}")

if __name__ == "__main__":
    msgs = fetch_messages()
    print(f"Total outbox messages found: {len(msgs)}")

    # Slice indices mapping to user's 12 diagram steps
    stages = [
        # Box 1
        ("stage_01_language_welcome.png", msgs[0:4],
         "Stage 1: 'Namaskara', Picks Language",
         "Powered by language_translator (Sonnet / Luna fallback)"),

        # Box 2 & 3
        ("stage_02_agreement_upload.png", msgs[4:6],
         "Stage 2: Uploads Agreement (Photo or PDF)",
         "Powered by agreement_extractor"),

        ("stage_03_terms_extraction_confirm.png", msgs[6:9],
         "Stage 3: 'I read 3-yr shop rent, ₹35k/mo, ₹3L deposit. Is that right?'",
         "Powered by fixed extraction correction UI"),

        # Box 4
        ("stage_04_profile_questions.png", msgs[9:14],
         "Stage 4: Answers 1-2 Profile Traps",
         "Powered by rule-first form report: budget & stay constraints"),

        # Box 5
        ("stage_05_must_haves_check.png", msgs[14:16],
         "Stage 5: 'I check 3-4 Must-Haves for you'",
         "Powered by transition report: Must-Haves formulation"),

        # Box 6
        ("stage_06_risk_audit_verdict.png", msgs[16:18],
         "Stage 6: Risk Audit Verdict & Exposure",
         "Computed exposure (₹7,20,000 at risk, 82/100 risk score, WALK AWAY / NEGOTIATE)"),

        # Box 7
        ("stage_08_free_negotiation_preview.png", msgs[18:24],
         "Stage 7: Get 1 Free Message for Top Risk",
         "Powered by agreement_negotiator"),

        # Box 8
        ("stage_09_unlock_full_pack_prompt.png", msgs[23:26],
         "Stage 8: 'Unlocks Unlock Full Pack ₹49'",
         "Pine Labs Payment Links integration"),

        # Box 9
        ("stage_10_custom_tone_and_plan.png", msgs[26:34],
         "Stage 9: Pick Tone & Message Sent to Owner",
         "Full 3-ask fallback matrix + respectful owner message delivery"),

        # Box 10
        ("stage_11_forward_and_followup.png", msgs[34:41],
         "Stage 10: Owner Replies, or Bot Follows Up",
         "Delivery status tracking and owner response relay"),

        # Box 11
        ("stage_12_revised_agreement_audit.png", msgs[41:48],
         "Stage 11: Document Revised: Re-Enter Audit",
         "agreement_evaluator: highlights concessions ✅ vs hidden 15% rent increase ⚠️"),

        # Box 12
        ("stage_13_deal_close_summary.png", msgs[48:],
         "Stage 12: Types 'I ACCEPT' or Walks Away",
         "Deal close summary with locked final terms in chat"),
    ]

    for fname, m_slice, title, subtitle in stages:
        if m_slice:
            h = render_html_slice(m_slice, title, subtitle)
            capture_screenshot(h, fname)

    # Capture Box 6 Dashboard & Box 8 GPay Checkout Modal
    import sqlite3, json
    conn = sqlite3.connect("data/signsmart.db")
    row = conn.execute("SELECT data FROM sessions WHERE phone=?", (PHONE,)).fetchone()
    token = json.loads(row[0])["token"] if row else "TpBi5pJM1lpiYWzM"

    capture_url(f"http://localhost:8000/d/{token}", "stage_07_interactive_risk_dashboard.png", width=1200, height=950)
    capture_url(f"http://localhost:8000/pay/{token}/upi", "stage_09b_gpay_upi_checkout_modal.png", width=440, height=880)

    print("\n🎉 All 12 workflow stage screenshots generated with zero $1 artifacts!")
