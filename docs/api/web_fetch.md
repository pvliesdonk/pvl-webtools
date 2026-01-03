# web_fetch

Web page fetching and content extraction module.

## Overview

The `web_fetch` module provides async functions for fetching web pages and extracting their content in various formats optimized for different use cases.

## Extraction Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `markdown` | LLM-friendly markdown via markitdown | AI/LLM consumption, preserves structure |
| `article` | Plain text via trafilatura | News articles, blog posts |
| `raw` | Raw HTML (truncated) | HTML analysis, debugging |
| `metadata` | Title, description, OG tags | Link previews, SEO analysis |

## Quick Example

```python
import asyncio
from pvlwebtools import web_fetch, FetchConfig

async def main():
    # Basic usage
    result = await web_fetch("https://example.com")
    print(result.content)

    # With custom config
    config = FetchConfig(max_markdown_length=50_000)
    result = await web_fetch("https://example.com", config=config)

asyncio.run(main())
```

## API Reference

::: pvlwebtools.web_fetch
    options:
      members:
        - web_fetch
        - FetchConfig
        - FetchResult
        - WebFetchError
        - ExtractMode
        - DEFAULT_CONFIG
