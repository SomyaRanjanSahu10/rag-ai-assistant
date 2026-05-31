"""Document repository — all DB operations for the Document model."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from models.document import Document

logger = logging.getLogger(__name__)


async def create_document(db: AsyncSession, data: dict) -> Document:
    doc = Document(**data)
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


async def get_document(db: AsyncSession, doc_id: str, user_id: str) -> Document | None:
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_document_by_saved_name(db: AsyncSession, saved_name: str, user_id: str) -> Document | None:
    result = await db.execute(
        select(Document).where(Document.saved_name == saved_name, Document.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_documents(db: AsyncSession, user_id: str) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def update_document(db: AsyncSession, doc: Document, updates: dict) -> Document:
    for k, v in updates.items():
        setattr(doc, k, v)
    db.add(doc)
    await db.flush()
    return doc


async def delete_document(db: AsyncSession, doc: Document):
    await db.delete(doc)
    await db.flush()
