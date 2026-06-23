"""Resolve external tools on Windows (PATH, venv module, bundled ffmpeg)."""

import re
import shutil
import subprocess
import sys
from pathlib import Path


def ffmpeg_exe() -> str:
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    raise RuntimeError(
        "ffmpeg not found. Install ffmpeg (https://ffmpeg.org) and add it to PATH, "
        "or run: pip install imageio-ffmpeg"
    )


def ffmpeg_location() -> str:
    """Directory containing ffmpeg — required by yt-dlp for audio+video merge."""
    return str(Path(ffmpeg_exe()).resolve().parent)


def ytdlp_cmd() -> list[str]:
    """Use python -m yt_dlp so the worker venv does not need yt-dlp on PATH."""
    script = shutil.which("yt-dlp")
    if script:
        return [script]
    return [sys.executable, "-m", "yt_dlp"]


def check_worker_tools() -> None:
    ffmpeg_exe()
    cmd = ytdlp_cmd()
    if cmd[0] == sys.executable:
        import importlib.util

        if importlib.util.find_spec("yt_dlp") is None:
            raise RuntimeError(
                "yt-dlp is not installed. Run: pip install -r requirements.txt"
            )


def probe_media(media_path: Path) -> dict:
    """Inspect streams via ffmpeg (-i). Returns has_video, has_audio, duration_sec."""
    result = subprocess.run(
        [ffmpeg_exe(), "-i", str(media_path), "-hide_banner"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stderr = result.stderr
    has_video = bool(re.search(r"Stream #\d+:\d+.*: Video:", stderr))
    has_audio = bool(re.search(r"Stream #\d+:\d+.*: Audio:", stderr))
    duration_sec = 0.0
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    if match:
        hours, minutes, seconds = match.groups()
        duration_sec = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return {
        "has_video": has_video,
        "has_audio": has_audio,
        "duration_sec": duration_sec,
    }


def video_has_video(video_path: Path) -> bool:
    """Return True if the file contains at least one video stream."""
    return probe_media(video_path)["has_video"]


def video_has_audio(video_path: Path) -> bool:
    """Return True if the file contains at least one audio stream."""
    return probe_media(video_path)["has_audio"]


def media_duration_sec(media_path: Path) -> float:
    """Duration in seconds from container metadata."""
    duration = probe_media(media_path)["duration_sec"]
    if duration > 0:
        return duration
    return 0.0
