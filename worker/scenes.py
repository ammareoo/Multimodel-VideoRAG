"""Fast scene segmentation — ffmpeg scene filter with time-interval fallback.

PySceneDetect decodes every frame on CPU and can appear hung for several minutes.
This module completes in seconds on typical YouTube-length videos.
"""

import re
import subprocess
from dataclasses import dataclass

import cv2

from settings import MAX_SCENES, SCENE_INTERVAL_SEC, SCENE_THRESHOLD
from tools import ffmpeg_exe


@dataclass
class Scene:
    scene_id: int
    start_sec: float
    end_sec: float
    keyframe_sec: float


def detect_scenes(video_path: str) -> list[Scene]:
    duration = _video_duration(video_path)
    if duration <= 0:
        duration = 60.0

    cuts = _ffmpeg_scene_cuts(video_path)
    if cuts:
        scenes = _scenes_from_cuts(cuts, duration)
    else:
        scenes = _interval_scenes(duration)

    if len(scenes) > MAX_SCENES:
        scenes = _merge_scenes(scenes, MAX_SCENES)

    return scenes


def _video_duration(video_path: str) -> float:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return 0.0
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    if fps <= 0 or frame_count <= 0:
        return 0.0
    return float(frame_count / fps)


def _ffmpeg_scene_cuts(video_path: str) -> list[float]:
    # Map PySceneDetect-style threshold (default 27) to ffmpeg scene score (~0.1–0.5).
    scene_score = min(0.5, max(0.15, SCENE_THRESHOLD / 100.0))
    cmd = [
        ffmpeg_exe(),
        "-hide_banner",
        "-i",
        str(video_path),
        "-filter:v",
        f"select='gt(scene,{scene_score})',showinfo",
        "-f",
        "null",
        "-",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return []

    if result.returncode != 0:
        return []

    cuts = [0.0]
    for line in result.stderr.splitlines():
        match = re.search(r"pts_time:([\d.]+)", line)
        if match:
            cuts.append(float(match.group(1)))

    return sorted(set(cuts)) if len(cuts) > 1 else []


def _scenes_from_cuts(cuts: list[float], duration: float) -> list[Scene]:
    scenes: list[Scene] = []
    bounds = cuts + [duration]
    for i in range(len(bounds) - 1):
        start = bounds[i]
        end = bounds[i + 1]
        if end - start < 0.5:
            continue
        scenes.append(
            Scene(
                scene_id=len(scenes),
                start_sec=start,
                end_sec=end,
                keyframe_sec=start + (end - start) / 2,
            )
        )
    return scenes


def _interval_scenes(duration: float) -> list[Scene]:
    interval = max(SCENE_INTERVAL_SEC, duration / MAX_SCENES)
    scenes: list[Scene] = []
    start = 0.0
    while start < duration:
        end = min(start + interval, duration)
        scenes.append(
            Scene(
                scene_id=len(scenes),
                start_sec=start,
                end_sec=end,
                keyframe_sec=start + (end - start) / 2,
            )
        )
        start = end
    if not scenes:
        scenes.append(Scene(scene_id=0, start_sec=0.0, end_sec=duration, keyframe_sec=0.0))
    return scenes


def _merge_scenes(scenes: list[Scene], target: int) -> list[Scene]:
    """Reduce scene count by merging adjacent segments."""
    if len(scenes) <= target:
        return scenes

    merged: list[Scene] = []
    group_size = (len(scenes) + target - 1) // target
    for i in range(0, len(scenes), group_size):
        group = scenes[i : i + group_size]
        start = group[0].start_sec
        end = group[-1].end_sec
        merged.append(
            Scene(
                scene_id=len(merged),
                start_sec=start,
                end_sec=end,
                keyframe_sec=start + (end - start) / 2,
            )
        )
    return merged
