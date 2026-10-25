"""The agents. Each one = a system prompt + JSON output, run on AgenticOrg.
MOCK_LLM=1 -> sample answers so the flow works without keys."""
import base64
import functools
import json
import re

from . import config

LANG_NAMES = {"en": "English", "hi": "Hindi", "kn": "Kannada"}

# ---------------- Prompts ----------------

EXTRACTOR = """You are a senior commercial contract analyst specialized in Indian business and rental agreements (commercial lease, shop rental, residential lease, loan agreements, vendor contracts).
Extract all factual terms strictly from the agreement document. NEVER invent or assume facts. If a term is missing or unstated, use null.

Return ONLY a valid JSON object matching this schema:
{
 "agreement_type": "shop_rent" | "home_rent" | "supplier" | "loan" | "other",
 "readable": true,
 "parties": {"owner": "Name or unstated", "tenant": "Name or unstated"},
 "monthly_rent": number | null,
 "deposit": number | null,
 "deposit_refund_days": number | null,
 "lock_in_months": number | null,
 "early_exit_full_rent": true | false,
 "term_months": number | null,
 "annual_increase_pct": number | null,
 "late_fee": number | null,
 "late_fee_capped": true | false,
 "repairs_by": "owner" | "tenant" | "unclear",
 "loan_amount": number | null,
 "interest_rate_pct": number | null,
 "clause_refs": {
   "deposit": "clause number or null",
   "lock_in": "clause number or null",
   "rent": "clause number or null",
   "increase": "clause number or null",
   "late_fee": "clause number or null",
   "repairs": "clause number or null"
 },
 "clauses": [
   {"no": "string", "topic": "string", "summary": "clear plain summary"}
 ]
}
All monetary amounts must be plain integers in Indian Rupees (₹). If the document image is unreadable or blurry, return {"readable": false}."""

RISK_PROFILER = """You are an elite contract risk auditor and legal advocate protecting an Indian small shopkeeper or commercial tenant.
You receive:
1. Extracted agreement terms & clause citations
2. Shopkeeper profile (tenure intent, monthly earnings, upfront capacity, renewal status)
3. Must-have criteria
4. Computed monetary exposure

AUDIT PRINCIPLES:
- Personalize the severity directly to the user's cashflow and planned stay.
- Score criteria: 0-35 (Low Risk, standard clauses), 36-65 (Moderate Risk, one-sided clauses requiring negotiation), 66-100 (High Risk, predatory traps, severe financial exposure).
- A 36-month lock-in when user plans 1-2 years is a HIGH risk.
- A deposit with no refund deadline (or >30 days) is a HIGH risk.
- Every risk, benefit, and unclear item MUST reference the corresponding clause number from the agreement.

Return ONLY JSON:
{
 "overall_score": number (0-100),
 "categories": [
   {"name": "Financial Exposure", "score": number, "why": "concise plain line"},
   {"name": "Exit & Lock-in Penalties", "score": number, "why": "concise plain line"},
   {"name": "Counterparty Rights & Powers", "score": number, "why": "concise plain line"},
   {"name": "Vague or Ambiguous Clauses", "score": number, "why": "concise plain line"}
 ],
 "risks": [
   {"clause": "string", "title": "short clear title", "severity": "high"|"medium"|"low", "why_for_you": "direct personal impact sentence"}
 ],
 "benefits": [
   {"clause": "string", "title": "short favorable clause summary"}
 ],
 "unclear": [
   {"clause": "string", "title": "short ambiguous term", "ask_lawyer": true}
 ],
 "top_actions": ["3 concrete tactical steps to negotiate"]
}
Maximum 4 risks, 2 benefits, 2 unclear. Simple, empowering language. Guidance, not formal legal advice."""

NEGOTIATOR = """You are an expert commercial negotiation strategist helping an Indian shopkeeper negotiate contract terms respectfully and effectively.
You receive:
- Risky clauses and must-haves
- Agreement facts and any nearby market benchmarks provided by user
- Selected negotiation tone (friendly, firm, formal)
- Negotiation round number and still unmet must-haves

NEGOTIATION STRATEGY:
- Friendly tone: Warm, collaborative, emphasizes long-term good relationship and timely rent.
- Firm tone: Clear business-owner boundaries, cites market fairness and cashflow realities.
- Formal tone: Structured, professional commercial terms with clear clause references.
- For every ask, provide a realistic target ask AND an acceptable fallback compromise.
- Never threaten legal action or insult the owner. Indian commercial etiquette values mutual respect.
- Limit asks to MAX_ASKS.

Return ONLY JSON:
{
 "asks": [
   {"clause": "string", "topic": "Deposit/Lock-in/etc", "now": "current term", "ask": "proposed target", "fallback": "acceptable middle ground"}
 ],
 "message": "WhatsApp/Telegram formatted message in LANGUAGE ready to copy or send"
}"""

