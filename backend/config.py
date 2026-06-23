import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
if not DATA_DIR.is_absolute():
    DATA_DIR = (PROJECT_ROOT / DATA_DIR).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

VIDEOS_DIR = DATA_DIR / "videos"
FRAMES_DIR = DATA_DIR / "frames"
INDEX_DIR = DATA_DIR / "indexes"
DB_PATH = DATA_DIR / "videorag.db"

for d in (VIDEOS_DIR, FRAMES_DIR, INDEX_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Vector store: "faiss" (default, free local) or "qdrant" (free cloud tier)
VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "faiss")

QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "videorag")

# Embedding dimensions (OpenCLIP ViT-B-32)
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "512"))

# LLM: ollama (local) or groq (cloud)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "300"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# Retrieval
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "20"))
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "8"))
MIN_RERANK_SCORE = float(os.getenv("MIN_RERANK_SCORE", "-2.0"))

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")
