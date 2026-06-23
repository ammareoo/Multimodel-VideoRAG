from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import videos
from config import CORS_ORIGINS, LLM_PROVIDER, VECTOR_BACKEND
from models import db
from models.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title="Multimodal VideoRAG API",
    description="Production-grade free multimodal video RAG system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        vector_backend=VECTOR_BACKEND,
        llm_provider=LLM_PROVIDER,
    )
