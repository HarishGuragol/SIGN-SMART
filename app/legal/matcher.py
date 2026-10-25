"""Search the local legal knowledge base (kb.json) using Gemini embeddings.
Returns authentic statutory provisions with section numbers and official source URLs.
"""
import json
import math
from pathlib import Path
from typing import List, Dict, Any
import httpx
from .. import config

KB_PATH = Path(__file__).parent / "kb.json"
_KB_CACHE: List[Dict[str, Any]] = []

def _load_kb() -> List[Dict[str, Any]]:
    global _KB_CACHE
    if not _KB_CACHE and KB_PATH.exists():
        _KB_CACHE = json.loads(KB_PATH.read_text(encoding="utf-8"))
    return _KB_CACHE

def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

_QUERY_CACHE: Dict[str, List[float]] = {}

def embed_query(query: str) -> List[float]:
    """Embed query using Gemini embedding model with local cache to save tokens."""
    clean_q = query[:200].strip().lower()
    if clean_q in _QUERY_CACHE:
        return _QUERY_CACHE[clean_q]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_EMBED_MODEL}:embedContent"
    body = {
        "model": f"models/{config.GEMINI_EMBED_MODEL}",
        "content": {"parts": [{"text": clean_q}]},
        "taskType": "RETRIEVAL_QUERY",
        "outputDimensionality": 768
    }
    r = httpx.post(url, params={"key": config.GEMINI_API_KEY}, json=body, timeout=30)
    r.raise_for_status()
    values = r.json()["embedding"]["values"]
    res = [round(x, 5) for x in values]
    _QUERY_CACHE[clean_q] = res
    return res

def search_legal_kb(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Retrieve top_k matching Indian legal sections for a query."""
    kb = _load_kb()
    if not kb:
        return []
    try:
        q_vec = embed_query(query)
    except Exception as e:
        print(f"[legal_matcher embed error] {e}")
        return []

    scored = []
    for item in kb:
        sim = _cosine_similarity(q_vec, item["embedding"])
        scored.append((sim, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, item in scored[:top_k]:
        results.append({
            "act": item["act"],
            "section": item["section"],
            "title": item["title"],
            "url": item["url"],
            "snippet": item["text"][:350] + ("..." if len(item["text"]) > 350 else ""),
            "relevance_score": round(score, 3)
        })
    return results

def get_citations_for_risks(risks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enrich each risk item with verified statutory citations and official links."""
    enriched = []
    for r in risks:
        risk_copy = dict(r)
        query = f"{r.get('title', '')} {r.get('why_for_you', '')}"
        matches = search_legal_kb(query, top_k=2)
        if matches:
            risk_copy["legal_citations"] = matches
        enriched.append(risk_copy)
    return enriched
