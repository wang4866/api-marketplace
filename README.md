# Local AI Proxy

**Turn your local Ollama into a production-ready OpenAI-compatible API. One command, zero cloud.**

```
pip install local-ai-proxy
local-ai
```

## Features

- **OpenAI-compatible API** - Use any OpenAI SDK with `base_url=http://localhost:8000/v1`
- **11 local models** - qwen3.5, gemma4, llama3.2, bge-m3 embeddings
- **Streaming SSE** - Real-time chat output
- **4 pricing tiers** - Free to Enterprise-ready
- **Usage tracking** - Built-in API key system with SQLite
- **SSD latency** - No network round-trips
- **Privacy** - Your data never leaves your machine

## Quick Start

```bash
# Install
pip install local-ai-proxy

# Start (macOS)
local-ai serve

# List models
local-ai models

# Chat
local-ai chat "What is the meaning of life?"

# Embeddings
local-ai embed "Hello world"

# Open dashboard
local-ai dashboard
```

## Use with any OpenAI SDK

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-local")
response = client.chat.completions.create(
    model="qwen2.5:7b",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

## Support

If this tool saves you time or money, consider donating:

- **USDT (TRC20):** `0x85Ea457bE39E42C05D296D9b526e03a68D48A1f`
- **GitHub Sponsors:** https://github.com/sponsors/wang4866

Built with :heart: by Hermes Agent. MIT License.
