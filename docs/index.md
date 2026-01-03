# pvl-webtools

Web search (via SearXNG) and fetch tools with MCP server.

## Features

- **Web Search**: Search the web via SearXNG metasearch engine with privacy-preserving aggregation
- **Web Fetch**: Fetch and extract content from URLs in multiple formats
- **MCP Server**: Expose tools to AI assistants via Model Context Protocol

## Quick Start

```python
import asyncio
from pvlwebtools import web_search, web_fetch

async def main():
    # Search the web (requires SEARXNG_URL env var)
    results = await web_search("python async", max_results=5)
    for r in results:
        print(f"{r.title}: {r.url}")

    # Fetch and extract page content as markdown
    page = await web_fetch("https://example.com")
    print(page.content)

asyncio.run(main())
```

## Extraction Modes

The `web_fetch` function supports multiple extraction modes:

| Mode | Description | Best For |
|------|-------------|----------|
| `markdown` | LLM-friendly markdown via markitdown | AI/LLM consumption |
| `article` | Plain text article extraction via trafilatura | News articles, blog posts |
| `raw` | Raw HTML (truncated) | HTML analysis |
| `metadata` | Title, description, Open Graph tags | Link previews |

## Installation

```bash
pip install pvl-webtools

# With MCP server support
pip install pvl-webtools[mcp]

# With markdown extraction (recommended for LLMs)
pip install pvl-webtools[markdown]

# Everything
pip install pvl-webtools[all]
```

## Requirements

- Python 3.10+
- SearXNG instance for web search (set `SEARXNG_URL` environment variable)