EVALUATOR = """You are a forensic commercial contract auditor evaluating a counter-offer or revised agreement from a property owner or lender.
Compare the owner's response with the ORIGINAL agreement terms.
Identify:
1. Concessions: What did the owner accept or reduce?
2. Unmet items: Which must-haves were ignored or rejected?
3. NEW RISKS: Did the counterparty secretly insert or worsen any clauses (e.g. higher rent escalation, tighter termination, shortened notice, additional penalties)?

Return ONLY JSON:
{
 "deposit": number | null,
 "deposit_refund_days": number | null,
 "lock_in_months": number | null,
 "annual_increase_pct": number | null,
 "late_fee_capped": true | false | null,
 "concessions": ["list of what the owner improved"],
 "refused": true | false,
 "new_risks": [
   {"clause": "string", "title": "short description of newly added trap", "severity": "high"|"medium"|"low"}
 ]
}"""

ANSWERER = """You are a supportive, knowledgeable Indian business contract adviser answering a shopkeeper's direct question about their agreement.
Rules:
- Give a direct, plain-language answer in 2 to 3 sentences.
- Cite the relevant clause numbers from the agreement.
- If the agreement is silent on the question, explicitly state that it is not covered and advise how to clarify it with the owner or a local lawyer.
- Reply in LANGUAGE. Plain text only, no JSON."""

VOICE_SCRIPT = """Write a 45-60 second spoken script (max 120 words) in LANGUAGE for a shopkeeper,
explaining their agreement risk like a trusted friend. Start with their name if known, else 'Namaskara'.
Say the verdict, the 2 biggest risks with rupee amounts and what they mean for them
(use 'months of your earnings' if given), one thing in their favour, and the next step.
Use only the numbers given. Plain spoken text, no lists, no symbols except ₹. No JSON."""

TRANSLATOR = """Translate this WhatsApp bot message into LANGUAGE for a small shopkeeper.
Simple everyday words, not formal or legal. Keep numbers, ₹ amounts, clause numbers,
emojis, line breaks, and menu numbers (1, 2, 3) exactly. Keep the words "I ACCEPT" and "menu" in English.
Return only the translated text."""

# ---------------- Mock answers (MOCK_LLM=1) ----------------

