"""OpenAI embeddings (text-embedding-3-small @ 1536d) with batching + retry."""
from __future__ import annotations

import asyncio

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

_client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

_BATCH = 128
_MAX_CHARS = 8000  # keep well under the model's token limit per input


def _clean(text: str) -> str:
    text = (text or "").replace("\x00", " ").strip()
    return text[:_MAX_CHARS] if text else " "


@retry(reraise=True, stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=1, max=20))
def _embed_batch(texts: list[str]) -> list[list[float]]:
    resp = _client.embeddings.create(
        model=settings.openai_embedding_model,
        input=texts,
        dimensions=settings.embedding_dim,
    )
    return [d.embedding for d in resp.data]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts, batching to stay within API limits."""
    if not texts:
        return []
    cleaned = [_clean(t) for t in texts]
    out: list[list[float]] = []
    for i in range(0, len(cleaned), _BATCH):
        out.extend(_embed_batch(cleaned[i : i + _BATCH]))
    return out


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


async def embed_texts_async(texts: list[str]) -> list[list[float]]:
    return await asyncio.to_thread(embed_texts, texts)


async def embed_text_async(text: str) -> list[float]:
    return await asyncio.to_thread(embed_text, text)
