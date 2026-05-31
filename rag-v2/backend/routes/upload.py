"""
Upload Route
============
POST /api/upload           — single file upload
POST /api/upload/multiple  — batch upload
"""

import os
import uuid
import time
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth_deps import get_current_user
from models.user import User
from repositories.document_repo import create_document, list_documents, get_document, delete_document as db_delete_doc
from rag.vectorstore import delete_by_source, get_all_sources
from services.document_processor import extract_text_from_file
from rag.chunker import chunk_document
from rag.vectorstore import add_documents
from utils.errors import ValidationError, FileProcessingError, NotFoundError, ForbiddenError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Documents"])

UPLOAD_DIR   = "uploads"
MAX_SIZE     = int(os.getenv("MAX_FILE_SIZE_MB", "50")) * 1024 * 1024
ALLOWED_EXTS = {".pdf": "pdf", ".docx": "docx", ".txt": "txt",
                ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image"}


def _validate(filename: str, size: int) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise ValidationError(f"File type '{ext}' not supported. Allowed: {', '.join(ALLOWED_EXTS)}")
    if size > MAX_SIZE:
        raise ValidationError(f"File too large ({size/1e6:.1f} MB). Max {MAX_SIZE//1e6:.0f} MB")
    return ALLOWED_EXTS[ext]


def _safe_name(original: str) -> str:
    name = Path(original).name
    name = "".join(c if c.isalnum() or c in "._- " else "_" for c in name)
    return f"{uuid.uuid4().hex[:8]}_{name}"


async def _index_file(file_path: str, saved_name: str, file_type: str, user_id: str, doc_id: str, db: AsyncSession):
    """Extract → chunk → embed → store. Updates document status in DB."""
    from repositories.document_repo import get_document, update_document
    try:
        text, meta = extract_text_from_file(file_path)
        if not text.strip():
            raise FileProcessingError("No text could be extracted from this file")

        chunks = chunk_document(
            text=text, source_file=saved_name, file_type=file_type,
            user_id=user_id, document_id=doc_id,
            extra_meta={"page_count": meta.get("page_count", 1)},
        )
        if not chunks:
            raise FileProcessingError("Document text was too short after processing")

        texts    = [c[0] for c in chunks]
        metas    = [c[1] for c in chunks]
        ids      = [c[2] for c in chunks]
        add_documents(texts, metas, ids)

        doc = await get_document(db, doc_id, user_id)
        if doc:
            await update_document(db, doc, {
                "status": "ready",
                "chunk_count": len(chunks),
                "char_count": len(text),
                "extraction_method": meta.get("method", "unknown"),
            })
            await db.commit()

    except Exception as exc:
        logger.error("Indexing failed for %s: %s", saved_name, exc)
        try:
            doc = await get_document(db, doc_id, user_id)
            if doc:
                await update_document(db, doc, {"status": "error", "error_message": str(exc)})
                await db.commit()
        except Exception:
            pass


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content  = await file.read()
    size     = len(content)
    ftype    = _validate(file.filename, size)
    saved    = _safe_name(file.filename)
    fpath    = os.path.join(UPLOAD_DIR, saved)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(fpath, "wb") as f:
        f.write(content)

    # Create DB record (status=processing)
    doc = await create_document(db, {
        "user_id":    current_user.id,
        "original_name": file.filename,
        "saved_name": saved,
        "file_type":  ftype,
        "file_size":  size,
        "status":     "processing",
    })
    await db.commit()

    # Index in background so we respond immediately
    background_tasks.add_task(_index_file, fpath, saved, ftype, current_user.id, doc.id, db)

    logger.info("Upload queued: %s by user %s", saved, current_user.id)
    return JSONResponse(status_code=202, content={
        "success": True,
        "message": f"'{file.filename}' uploaded and indexing in background",
        "document": doc.to_dict(),
    })


@router.get("/documents")
async def get_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    docs = await list_documents(db, current_user.id)
    return {
        "success": True,
        "documents": [d.to_dict() for d in docs],
        "total": len(docs),
    }


@router.delete("/documents/{doc_id}")
async def delete_doc(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await get_document(db, doc_id, current_user.id)
    if not doc:
        raise NotFoundError("Document")

    # Remove from vector store
    deleted_chunks = delete_by_source(doc.saved_name, current_user.id)

    # Remove from disk
    fpath = os.path.join(UPLOAD_DIR, doc.saved_name)
    if os.path.exists(fpath):
        os.remove(fpath)

    await db_delete_doc(db, doc)
    await db.commit()

    return {
        "success": True,
        "message": f"Deleted '{doc.original_name}'",
        "chunks_deleted": deleted_chunks,
    }
