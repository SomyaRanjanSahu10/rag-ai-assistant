"""
Groq LLM Service — streaming + conversation-aware RAG prompting.
"""

import os
import time
import logging
from typing import AsyncGenerator
from groq import Groq, APIError, APITimeoutError, RateLimitError

from utils.errors import GroqAPIError

logger = logging.getLogger(__name__)

DEFAULT_MODEL   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_TOKENS      = int(os.getenv("MAX_TOKENS", "2048"))
TEMPERATURE     = float(os.getenv("TEMPERATURE", "0.1"))

_client: Groq | None = None


def get_groq_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise GroqAPIError("GROQ_API_KEY is not configured")
        _client = Groq(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You are DocMind, an intelligent document assistant.

Your job is to answer questions accurately using the provided document context.

Rules:
- Base answers primarily on the context provided. If context is insufficient, say so clearly.
- Cite sources using [Source: filename] notation when referencing specific information.
- Use markdown formatting: **bold**, bullet lists, code blocks, tables where appropriate.
- Be concise yet complete. Prefer structured answers for multi-part questions.
- If asked something not covered by the documents, acknowledge this honestly.
- Never fabricate facts or make up document content.

Context from documents:
---
{context}
---"""


def _format_context(chunks: list[dict]) -> str:
    if not chunks:
        return "No relevant context found in the uploaded documents."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        src  = meta.get("source_file", "Unknown")
        disp = src.split("_", 1)[-1] if "_" in src[:9] else src
        page = meta.get("chunk_index", "?")
        rel  = chunk.get("relevance_score", 0)
        parts.append(f"[{i}] Source: {disp} | chunk {page} | relevance {rel:.0%}\n{chunk.get('text', '')}")
    return "\n\n---\n\n".join(parts)


def build_messages(
    query: str,
    chunks: list[dict],
    history: list[dict] | None = None,
) -> list[dict]:
    context = _format_context(chunks)
    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(context=context)}]

    # Inject last N conversation turns
    if history:
        for msg in history[-12:]:
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": query})
    return messages


async def stream_rag_response(
    query: str,
    chunks: list[dict],
    history: list[dict] | None = None,
    model: str = DEFAULT_MODEL,
) -> AsyncGenerator[str, None]:
    """Async generator that yields text tokens as they stream from Groq."""
    client = get_groq_client()
    messages = build_messages(query, chunks, history)

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    except RateLimitError as exc:
        logger.error("Groq rate limit: %s", exc)
        yield "\n\n⚠️ Rate limit reached. Please wait a moment and try again."

    except APITimeoutError:
        logger.error("Groq API timeout")
        yield "\n\n⚠️ The LLM took too long to respond. Please try again."

    except APIError as exc:
        logger.error("Groq API error: %s", exc)
        yield f"\n\n⚠️ LLM error: {exc}"

    except Exception as exc:
        logger.exception("Unexpected error in stream_rag_response")
        yield f"\n\n⚠️ Unexpected error: {exc}"


def generate_session_title(first_message: str) -> str:
    """Generate a short chat session title from the user's first message."""
    try:
        client = get_groq_client()
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": f"Create a very short (4-6 words) title for a chat that starts with: '{first_message[:200]}'. Return ONLY the title, no quotes or punctuation."
            }],
            max_tokens=20,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()[:80]
    except Exception:
        return first_message[:50] + ("…" if len(first_message) > 50 else "")
