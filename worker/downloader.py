import json
import subprocess
from pathlib import Path

from settings import MAX_HEIGHT, PREFERRED_HEIGHT, TEMP_DIR, VIDEOS_DIR
from tools import ffmpeg_location, probe_media, ytdlp_cmd

# Always require a video stream; audio is merged when available.
_FORMAT_MERGE = (
    f"bestvideo[height<={PREFERRED_HEIGHT}]+bestaudio/"
    f"bestvideo[height<={MAX_HEIGHT}]+bestaudio/"
    f"best[height<={MAX_HEIGHT}][vcodec!=none][acodec!=none]/"
    f"best[height<={MAX_HEIGHT}][vcodec!=none]/"
    f"worst[height>=240][vcodec!=none]/best[vcodec!=none]"
)
_FORMAT_MUXED = (
    f"best[ext=mp4][vcodec!=none][acodec!=none][height<={MAX_HEIGHT}]/"
    f"best[vcodec!=none][acodec!=none][height<={MAX_HEIGHT}]/"
    f"best[vcodec!=none][height<={MAX_HEIGHT}]/"
    f"worst[height>=240][vcodec!=none]/best[vcodec!=none]"
)
_FORMAT_VIDEO_ONLY = (
    f"best[vcodec!=none][height<={MAX_HEIGHT}]/"
    f"worst[height>=240][vcodec!=none]/best[vcodec!=none]"
)


def download_video(url: str, video_id: str) -> tuple[Path, str]:
    """Download YouTube video with video stream required; retry when merge yields bad files."""
    final_path = VIDEOS_DIR / f"{video_id}.mp4"
    title = _run_download(url, video_id, _FORMAT_MERGE)
    info = probe_media(final_path)

    if not info["has_video"]:
        final_path.unlink(missing_ok=True)
        title = _run_download(url, video_id, _FORMAT_MUXED)
        info = probe_media(final_path)

    if not info["has_video"]:
        final_path.unlink(missing_ok=True)
        title = _run_download(url, video_id, _FORMAT_VIDEO_ONLY)
        info = probe_media(final_path)

    if not info["has_video"]:
        raise RuntimeError(
            "Download did not include a video stream. The URL may be audio-only or restricted."
        )

    if not info["has_audio"]:
        # Video-only (e.g. some Shorts) — retry muxed progressive with audio.
        final_path.unlink(missing_ok=True)
        title = _run_download(url, video_id, _FORMAT_MUXED)
        info = probe_media(final_path)

    return final_path, title


def _run_download(url: str, video_id: str, format_str: str) -> str:
    temp_output = TEMP_DIR / f"{video_id}_raw.%(ext)s"
    final_path = VIDEOS_DIR / f"{video_id}.mp4"

    cmd = [
        *ytdlp_cmd(),
        "--no-playlist",
        "--write-info-json",
        "--ffmpeg-location",
        ffmpeg_location(),
        "--prefer-ffmpeg",
        "-f",
        format_str,
        "--merge-output-format",
        "mp4",
        "-o",
        str(temp_output),
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr or result.stdout}")

    raw_files = list(TEMP_DIR.glob(f"{video_id}_raw.*"))
    video_files = [f for f in raw_files if f.suffix in (".mp4", ".webm", ".mkv", ".m4a")]
    if not video_files:
        raise RuntimeError("Download succeeded but no media file found")

    raw_path = video_files[0]
    title = _extract_title(raw_files)

    if raw_path != final_path:
        if final_path.exists():
            final_path.unlink(missing_ok=True)
        raw_path.rename(final_path)

    for f in TEMP_DIR.glob(f"{video_id}_raw.*"):
        if f.suffix == ".json":
            f.unlink(missing_ok=True)

    return title


def _extract_title(files: list[Path]) -> str:
    for f in files:
        if f.suffix == ".json":
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                return data.get("title", "Untitled Video")
            except (json.JSONDecodeError, OSError):
                pass
    return "Untitled Video"
