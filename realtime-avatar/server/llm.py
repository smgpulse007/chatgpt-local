from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Dict

import httpx

from config import settings

SYSTEM_PROMPT = "Be concise. Start with a short sentence (<= 12 words). Then continue."


async def _post_chat(prompt: str) -> str:
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{settings.LLM_URL}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"].strip()


def _split_sentences(text: str) -> Dict[str, str]:
    if not text:
        return {"first": "", "rest": ""}
    parts = text.split(". ", 1)
    first = parts[0].strip()
    rest = parts[1].strip() if len(parts) > 1 else ""
    if first and not first.endswith("."):
        first += "."
    return {"first": first, "rest": rest}


async def infer(prompt: str) -> Dict[str, str]:
    text = await _post_chat(prompt)
    return _split_sentences(text)


async def stream_infer(prompt: str) -> AsyncGenerator[str, None]:
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", f"{settings.LLM_URL}/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                yield line


__all__ = ["infer", "stream_infer"]
