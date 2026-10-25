"""Build the legal knowledge base from official statute text.

Sources (all public, authoritative text):
  * Model Tenancy Act, 2021 - MoHUA PDF (app/legal/sources/model_tenancy_act_2021.pdf)
  * Central Acts + Karnataka Rent Act sections - fetched from indiankanoon.org,
    which mirrors the India Code text. Each fetched page's title is checked to be
    exactly "Section N in The <Act>" so we never store the wrong provision.

Output: app/legal/kb.json  ->  [{id, act, section, title, text, url, embedding}]
Kept deliberately small (a few hundred KB-2 MB) - no vector DB needed.

Run:  .venv_local/bin/python -m app.legal.build_kb
"""
import html
import json
import re
import sys
import time
from pathlib import Path

import httpx

from app import config

HERE = Path(__file__).parent
SRC = HERE / "sources"
OUT = HERE / "kb.json"
UA = {"User-Agent": "Mozilla/5.0 (SignSmart legal KB builder; contact via GitHub)"}

MTA_URL = "https://mohua.gov.in/static/uploads/2025/11/0e6aea16d11ed1a622f1de43ff3710b4.pdf"

# (Act title exactly as Indian Kanoon names it, [sections])
SECTIONS = [
    ("The Indian Contract Act, 1872", [10, 14, 16, 19, 23, 73, 74]),
    ("The Transfer of Property Act, 1882", [105, 106, 107, 108, 111, 114]),
    ("The Registration Act, 1908", [17, 49]),
    ("The Karnataka Rent Act, 1999", [11, 15, 21, 27]),
]


def _clean(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def fetch_section(client, act, sec):
    want = f"Section {sec} in {act}"
    q = f'"{want}" doctypes:laws'
    r = client.get("https://indiankanoon.org/search/", params={"formInput": q})
    ids = re.findall(r'href="/doc/(\d+)/"', r.text)
    for doc_id in dict.fromkeys(ids[:8]):
        url = f"https://indiankanoon.org/doc/{doc_id}/"
        page = client.get(url).text
        m = re.search(r'<h2 class="doc_title">(.*?)</h2>', page, re.S)
        title = _clean(m.group(1)) if m else ""
        if title.lower() != want.lower():
            time.sleep(0.5)
            continue
        body = re.search(r'<section class="akn-section".*?</section>', page, re.S)
        if not body:
            body = re.search(r'<div class="judgments">(.*?)<div class="ad_doc"', page, re.S)
        text = _clean(body.group(0)) if body else ""
        if len(text) < 40:
            return None
        return {"act": act.replace("The ", "", 1), "section": str(sec), "title": title,
                "text": text, "url": url}
    return None


def mta_chunks():
    from pypdf import PdfReader
    pdf = SRC / "model_tenancy_act_2021.pdf"
    if not pdf.exists():
        pdf.write_bytes(httpx.get(MTA_URL, headers=UA, timeout=90, follow_redirects=True).content)
    text = "\n".join(p.extract_text() or "" for p in PdfReader(str(pdf)).pages)
    text = re.sub(r"[ \t]+", " ", text)
    # Section headings look like "7. (1) ..." or "11. Security deposit.—" at line start
    parts = re.split(r"\n(?=\s?(\d{1,2})\.\s+[A-Z(])", text)
    chunks, cur_no, buf = [], None, parts[0]
    i = 1
    while i < len(parts):
        if cur_no is not None:
            chunks.append((cur_no, buf))
        cur_no, buf = parts[i], parts[i + 1] if i + 1 < len(parts) else ""
        i += 2
    if cur_no is not None:
        chunks.append((cur_no, buf))
    out, seen = [], set()
    for no, body in chunks:
        body = re.sub(r"\s+", " ", body).strip()
        if len(body) < 80 or int(no) > 60 or no in seen:
            continue
        seen.add(no)
        first = re.split(r"[.—:-]", body, maxsplit=1)[0][:90]
        out.append({"act": "Model Tenancy Act, 2021", "section": no,
                    "title": f"Section {no}, Model Tenancy Act 2021 - {first}",
                    "text": body[:6000], "url": MTA_URL})
    return out


def embed(texts, task="RETRIEVAL_DOCUMENT"):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_EMBED_MODEL}:batchEmbedContents"
    reqs = [{"model": f"models/{config.GEMINI_EMBED_MODEL}", "content": {"parts": [{"text": t[:8000]}]},
             "taskType": task, "outputDimensionality": 768} for t in texts]
    vecs = []
    for i in range(0, len(reqs), 50):
        r = httpx.post(url, params={"key": config.GEMINI_API_KEY}, json={"requests": reqs[i:i + 50]}, timeout=120)
        r.raise_for_status()
        vecs += [[round(x, 5) for x in e["values"]] for e in r.json()["embeddings"]]
    return vecs


def main():
    docs = mta_chunks()
    print(f"Model Tenancy Act: {len(docs)} sections")
    with httpx.Client(headers=UA, timeout=30, follow_redirects=True) as c:
        for act, secs in SECTIONS:
            for s in secs:
                d = fetch_section(c, act, s)
                print(("  ok   " if d else "  MISS ") + f"{act} s.{s}")
                if d:
                    docs.append(d)
                time.sleep(1)  # be polite to the source
    vecs = embed([f"{d['title']}\n{d['text']}" for d in docs])
    for i, (d, v) in enumerate(zip(docs, vecs)):
        d["id"] = i
        d["embedding"] = v
    OUT.write_text(json.dumps(docs, ensure_ascii=False))
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB, {len(docs)} provisions)")


if __name__ == "__main__":
    sys.exit(main())
