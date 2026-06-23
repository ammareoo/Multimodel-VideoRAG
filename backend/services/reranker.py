"""Cross-encoder reranking for retrieval quality."""

from functools import lru_cache
from typing import Any

from config import MIN_RERANK_SCORE, RERANK_TOP_K


@lru_cache(maxsize=1)
def _load_reranker():
    from sentence_transformers import CrossEncoder

    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank(query: str, candidates: list[dict[str, Any]], top_k: int = RERANK_TOP_K) -> list[dict[str, Any]]:
    if not candidates:
        return []

    model = _load_reranker()
    pairs = [(query, c.get("text", "") or "") for c in candidates]
    scores = model.predict(pairs)

    ranked = []
    for candidate, score in zip(candidates, scores):
        item = dict(candidate)
        item["rerank_score"] = float(score)
        ranked.append(item)

    ranked.sort(key=lambda x: x["rerank_score"], reverse=True)
    filtered = [r for r in ranked if r["rerank_score"] >= MIN_RERANK_SCORE]
    return filtered[:top_k] if filtered else ranked[: min(3, len(ranked))]
