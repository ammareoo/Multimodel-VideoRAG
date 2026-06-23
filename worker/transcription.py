from dataclasses import dataclass
from functools import lru_cache

from settings import CHUNK_DURATION_SEC, CHUNK_OVERLAP_SEC, WHISPER_MODEL


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptChunk:
    start: float
    end: float
    text: str
    segment_count: int


@lru_cache(maxsize=1)
def _load_model():
    from faster_whisper import WhisperModel

    return WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")


def transcribe(audio_path: str) -> tuple[list[TranscriptSegment], list[TranscriptChunk]]:
    model = _load_model()
    segments_iter, _ = model.transcribe(
        audio_path,
        beam_size=5,
        vad_filter=True,
        word_timestamps=False,
    )

    segments: list[TranscriptSegment] = []
    for seg in segments_iter:
        text = seg.text.strip()
        if text:
            segments.append(TranscriptSegment(start=seg.start, end=seg.end, text=text))

    chunks = _semantic_chunk(segments)
    return segments, chunks


def _semantic_chunk(segments: list[TranscriptSegment]) -> list[TranscriptChunk]:
    """Overlapping time-aligned chunks for context continuity."""
    if not segments:
        return []

    chunks: list[TranscriptChunk] = []
    i = 0
    n = len(segments)
    while i < n:
        window_start = segments[i].start
        j = i
        while j < n and segments[j].end - window_start < CHUNK_DURATION_SEC:
            j += 1
        if j >= n:
            j = n - 1

        window_segments = segments[i : j + 1]
        chunks.append(
            TranscriptChunk(
                start=window_start,
                end=window_segments[-1].end,
                text=" ".join(s.text for s in window_segments),
                segment_count=len(window_segments),
            )
        )

        overlap_start = window_segments[-1].end - CHUNK_OVERLAP_SEC
        next_i = j + 1
        for k in range(i + 1, j + 1):
            if segments[k].start >= overlap_start:
                next_i = k
                break

        if next_i <= i:
            next_i = i + 1
        i = next_i

    return chunks
