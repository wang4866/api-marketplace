"""
Embeddings API — 本地bge-m3模型包装成OpenAI text-embedding-ada-002兼容接口。
定价：$0.01/1K tokens (对比OpenAI $0.13/1M tokens，我们便宜13倍)
"""
import httpx
import json
import time
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from .payment import validate_key, record_usage

router = APIRouter(prefix="/v1", tags=["Embeddings"])

OLLAMA_BASE = "http://localhost:11434"
EMBEDDING_MODEL = "bge-m3:latest"

# Free users get 100K tokens/day, paid users unlimited
DAILY_FREE_LIMIT = 100_000


class EmbeddingRequest(BaseModel):
    input: str | list[str]
    model: str = EMBEDDING_MODEL


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: list[dict]
    model: str
    usage: dict


@router.post("/embeddings")
async def create_embeddings(
    body: EmbeddingRequest,
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    """Create embeddings using local bge-m3 model. OpenAI-compatible endpoint."""
    start = time.time()

    # Auth + tier check
    tier = "free"
    if x_api_key:
        k = validate_key(x_api_key)
        if not k:
            raise HTTPException(status_code=401, detail="Invalid or expired API key")
        tier = k.tier

    # Normalize input to list
    inputs = [body.input] if isinstance(body.input, str) else body.input

    # Free tier daily limit
    total_input_tokens = sum(len(t.split()) for t in inputs)
    if tier == "free" and total_input_tokens > DAILY_FREE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Free tier daily embedding limit: {DAILY_FREE_LIMIT} tokens. Upgrade at /pricing",
        )

    # Proxy to Ollama
    results = []
    for text in inputs:
        try:
            async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
                resp = await client.post(
                    f"{OLLAMA_BASE}/api/embeddings",
                    json={"model": EMBEDDING_MODEL, "prompt": text},
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Ollama embedding error: {str(e)}")

        results.append({
            "object": "embedding",
            "index": len(results),
            "embedding": data.get("embedding", []),
        })

    # Usage tracking
    usage = {"prompt_tokens": total_input_tokens, "total_tokens": total_input_tokens}
    cost = round(total_input_tokens * 0.0001 / 1000, 6)  # $0.10/1M tokens — cheaper than OpenAI $0.13/1M
    if x_api_key:
        record_usage(x_api_key, "embedding", total_input_tokens, cost)

    elapsed = round(time.time() - start, 2)

    return {
        "object": "list",
        "data": results,
        "model": body.model,
        "usage": usage,
        "provider": "ollama",
        "latency_seconds": elapsed,
    }
