"""
Chunker — configurable, duplicate-aware text splitter.
Stores user_id and document_id in every chunk's metadata.
"""

import re
import hashlib
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

CHUNK_SIZE    = 900
CHUNK_OVERLAP = 180
MIN_CHUNK     = 80


def chunk_document(
    text: str,
    source_file: str,
    file_type: str,
    user_id: str,
    document_id: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    extra_meta: dict | None = None,
) -> list[tuple[str, dict, str]]:
    """
    Split text → (chunk_text, metadata, unique_id) triples.
    Metadata includes user_id for scoped retrieval.
    """
    if not text or not text.strip():
        return []

    cleaned = _clean(text)
    if len(cleaned) < MIN_CHUNK:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
    )
    raw_chunks = splitter.split_text(cleaned)

    # Deduplicate by content hash
    seen_hashes: set[str] = set()
    results = []

    for i, chunk in enumerate(raw_chunks):
        chunk = chunk.strip()
        if len(chunk) < MIN_CHUNK:
            continue

        content_hash = hashlib.md5(chunk.encode()).hexdigest()[:8]
        if content_hash in seen_hashes:
            logger.debug("Skipping duplicate chunk %d in %s", i, source_file)
            continue
        seen_hashes.add(content_hash)

        meta: dict = {
            "source_file": source_file,
            "file_type": file_type,
            "user_id": user_id,
            "document_id": document_id,
            "chunk_index": i,
            "total_chunks": len(raw_chunks),
            "chunk_size": len(chunk),
            "content_hash": content_hash,
        }
        if extra_meta:
            meta.update(extra_meta)

        safe = source_file.replace("/", "_").replace(" ", "_")
        chunk_id = f"{user_id[:8]}_{safe}_{i}_{content_hash}"
        results.append((chunk, meta, chunk_id))

    logger.info("Chunked '%s': %d/%d chunks kept (user=%s)", source_file, len(results), len(raw_chunks), user_id[:8])
    return results


def _clean(text: str) -> str:
    text = text.replace("\x00", " ")
    text = "".join(c if c.isprintable() or c in "\n\t" else " " for c in text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()