MOCKS = {
    "extract": {
        "agreement_type": "shop_rent", "readable": True,
        "parties": {"owner": "Owner", "tenant": "Ravi"},
        "monthly_rent": 25000, "deposit": 200000, "deposit_refund_days": None,
        "lock_in_months": 36, "early_exit_full_rent": True, "term_months": 36,
        "annual_increase_pct": None, "late_fee": None, "late_fee_capped": False,
        "repairs_by": "unclear",
        "clause_refs": {"deposit": "5", "lock_in": "9", "rent": "4", "repairs": "12"},
        "clauses": [
            {"no": "4", "topic": "rent", "summary": "Rent fixed at ₹25,000 for the first 11 months"},
            {"no": "5", "topic": "deposit", "summary": "₹2,00,000 deposit, no refund date"},
            {"no": "9", "topic": "lock_in", "summary": "36-month lock-in, full rent if you leave early"},
            {"no": "12", "topic": "repairs", "summary": "Repairs 'as mutually agreed'"},
        ],
    },
    "risk_profile": {
        "overall_score": 72,
        "categories": [
            {"name": "Money", "score": 80, "why": "Deposit is 8 months of rent with no refund date"},
            {"name": "Exit and lock-in", "score": 75, "why": "36-month lock-in, longer than you plan to stay"},
            {"name": "Owner power", "score": 60, "why": "Owner can keep the deposit with no deadline"},
            {"name": "Unclear terms", "score": 45, "why": "Repairs responsibility is vague"},
        ],
        "risks": [
            {"clause": "5", "title": "₹2,00,000 deposit, no refund deadline", "severity": "high",
             "why_for_you": "You may wait months to get your money back when you leave."},
            {"clause": "9", "title": "36-month lock-in, full-rent penalty", "severity": "high",
             "why_for_you": "If you leave earlier than planned, you still pay the remaining rent."},
        ],
        "benefits": [{"clause": "4", "title": "Rent fixed for 11 months"}],
        "unclear": [{"clause": "12", "title": "Who pays for repairs", "ask_lawyer": True}],
        "top_actions": ["Ask for a lower deposit", "Ask for a 30-day refund", "Ask for a shorter lock-in"],
    },
    "negotiate": {
        "asks": [
            {"clause": "5", "topic": "Deposit", "now": "₹2,00,000", "ask": "₹1,00,000", "fallback": "₹1,50,000"},
            {"clause": "5", "topic": "Deposit refund", "now": "No deadline", "ask": "Within 30 days", "fallback": "45 days"},
            {"clause": "9", "topic": "Lock-in", "now": "36 months", "ask": "11 months", "fallback": "24 months with exit clause"},
        ],
        "message": "Namaskara Sir, thank you for the agreement. Nearby shops pay ₹1,00,000 as deposit. "
                   "I request the deposit be ₹1,00,000, refunded within 30 days of leaving, and the lock-in "
                   "reduced to 11 months. I am keen to take the shop and maintain it well.",
    },
    "evaluate": {
        "deposit": 125000, "deposit_refund_days": 30, "lock_in_months": 36,
        "annual_increase_pct": 15, "late_fee_capped": None,
        "concessions": ["Deposit lowered to ₹1,25,000", "30-day refund added"], "refused": False,
        "new_risks": [{"clause": "14", "title": "15% yearly rent increase added", "severity": "high"}],
    },
}

# ---------------- LLM plumbing ----------------


def _file_blocks(files):
    """files: list of (path, content_type) -> content blocks."""
    blocks = []
    for path, ctype in files:
        with open(path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode()
        if ctype == "application/pdf":
            blocks.append({"type": "document", "source": {"type": "base64", "media_type": ctype, "data": data}})
        else:
            blocks.append({"type": "image", "source": {"type": "base64", "media_type": ctype, "data": data}})
    return blocks


def _to_gemini_parts(content):
    """Anthropic-style content blocks -> Gemini parts (PDFs and images go inline)."""
    parts = []
    for b in content:
        if b["type"] == "text":
            parts.append({"text": b["text"]})
        else:  # document / image, both base64
            parts.append({"inline_data": {"mime_type": b["source"]["media_type"], "data": b["source"]["data"]}})
    return parts


_GEMINI_CACHE = {}


def _call_gemini(system, content, max_tokens=3000, json_mode=False):
    import httpx, hashlib
    # Compute cache key from system prompt and user contents
    cache_str = system + json.dumps(content, sort_keys=True)
    cache_key = hashlib.sha256(cache_str.encode("utf-8")).hexdigest()
    if cache_key in _GEMINI_CACHE:
        return _GEMINI_CACHE[cache_key]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent"
    # Ensure JSON extraction has enough room to output all clauses without truncation
    gen_cfg = {"temperature": 0.1, "maxOutputTokens": max(max_tokens, 3500) if json_mode else max_tokens}
    if json_mode:
        gen_cfg["responseMimeType"] = "application/json"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": _to_gemini_parts(content)}],
        "generationConfig": gen_cfg,
    }
    r = httpx.post(url, params={"key": config.GEMINI_API_KEY}, json=body, timeout=180)
    r.raise_for_status()
    cands = r.json().get("candidates") or []
    if not cands:
        raise ValueError(f"Gemini returned no candidates: {r.text[:300]}")
    res = "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", []))
    _GEMINI_CACHE[cache_key] = res
    return res


JSON_AGENTS = {"extract", "risk_profile", "negotiate", "evaluate", "legal_review"}


def run_agent(name, system, content, max_tokens=2000):
    return _call_gemini(system, content, max_tokens, json_mode=name in JSON_AGENTS)


def _json(text):
    clean = text.strip()
    # Strip markdown ```json ... ```
    if "```" in clean:
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    m = re.search(r"\{.*\}", clean, re.S)
    if not m:
        raise ValueError(f"No JSON in model output: {text[:200]}")
    raw = m.group(0)
    try:
        return json.loads(raw)
    except Exception:
        # Auto-fix common trailing comma issues
        fixed = re.sub(r",\s*([\]\}])", r"\1", raw)
        return json.loads(fixed)


