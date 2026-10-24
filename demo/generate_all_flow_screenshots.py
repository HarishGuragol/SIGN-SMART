import html
import re
import subprocess
from pathlib import Path
import httpx

OUT_DIR = Path("/Users/harishguragol/Downloads/signsmart/demo/screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Fetch all messages
r = httpx.get("http://localhost:8000/api/outbox?phone=web:demo")
msgs = r.json()

OPT_LINE = re.compile(r"^(\d{1,2})\s+(.{1,80})$")
URL_RE = re.compile(r"(https?://\S+)")

def render_html_for_slice(slice_msgs, title, subtitle):
    html_parts = []
    for m in slice_msgs:
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
  padding: 20px 24px;
  box-shadow: 0 16px 36px rgba(0,0,0,0.5);
}}
.header {{
  text-align: center;
  padding: 8px 0 16px;
  border-bottom: 1px solid #1E293B;
  margin-bottom: 20px;
}}
.header h1 {{ margin: 0 0 4px; font-size: 18px; color: #38BDF8; font-weight: 700; }}
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
  line-height: 1.5;
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
  padding: 6px 12px;
  border-radius: 10px;
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
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(subtitle)}</p>
  </div>
  {"".join(html_parts)}
</div>
</body>
</html>"""

# Define the flow steps
steps = [
    ("step_01_welcome_and_language.png", msgs[0:4], "Step 1: Language & Onboarding", "User initiates interaction and selects preferred language (English / Hindi / Kannada)"),
    ("step_02_agreement_extracted.png", msgs[4:9], "Step 2: Agreement Upload & Extraction", "AI Extractor agent reads commercial lease terms (₹35k/mo, ₹3L deposit, 36m lock-in)"),
    ("step_03_profile_and_musthaves.png", msgs[9:16], "Step 3: Risk Profile & Custom Must-Haves", "Dynamic questions tailored to tenant tenure intent and budget constraints"),
    ("step_04_risk_report_verdict.png", msgs[16:18], "Step 4: AI Risk Audit Verdict", "Computed money-at-risk exposure, overall risk score & advice (WALK AWAY / NEGOTIATE)"),
    ("step_06_upsell_and_payment_prompt.png", msgs[18:26], "Step 5: Negotiation Pack Upsell & Payment Link", "Free preview delivered, with ₹49 full unlock link via Google Pay / UPI QR"),
    ("step_08_tone_selection_and_plan.png", msgs[26:34], "Step 6: Negotiation Plan & Custom Tone", "Full clause-by-clause fallback matrix and respectful landlord message generated"),
    ("step_09_forward_to_owner.png", msgs[34:39], "Step 7: Approved Message Ready for Owner", "User forwards the calibrated request to the counterparty"),
    ("step_10_revised_agreement_comparison.png", msgs[39:48], "Step 8: Revised Agreement Forensic Audit", "AI Evaluator detects accepted concessions vs newly hidden 15% rent hike"),
    ("step_11_round_2_counter_offer.png", msgs[48:52], "Step 9: Round 2 Targeted Counter-Proposal", "Focused negotiation addressing only remaining uncapped penalties"),
]

for filename, slice_msgs, title, subtitle in steps:
    html_content = render_html_for_slice(slice_msgs, title, subtitle)
    tmp_html = OUT_DIR / f"{filename}.html"
    tmp_html.write_text(html_content, encoding="utf-8")
    png_path = OUT_DIR / filename
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless",
        "--disable-gpu",
        "--user-data-dir=/tmp/chromedata",
        "--window-size=900,1050",
        f"--screenshot={png_path}",
        f"file://{tmp_html}"
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tmp_html.unlink(missing_ok=True)
    print(f"Captured {filename}")

# Capture live web pages for Dashboard and Payment
dash_png = OUT_DIR / "step_05_interactive_risk_dashboard.png"
subprocess.run([
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "--headless", "--disable-gpu", "--user-data-dir=/tmp/chromedata",
    "--window-size=1200,950",
    f"--screenshot={dash_png}",
    "http://localhost:8000/d/TpBi5pJM1lpiYWzM"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("Captured step_05_interactive_risk_dashboard.png")

pay_png = OUT_DIR / "step_07_gpay_upi_checkout_modal.png"
subprocess.run([
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "--headless", "--disable-gpu", "--user-data-dir=/tmp/chromedata",
    "--window-size=440,880",
    f"--screenshot={pay_png}",
    "http://localhost:8000/pay/TpBi5pJM1lpiYWzM/upi"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("Captured step_07_gpay_upi_checkout_modal.png")

print("All step screenshots generated successfully!")
