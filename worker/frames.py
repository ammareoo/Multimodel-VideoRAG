"""Extract sampled frames per VideoRAG-style time segment."""

from pathlib import Path

import cv2
import numpy as np

from segments import TimeSegment
from settings import FRAMES_DIR, FRAMES_PER_SEGMENT


def extract_segment_frames(
    video_path: str,
    video_id: str,
    windows: list[TimeSegment],
    num_frames: int | None = None,
) -> dict[int, list[dict]]:
    """Sample frames at linspace within each segment (VideoRAG uses ~5 frames)."""
    out_dir = FRAMES_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    n_frames = int(num_frames or FRAMES_PER_SEGMENT)
    segment_frames: dict[int, list[dict]] = {}

    for window in windows:
        if window.end_sec <= window.start_sec:
            continue

        times = np.linspace(window.start_sec, max(window.end_sec - 0.05, window.start_sec), n_frames)
        frames: list[dict] = []

        for idx, t in enumerate(times):
            frame_num = int(t * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if not ret:
                continue

            filename = f"seg_{window.segment_id:04d}_{idx}_{int(t)}s.jpg"
            frame_path = out_dir / filename
            cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 75])

            rel = str(frame_path.relative_to(FRAMES_DIR.parent))
            frames.append({
                "segment_id": window.segment_id,
                "timestamp_start": window.start_sec,
                "timestamp_end": window.end_sec,
                "keyframe_sec": float(t),
                "frame_path": rel,
                "frame_filename": filename,
            })

        if frames:
            segment_frames[window.segment_id] = frames

    cap.release()
    return segment_frames
