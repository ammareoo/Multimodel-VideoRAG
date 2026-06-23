import os
import sys
from pathlib import Path

from dotenv import load_dotenv

WORKER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = WORKER_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

load_dotenv(PROJECT_ROOT / ".env")

sys.path.insert(0, str(BACKEND_DIR))

DATA_DIR = Path(os.getenv("DATA_DIR", BACKEND_DIR / "data"))
if not DATA_DIR.is_absolute():
    DATA_DIR = (PROJECT_ROOT / DATA_DIR).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

VIDEOS_DIR = DATA_DIR / "videos"
FRAMES_DIR = DATA_DIR / "frames"
TEMP_DIR = DATA_DIR / "temp"
INDEX_DIR = DATA_DIR / "indexes"

for d in (VIDEOS_DIR, FRAMES_DIR, TEMP_DIR, INDEX_DIR):
    d.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "videorag.db"

# Video download quality
MAX_HEIGHT = int(os.getenv("MAX_VIDEO_HEIGHT", "480"))
PREFERRED_HEIGHT = int(os.getenv("PREFERRED_VIDEO_HEIGHT", "360"))

# Whisper model size: tiny, base, small (small recommended for balance)
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")

# VideoRAG-style fixed windows (seconds)
SEGMENT_LENGTH_SEC = float(os.getenv("SEGMENT_LENGTH_SEC", "30"))
FRAMES_PER_SEGMENT = int(os.getenv("FRAMES_PER_SEGMENT", "3"))
MAX_SEGMENTS = int(os.getenv("MAX_SEGMENTS", "120"))

# Transcript chunking
CHUNK_DURATION_SEC = float(os.getenv("CHUNK_DURATION_SEC", "30"))
CHUNK_OVERLAP_SEC = float(os.getenv("CHUNK_OVERLAP_SEC", "5"))

# OCR dedup similarity threshold
OCR_DEDUP_THRESHOLD = float(os.getenv("OCR_DEDUP_THRESHOLD", "0.85"))

POLL_INTERVAL_SEC = int(os.getenv("WORKER_POLL_INTERVAL", "5"))