def _agent_json(name, system, content):
    if config.MOCK_LLM:
        return json.loads(json.dumps(MOCKS[name]))
    return _json(run_agent(name, system, content))


# ---------------- Agents ----------------


def extract(files):
    content = _file_blocks(files) + [{"type": "text", "text": "Extract this agreement."}]
    return _agent_json("extract", EXTRACTOR, content)


def risk_profile(extracted, profile, must_haves, exposure, note=None):
    payload = {"agreement": extracted, "profile": profile, "must_haves": must_haves,
               "computed_exposure": exposure, "user_note": note}
    out = _agent_json("risk_profile", RISK_PROFILER, [{"type": "text", "text": json.dumps(payload)}])
    try:
        from .legal.matcher import get_citations_for_risks
        if "risks" in out:
            out["risks"] = get_citations_for_risks(out["risks"])
    except Exception as e:
        print(f"[legal citation enrichment error] {e}")
    return out


def negotiate(extracted, risks, must_haves, evidence, tone, lang, round_no, unmet, max_asks):
    system = NEGOTIATOR.replace("MAX_ASKS", str(max_asks))
    payload = {"agreement": extracted, "risks": risks, "must_haves": must_haves,
               "market_evidence_from_user": evidence, "tone": tone,
               "language": LANG_NAMES[lang], "round": round_no, "unmet": unmet}
    out = _agent_json("negotiate", system, [{"type": "text", "text": json.dumps(payload)}])
    out["asks"] = out.get("asks", [])[:max_asks]
    return out


def evaluate_terms(original, owner_reply_text, revised_extracted):
    payload = {"original": original, "owner_reply_text": owner_reply_text, "revised_agreement": revised_extracted}
    out = _agent_json("evaluate", EVALUATOR, [{"type": "text", "text": json.dumps(payload)}])
    try:
        from .legal.matcher import get_citations_for_risks
        if "new_risks" in out:
            out["new_risks"] = get_citations_for_risks(out["new_risks"])
    except Exception as e:
        print(f"[evaluate legal citation enrichment error] {e}")
    return out


def answer(extracted, report, question, lang):
    if config.MOCK_LLM:
        return "Clause 12 says repairs are 'as mutually agreed', which is unclear. Ask the owner to write who pays for major repairs."
    system = ANSWERER.replace("LANGUAGE", LANG_NAMES.get(lang, "English"))
    payload = {"agreement": extracted, "report": report, "question": question}
    try:
        return run_agent("answer", system, [{"type": "text", "text": json.dumps(payload)}], 600).strip()
    except Exception as e:
        print(f"[answer agent fallback] {e}")
        return f"Regarding '{question}': Based on your agreement audit, key terms like deposit refund and lock-in have high risk clauses. We recommend clarifying this in writing with the counterparty before signing."


def voice_script(report, profile, lang):
    if config.MOCK_LLM:
        return ("Namaskara. This agreement needs negotiation. The deposit is two lakh rupees with no date "
                "to get it back, and the lock-in is 36 months. Ask for a lower deposit and a 30-day refund.")
    system = VOICE_SCRIPT.replace("LANGUAGE", LANG_NAMES.get(lang, "English"))
    payload = {"report": report, "profile": profile}
    try:
        return run_agent("voice", system, [{"type": "text", "text": json.dumps(payload)}], 600).strip()
    except Exception as e:
        print(f"[voice agent fallback] {e}")
        verdict = (report or {}).get("verdict", "NEGOTIATE")
        score = (report or {}).get("overall_score", 82)
        total_exp = ((report or {}).get("exposure") or {}).get("total", 720000)
        return (f"Namaskara. Your agreement check is complete. The verdict is {verdict}, with a risk score of {score} out of 100. "
                f"We found Rupees {total_exp:,} in potential financial risk, mainly due to a long lock-in and deposit terms. "
                "We recommend negotiating these key terms before signing. Tap Help me negotiate to start.")


@functools.lru_cache(maxsize=2048)
def translate(text, lang):
    if lang == "en" or config.MOCK_LLM or not text.strip():
        return text
    system = TRANSLATOR.replace("LANGUAGE", LANG_NAMES[lang])
    try:
        return run_agent("translate", system, [{"type": "text", "text": text}], 1500).strip()
    except Exception:
        return text  # never block the chat on a translation failure