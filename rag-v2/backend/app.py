"""
DocMind v2 — Production RAG Application
========================================
FastAPI entry point. Wires together:
  - Database init
  - Vector store init
  - Middleware (CORS, rate limiting, logging)
  - Route modules
  - Global error handlers
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

os.makedirs("uploads", exist_ok=True)
os.makedirs("vectorstore", exist_ok=True)
os.makedirs("logs", exist_ok=True)

from utils.logger import setup_logging
setup_logging()

logger = logging.getLogger(__name__)

from database import init_db, close_db
from rag.vectorstore import initialize_vectorstore
from utils.errors import register_exception_handlers
from middleware.rate_limit import RateLimitMiddleware

from routes.auth import router as auth_router
from routes.upload import router as upload_router
from routes.chat import router as chat_router
from routes.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 DocMind v2 starting…")
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("vectorstore", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    await init_db()
    # initialize_vectorstore()  # Vector store is now lazily initialized on first use to avoid startup delays   

    logger.info("✅ All systems ready")
    yield

    await close_db()
    logger.info("👋 Shutdown complete")


app = FastAPI(
    title="DocMind API v2",
    description="Production RAG AI Document Assistant",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,https://docmind-ai-assistant.vercel.app").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

# ── Rate limiting ──────────────────────────────────────────────────────────────
app.add_middleware(RateLimitMiddleware)

# ── Error handlers ─────────────────────────────────────────────────────────────
register_exception_handlers(app)

# ── Routes ─────────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(chat_router)
app.include_router(health_router)

# ── Static files ───────────────────────────────────────────────────────────────
if os.path.exists("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def root():
    return {"name": "DocMind API v2", "docs": "/docs", "health": "/api/health"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=False, log_level="info")
