"""
API Marketplace - Main Application
Web-to-Markdown Conversion API
"""

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pathlib import Path
from pydantic import BaseModel, HttpUrl
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .web_to_md import url_to_markdown
from .payment import validate_key, create_key, TIERS
from .ollama_proxy import router as ollama_router
from .embeddings_proxy import router as embeddings_router

# --- App Setup ---

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Web2MD API",
    description="Convert any webpage to clean Markdown. Simple, fast, developer-friendly.",
    version="1.0.0",
    contact={
        "name": "API Marketplace",
        "url": "https://github.com/wang4866/api-marketplace",
    },
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ollama_router)
app.include_router(embeddings_router)


# --- Request/Response Models ---

class ConvertRequest(BaseModel):
    url: str
    include_images: bool = False


class ConvertResponse(BaseModel):
    success: bool
    title: str
    content: str
    url: str
    word_count: int
    char_count: int


class BatchConvertRequest(BaseModel):
    urls: list[str]
    include_images: bool = False
    parallel: bool = True


class BatchConvertResponse(BaseModel):
    success: bool
    total: int
    succeeded: int
    failed: int
    results: list[ConvertResponse | dict]


class CreateKeyRequest(BaseModel):
    tier: str = "free"
    email: str = "anonymous@user.com"


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: str = ""


# --- API Endpoints ---

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Web2MD API",
        "version": "1.0.0",
        "description": "Convert any webpage to clean Markdown",
        "endpoints": {
            "convert": "POST /convert - Convert a URL to Markdown",
            "health": "GET /health - Health check",
            "docs": "GET /docs - API documentation (Swagger UI)",
        },
    }


@app.get("/health")
async def health(x_api_key: str = Header(None, alias="X-API-Key")):
    """Health check endpoint."""
    key_info = None
    if x_api_key:
        k = validate_key(x_api_key)
        if k:
            key_info = {"tier": k.tier, "usage_today": k.usage_today}
    return {"status": "healthy", "service": "web2md-api", "key": key_info}


@app.get("/pricing")
async def pricing():
    """Get available pricing tiers."""
    return {"tiers": {k: {kk: vv for kk, vv in v.items() if kk != "price_monthly"} | {"price_usd_monthly": v["price_monthly"]} for k, v in TIERS.items()}}


@app.post("/key/create")
async def create_api_key(body: CreateKeyRequest = CreateKeyRequest()):
    """Create a new API key (for testing). Production goes through Stripe."""
    if body.tier not in TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Options: {list(TIERS.keys())}")
    key = create_key(body.tier, body.email)
    return {"key": key.key, "tier": key.tier, "expires_at": key.expires_at}


@app.get("/key/info")
async def key_info(x_api_key: str = Header(alias="X-API-Key")):
    """Get info about your API key."""
    k = validate_key(x_api_key)
    if not k:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    tier_config = TIERS.get(k.tier, {})
    return {
        "tier": k.tier,
        "usage_today": k.usage_today,
        "daily_limit": tier_config.get("requests_per_day", "unlimited"),
        "max_content_length": tier_config.get("max_content_length", "unlimited"),
        "expires_at": k.expires_at,
    }


@app.post(
    "/convert",
    response_model=ConvertResponse,
    responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
    summary="Convert webpage URL to Markdown",
    description="Fetch a webpage and convert its main content to clean Markdown format.",
)
@limiter.limit("100/hour")
async def convert(request: Request, body: ConvertRequest, x_api_key: str = Header(None, alias="X-API-Key")):
    """
    Convert a webpage URL to clean Markdown.

    - **url**: The full URL of the webpage to convert (required)
    - **include_images**: Whether to include image markdown references (default: false)
    """
    # Track usage if API key provided
    if x_api_key:
        k = validate_key(x_api_key)
        if not k:
            raise HTTPException(status_code=401, detail="Invalid or expired API key")

    url = body.url.strip()

    # Basic URL validation
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Must start with http:// or https://",
        )

    try:
        result = await url_to_markdown(url, include_images=body.include_images)
        return ConvertResponse(
            success=True,
            title=result["title"],
            content=result["content"],
            url=result["url"],
            word_count=result["word_count"],
            char_count=result["char_count"],
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch URL: HTTP {e.response.status_code}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch URL: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}",
        )


@app.post(
    "/batch",
    response_model=BatchConvertResponse,
    summary="Batch convert multiple URLs to Markdown",
    description="Convert multiple webpage URLs to Markdown in one call.",
)
async def batch_convert(request: Request, body: BatchConvertRequest, x_api_key: str = Header(None, alias="X-API-Key")):
    """Convert multiple URLs to Markdown."""
    # Validate API key
    tier = "free"
    if x_api_key:
        k = validate_key(x_api_key)
        if not k:
            raise HTTPException(status_code=401, detail="Invalid or expired API key")
        tier = k.tier

    # Tier limit on batch size
    max_batch = {"free": 3, "starter": 20, "pro": 100, "enterprise": 500}.get(tier, 5)
    if len(body.urls) > max_batch:
        raise HTTPException(status_code=400, detail=f"Free tier max {max_batch} URLs per batch. Upgrade for larger batches.")

    import asyncio

    async def convert_one(url: str) -> ConvertResponse | dict:
        try:
            result = await url_to_markdown(url, include_images=body.include_images)
            return ConvertResponse(
                success=True, title=result["title"],
                content=f"{result['content'][:200]}...",  # Truncated in batch view
                url=result["url"],
                word_count=result["word_count"],
                char_count=result["char_count"],
            )
        except Exception as e:
            return {"success": False, "url": url, "error": str(e)}

    if body.parallel:
        tasks = [convert_one(url) for url in body.urls]
        results = await asyncio.gather(*tasks, return_exceptions=False)
    else:
        results = []
        for url in body.urls:
            results.append(await convert_one(url))

    succeeded = sum(1 for r in results if isinstance(r, ConvertResponse))
    return BatchConvertResponse(
        success=True,
        total=len(body.urls),
        succeeded=succeeded,
        failed=len(body.urls) - succeeded,
        results=[r if isinstance(r, ConvertResponse) else r for r in results],
    )


# --- Admin ---

_HTML_DIR = Path(__file__).parent / "templates"

@app.get("/admin")
async def admin_dashboard():
    """Admin dashboard (HTML)."""
    html_path = _HTML_DIR / "dashboard.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"), status_code=200)
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)


# --- Run ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
