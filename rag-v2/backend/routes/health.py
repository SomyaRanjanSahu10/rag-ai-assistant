"""Health check."""
import os
from fastapi import APIRouter
from rag.vectorstore import get_document_count

router = APIRouter(prefix="/api", tags=["Health"])

@router.get("/health")
async def health():
    try:
        chunks = get_document_count()
        return {"status": "healthy", "version": "2.0.0", "chunks_indexed": chunks, "groq_configured": bool(os.getenv("GROQ_API_KEY"))}
    except Exception as exc:
        return {"status": "degraded", "error": str(exc)}
