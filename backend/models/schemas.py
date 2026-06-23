from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl


class JobStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPRESSING = "compressing"
    SCENE_DETECTION = "scene_detection"
    TRANSCRIBING = "transcribing"
    EXTRACTING_FRAMES = "extracting_frames"
    OCR = "ocr"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class SubmitVideoRequest(BaseModel):
    url: str = Field(..., min_length=10, description="YouTube video URL")


class SubmitVideoResponse(BaseModel):
    job_id: str
    video_id: str
    status: JobStatus


class JobStatusResponse(BaseModel):
    job_id: str
    video_id: str
    url: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    message: str = ""
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class EvidenceItem(BaseModel):
    id: str
    text: str
    timestamp_start: float
    timestamp_end: float
    modality: str
    scene_id: Optional[int] = None
    frame_path: Optional[str] = None
    confidence: Optional[float] = None
    rerank_score: Optional[float] = None


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2)
    video_id: str


class AskResponse(BaseModel):
    answer: str
    confidence: str
    evidence: list[EvidenceItem]
    insufficient_evidence: bool = False


class VideoSummary(BaseModel):
    video_id: str
    url: str
    title: Optional[str] = None
    status: JobStatus
    chunk_count: int = 0
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    vector_backend: str
    llm_provider: str
