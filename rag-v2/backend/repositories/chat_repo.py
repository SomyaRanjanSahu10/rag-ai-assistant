"""Chat repository — DB operations for sessions and messages."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from models.chat import ChatSession, ChatMessage

logger = logging.getLogger(__name__)


# ── Sessions ───────────────────────────────────────────────────────────────────

async def create_session(db: AsyncSession, user_id: str, model: str = "llama-3.3-70b-versatile") -> ChatSession:
    session = ChatSession(user_id=user_id, model=model)
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: str, user_id: str) -> ChatSession | None:
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_sessions(db: AsyncSession, user_id: str, limit: int = 50) -> list[ChatSession]:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id, ChatSession.is_archived == False)
        .order_by(ChatSession.updated_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def rename_session(db: AsyncSession, session: ChatSession, title: str) -> ChatSession:
    session.title = title[:200]
    db.add(session)
    await db.flush()
    return session


async def delete_session(db: AsyncSession, session: ChatSession):
    await db.delete(session)
    await db.flush()


# ── Messages ───────────────────────────────────────────────────────────────────

async def add_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    sources: list | None = None,
    chunks_used: int = 0,
    latency_ms: int = 0,
) -> ChatMessage:
    msg = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        sources=sources or [],
        chunks_used=chunks_used,
        latency_ms=latency_ms,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg


async def get_messages(db: AsyncSession, session_id: str, limit: int = 100) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def increment_message_count(db: AsyncSession, session: ChatSession):
    session.message_count = (session.message_count or 0) + 2  # user + assistant
    db.add(session)
    await db.flush()
