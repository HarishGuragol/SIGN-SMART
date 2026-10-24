"""The agents. Each one = a system prompt + JSON output, run on AgenticOrg.
MOCK_LLM=1 -> sample answers so the flow works without keys."""
import base64
import functools
import json
import re

from . import config

LANG_NAMES = {"en": "English", "hi": "Hindi", "kn": "Kannada"}

# ---------------- Prompts ----------------

EXTRACTOR = """You read agreements (rent, supplier, loan) for small Indian shopkeepers.
Extract facts ONLY from the document. Never invent. Use null when not stated.
Return ONLY JSON:
{
 "agreement_type": "shop_rent|home_rent|supplier|loan|other",
 "readable": true,
 "parties": {"owner": "", "tenant": ""},
 "monthly_rent": number|null,
 "deposit": number|null,
 "deposit_refund_days": number|null,
 "lock_in_months": number|null,
 "early_exit_full_rent": true|false,
 "term_months": number|null,
 "annual_increase_pct": number|null,
 "late_fee": number|null,
 "late_fee_capped": true|false,
 "repairs_by": "owner|tenant|unclear",
 "clause_refs": {"deposit": "5", "lock_in": "9", "rent": "4", "increase": null, "late_fee": null, "repairs": "12"},
 "clauses": [{"no": "5", "topic": "deposit", "summary": "one plain line"}]
}
Amounts in rupees as plain numbers. If the image is unreadable, return {"readable": false}."""

RISK_PROFILER = """You are a risk analyst protecting a small Indian shopkeeper.
You get: the extracted agreement, the shopkeeper's profile (planned stay, monthly earnings,
upfront limit, new or renewal), their must-haves, and money exposure ALREADY computed in code.
Personalise the risk to THEIR situation. Use the computed numbers as given; do not invent numbers.
Every risk and benefit MUST cite a clause number that exists in the agreement.
Return ONLY JSON:
{
 "overall_score": 0-100,
 "categories": [
   {"name": "Money", "score": 0-100, "why": "one line"},
   {"name": "Exit and lock-in", "score": 0-100, "why": ""},
   {"name": "Owner power", "score": 0-100, "why": ""},
   {"name": "Unclear terms", "score": 0-100, "why": ""}
 ],
 "risks": [{"clause": "5", "title": "short", "severity": "high|medium|low", "why_for_you": "one simple sentence about THEIR situation"}],
 "benefits": [{"clause": "4", "title": "short"}],
 "unclear": [{"clause": "12", "title": "short", "ask_lawyer": true}],
 "top_actions": ["max 3 short actions"]
}
Max 4 risks, 2 benefits, 2 unclear. Simple words. Guidance, not legal advice."""

NEGOTIATOR = """You help a small shopkeeper ask the owner for better terms, politely.
You get the risks, must-haves, agreement facts, any market evidence the shopkeeper gave,
tone, round number, and which must-haves are still unmet.
RULES:
- Never invent market rates. Use ONLY evidence the user gave. If none, argue from the agreement itself.
- Each ask has a fallback the user can accept.
- Round 2: thank the owner for what was agreed, ask only about what is still open.
- The message is short, respectful, WhatsApp style, in the requested language. No legal threats.
- Limit asks to MAX_ASKS.
Return ONLY JSON:
{"asks": [{"clause": "5", "topic": "Deposit", "now": "₹2,00,000", "ask": "₹1,00,000", "fallback": "₹1,50,000"}],
 "message": "the message text"}"""

EVALUATOR = """You compare the owner's reply (text and/or revised agreement) with the ORIGINAL agreement.
Extract the NEW values the owner agreed to. Use null if not mentioned (meaning unchanged).
Also list NEW risks: anything added or changed that was NOT in the original and hurts the shopkeeper.
Set refused=true only if the owner clearly refuses to negotiate at all.
Return ONLY JSON:
{"deposit": number|null, "deposit_refund_days": number|null, "lock_in_months": number|null,
 "annual_increase_pct": number|null, "late_fee_capped": true|false|null,
 "concessions": ["short lines"], "refused": false,
 "new_risks": [{"clause": "14", "title": "short", "severity": "high|medium|low"}]}"""

ANSWERER = """Answer the shopkeeper's question about THEIR agreement in 2-4 simple sentences,
citing clause numbers. If the agreement doesn't say, say so and suggest asking the owner or a lawyer.
Reply in LANGUAGE. Plain text, no JSON."""

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


def _call_llm(system, content, max_tokens=2000):
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=config.LLM_MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": content}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


