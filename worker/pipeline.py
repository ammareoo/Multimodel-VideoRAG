import shutil
import time
import traceback
from pathlib import Path

from cleanup import cleanup_on_failure, cleanup_temp
from compress import compress_video, extract_audio
from downloader import download_video
from embeddings import EmbeddingEngine, build_segment_index_records
from frames import extract_segment_frames
from job_client import get_next_pending_job, update_job
from segment_builder import build_segment_evidence
from segments import build_time_segments, map_transcript_to_segments, video_duration
from settings import POLL_INTERVAL_SEC, SEGMENT_LENGTH_SEC, VIDEOS_DIR
from tools import check_worker_tools, probe_media
from transcription import transcribe

from models import db  # noqa: E402 — via sys.path in settings
from services.vector_store import VectorStore  # noqa: E402


def process_job(job: dict) -> None:
    job_id = job["job_id"]
    video_id = job["video_id"]
    url = job["url"]

    current_stage = "downloading"
    last_progress = 0

    try:
        update_job(job_id, status="downloading", progress=5, message="Downloading video...")
        last_progress = 5
        video_path, title = download_video(url, video_id)
        media_info = probe_media(video_path)
        has_audio = media_info["has_audio"]
        has_video = media_info["has_video"]
        audio_note = "" if has_audio else " (no audio — OCR/visual only)"
        update_job(job_id, title=title, progress=15, message=f"Download complete{audio_note}")
        last_progress = 15

        current_stage = "compressing"
        update_job(job_id, status="compressing", progress=20, message="Compressing and normalizing fps...")
        last_progress = 20
        compressed = compress_video(video_path, video_id)
        shutil.move(str(compressed), str(VIDEOS_DIR / f"{video_id}.mp4"))
        working_video = VIDEOS_DIR / f"{video_id}.mp4"

        current_stage = "scene_detection"
        duration = video_duration(str(working_video))
        windows = build_time_segments(duration, SEGMENT_LENGTH_SEC)
        update_job(
            job_id,
            status="scene_detection",
            progress=30,
            message=f"Built {len(windows)} time segments ({int(SEGMENT_LENGTH_SEC)}s windows)...",
        )
        last_progress = 30

        current_stage = "transcribing"
        update_job(job_id, status="transcribing", progress=40, message="Transcribing audio...")
        last_progress = 40
        whisper_segments: list = []
        if has_audio:
            audio_path = extract_audio(working_video, video_id)
            if audio_path:
                whisper_segments, _ = transcribe(str(audio_path))
        transcript_by_segment = map_transcript_to_segments(whisper_segments, windows)
        if not has_audio:
            update_job(
                job_id,
                progress=50,
                message="No audio track — using on-screen text and visuals only",
            )

        current_stage = "extracting_frames"
        update_job(
            job_id,
            status="extracting_frames",
            progress=55,
            message="Sampling frames per segment..." if has_video else "Skipping frames (audio-only)...",
        )
        last_progress = 55
        segment_frames = (
            extract_segment_frames(str(working_video), video_id, windows)
            if has_video
            else {}
        )

        current_stage = "ocr"
        update_job(job_id, status="ocr", progress=65, message="Building multimodal segment evidence...")
        last_progress = 65
        evidence = build_segment_evidence(windows, transcript_by_segment, segment_frames)

        current_stage = "embedding"
        update_job(job_id, status="embedding", progress=75, message="Generating segment embeddings...")
        last_progress = 75
        engine = EmbeddingEngine()
        records, vectors = build_segment_index_records(video_id, evidence, segment_frames, engine)

        current_stage = "indexing"
        update_job(job_id, status="indexing", progress=90, message="Indexing vectors...")
        last_progress = 90
        if len(records) == 0:
            raise RuntimeError(
                "No indexable content found. The video may be blank, corrupted, or lack "
                "both speech and readable on-screen text."
            )
        count = VectorStore.save_chunks(video_id, records, vectors)

        cleanup_temp(video_id)

        update_job(
            job_id,
            status="completed",
            progress=100,
            message=f"Ready — indexed {count} segment(s)",
            metadata={
                "segments": len(windows),
                "indexed_segments": count,
                "has_audio": has_audio,
                "has_video": has_video,
                "transcript_segments": len(transcript_by_segment),
                "pipeline": "videorag_segments_v2",
            },
        )
    except Exception as exc:
        cleanup_on_failure(video_id)
        update_job(
            job_id,
            status="failed",
            progress=last_progress,
            message=f"Failed during {current_stage.replace('_', ' ')}",
            error=str(exc),
            metadata={"failed_stage": current_stage},
        )
        traceback.print_exc()


def run_worker_loop() -> None:
    check_worker_tools()
    print("VideoRAG worker started. Polling for jobs...")
    while True:
        job = get_next_pending_job()
        if job:
            print(f"Processing job {job['job_id']} — {job['url']}")
            process_job(job)
        else:
            time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    db.init_db()
    run_worker_loop()
