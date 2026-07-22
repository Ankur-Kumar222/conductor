"""Thin OpenAI wrapper for structured + text completions (GPT-5, Responses API)."""
from __future__ import annotations

import asyncio
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

_client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

T = TypeVar("T", bound=BaseModel)


@retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def structured(system: str, user: str, schema: type[T], model: str | None = None,
               effort: str = "low") -> T:
    """Return a validated Pydantic object using the Responses API structured output."""
    resp = _client.responses.parse(
        model=model or settings.openai_chat_model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        text_format=schema,
        reasoning={"effort": effort},
    )
    parsed = resp.output_parsed
    if parsed is None:
        raise ValueError("LLM returned no parsed output")
    return parsed


@retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def text(system: str, user: str, model: str | None = None, effort: str = "low") -> str:
    resp = _client.responses.create(
        model=model or settings.openai_chat_model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        reasoning={"effort": effort},
    )
    return resp.output_text


async def structured_async(system: str, user: str, schema: type[T], model: str | None = None,
                           effort: str = "low") -> T:
    return await asyncio.to_thread(structured, system, user, schema, model, effort)


async def text_async(system: str, user: str, model: str | None = None, effort: str = "low") -> str:
    return await asyncio.to_thread(text, system, user, model, effort)
