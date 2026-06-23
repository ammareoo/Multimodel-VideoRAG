"""FAISS (default) or Qdrant vector storage with metadata sidecar."""

import json
import uuid
from typing import Any, Optional

import numpy as np

from config import (
    EMBEDDING_DIM,
    INDEX_DIR,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    QDRANT_URL,
    VECTOR_BACKEND,
)


class VectorStore:
    def __init__(self, video_id: str):
        self.video_id = video_id
        self.index_path = INDEX_DIR / f"{video_id}.faiss"
        self.meta_path = INDEX_DIR / f"{video_id}.meta.json"
        self._index = None
        self._metadata: list[dict[str, Any]] = []

    def _load_faiss(self):
        import faiss

        if self.index_path.exists():
            self._index = faiss.read_index(str(self.index_path))
            if self.meta_path.exists():
                self._metadata = json.loads(self.meta_path.read_text(encoding="utf-8"))
            else:
                self._metadata = []
        else:
            self._index = faiss.IndexFlatIP(EMBEDDING_DIM)
            self._metadata = []

    def load(self) -> bool:
        if VECTOR_BACKEND == "qdrant":
            if self.meta_path.exists():
                self._metadata = json.loads(self.meta_path.read_text(encoding="utf-8"))
            return bool(self._metadata) or self._qdrant_exists()
        if not self.index_path.exists():
            if self.meta_path.exists():
                self._metadata = json.loads(self.meta_path.read_text(encoding="utf-8"))
            return bool(self._metadata)
        self._load_faiss()
        return True

    def _qdrant_exists(self) -> bool:
        if not QDRANT_URL:
            return False
        from qdrant_client import QdrantClient
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
        result = client.scroll(
            collection_name=QDRANT_COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(key="video_id", match=MatchValue(value=self.video_id))]
            ),
            limit=1,
        )
        return len(result[0]) > 0

    def search(self, query_vector: np.ndarray, top_k: int = 20) -> list[dict[str, Any]]:
        if VECTOR_BACKEND == "qdrant":
            return self._search_qdrant(query_vector, top_k)
        return self._search_faiss(query_vector, top_k)

    def _search_faiss(self, query_vector: np.ndarray, top_k: int) -> list[dict[str, Any]]:
        if self._index is None:
            self._load_faiss()
        if self._index.ntotal == 0:
            return []

        q = query_vector.reshape(1, -1).astype(np.float32)
        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(q, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            meta = dict(self._metadata[idx])
            meta["vector_score"] = float(score)
            meta["id"] = meta.get("id", str(idx))
            results.append(meta)
        return results

    def _search_qdrant(self, query_vector: np.ndarray, top_k: int) -> list[dict[str, Any]]:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
        hits = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vector.tolist(),
            query_filter=Filter(
                must=[FieldCondition(key="video_id", match=MatchValue(value=self.video_id))]
            ),
            limit=top_k,
        )
        results = []
        for hit in hits:
            payload = dict(hit.payload or {})
            payload["vector_score"] = hit.score
            payload["id"] = str(hit.id)
            results.append(payload)
        return results

    @staticmethod
    def save_chunks(video_id: str, chunks: list[dict[str, Any]], vectors: np.ndarray) -> int:
        """Called by worker after embedding generation."""
        if VECTOR_BACKEND == "qdrant":
            return VectorStore._save_qdrant(video_id, chunks, vectors)
        return VectorStore._save_faiss(video_id, chunks, vectors)

    @staticmethod
    def _write_metadata(video_id: str, chunks: list[dict]) -> list[dict]:
        meta_path = INDEX_DIR / f"{video_id}.meta.json"
        metadata = []
        for i, chunk in enumerate(chunks):
            entry = dict(chunk)
            entry["id"] = entry.get("id", str(i))
            metadata.append(entry)
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return metadata

    @staticmethod
    def _save_faiss(video_id: str, chunks: list[dict], vectors: np.ndarray) -> int:
        import faiss

        index_path = INDEX_DIR / f"{video_id}.faiss"
        meta_path = INDEX_DIR / f"{video_id}.meta.json"
        tmp_index_path = INDEX_DIR / f"{video_id}.faiss.tmp"
        tmp_meta_path = INDEX_DIR / f"{video_id}.meta.json.tmp"

        index = faiss.IndexFlatIP(EMBEDDING_DIM)
        vecs = vectors.astype(np.float32)
        faiss.normalize_L2(vecs)
        index.add(vecs)

        metadata = []
        for i, chunk in enumerate(chunks):
            entry = dict(chunk)
            entry["id"] = entry.get("id", str(i))
            metadata.append(entry)

        faiss.write_index(index, str(tmp_index_path))
        tmp_meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        tmp_meta_path.replace(meta_path)
        tmp_index_path.replace(index_path)
        return len(metadata)

    @staticmethod
    def _save_qdrant(video_id: str, chunks: list[dict], vectors: np.ndarray) -> int:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, PointStruct, VectorParams

        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
        collections = [c.name for c in client.get_collections().collections]
        if QDRANT_COLLECTION not in collections:
            client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            )

        points = []
        for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
            payload = dict(chunk)
            payload["video_id"] = video_id
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{video_id}:{i}"))
            payload["id"] = point_id
            points.append(PointStruct(id=point_id, vector=vec.tolist(), payload=payload))

        client.upsert(collection_name=QDRANT_COLLECTION, points=points)
        VectorStore._write_metadata(video_id, chunks)
        return len(points)

    @staticmethod
    def chunk_count(video_id: str) -> int:
        meta_path = INDEX_DIR / f"{video_id}.meta.json"
        if meta_path.exists():
            return len(json.loads(meta_path.read_text(encoding="utf-8")))
        return 0
