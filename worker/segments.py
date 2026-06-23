"""VideoRAG-style fixed time windows (30s segments).

Inspired by HKUDS VideoRAG: predictable segmentation scales to long videos
and aligns transcript, OCR, and visual evidence to the same time axis.
"""

from dataclasses import dataclass
from pathlib import Path

import cv2

from settings import MAX_SEGMENTS, SEGMENT_LENGTH_SEC
from tools import media_duration_sec
from transcription import TranscriptSegment


@dataclass
class TimeSegment:
    segment_id: int
    start_sec: float
    end_sec: float

    @property
    def mid_sec(self) -> float:
        return self.start_sec + (self.end_sec - self.start_sec) / 2


def video_duration(video_path: str) -> float:
    path = Path(video_path) if not isinstance(video_path, Path) else video_path
    duration = media_duration_sec(path)
    if duration > 0:
        return duration

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return 0.0
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    if fps <= 0 or frame_count <= 0:
        return 0.0
    return float(frame_count / fps)


def build_time_segments(duration: float, segment_length: float | None = None) -> list[TimeSegment]:
    """Split video into fixed-duration windows (default 30s, VideoRAG default)."""
    if duration <= 0:
        duration = 60.0

    length = segment_length or SEGMENT_LENGTH_SEC
    # Cap segment count for very long videos
    if duration / length > MAX_SEGMENTS:
        length = duration / MAX_SEGMENTS

    segments: list[TimeSegment] = []
    start = 0.0
    while start < duration - 0.01:
        end = min(start + length, duration)
        segments.append(TimeSegment(segment_id=len(segments), start_sec=start, end_sec=end))
        start = end

    if not segments:
        segments.append(TimeSegment(segment_id=0, start_sec=0.0, end_sec=duration))
    return segments


def map_transcript_to_segments(
    whisper_segments: list[TranscriptSegment],
    windows: list[TimeSegment],
) -> dict[int, str]:
    """Map Whisper output onto fixed time windows (VideoRAG merge pattern)."""
    texts: dict[int, list[str]] = {w.segment_id: [] for w in windows}

    for seg in whisper_segments:
        if not seg.text.strip():
            continue
        for window in windows:
            if seg.end <= window.start_sec or seg.start >= window.end_sec:
                continue
            stamp = f"[{window.start_sec:.1f} -> {window.end_sec:.1f}]"
            texts[window.segment_id].append(f"{stamp} {seg.text.strip()}")

    return {
        wid: "\n".join(parts)
        for wid, parts in texts.items()
        if parts
    }


def format_segment_transcript(raw: str) -> str:
    """VideoRAG-style labeled transcript block."""
    if not raw.strip():
        return ""
    return f"Transcript:\n{raw.strip()}"
