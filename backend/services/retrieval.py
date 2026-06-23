"""Hybrid multimodal retrieval: semantic + OCR + temporal neighbors + rerank."""

import re
from typing import Any

from config import RETRIEVAL_TOP_K, RERANK_TOP_K
from services.embedder import embed_text
from services.reranker import rerank
from services.vector_store import VectorStore


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _keyword_search(query: str, store: VectorStore, modality: str) -> list[dict]:
    """Keyword overlap search for OCR and transcript modalities."""
    if not store._metadata:
        store.load()

    query_tokens = set(_normalize(query).split())
    if not query_tokens:
        return []

    hits: list[dict] = []
    for meta in store._metadata:
        if meta.get("modality") != modality:
            continue
        text = _normalize(meta.get("text", ""))
        overlap = sum(1 for t in query_tokens if t in text)
        if overlap >= 1:
            hit = dict(meta)
            hit["keyword_score"] = overlap / len(query_tokens)
            hits.append(hit)

    hits.sort(key=lambda x: x.get("keyword_score", 0), reverse=True)
    return hits[:10]


def _temporal_neighbors(results: list[dict], store: VectorStore, window_sec: float = 15.0) -> list[dict]:
    """Expand retrieval with temporally adjacent chunks for context continuity."""
    if not results or not store._metadata:
        return results

    seen_ids = {r.get("id") for r in results}
    expanded = list(results)

    for r in results:
        ts = r.get("timestamp_start", 0)
        for meta in store._metadata:
            mid = meta.get("id")
            if mid in seen_ids:
                continue
            mts = meta.get("timestamp_start", 0)
            if abs(mts - ts) <= window_sec:
                neighbor = dict(meta)
                neighbor["temporal_neighbor"] = True
                expanded.append(neighbor)
                seen_ids.add(mid)

    return expanded


def hybrid_search(query: str, video_id: str) -> list[dict[str, Any]]:
    store = VectorStore(video_id)
    if not store.load():
        return []

    query_vec = embed_text(query)
    semantic = store.search(query_vec, top_k=RETRIEVAL_TOP_K)

    ocr_keyword = _keyword_search(query, store, "ocr")
    transcript_keyword = _keyword_search(query, store, "transcript")
    segment_keyword = _keyword_search(query, store, "segment")

    # Merge and deduplicate
    merged: dict[str, dict] = {}
    for item in semantic + ocr_keyword + transcript_keyword + segment_keyword:
        key = item.get("id") or f"{item.get('modality')}:{item.get('timestamp_start')}"
        if key not in merged or item.get("vector_score", 0) > merged[key].get("vector_score", 0):
            merged[key] = item

    candidates = list(merged.values())
    candidates = _temporal_neighbors(candidates, store)

    # Deduplicate again after temporal expansion
    deduped: dict[str, dict] = {}
    for c in candidates:
        key = c.get("id") or f"{c.get('modality')}:{c.get('timestamp_start')}:{c.get('text', '')[:40]}"
        deduped[key] = c

    ranked = rerank(query, list(deduped.values()), top_k=RERANK_TOP_K)
    return ranked
