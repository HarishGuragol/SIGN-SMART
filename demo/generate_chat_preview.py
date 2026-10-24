import html
import re
from pathlib import Path

LOG_PATH = Path("/Users/harishguragol/.gemini/antigravity/brain/88fbadee-3ad0-4896-b01a-5fb41b61848b/.system_generated/tasks/task-273.log")
lines = LOG_PATH.read_text(encoding="utf-8").splitlines()

msgs = []
cur_sender = None
cur_text = []

for line in lines:
    if line.startswith(">>> USER:"):
        if cur_sender and cur_text:
            msgs.append((cur_sender, "\n".join(cur_text).strip()))
            cur_text = []
        cur_sender = "user"
        cur_text.append(line[len(">>> USER:"):].strip())
    elif line.startswith("BOT:"):
        # bot message
        b_text = line[len("BOT:"):].strip()
        if cur_sender == "bot":
            cur_text.append(b_text)
        else:
            if cur_sender and cur_text:
                msgs.append((cur_sender, "\n".join(cur_text).strip()))
                cur_text = []
            cur_sender = "bot"
            cur_text.append(b_text)

if cur_sender and cur_text:
    msgs.append((cur_sender, "\n".join(cur_text).strip()))

OPT_LINE = re.compile(r"^(\d{1,2})\s+(.{1,80})$")
URL_RE = re.compile(r"(https?://\S+)")

html_parts = []
for sender, body in msgs:
    is_user = sender == "user"
    lines = body.split("\n")
    opt_lines = []
    text_lines = []
    link_lines = []
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

full_html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Sign Smart Chat Log</title>
<style>
* {{ box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #0B1120;
  color: #F8FAFC;
  margin: 0;
  padding: 32px 16px;
  display: flex;
  justify-content: center;
}}
.container {{
  max-width: 680px;
  width: 100%;
  background: #0F172A;
  border: 1px solid #1E293B;
  border-radius: 24px;
  padding: 24px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.5);
}}
.header {{
  text-align: center;
  padding: 12px 0 20px;
  border-bottom: 1px solid #1E293B;
  margin-bottom: 24px;
}}
.header h1 {{ margin: 0 0 6px; font-size: 20px; color: #38BDF8; font-weight: 700; }}
.header p {{ margin: 0; color: #94A3B8; font-size: 13px; }}
.row {{
  display: flex;
  margin-bottom: 14px;
}}
.row.bot {{ justify-content: flex-start; }}
.row.user {{ justify-content: flex-end; }}
.bubble {{
  max-width: 84%;
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
  margin: -6px 0 16px 8px;
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
  margin: -6px 0 16px 8px;
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
  margin-bottom: 6px;
}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Sign Smart · Live Verified Session Flow</h1>
    <p>Document Extraction → Risk Profiling → Negotiation Pack → Counter-Offer Evaluation</p>
  </div>
  {"".join(html_parts)}
</div>
</body>
</html>
"""

out_file = Path("demo/screenshots/chat_preview.html")
out_file.parent.mkdir(parents=True, exist_ok=True)
out_file.write_text(full_html, encoding="utf-8")
print(f"Generated {out_file} with {len(msgs)} chat turns")
