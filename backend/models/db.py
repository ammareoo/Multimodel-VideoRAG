import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from config import DB_PATH
from models.schemas import JobStatus


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                video_id TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                progress INTEGER NOT NULL DEFAULT 0,
                message TEXT DEFAULT '',
                error TEXT,
                metadata_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
            CREATE INDEX IF NOT EXISTS idx_jobs_video_id ON jobs(video_id);
            """
        )


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def create_job(url: str, video_id: Optional[str] = None) -> dict[str, Any]:
    job_id = str(uuid.uuid4())
    video_id = video_id or str(uuid.uuid4())
    now = _utcnow()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO jobs (job_id, video_id, url, status, progress, message, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, video_id, url, JobStatus.PENDING.value, 0, "Queued", now, now),
        )
    return {"job_id": job_id, "video_id": video_id, "status": JobStatus.PENDING}


def get_next_pending_job() -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM jobs
            WHERE status = ?
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (JobStatus.PENDING.value,),
        ).fetchone()
        return dict(row) if row else None


def update_job(
    job_id: str,
    *,
    status: Optional[JobStatus] = None,
    progress: Optional[int] = None,
    message: Optional[str] = None,
    error: Optional[str] = None,
    title: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    fields: list[str] = ["updated_at = ?"]
    values: list[Any] = [_utcnow()]

    if status is not None:
        fields.append("status = ?")
        values.append(status.value)
    if progress is not None:
        fields.append("progress = ?")
        values.append(progress)
    if message is not None:
        fields.append("message = ?")
        values.append(message)
    if error is not None:
        fields.append("error = ?")
        values.append(error)
    if title is not None:
        fields.append("title = ?")
        values.append(title)
    if metadata is not None:
        fields.append("metadata_json = ?")
        values.append(json.dumps(metadata))

    values.append(job_id)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE jobs SET {', '.join(fields)} WHERE job_id = ?",
            values,
        )


def get_job(job_id: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def get_job_by_video_id(video_id: str) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE video_id = ? ORDER BY created_at DESC LIMIT 1",
            (video_id,),
        ).fetchone()
        return dict(row) if row else None


def list_videos(limit: int = 50) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM jobs
            WHERE status = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (JobStatus.COMPLETED.value, limit),
        ).fetchall()
        return [dict(r) for r in rows]
