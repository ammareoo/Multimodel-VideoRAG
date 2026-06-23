import uuid
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from settings import FRAMES_DIR


class EmbeddingEngine:
    def __init__(self):
        import open_clip

        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32",
            pretrained="laion2b_s34b_b79k",
        )
        self.tokenizer = open_clip.get_tokenizer("ViT-B-32")
        self.model.eval()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = self.model.to(self.device)
        self.embedding_dim = int(self.model.text_projection.shape[1])

    def embed_text(self, text: str) -> np.ndarray:
        tokens = self.tokenizer([text]).to(self.device)
        with torch.no_grad():
            vec = self.model.encode_text(tokens)
            vec = vec / vec.norm(dim=-1, keepdim=True)
        return vec.cpu().numpy()[0].astype(np.float32)

    def embed_image(self, image_path: Path) -> np.ndarray | None:
        try:
            img = Image.open(image_path).convert("RGB")
        except OSError:
            return None
        tensor = self.preprocess(img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            vec = self.model.encode_image(tensor)
            vec = vec / vec.norm(dim=-1, keepdim=True)
        return vec.cpu().numpy()[0].astype(np.float32)


def build_segment_index_records(
    video_id: str,
    evidence: list,
    segment_frames: dict[int, list[dict]],
    engine: EmbeddingEngine,
) -> tuple[list[dict], np.ndarray]:
    """One index record per time segment with fused text + visual embedding."""
    chunks: list[dict] = []
    vectors: list[np.ndarray] = []

    for seg in evidence:
        text = seg.build_document().strip()
        if not text:
            continue

        vec = engine.embed_text(text)

        # Blend with middle-frame image embedding when available (VideoRAG multi-modal)
        frames = segment_frames.get(seg.segment_id, [])
        if frames:
            mid = frames[len(frames) // 2]
            frame_path = FRAMES_DIR.parent / mid["frame_path"]
            img_vec = engine.embed_image(frame_path)
            if img_vec is not None:
                vec = (vec + img_vec) / 2.0
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm

        chunks.append({
            "id": str(uuid.uuid4()),
            "video_id": video_id,
            "text": text,
            "timestamp_start": seg.start_sec,
            "timestamp_end": seg.end_sec,
            "modality": "segment",
            "scene_id": seg.segment_id,
            "frame_path": seg.frame_path,
            "frame_filename": seg.frame_filename,
            "confidence": seg.ocr_confidence,
        })
        vectors.append(vec.astype(np.float32))

    if not vectors:
        return [], np.empty((0, engine.embedding_dim), dtype=np.float32)

    return chunks, np.stack(vectors)


def build_index_records(
    video_id: str,
    transcript_chunks: list,
    ocr_data: list[dict],
    keyframes: list[dict],
    engine: EmbeddingEngine,
) -> tuple[list[dict], np.ndarray]:
    chunks: list[dict] = []
    vectors: list[np.ndarray] = []

    for item in transcript_chunks:
        text = item.text.strip()
        if not text:
            continue
        vec = engine.embed_text(text)
        chunks.append({
            "id": str(uuid.uuid4()),
            "video_id": video_id,
            "text": text,
            "timestamp_start": item.start,
            "timestamp_end": item.end,
            "modality": "transcript",
            "scene_id": None,
            "frame_path": None,
            "confidence": None,
        })
        vectors.append(vec)

    for item in ocr_data:
        text = item["text"].strip()
        if not text:
            continue
        vec = engine.embed_text(text)
        chunks.append({
            "id": str(uuid.uuid4()),
            "video_id": video_id,
            "text": text,
            "timestamp_start": item["timestamp_start"],
            "timestamp_end": item["timestamp_end"],
            "modality": "ocr",
            "scene_id": item.get("scene_id"),
            "frame_path": item.get("frame_path"),
            "confidence": item.get("confidence"),
        })
        vectors.append(vec)

    for kf in keyframes:
        frame_rel = kf.get("frame_path", "")
        frame_path = FRAMES_DIR.parent / frame_rel
        vec = engine.embed_image(frame_path)
        if vec is None:
            continue

        scene_id = kf["scene_id"]
        ts_start = kf["timestamp_start"]
        ts_end = kf["timestamp_end"]
        text = f"Visual scene {scene_id} at {_fmt(ts_start)}"

        chunks.append({
            "id": str(uuid.uuid4()),
            "video_id": video_id,
            "text": text,
            "timestamp_start": ts_start,
            "timestamp_end": ts_end,
            "modality": "visual",
            "scene_id": scene_id,
            "frame_path": frame_rel,
            "frame_filename": kf.get("frame_filename"),
            "confidence": None,
        })
        vectors.append(vec)

    if not vectors:
        return [], np.empty((0, engine.embedding_dim), dtype=np.float32)

    return chunks, np.stack(vectors)


def _fmt(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"