# Which AgenticOrg agent type handles each step (the "custom agent type" you created).
AGENTICORG_TYPES = {
    "extract": "agreement_extractor",
    "risk_profile": "agreement_risk_profiler",
    "negotiate": "agreement_negotiator",
    "evaluate": "agreement_evaluator",
    "translate": "language_translator",
    "answer": "chat_agent",
    "voice": "chat_agent",
}

_aorg_client = None


def _agenticorg():
    global _aorg_client
    if _aorg_client is None:
        from agenticorg import AgenticOrg
        kwargs = {"api_key": config.AGENTICORG_API_KEY}
        if config.AGENTICORG_URL:
            kwargs["base_url"] = config.AGENTICORG_URL  # hackathon instance
        try:
            _aorg_client = AgenticOrg(**kwargs)
        except TypeError:
            # SDK may not take base_url; run help(AgenticOrg) to find the right name
            _aorg_client = AgenticOrg(api_key=config.AGENTICORG_API_KEY)
    return _aorg_client


def _to_agenticorg_inputs(system, content):
    """PDFs: text extracted here. Photos: sent as base64 for the agent's model to read."""
    texts, images, doc_text = [], [], []
    for b in content:
        if b["type"] == "text":
            texts.append(b["text"])
        elif b["type"] == "document":
            try:
                import io
                from pypdf import PdfReader
                pdf = PdfReader(io.BytesIO(base64.b64decode(b["source"]["data"])))
                doc_text.append("\n".join(p.extract_text() or "" for p in pdf.pages))
            except Exception as e:
                print(f"[pdf text extraction failed] {e}")
        elif b["type"] == "image":
            images.append({"media_type": b["source"]["media_type"], "data_base64": b["source"]["data"]})
    inputs = {"instructions": system, "input": "\n".join(texts)}
    if doc_text:
        inputs["document_text"] = "\n\n".join(doc_text)
    if images:
        inputs["images"] = images
    return inputs


def run_on_agenticorg(agent_name, system, content):
    """Run one of our AgenticOrg employees via the SDK (pip install agenticorg)."""
    import os
    agent = os.getenv(f"AGENTICORG_AGENT_{agent_name.upper()}") or AGENTICORG_TYPES[agent_name]
    result = _agenticorg().agents.run(agent, inputs=_to_agenticorg_inputs(system, content))
    print(f"[agenticorg] {agent}: status={result.status} confidence={getattr(result, 'confidence', None)}")
    out = result.output
    if isinstance(out, (dict, list)):
        if isinstance(out, dict) and len(out) == 1 and isinstance(next(iter(out.values())), (str, dict)):
            inner = next(iter(out.values()))
            return inner if isinstance(inner, str) else json.dumps(inner)
        return json.dumps(out)
    return str(out)


def run_agent(name, system, content, max_tokens=2000):
    if config.AGENT_BACKEND == "agenticorg":
        try:
            return run_on_agenticorg(name, system, content)
        except Exception as e:
            print(f"[agenticorg failed for {name}] {e}")
            if config.ANTHROPIC_API_KEY:  # emergency fallback only if a direct key is set
                return _call_llm(system, content, max_tokens)
            raise
    return _call_llm(system, content, max_tokens)


def _json(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"No JSON in model output: {text[:200]}")
    return json.loads(m.group(0))


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
    return _agent_json("risk_profile", RISK_PROFILER, [{"type": "text", "text": json.dumps(payload)}])


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
    return _agent_json("evaluate", EVALUATOR, [{"type": "text", "text": json.dumps(payload)}])


def answer(extracted, report, question, lang):
    if config.MOCK_LLM:
        return "Clause 12 says repairs are 'as mutually agreed', which is unclear. Ask the owner to write who pays for major repairs."
    system = ANSWERER.replace("LANGUAGE", LANG_NAMES[lang])
    payload = {"agreement": extracted, "report": report, "question": question}
    return run_agent("answer", system, [{"type": "text", "text": json.dumps(payload)}], 600).strip()


def voice_script(report, profile, lang):
    if config.MOCK_LLM:
        return ("Namaskara. This agreement needs negotiation. The deposit is two lakh rupees with no date "
                "to get it back, and the lock-in is 36 months. Ask for a lower deposit and a 30-day refund.")
    system = VOICE_SCRIPT.replace("LANGUAGE", LANG_NAMES[lang])
    payload = {"report": report, "profile": profile}
    return run_agent("voice", system, [{"type": "text", "text": json.dumps(payload)}], 600).strip()


@functools.lru_cache(maxsize=2048)
def translate(text, lang):
    if lang == "en" or config.MOCK_LLM or not text.strip():
        return text
    system = TRANSLATOR.replace("LANGUAGE", LANG_NAMES[lang])
    try:
        return run_agent("translate", system, [{"type": "text", "text": text}], 1500).strip()
    except Exception:
        return text  # never block the chat on a translation failure