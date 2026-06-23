import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

from settings import FRAMES_DIR, OCR_DEDUP_THRESHOLD


@lru_cache(maxsize=1)
def _load_ocr():
    try:
        from paddleocr import PaddleOCR
        return PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    except Exception:
        import easyocr
        return easyocr.Reader(["en"], gpu=False)


def _run_ocr_on_image(frame_path: Path) -> list[tuple[str, float]]:
    engine = _load_ocr()
    results: list[tuple[str, float]] = []

    if hasattr(engine, "ocr"):
        # PaddleOCR
        raw = engine.ocr(str(frame_path), cls=True)
        if raw and raw[0]:
            for line in raw[0]:
                if line and len(line) >= 2:
                    text = line[1][0].strip()
                    conf = float(line[1][1])
                    if text:
                        results.append((text, conf))
    else:
        # EasyOCR fallback
        raw = engine.readtext(str(frame_path))
        for _bbox, text, conf in raw:
            text = text.strip()
            if text:
                results.append((text, float(conf)))

    return results


def _normalize_ocr(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _is_duplicate(text: str, seen: list[str]) -> bool:
    norm = _normalize_ocr(text)
    for prev in seen:
        if SequenceMatcher(None, norm, prev).ratio() >= OCR_DEDUP_THRESHOLD:
            return True
    return False


def ocr_frame_text(frame_path: Path) -> tuple[str, float] | None:
    """OCR a single frame; returns combined text and average confidence."""
    if not frame_path.exists():
        return None

    lines = _run_ocr_on_image(frame_path)
    if not lines:
        return None

    combined = " | ".join(t for t, _ in lines)
    avg_conf = sum(c for _, c in lines) / len(lines)
    return combined, round(avg_conf, 3)


def extract_ocr(keyframes: list[dict], scenes: list) -> list[dict]:
    """OCR only on scene keyframes with deduplication."""
    seen_normalized: list[str] = []
    ocr_results: list[dict] = []

    for kf in keyframes:
        frame_rel = kf.get("frame_path", "")
        frame_path = FRAMES_DIR.parent / frame_rel
        if not frame_path.exists():
            continue

        lines = _run_ocr_on_image(frame_path)
        if not lines:
            continue

        combined = " | ".join(t for t, _ in lines)
        if _is_duplicate(combined, seen_normalized):
            continue

        seen_normalized.append(_normalize_ocr(combined))
        avg_conf = sum(c for _, c in lines) / len(lines)
        ocr_results.append({
            "text": combined,
            "timestamp_start": kf["timestamp_start"],
            "timestamp_end": kf["timestamp_end"],
            "scene_id": kf["scene_id"],
            "modality": "ocr",
            "frame_path": frame_rel,
            "frame_filename": kf.get("frame_filename"),
            "confidence": round(avg_conf, 3),
        })

    return ocr_results
