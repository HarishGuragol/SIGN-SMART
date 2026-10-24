import html
import re
from pathlib import Path
from app import channel, config

OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

msgs = channel.OUTBOX.get("web:demo", [])
OPT_LINE = re.compile(r"^(\d{1,2})\s+(.{1,80})$")
URL_RE = re.compile(r"(https?://\S+)")

html_parts = []
for m in msgs:
    sender = m.get("from", "bot")
    body = m.get("body", "")
    is_user = sender == "user"
    
    # parse lines
    lines = body.split("\n")
    opt_lines = []
    text_lines = []
    link_lines = []
    for line in lines:
        trimmed = line.strip()
        mo = OPT_LINE.match(trimmed)
        if mo and not URL_RE.search(trimmed):
            opt_lines.append(mo.group(2))
            continue
        if URL_RE.search(trimmed) and URL_RE.sub("", trimmed).strip() == "":
            link_lines.append(trimmed)
            continue
        text_lines.append(line)
    
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
        links = "".join([f'<a class="linkbtn" href="{html.escape(l)}" target="_blank">🔗 Open Link: {html.escape(l)}</a>' for l in link_lines])
        html_parts.append(f'<div class="links">{links}</div>')

full_html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Sign Smart Chat Demo</title>
<style>
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #0F172A;
  color: #F8FAFC;
  margin: 0;
  padding: 24px;
  display: flex;
  justify-content: center;
}}
.container {{
  max-width: 650px;
  width: 100%;
}}
.header {{
  text-align: center;
  padding: 16px 0 24px;
  border-bottom: 1px solid #334155;
  margin-bottom: 24px;
}}
.header h1 {{ margin: 0 0 6px; font-size: 22px; color: #38BDF8; }}
.header p {{ margin: 0; color: #94A3B8; font-size: 13px; }}
.row {{
  display: flex;
  margin-bottom: 14px;
}}
.row.bot {{ justify-content: flex-start; }}
.row.user {{ justify-content: flex-end; }}
.bubble {{
  max-width: 82%;
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
}}
.options {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: -6px 0 16px 8px;
}}
.btn {{
  background: #334155;
  color: #38BDF8;
  padding: 6px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
  border: 1px solid #475569;
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
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  margin-bottom: 4px;
}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Sign Smart · Full Verification Chat</h1>
    <p>Live session output: End-to-End Extraction, Risk Audit & Negotiation Flow</p>
  </div>
  {"".join(html_parts)}
</div>
</body>
</html>
"""

Path("demo/screenshots/chat_preview.html").write_text(full_html, encoding="utf-8")
print(f"Generated demo/screenshots/chat_preview.html with {len(msgs)} messages")
