"""
Ollama Chat Proxy — 把本地Ollama模型包装成OpenAI兼容API，带API Key计费。
支持流式SSE返回。
"""
import os
import httpx
import json
import time
import asyncio
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from .payment import validate_key, record_usage

router = APIRouter(prefix="/v1", tags=["Ollama Chat Proxy"])

OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")

# Model → tier mapping
MODEL_TIERS = {
    # Free tier
    "qwen2.5:7b": "free",
    "qwen2.5:7b-instruct": "free",
    "llama3.2:3b": "free",
    "llama3.2:3b-instruct": "free",
    "gemma3:1b": "free",
    "gemma3:1b-it-qat": "free",
    "phi3:mini": "free",
    "bge-m3:latest": "free",
    # Starter tier
    "qwen3.5:9b": "starter",
    "qwen3.5:9b-instruct": "starter",
    "qwen3.5:latest": "starter",
    "qwen3.5:9b-mlx": "starter",
    "qwen3.5:9b-mlx-fast": "starter",
    "qwen3.5:9b-mlx-custom": "starter",
    # Pro tier
    "gemma4:e4b-it-q4_K_M": "pro",
    "gemma4:e4b": "pro",
}

# Cost per model (USD cents per 1K tokens)
MODEL_COST = {
    # Free
    "qwen2.5:7b": 0.01,
    "qwen2.5:7b-instruct": 0.01,
    "llama3.2:3b": 0.005,
    "llama3.2:3b-instruct": 0.005,
    "gemma3:1b": 0.003,
    "gemma3:1b-it-qat": 0.003,
    "phi3:mini": 0.005,
    "bge-m3:latest": 0.005,
    # Starter
    "qwen3.5:9b": 0.02,
    "qwen3.5:9b-instruct": 0.02,
    "qwen3.5:latest": 0.02,
    "qwen3.5:9b-mlx": 0.02,
    "qwen3.5:9b-mlx-fast": 0.02,
    "qwen3.5:9b-mlx-custom": 0.02,
    # Pro
    "gemma4:e4b-it-q4_K_M": 0.03,
    "gemma4:e4b": 0.03,
}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "qwen2.5:7b"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


TIERMAP = {"free": 0, "starter": 1, "pro": 2, "enterprise": 3}


async def _validate_access(body: ChatRequest, x_api_key: str | None) -> tuple[str, str | None]:
    """Validate API key and tier access. Returns (tier, api_key_or_none)."""
    tier = "free"
    if x_api_key:
        k = validate_key(x_api_key)
        if not k:
            raise HTTPException(status_code=401, detail="Invalid or expired API key")
        tier = k.tier

    required_tier = MODEL_TIERS.get(body.model, "pro")
    if TIERMAP.get(tier, 0) < TIERMAP.get(required_tier, 2):
        raise HTTPException(
            status_code=402,
            detail=f"Model '{body.model}' requires {required_tier} tier or higher. Your tier: {tier}",
        )

    # Check Ollama is running
    try:
        async with httpx.AsyncClient(timeout=2.0, trust_env=False) as client:
            await client.get(f"{OLLAMA_BASE}/api/tags")
    except Exception:
        raise HTTPException(status_code=503, detail="Ollama backend not available")

    return tier, x_api_key


async def _proxy_nonstream(body: ChatRequest) -> dict:
    """Non-streaming proxy to Ollama."""
    ollama_payload = {"model": body.model, "messages": [m.model_dump() for m in body.messages], "stream": False}
    if body.temperature is not None:
        ollama_payload.setdefault("options", {})["temperature"] = body.temperature
    if body.max_tokens is not None:
        ollama_payload.setdefault("options", {})["num_predict"] = body.max_tokens

    async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
        resp = await client.post(f"{OLLAMA_BASE}/api/chat", json=ollama_payload)
        resp.raise_for_status()
        return resp.json()


async def _sse_stream(body: ChatRequest, api_key: str | None):
    """Stream Ollama response as OpenAI SSE chunks."""
    ollama_payload = {"model": body.model, "messages": [m.model_dump() for m in body.messages], "stream": True}
    if body.temperature is not None:
        ollama_payload.setdefault("options", {})["temperature"] = body.temperature
    if body.max_tokens is not None:
        ollama_payload.setdefault("options", {})["num_predict"] = body.max_tokens

    chat_id = f"chatcmpl-{int(time.time())}"
    created = int(time.time())
    model = body.model
    full_content = ""
    prompt_tokens = 0
    completion_tokens = 0

    # First chunk: role
    yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"

    async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
        async with client.stream("POST", f"{OLLAMA_BASE}/api/chat", json=ollama_payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                delta_content = chunk.get("message", {}).get("content", "")
                if delta_content:
                    full_content += delta_content
                    yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'content': delta_content}, 'finish_reason': None}]})}\n\n"

                if chunk.get("done"):
                    prompt_tokens = chunk.get("prompt_eval_count", 0) or len(str(ollama_payload)) // 4
                    completion_tokens = chunk.get("eval_count", 0) or len(full_content) // 4
                    break

    total_tokens = prompt_tokens + completion_tokens

    # Final chunk with finish_reason + usage
    yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens, 'total_tokens': total_tokens}})}\n\n"

    # [DONE] marker
    yield "data: [DONE]\n\n"

    # Record usage
    if api_key and total_tokens > 0:
        cost_per_1k = MODEL_COST.get(body.model, 0.02)
        est_cost = round(total_tokens * cost_per_1k / 1000, 6)
        record_usage(api_key, "chat_stream", total_tokens, est_cost)


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    body: ChatRequest,
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    """OpenAI-compatible chat completions endpoint backed by local Ollama models.
    Supports both streaming (SSE) and non-streaming responses."""
    start_time = time.time()
    tier, api_key = await _validate_access(body, x_api_key)

    if body.stream:
        # Streaming response
        async def generate():
            async for chunk in _sse_stream(body, api_key):
                yield chunk

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming
    try:
        ollama_resp = await _proxy_nonstream(body)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

    content = ollama_resp.get("message", {}).get("content", "")
    prompt_tokens = ollama_resp.get("prompt_eval_count", 0) or len(str(body.model_dump())) // 4
    completion_tokens = ollama_resp.get("eval_count", 0) or len(content) // 4
    total_tokens = prompt_tokens + completion_tokens

    cost_per_1k = MODEL_COST.get(body.model, 0.02)
    est_cost = round(total_tokens * cost_per_1k / 1000, 6)
    if api_key:
        record_usage(api_key, "chat", total_tokens, est_cost)

    elapsed = round(time.time() - start_time, 2)

    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
        "provider": "ollama",
        "latency_seconds": elapsed,
    }


@router.get("/models")
async def list_models():
    """List available models from Ollama."""
    try:
        async with httpx.AsyncClient(timeout=5.0, trust_env=False) as client:
            resp = await client.get(f"{OLLAMA_BASE}/api/tags")
            resp.raise_for_status()
            data = resp.json()

        models = []
        for m in data.get("models", []):
            name = m.get("name", "unknown")
            models.append({
                "id": name,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "ollama",
                "tier_required": MODEL_TIERS.get(name, "pro"),
                "cost_per_1k_tokens_usd": MODEL_COST.get(name, 0.02),
            })

        return {"object": "list", "data": models}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {str(e)}")
