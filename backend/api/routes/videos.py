import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import FRAMES_DIR, VIDEOS_DIR
from models import db
from models.schemas import (
    AskRequest,
    AskResponse,
    EvidenceItem,
    JobStatus,
    JobStatusResponse,
    SubmitVideoRequest,
    SubmitVideoResponse,
    VideoSummary,
)
from services.llm import generate_answer
from services.retrieval import hybrid_search
from services.vector_store import VectorStore

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("/submit", response_model=SubmitVideoResponse)
def submit_video(req: SubmitVideoRequest):
    if "youtube.com" not in req.url and "youtu.be" not in req.url:
        raise HTTPException(status_code=400, detail="Only YouTube URLs are supported")
    job = db.create_job(req.url.strip())
    return SubmitVideoResponse(
        job_id=job["job_id"],
        video_id=job["video_id"],
        status=JobStatus.PENDING,
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_response(job)


@router.get("/status/{video_id}", response_model=JobStatusResponse)
def get_status_by_video(video_id: str):
    job = db.get_job_by_video_id(video_id)
    if not job:
        raise HTTPException(status_code=404, detail="Video not found")
    return _job_response(job)


@router.get("", response_model=list[VideoSummary])
def list_videos():
    jobs = db.list_videos()
    return [
        VideoSummary(
            video_id=j["video_id"],
            url=j["url"],
            title=j.get("title"),
            status=JobStatus(j["status"]),
            chunk_count=VectorStore.chunk_count(j["video_id"]),
            created_at=datetime.fromisoformat(j["created_at"]),
        )
        for j in jobs
    ]


@router.post("/{video_id}/ask", response_model=AskResponse)
def ask_video(video_id: str, req: AskRequest):
    if req.video_id != video_id:
        raise HTTPException(status_code=400, detail="video_id mismatch")

    job = db.get_job_by_video_id(video_id)
    if not job:
        raise HTTPException(status_code=404, detail="Video not found")
    if job["status"] != JobStatus.COMPLETED.value:
        raise HTTPException(status_code=409, detail="Video is still processing")

    contexts = hybrid_search(req.question, video_id)
    result = generate_answer(req.question, contexts)

    evidence = [
        EvidenceItem(
            id=str(c.get("id", i)),
            text=c.get("text") or "",
            timestamp_start=float(c.get("timestamp_start", 0)),
            timestamp_end=float(c.get("timestamp_end", c.get("timestamp_start", 0))),
            modality=c.get("modality", "unknown"),
            scene_id=c.get("scene_id"),
            frame_path=c.get("frame_path"),
            confidence=c.get("confidence"),
            rerank_score=c.get("rerank_score"),
        )
        for i, c in enumerate(contexts)
    ]

    return AskResponse(
        answer=result["answer"],
        confidence=result["confidence"],
        evidence=evidence,
        insufficient_evidence=result.get("insufficient_evidence", False),
    )


@router.get("/{video_id}/frames/{filename}")
def get_frame(video_id: str, filename: str):
    frame_path = FRAMES_DIR / video_id / filename
    if not frame_path.exists() or not _is_safe_path(frame_path, FRAMES_DIR / video_id):
        raise HTTPException(status_code=404, detail="Frame not found")
    return FileResponse(frame_path, media_type="image/jpeg")


@router.get("/{video_id}/video")
def get_video_file(video_id: str):
    for ext in (".mp4", ".webm", ".mkv"):
        path = VIDEOS_DIR / f"{video_id}{ext}"
        if path.exists():
            return FileResponse(path, media_type="video/mp4")
    raise HTTPException(status_code=404, detail="Video file not found")


def _job_response(job: dict) -> JobStatusResponse:
    metadata_raw = job.get("metadata_json") or "{}"
    try:
        metadata = json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw
    except json.JSONDecodeError:
        metadata = {}

    return JobStatusResponse(
        job_id=job["job_id"],
        video_id=job["video_id"],
        url=job["url"],
        status=JobStatus(job["status"]),
        progress=job["progress"],
        message=job.get("message") or "",
        error=job.get("error"),
        metadata=metadata,
        created_at=datetime.fromisoformat(job["created_at"]),
        updated_at=datetime.fromisoformat(job["updated_at"]),
    )


def _is_safe_path(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False
