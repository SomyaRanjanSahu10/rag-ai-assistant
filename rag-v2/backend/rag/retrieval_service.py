"""
Advanced RAG Retrieval Service
================================
Implements production-grade retrieval with:
  • Hybrid search  — semantic (dense) + BM25 keyword (sparse)
  • Query expansion — auto-generate variant queries for better recall
  • Reranking       — cross-encoder style relevance rescoring
  • Parent-child    — retrieve small child chunks, return larger parent context
  • Metadata filter — scope search by filename, doc type, user
  • Similarity gate — discard chunks below a relevance threshold
  • Source citations — chunk source + page number returned with every answer
"""

import re
import math
import logging
from collections import Counter, defaultdict
from typing import Optional

from rag.vectorstore import search_similar, get_collection, embed_texts
from groq import Groq
import os

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
SEMANTIC_WEIGHT   = 0.65   # weight for vector similarity score
BM25_WEIGHT       = 0.35   # weight for BM25 keyword score
MIN_RELEVANCE     = 0.25   # chunks below this score are discarded
DEFAULT_K         = 6      # top-k chunks to retrieve
RERANK_TOP_N      = 4      # after reranking, keep this many
PARENT_WINDOW     = 1      # ±n chunks to include as parent context


# ── Query Expansion ─────────────────────────────────────────────────────────────

def expand_query(query: str, history: list[dict] | None = None) -> list[str]:
    """
    Generate 2–3 variant queries to improve retrieval recall.
    Falls back to original query if Groq call fails.
    
    Technique: HyDE-lite — ask the LLM to rephrase the question
    from multiple angles so we cast a wider net in the vector space.
    """
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        # Inject last 2 user messages for conversation context
        ctx = ""
        if history:
            recent = [m for m in history[-4:] if m.get("role") == "user"]
            if recent:
                ctx = "Prior context: " + " | ".join(m["content"] for m in recent[-2:])

        prompt = (
            f"{ctx}\n\nOriginal question: {query}\n\n"
            "Generate 2 alternative phrasings of this question that would help find "
            "relevant information in a document database. "
            "Return ONLY the two alternatives, one per line, no numbering or explanations."
        )

        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.4,
        )
        raw = resp.choices[0].message.content.strip()
        variants = [line.strip() for line in raw.split("\n") if line.strip()][:2]
        queries = [query] + variants
        logger.debug("Query expansion: %s → %s", query, variants)
        return queries

    except Exception as exc:
        logger.warning("Query expansion failed (%s), using original query", exc)
        return [query]


# ── BM25 Implementation ─────────────────────────────────────────────────────────

