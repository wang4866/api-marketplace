<<<<<<< HEAD
# api-marketplace
=======
# Web2MD API

Convert any webpage to clean Markdown. Simple, fast, developer-friendly.

## Features

- ✅ Fetches any public URL
- ✅ Extracts main content (ignores ads, nav, footer)
- ✅ Returns clean, well-formatted Markdown
- ✅ Rate-limited (100 req/hour per IP)
- ✅ Free to use (reasonable usage)

## API Usage

### `POST /convert`

```json
{
  "url": "https://example.com/article",
  "include_images": false
}
```

### Response

```json
{
  "success": true,
  "title": "Article Title",
  "content": "# Markdown content...",
  "url": "https://example.com/article",
  "word_count": 1250,
  "char_count": 7800
}
```

## Deployment

### One-click on Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### Local development

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Tech Stack

- FastAPI
- BeautifulSoup4
- markdownify
- httpx
>>>>>>> 2381bc9 (Initial commit: Web2MD API - Convert webpage to Markdown)
