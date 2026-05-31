"""Communicate with the local API Marketplace server."""
import httpx
from typing import Any, Optional, List, Dict

API_BASE = "http://localhost:8000"

# Must set trust_env=False to bypass macOS SOCKS5 proxy
_client = httpx.Client(trust_env=False, timeout=httpx.Timeout(30.0))

def _get(path: str) -> Dict[str, Any]:
    r = _client.get(API_BASE + path)
    r.raise_for_status()
    return r.json()

def _post(path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    r = _client.post(API_BASE + path, json=data)
    r.raise_for_status()
    return r.json()

def health() -> Dict[str, Any]:
    return _get("/health")

def list_models() -> List[Dict[str, Any]]:
    return _get("/v1/models").get("data", [])

def chat(model: str, prompt: str) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    data = _post("/v1/chat/completions", payload)
    return data["choices"][0]["message"]["content"]

def embed(input_text: str) -> Dict[str, Any]:
    return _post("/v1/embeddings", {"input": [input_text]})

def check_ollama() -> bool:
    try:
        r = httpx.Client(trust_env=False, timeout=3).get("http://localhost:11434/api/tags")
        return r.status_code == 200
    except Exception:
        return False