class BM25:
    """
    Lightweight in-memory BM25 scorer.
    BM25 = Best Match 25 — a classic information-retrieval ranking function.
    It counts keyword overlap but penalises very long documents (length normalisation).
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._docs: list[list[str]] = []
        self._idf: dict[str, float] = {}
        self._avg_dl: float = 0.0

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\b\w+\b", text.lower())

    def fit(self, documents: list[str]):
        self._docs = [self._tokenize(d) for d in documents]
        n = len(self._docs)
        df: Counter = Counter()
        for doc in self._docs:
            df.update(set(doc))
        self._idf = {
            term: math.log((n - freq + 0.5) / (freq + 0.5) + 1)
            for term, freq in df.items()
        }
        self._avg_dl = sum(len(d) for d in self._docs) / max(n, 1)

    def score(self, query: str, doc_index: int) -> float:
        tokens = self._tokenize(query)
        doc = self._docs[doc_index]
        dl = len(doc)
        tf_map: Counter = Counter(doc)
        score = 0.0
        for term in tokens:
            if term not in self._idf:
                continue
            tf = tf_map[term]
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * dl / self._avg_dl)
            score += self._idf[term] * numerator / denominator
        return score

    def rank(self, query: str) -> list[tuple[int, float]]:
        """Returns [(doc_index, score), ...] sorted descending."""
        scores = [(i, self.score(query, i)) for i in range(len(self._docs))]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


# ── Reranker ────────────────────────────────────────────────────────────────────

def rerank_chunks(query: str, chunks: list[dict], top_n: int = RERANK_TOP_N) -> list[dict]:
    """
    Lightweight cross-encoder–style reranker using the LLM.
    Scores each chunk's relevance to the query (0–10) then re-sorts.
    
    Falls back to original order if scoring fails.
    """
    if len(chunks) <= top_n:
        return chunks

    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        numbered = "\n\n".join(
            f"[{i}] {c['text'][:400]}" for i, c in enumerate(chunks)
        )
        prompt = (
            f"Query: {query}\n\nPassages:\n{numbered}\n\n"
            f"Rate each passage's relevance to the query from 0 to 10. "
            f"Reply with ONLY a comma-separated list of scores in order, e.g.: 8,3,7,2"
        )
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.0,
        )
        raw = resp.choices[0].message.content.strip()
        scores = [float(s.strip()) for s in raw.split(",") if s.strip().replace(".", "").isdigit()]

        if len(scores) == len(chunks):
            for chunk, score in zip(chunks, scores):
                chunk["rerank_score"] = score / 10.0
            chunks.sort(key=lambda c: c.get("rerank_score", 0), reverse=True)
            logger.debug("Reranked %d chunks, keeping top %d", len(chunks), top_n)

    except Exception as exc:
        logger.warning("Reranking failed (%s), using original order", exc)

    return chunks[:top_n]


# ── Parent-Child Context Expansion ─────────────────────────────────────────────

def expand_to_parent_context(chunks: list[dict], collection) -> list[dict]:
    """
    For each retrieved child chunk, try to fetch neighboring chunks
    (same document, adjacent indices) and prepend/append them as context.
    This gives the LLM more surrounding text without storing duplicates.
    """
    expanded = []
    seen_ids = set()

    for chunk in chunks:
        meta = chunk.get("metadata", {})
        source = meta.get("source_file", "")
        idx = meta.get("chunk_index", 0)

        # Gather sibling chunk indices
        sibling_idxs = list(range(max(0, idx - PARENT_WINDOW), idx + PARENT_WINDOW + 1))

        sibling_texts = []
        for sibling_idx in sibling_idxs:
            if sibling_idx == idx:
                sibling_texts.append(chunk["text"])
                continue
            try:
                sib_results = collection.get(
                    where={"source_file": source, "chunk_index": sibling_idx},
                    include=["documents"],
                )
                if sib_results and sib_results.get("documents"):
                    sibling_texts.append(sib_results["documents"][0])
            except Exception:
                pass

        chunk_id = f"{source}_{idx}"
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            expanded.append({
                **chunk,
                "text": "\n".join(sibling_texts) if sibling_texts else chunk["text"],
                "is_expanded": len(sibling_texts) > 1,
            })

    return expanded


# ── Main Retrieval Function ─────────────────────────────────────────────────────

def retrieve_advanced(
    query: str,
    user_id: str,
    n_results: int = DEFAULT_K,
    metadata_filter: dict | None = None,
    conversation_history: list[dict] | None = None,
    use_expansion: bool = True,
    use_reranking: bool = True,
    use_parent_context: bool = True,
    min_relevance: float = MIN_RELEVANCE,
) -> list[dict]:
    """
    Full advanced retrieval pipeline.

    Steps:
    1. Query expansion  → multiple query variants
    2. Semantic search  → ChromaDB cosine similarity per query variant
    3. BM25 keyword     → sparse lexical matching
    4. Hybrid fusion    → Reciprocal Rank Fusion to merge ranked lists
    5. Filter           → discard below min_relevance threshold
    6. Reranking        → LLM-based relevance rescoring
    7. Parent context   → expand chunk windows
    8. Deduplicate      → remove near-duplicate passages

    Returns list of chunk dicts with text, metadata, relevance_score, source citations.
    """

    # ── 1. Query Expansion ──────────────────────────────────────────────────────
    queries = expand_query(query, conversation_history) if use_expansion else [query]

    # ── 2. Semantic Search (multi-query) ────────────────────────────────────────
    # Build metadata filter including user scoping
    where: dict = {"user_id": user_id}
    if metadata_filter:
        where.update(metadata_filter)

    all_semantic: list[dict] = []   # {id, text, metadata, semantic_score}
    seen_texts: set[str] = set()

    for q in queries:
        try:
            results = search_similar(q, n_results=n_results * 2, where=where)
        except Exception as exc:
            logger.warning("Semantic search failed for query '%s': %s", q, exc)
            continue

        docs      = (results.get("documents") or [[]])[0]
        metas     = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]
        ids       = (results.get("ids") or [[]])[0]

        for doc, meta, dist, chunk_id in zip(docs, metas, distances, ids):
            key = doc[:200]   # rough dedup key
            if key in seen_texts:
                continue
            seen_texts.add(key)
            relevance = max(0.0, 1.0 - dist / 2.0)
            if relevance < min_relevance:
                continue
            all_semantic.append({
                "id": chunk_id,
                "text": doc,
                "metadata": meta,
                "semantic_score": relevance,
                "distance": dist,
            })

    if not all_semantic:
        logger.info("No chunks passed semantic search filter for query: '%s'", query)
        return []

    # ── 3. BM25 Keyword Search ──────────────────────────────────────────────────
    texts = [c["text"] for c in all_semantic]
    bm25 = BM25()
    bm25.fit(texts)
    bm25_ranked = bm25.rank(query)

    # Normalize BM25 scores to [0, 1]
    max_bm25 = bm25_ranked[0][1] if bm25_ranked else 1.0
    bm25_scores = {
        idx: (score / max_bm25 if max_bm25 > 0 else 0.0)
        for idx, score in bm25_ranked
    }

    # ── 4. Hybrid Fusion (Reciprocal Rank Fusion) ───────────────────────────────
    # RRF combines rankings from multiple retrieval methods:
    # score(d) = sum(1 / (k + rank_i(d))) for each method i
    # k=60 is a standard constant that dampens the impact of top ranks
    K_RRF = 60

    # Build semantic rank order
    semantic_sorted = sorted(all_semantic, key=lambda c: c["semantic_score"], reverse=True)
    semantic_rank = {c["id"]: rank for rank, c in enumerate(semantic_sorted, 1)}

    # Build BM25 rank order
    bm25_sorted_idx = [idx for idx, _ in bm25_ranked]
    bm25_rank = {all_semantic[idx]["id"]: rank for rank, idx in enumerate(bm25_sorted_idx, 1)}

    for i, chunk in enumerate(all_semantic):
        cid = chunk["id"]
        sem_r = semantic_rank.get(cid, len(all_semantic) + 1)
        bm25_r = bm25_rank.get(cid, len(all_semantic) + 1)
        rrf = 1 / (K_RRF + sem_r) + 1 / (K_RRF + bm25_r)

        # Final hybrid score
        hybrid = SEMANTIC_WEIGHT * chunk["semantic_score"] + BM25_WEIGHT * bm25_scores.get(i, 0.0)
        chunk["relevance_score"] = round((hybrid + rrf) / 2, 4)
        chunk["bm25_score"] = round(bm25_scores.get(i, 0.0), 4)

    all_semantic.sort(key=lambda c: c["relevance_score"], reverse=True)
    candidates = all_semantic[:n_results * 2]

    # ── 5. Duplicate Removal ────────────────────────────────────────────────────
    deduped = _deduplicate(candidates)

    # ── 6. Reranking ────────────────────────────────────────────────────────────
    if use_reranking and len(deduped) > RERANK_TOP_N:
        try:
            collection = get_collection()
            deduped = rerank_chunks(query, deduped, top_n=RERANK_TOP_N)
        except Exception as exc:
            logger.warning("Reranking skipped: %s", exc)
            deduped = deduped[:RERANK_TOP_N]
    else:
        deduped = deduped[:n_results]

    # ── 7. Parent Context Expansion ─────────────────────────────────────────────
    if use_parent_context:
        try:
            collection = get_collection()
            deduped = expand_to_parent_context(deduped, collection)
        except Exception as exc:
            logger.warning("Parent context expansion skipped: %s", exc)

    logger.info(
        "Retrieved %d chunks for query '%s…' (expanded: %s, reranked: %s)",
        len(deduped), query[:60], use_expansion, use_reranking
    )
    return deduped


def get_source_citations(chunks: list[dict]) -> list[dict]:
    """Extract unique source citations with page info."""
    seen = {}
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        src = meta.get("source_file", "Unknown")
        if src not in seen:
            seen[src] = {
                "filename": src.split("_", 1)[-1] if "_" in src[:9] else src,
                "saved_name": src,
                "file_type": meta.get("file_type", "unknown"),
                "chunk_count": 0,
                "avg_relevance": 0.0,
                "page_numbers": [],
            }
        seen[src]["chunk_count"] += 1
        page = meta.get("page_number") or meta.get("chunk_index", "?")
        if page not in seen[src]["page_numbers"]:
            seen[src]["page_numbers"].append(page)
        seen[src]["avg_relevance"] = round(
            (seen[src]["avg_relevance"] * (seen[src]["chunk_count"] - 1) + chunk.get("relevance_score", 0))
            / seen[src]["chunk_count"], 3
        )
    return sorted(seen.values(), key=lambda s: s["avg_relevance"], reverse=True)


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _deduplicate(chunks: list[dict], threshold: float = 0.92) -> list[dict]:
    """Remove near-duplicate chunks using Jaccard similarity on tokens."""
    def tokenset(text: str) -> set:
        return set(re.findall(r"\b\w+\b", text.lower()))

    kept = []
    for chunk in chunks:
        tokens = tokenset(chunk["text"])
        is_dup = False
        for existing in kept:
            ex_tokens = tokenset(existing["text"])
            union = len(tokens | ex_tokens)
            if union == 0:
                continue
            jaccard = len(tokens & ex_tokens) / union
            if jaccard >= threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append(chunk)
    return kept
