import subprocess
from pathlib import Path

from settings import TEMP_DIR
from tools import ffmpeg_exe, probe_media


def compress_video(input_path: Path, video_id: str, target_height: int = 360) -> Path:
    """Adaptive compression + fps normalization. Handles video-only, audio-only, and muxed inputs."""
    info = probe_media(input_path)
    output_path = TEMP_DIR / f"{video_id}_compressed.mp4"

    if not info["has_video"] and not info["has_audio"]:
        raise RuntimeError("File has no video or audio streams")

    if info["has_video"]:
        return _compress_with_video(input_path, output_path, target_height, info["has_audio"])

    return _wrap_audio_only(input_path, output_path)


def _compress_with_video(
    input_path: Path,
    output_path: Path,
    target_height: int,
    has_audio: bool,
) -> Path:
    cmd = [
        ffmpeg_exe(), "-y",
        "-i", str(input_path),
        "-vf", f"scale='if(gt(ih,{target_height}),-2,iw)':'if(gt(ih,{target_height}),{target_height},ih)',fps=15",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "28",
        "-movflags", "+faststart",
    ]
    if has_audio:
        cmd.extend(["-c:a", "aac", "-b:a", "64k"])
    else:
        cmd.append("-an")
    cmd.append(str(output_path))

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg compression failed: {result.stderr}")

    return output_path


def _wrap_audio_only(input_path: Path, output_path: Path) -> Path:
    """Re-mux audio-only downloads into mp4 (no video stream to compress)."""
    cmd = [
        ffmpeg_exe(), "-y",
        "-i", str(input_path),
        "-vn",
        "-c:a", "aac",
        "-b:a", "96k",
        "-movflags", "+faststart",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio remux failed: {result.stderr}")

    return output_path


def extract_audio(video_path: Path, video_id: str) -> Path | None:
    """Extract mono 16kHz audio for Whisper. Returns None if the video has no audio."""
    if not probe_media(video_path)["has_audio"]:
        return None

    audio_path = TEMP_DIR / f"{video_id}_audio.wav"

    cmd = [
        ffmpeg_exe(), "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed: {result.stderr}")

    return audio_path
