"""
Webpage to Markdown converter
Fetches a URL, extracts main content, converts to clean Markdown.
"""

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import re
from typing import Optional


async def fetch_url(url: str, timeout: int = 15) -> str:
    """Fetch HTML content from a URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.text


def extract_main_content(html: str, url: str) -> str:
    """Extract the main readable content from HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted elements
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "iframe", "noscript", "svg", "form",
                     "button", "input", "select", "textarea"]):
        tag.decompose()

    # Try to find main content area
    main_candidates = [
        soup.find("article"),
        soup.find("main"),
        soup.find("div", class_=re.compile(r"(content|post|article|entry|main)", re.I)),
        soup.find("div", id=re.compile(r"(content|post|article|entry|main)", re.I)),
    ]

    main_content = None
    for candidate in main_candidates:
        if candidate and len(candidate.get_text(strip=True)) > 200:
            main_content = candidate
            break

    if not main_content:
        # Fallback: use body
        body = soup.find("body")
        if body:
            main_content = body
        else:
            main_content = soup

    return str(main_content)


def clean_markdown(text: str) -> str:
    """Clean up the converted markdown."""
    # Remove excessive blank lines
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    # Remove excessive spaces
    text = re.sub(r" {3,}", "  ", text)
    # Clean up list formatting
    text = re.sub(r"\n{3,}(?=[*-])", "\n\n", text)
    return text.strip()


async def url_to_markdown(url: str, include_images: bool = False) -> dict:
    """
    Convert a webpage URL to clean Markdown.

    Args:
        url: The webpage URL to convert
        include_images: Whether to include image references in output

    Returns:
        dict with title, content (markdown), url, and word_count
    """
    html = await fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")

    # Extract title
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    # Extract main content HTML
    content_html = extract_main_content(html, url)

    # Convert to markdown
    markdown_content = md(
        content_html,
        heading_style="ATX",
        bullets="-",
        strip=["a"] if not include_images else [],
        autolinks=True,
        escape_asterisks=False,
        escape_underscores=False,
    )

    # Clean up
    markdown_content = clean_markdown(markdown_content)

    return {
        "title": title,
        "content": markdown_content,
        "url": url,
        "word_count": len(markdown_content.split()),
        "char_count": len(markdown_content),
    }
