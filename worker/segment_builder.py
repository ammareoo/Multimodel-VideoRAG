"""Build VideoRAG-style unified multimodal documents per time segment."""

from dataclasses import dataclass
from pathlib import Path

from ocr_engine import ocr_frame_text
from segments import TimeSegment, format_segment_transcript
from settings import FRAMES_DIR


@dataclass
class SegmentEvidence:
    segment_id: int
    start_sec: float
    end_sec: float
    transcript: str
    ocr_text: str
    ocr_confidence: float | None
    frame_path: str | None
    frame_filename: str | None

    def build_document(self) -> str:
        """Merged evidence block (Caption + Transcript pattern from VideoRAG)."""
        parts: list[str] = []
        if self.transcript.strip():
            parts.append(format_segment_transcript(self.transcript))
        if self.ocr_text.strip():
            parts.append(f"On-screen text:\n{self.ocr_text.strip()}")
        if self.frame_path:
            parts.append(f"Visual segment at {_fmt_time(self.start_sec)}")
        return "\n\n".join(parts)


def build_segment_evidence(
    windows: list[TimeSegment],
    transcript_by_segment: dict[int, str],
    segment_frames: dict[int, list[dict]],
) -> list[SegmentEvidence]:
    evidence: list[SegmentEvidence] = []

    for window in windows:
        frames = segment_frames.get(window.segment_id, [])
        frame = frames[len(frames) // 2] if frames else None

        ocr_text = ""
        ocr_conf: float | None = None
        if frame:
            frame_path = FRAMES_DIR.parent / frame["frame_path"]
            ocr_result = ocr_frame_text(frame_path)
            if ocr_result:
                ocr_text, ocr_conf = ocr_result

        doc = SegmentEvidence(
            segment_id=window.segment_id,
            start_sec=window.start_sec,
            end_sec=window.end_sec,
            transcript=transcript_by_segment.get(window.segment_id, ""),
            ocr_text=ocr_text,
            ocr_confidence=ocr_conf,
            frame_path=frame["frame_path"] if frame else None,
            frame_filename=frame.get("frame_filename") if frame else None,
        )
        if doc.build_document().strip():
            evidence.append(doc)

    return evidence


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
