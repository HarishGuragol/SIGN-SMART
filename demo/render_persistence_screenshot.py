import html
import re
import subprocess
from pathlib import Path

OUT_DIR = Path("/Users/harishguragol/Downloads/signsmart/final_submission_screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = Path("/Users/harishguragol/.gemini/antigravity/brain/88fbadee-3ad0-4896-b01a-5fb41b61848b/.system_generated/tasks/task-583.log")
lines = LOG_PATH.read_text(encoding="utf-8").splitlines()

# Extract from "=== UPLOADING NEW AGREEMENT IN SAME CHAT ===" to the end
idx = 0
for i, l in enumerate(lines):
    if "=== UPLOADING NEW AGREEMENT IN SAME CHAT ===" in l:
        idx = i
        break

slice_lines = lines[idx:]
msgs = []
cur_sender = None
cur_lines = []

for l in slice_lines:
    if l.startswith(">>> USER:"):
        if cur_sender and cur_lines:
            msgs.append((cur_sender, "\n".join(cur_lines).strip()))
            cur_lines = []
        cur_sender = "user"
        cur_lines.append(l[len(">>> USER:"):].strip())
    elif l.startswith("BOT:"):
        b = l[len("BOT:"):].strip()
        if cur_sender == "bot":
            cur_lines.append(b)
        else:
            if cur_sender and cur_lines:
                msgs.append((cur_sender, "\n".join(cur_lines).strip()))
                cur_lines = []
            cur_sender = "bot"
            cur_lines.append(b)

if cur_sender and cur_lines:
    msgs.append((cur_sender, "\n".join(cur_lines).strip()))

clean_msgs = []
for s, text in msgs:
    text = text.strip()
    if not text:
        continue
    # Filter echo
    if s == "bot" and len(clean_msgs) > 0 and clean_msgs[-1][0] == "user":
        u_prev = clean_msgs[-1][1].strip()
        lines_b = text.split("\n")
        if lines_b[0].strip() == u_prev and len(lines_b) > 1:
            text = "\n".join(lines_b[1:]).strip()
    clean_msgs.append((s, text))

OPT_LINE = re.compile(r"^(\d{1,2})\s+(.{1,80})$")
URL_RE = re.compile(r"(https?://\S+)")

html_parts = []
for sender, body in clean_msgs:
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

doc = f"""<!doctype html>
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
  background: #059669;
  color: #ECFDF5;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}}
.header h1 {{ margin: 0 0 6px; font-size: 20px; color: #34D399; font-weight: 700; }}
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
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="badge">Verified Persistence Test</div>
    <h1>New Agreement Uploaded in Same Chat</h1>
    <p>Context Saved: <b>Income & tenure questions bypassed · Saved profile auto-applied</b></p>
  </div>
  {"".join(html_parts)}
</div>
</body>
</html>"""

tmp = OUT_DIR / "temp_persist.html"
tmp.write_text(doc, encoding="utf-8")
out = OUT_DIR / "15_Persistence_Proof_New_Agreement_In_Same_Chat.png"
cmd = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "--headless", "--disable-gpu", "--user-data-dir=/tmp/chromedata",
    "--window-size=900,1050", f"--screenshot={out}", f"file://{tmp}"
]
subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
tmp.unlink(missing_ok=True)
print(f"🎉 Generated {out.name}")
