from settings import INDEX_DIR, TEMP_DIR


def cleanup_temp(video_id: str, keep_compressed: bool = False) -> None:
    patterns = [
        f"{video_id}_raw.*",
        f"{video_id}_audio.wav",
    ]
    if not keep_compressed:
        patterns.append(f"{video_id}_compressed.mp4")

    for pattern in patterns:
        for f in TEMP_DIR.glob(pattern):
            f.unlink(missing_ok=True)


def cleanup_on_failure(video_id: str) -> None:
    cleanup_temp(video_id, keep_compressed=False)
    for path in (
        INDEX_DIR / f"{video_id}.faiss",
        INDEX_DIR / f"{video_id}.meta.json",
        INDEX_DIR / f"{video_id}.faiss.tmp",
        INDEX_DIR / f"{video_id}.meta.json.tmp",
    ):
        path.unlink(missing_ok=True)
