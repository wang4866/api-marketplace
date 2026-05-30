"""
API Marketplace - Main Application
Web-to-Markdown Conversion API
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .web_to_md import url_to_markdown

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
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "web2md-api"}


@app.post(
    "/convert",
    response_model=ConvertResponse,
    responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
    summary="Convert webpage URL to Markdown",
    description="Fetch a webpage and convert its main content to clean Markdown format.",
)
@limiter.limit("100/hour")
async def convert(request: Request, body: ConvertRequest):
    """
    Convert a webpage URL to clean Markdown.

    - **url**: The full URL of the webpage to convert (required)
    - **include_images**: Whether to include image markdown references (default: false)
    """
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


# --- Run ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
