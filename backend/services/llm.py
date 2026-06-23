"""Grounded answer generation using Ollama/Groq or template fallback."""

import json
from typing import Any

import httpx

from config import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
)

_OLLAMA_CLIENT = httpx.Client(timeout=OLLAMA_TIMEOUT)


def _format_evidence(contexts: list[dict[str, Any]]) -> str:
    lines = []
    for i, c in enumerate(contexts, 1):
        ts_start = c.get("timestamp_start", 0)
        ts_end = c.get("timestamp_end", ts_start)
        modality = c.get("modality", "unknown")
        text = (c.get("text") or "").strip()
        if not text:
            continue
        lines.append(
            f"[Evidence {i}] [{_fmt_time(ts_start)} - {_fmt_time(ts_end)}] "
            f"({modality}): {text}"
        )
    return "\n".join(lines)


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _confidence_label(contexts: list[dict[str, Any]]) -> str:
    if not contexts:
        return "none"
    scores = [c.get("rerank_score", 0) for c in contexts]
    avg = sum(scores) / len(scores) if scores else 0
    if avg >= 5:
        return "high"
    if avg >= 0:
        return "medium"
    return "low"


def generate_answer(question: str, contexts: list[dict[str, Any]]) -> dict[str, Any]:
    evidence = _format_evidence(contexts) if contexts else "No retrieved evidence."
    confidence = _confidence_label(contexts) if contexts else "none"

    system_prompt = """You are a video QA assistant.
Answer the user's question directly and concisely.
If evidence is available, use it and include timestamps in [MM:SS] or [HH:MM:SS] format.
If evidence is sparse, still provide the best possible answer."""

    user_prompt = f"""Evidence from the video:
{evidence}

Question: {question}

Provide a grounded answer with timestamp citations. Reference the evidence modality when relevant."""

    if LLM_PROVIDER == "ollama":
        answer = _call_ollama(system_prompt, user_prompt)
        if answer:
            return {"answer": answer, "confidence": confidence, "insufficient_evidence": False}
    elif LLM_PROVIDER == "groq":
        answer = _call_groq(system_prompt, user_prompt)
        if answer:
            return {"answer": answer, "confidence": confidence, "insufficient_evidence": False}

    return _template_answer(question, contexts, confidence)


def _call_ollama(system: str, user: str) -> str | None:
    try:
        resp = _OLLAMA_CLIENT.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "options": {"temperature": 0.1},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "").strip()
    except (httpx.HTTPError, json.JSONDecodeError, KeyError):
        return None


def _call_groq(system: str, user: str) -> str | None:
    if not GROQ_API_KEY:
        return None
    try:
        resp = _OLLAMA_CLIENT.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.1,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError):
        return None


def _template_answer(question: str, contexts: list[dict[str, Any]], confidence: str) -> dict[str, Any]:
    """Deterministic fallback — no hallucination, evidence-only summary."""
    parts = [f"Based on retrieved evidence for: \"{question}\"\n"]
    for c in contexts[:5]:
        ts = _fmt_time(c.get("timestamp_start", 0))
        modality = c.get("modality", "unknown")
        text = (c.get("text") or "").strip()
        parts.append(f"- At [{ts}] ({modality}): {text}")

    parts.append("\nNote: Configure `LLM_PROVIDER=ollama` or `LLM_PROVIDER=groq` for natural language answers.")
    return {
        "answer": "\n".join(parts),
        "confidence": confidence,
        "insufficient_evidence": False,
    }
