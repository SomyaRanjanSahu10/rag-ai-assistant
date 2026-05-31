"""
Vector Store — ChromaDB wrapper with user-scoped metadata.
Each chunk stores user_id so retrieval can be filtered per user.
"""

import logging
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_client = None
_collection = None
_model = None

COLLECTION_NAME = "rag_documents_v2"
EMBEDDING_MODEL  = "sentence-transformers/all-MiniLM-L6-v2"


def initialize_vectorstore():
    global _client, _collection, _model
    import os
    logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
    _model = SentenceTransformer(EMBEDDING_MODEL)

    _client = chromadb.PersistentClient(
        path="./vectorstore",
        settings=Settings(anonymized_telemetry=False),
    )
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("ChromaDB ready. Chunks in store: %d", _collection.count())


def get_collection():
    if _collection is None:
        raise RuntimeError("Vector store not initialized")
    return _collection


def embed_texts(texts: list[str]) -> list[list[float]]:
    return _model.encode(texts, show_progress_bar=False).tolist()


def add_documents(texts: list[str], metadatas: list[dict], ids: list[str]):
    col = get_collection()
    embeddings = embed_texts(texts)
    col.add(documents=texts, embeddings=embeddings, metadatas=metadatas, ids=ids)
    logger.info("Added %d chunks to vector store", len(texts))


def search_similar(query: str, n_results: int = 6, where: dict | None = None) -> dict:
    col = get_collection()
    total = col.count()
    if total == 0:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}
    n = min(n_results, total)
    q_emb = embed_texts([query])[0]
    kwargs = {"query_embeddings": [q_emb], "n_results": n, "include": ["documents", "metadatas", "distances"]}
    if where:
        kwargs["where"] = where
    try:
        return col.query(**kwargs)
    except Exception as exc:
        logger.warning("ChromaDB query error (where=%s): %s", where, exc)
        kwargs.pop("where", None)
        return col.query(**kwargs)


def delete_by_source(source_file: str, user_id: str) -> int:
    col = get_collection()
    results = col.get(where={"$and": [{"source_file": source_file}, {"user_id": user_id}]}, include=["metadatas"])
    if results and results.get("ids"):
        col.delete(ids=results["ids"])
        return len(results["ids"])
    return 0


def get_all_sources(user_id: str) -> list[dict]:
    col = get_collection()
    if col.count() == 0:
        return []
    results = col.get(where={"user_id": user_id}, include=["metadatas"])
    seen = {}
    for meta in (results.get("metadatas") or []):
        src = meta.get("source_file", "unknown")
        if src not in seen:
            seen[src] = meta
    return list(seen.values())


def get_document_count() -> int:
    return get_collection().count()
