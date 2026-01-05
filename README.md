# pvl-webtools

Web search (via SearXNG) and fetch tools with MCP server.

[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://pvliesdonk.github.io/pvl-webtools/)

## Installation

```bash
pip install pvl-webtools

# With MCP server support
pip install pvl-webtools[mcp]

# With markitdown for LLM-friendly markdown output (recommended)
pip install pvl-webtools[markdown]

# With trafilatura for article text extraction
pip install pvl-webtools[extraction]

# Everything
pip install pvl-webtools[all]
```

## Usage

### Direct Usage

```python
import asyncio
from pvlwebtools import web_search, web_fetch

async def main():
    # Search (requires SEARXNG_URL env var)
    results = await web_search("python async best practices", max_results=5)
    for r in results:
        print(f"{r.title}: {r.url}")

    # Fetch and extract article
    page = await web_fetch("https://example.com/article")
    print(page.content)

asyncio.run(main())
```

### With SearXNG Client

```python
from pvlwebtools import SearXNGClient

client = SearXNGClient(url="http://localhost:8888")
if client.check_health():
    results = await client.search("query", domain_filter="wikipedia.org")
```

### As MCP Server

```bash
# Set SearXNG URL
export SEARXNG_URL="http://localhost:8888"

# Optional: enable verbose logging (sent to stderr)
export VERBOSE=1

# Run server
uvx pvl-webtools-mcp
```

### Docker (Streamable HTTP)

```bash
# Pull and run
docker run -d -p 8000:8000 \
  -e SEARXNG_URL="http://your-searxng:8888" \
  ghcr.io/pvliesdonk/pvl-webtools:latest

# MCP endpoint available at http://localhost:8000/mcp
```

See [Docker Deployment](https://pvliesdonk.github.io/pvl-webtools/docker/) for full documentation.

## Configuration

| Environment Variable | Description |
|---------------------|-------------|
| `SEARXNG_URL` | SearXNG instance URL (required for web_search) |
| `LOG_LEVEL` | Optional logging level for the MCP server (`DEBUG`, `INFO`, etc.). Logs are emitted on stderr so stdio transport stays valid. |
| `VERBOSE` | Convenience flag; set to `1`/`true` to enable debug logging without specifying a level. |

Legacy aliases `PVL_MCP_LOG_LEVEL` and `PVL_MCP_VERBOSE` are still accepted for backward compatibility.

## Tools

### web_search

Search the web via SearXNG metasearch engine.

- `query`: Search query
- `max_results`: 1-20 (default 5)
- `domain_filter`: Limit to domain (e.g., "wikipedia.org")
- `recency`: "all_time", "day", "week", "month", "year"

### web_fetch

Fetch and extract content from URLs.

- `url`: URL to fetch
- `extract_mode`:
  - `"markdown"` (default): LLM-friendly markdown via markitdown
  - `"article"`: Plain text via trafilatura
  - `"raw"`: Raw HTML (truncated)
  - `"metadata"`: Title, description, Open Graph tags

## License

MIT
