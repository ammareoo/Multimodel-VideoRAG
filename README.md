# Multimodal VideoRAG

Production-grade **free** multimodal Video RAG system. Paste a YouTube URL, process the video automatically, and ask grounded questions with timestamp evidence from **speech**, **OCR**, and **visual scenes**.

## Architecture

```
YouTube URL → Job Queue (SQLite)
    → Download (yt-dlp, 360p/480p)
    → Compress + normalize fps (ffmpeg)
    → Scene detection (PySceneDetect) → keyframes only
    → Audio extraction → Transcription (faster-whisper, chunked + overlap)
    → OCR on keyframes (PaddleOCR / EasyOCR, deduplicated)
    → Multimodal embeddings (OpenCLIP ViT-B-32)
    → Vector index (FAISS local or Qdrant cloud)
    → Hybrid retrieval + CrossEncoder reranking
    → Grounded answer (Ollama / evidence-only fallback)
```

### Why this is true multimodal (not transcript-only)

| Modality | Source | Use case |
|----------|--------|----------|
| **transcript** | faster-whisper | "What did the speaker say about X?" |
| **ocr** | PaddleOCR on scene keyframes | "What was written on the whiteboard?" |
| **visual** | OpenCLIP image embeddings | "What scene appeared at 5:30?" |

Retrieval combines **semantic vector search**, **keyword matching**, **temporal neighbors**, and **cross-encoder reranking** to minimize hallucinations.

## Project structure

```
videorag_project/
├── backend/          # FastAPI API, retrieval, LLM
├── worker/           # Video processing pipeline (polls job queue)
├── frontend/         # Next.js + Tailwind UI
├── docker-compose.yml
└── .env.example
```

## Prerequisites

- **Python 3.11 or 3.12** (3.13 is not supported by all ML wheels yet)
- **Node.js 18+**
- **ffmpeg** (in PATH)
- **yt-dlp** (installed via pip in worker)
- **Ollama** (optional, for natural language answers): `ollama pull gemma2:2b`

## Quick start (local)

### 1. Environment

```bash
cp .env.example .env
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
# Windows PowerShell:
$env:DATA_DIR = "..\data"
uvicorn main:app --reload --port 8000
```

### 3. Worker (separate terminal)

```bash
cd worker
pip install -r requirements.txt
# Must share DATA_DIR with backend:
$env:DATA_DIR = "..\data"
$env:PYTHONPATH = "..\backend"
python pipeline.py
```

### 4. Frontend

```bash
cd frontend
npm install
$env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
npm run dev
```

Open **http://localhost:3000** → paste a YouTube URL → wait for processing → chat.

### Optional: startup scripts (PowerShell)

```bash
./scripts/start_backend.ps1
./scripts/start_worker.ps1
./scripts/start_frontend.ps1
```

### 5. Ollama (recommended)

```bash
ollama pull gemma2:2b
ollama serve
```

Without Ollama, answers use a deterministic evidence-only template (no hallucination, but less natural).

## Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Docs: http://localhost:8000/docs

For Ollama inside Docker on Windows/Mac, `OLLAMA_BASE_URL` defaults to `host.docker.internal:11434`.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/videos/submit` | Submit YouTube URL |
| GET | `/api/videos/jobs/{job_id}` | Job status + progress |
| GET | `/api/videos/status/{video_id}` | Status by video ID |
| GET | `/api/videos` | List completed videos |
| POST | `/api/videos/{video_id}/ask` | Ask a question |
| GET | `/api/videos/{video_id}/frames/{filename}` | Keyframe image |
| GET | `/api/videos/{video_id}/video` | Processed video file |

## Environment variables

See [`.env.example`](.env.example). Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `./data` | Shared storage (backend + worker) |
| `VECTOR_BACKEND` | `faiss` | `faiss` (local) or `qdrant` (free cloud) |
| `LLM_PROVIDER` | `ollama` | `ollama` or template fallback |
| `WHISPER_MODEL` | `small` | faster-whisper model size |
| `PREFERRED_VIDEO_HEIGHT` | `360` | Download quality target |
| `MAX_VIDEO_HEIGHT` | `480` | Maximum download height |

## Free deployment guide

### Frontend → Cloudflare Pages / Netlify

1. Connect repo, set build command: `cd frontend && npm run build`
2. Output directory: `frontend/.next` (or use `next export` if static)
3. Env: `NEXT_PUBLIC_API_URL=https://your-backend.railway.app`

### Backend → Railway / Render (free tier)

1. Deploy `backend/` with start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
2. Mount persistent volume at `/app/data` for FAISS indexes and videos
3. Set `DATA_DIR=/app/data`, `CORS_ORIGINS=https://your-frontend.pages.dev`

### Worker → Railway / Render (separate service)

1. Deploy `worker/` with start command: `python pipeline.py`
2. **Same volume** as backend (`DATA_DIR`)
3. Set `PYTHONPATH=/app/backend`
4. Use CPU instance; first run downloads ML models (~2–4 GB)

### Vector DB

- **Default (FAISS)**: No external service. Indexes stored in `DATA_DIR/indexes/`.
- **Qdrant free tier**: Set `VECTOR_BACKEND=qdrant`, `QDRANT_URL`, `QDRANT_API_KEY` at [cloud.qdrant.io](https://cloud.qdrant.io).

### LLM

- **Ollama** on same host or a separate free VM
- Or use evidence-only mode (no LLM server needed)

## Performance optimizations

- Downloads at **360p** (max 480p) — saves bandwidth and storage
- **Scene keyframes only** — not every frame
- **OCR deduplication** — repeated slides not re-indexed
- **Overlapping transcript chunks** — temporal context preserved
- **Temp file cleanup** after processing
- **int8 Whisper** on CPU — low RAM

## Example questions

- "What was written on the whiteboard?"
- "What graph or diagram appeared?"
- "What happened after the speaker mentioned transformers?"
- "Summarize the main topics in the first 5 minutes."

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Worker not picking up jobs | Ensure `DATA_DIR` matches backend |
| `yt-dlp` fails | Update: `pip install -U yt-dlp` |
| Out of memory | Use `WHISPER_MODEL=tiny` or `base` |
| Slow first run | Models download on first use (Whisper, CLIP, OCR) |
| No natural answers | Install Ollama + `gemma2:2b` |

## License

MIT — built with free/open-source tools only.
