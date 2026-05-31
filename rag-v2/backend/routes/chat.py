"""
Chat Routes
===========
POST /api/chat/sessions              — create session
GET  /api/chat/sessions              — list sessions
GET  /api/chat/sessions/:id          — get session + messages
PUT  /api/chat/sessions/:id          — rename session
DELETE /api/chat/sessions/:id        — delete session
POST /api/chat/sessions/:id/stream   — streaming chat
"""

import json
import time
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth_deps import get_current_user
from models.user import User
from repositories.chat_repo import (
    create_session, get_session, list_sessions,
    rename_session, delete_session, add_message,
    get_messages, increment_message_count,
)
from rag.retrieval_service import retrieve_advanced, get_source_citations
from services.groq_service import stream_rag_response, generate_session_title
from utils.errors import NotFoundError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])


class CreateSessionRequest(BaseModel):
    model: str = "llama-3.3-70b-versatile"


class RenameRequest(BaseModel):
    title: str


class ChatRequest(BaseModel):
    message: str
    n_results: int = 6
    model: str = "llama-3.3-70b-versatile"
    metadata_filter: dict | None = None


# ── Session CRUD ───────────────────────────────────────────────────────────────

@router.post("/sessions", status_code=201)
async def create_chat_session(
    body: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await create_session(db, current_user.id, model=body.model)
    await db.commit()
    return {"success": True, "session": session.to_dict()}


@router.get("/sessions")
async def list_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sessions = await list_sessions(db, current_user.id)
    return {"success": True, "sessions": [s.to_dict() for s in sessions]}


@router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await get_session(db, session_id, current_user.id)
    if not session:
        raise NotFoundError("Chat session")
    messages = await get_messages(db, session_id)
    return {
        "success": True,
        "session": session.to_dict(),
        "messages": [m.to_dict() for m in messages],
    }


@router.put("/sessions/{session_id}")
async def rename_chat_session(
    session_id: str,
    body: RenameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await get_session(db, session_id, current_user.id)
    if not session:
        raise NotFoundError("Chat session")
    session = await rename_session(db, session, body.title)
    await db.commit()
    return {"success": True, "session": session.to_dict()}


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await get_session(db, session_id, current_user.id)
    if not session:
        raise NotFoundError("Chat session")
    await delete_session(db, session)
    await db.commit()
    return {"success": True, "message": "Session deleted"}


# ── Streaming Chat ─────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/stream")
async def stream_chat(
    session_id: str,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await get_session(db, session_id, current_user.id)
    if not session:
        raise NotFoundError("Chat session")

    if not body.message.strip():
        raise ValueError("Message cannot be empty")

    async def event_generator():
        start = time.time()
        full_response = ""

        # ── 1. Retrieve context ──────────────────────────────────────────────
        history_msgs = await get_messages(db, session_id, limit=20)
        history = [{"role": m.role, "content": m.content} for m in history_msgs]

        chunks = retrieve_advanced(
            query=body.message,
            user_id=current_user.id,
            n_results=body.n_results,
            metadata_filter=body.metadata_filter,
            conversation_history=history,
        )
        sources = get_source_citations(chunks)

        yield f"data: {json.dumps({'type': 'start', 'chunks_found': len(chunks), 'sources': sources})}\n\n"

        # ── 2. Stream LLM response ───────────────────────────────────────────
        async for token in stream_rag_response(
            query=body.message,
            chunks=chunks,
            history=history,
            model=body.model,
        ):
            full_response += token
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        # ── 3. Persist messages + update session ─────────────────────────────
        latency = int((time.time() - start) * 1000)
        try:
            await add_message(db, session_id, "user", body.message)
            await add_message(
                db, session_id, "assistant", full_response,
                sources=sources, chunks_used=len(chunks), latency_ms=latency,
            )
            # Auto-generate title from first user message
            if session.message_count == 0:
                title = generate_session_title(body.message)
                await rename_session(db, session, title)

            await increment_message_count(db, session)
            await db.commit()
        except Exception as exc:
            logger.error("Failed to persist chat message: %s", exc)

        yield f"data: {json.dumps({'type': 'done', 'sources': sources, 'latency_ms': latency})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
