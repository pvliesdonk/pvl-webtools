# Getting Started

## Installation

Install pvl-webtools using pip:

```bash
pip install pvl-webtools
```

### Optional Dependencies

pvl-webtools has several optional dependencies for different use cases:

```bash
# MCP server support (for AI assistants)
pip install pvl-webtools[mcp]

# Markdown extraction via markitdown (recommended for LLMs)
pip install pvl-webtools[markdown]

# Article extraction via trafilatura
pip install pvl-webtools[extraction]

# Install everything
pip install pvl-webtools[all]
```

## Configuration

### SearXNG URL

For web search functionality, you need a SearXNG instance. Set the URL via environment variable:

```bash
export SEARXNG_URL="http://localhost:8888"
```

Or pass it directly when searching:

```python
results = await web_search("query", searxng_url="http://localhost:8888")
```

## Basic Usage

### Web Fetch

Fetch and extract content from URLs:

```python
import asyncio
from pvlwebtools import web_fetch

async def main():
    # Default: markdown extraction (best for LLMs)
    result = await web_fetch("https://example.com")
    print(result.content)

    # Article extraction (plain text)
    result = await web_fetch("https://example.com", extract_mode="article")

    # Metadata only
    result = await web_fetch("https://example.com", extract_mode="metadata")

asyncio.run(main())
```

### Web Search

Search the web via SearXNG:

```python
import asyncio
from pvlwebtools import web_search

async def main():
    results = await web_search("python async best practices", max_results=5)

    for r in results:
        print(f"{r.title}")
        print(f"  {r.url}")
        print(f"  {r.snippet[:100]}...")
        print()

asyncio.run(main())
```

### Custom Configuration

Use `FetchConfig` to customize fetch behavior:

```python
from pvlwebtools import web_fetch, FetchConfig

# Create custom config with larger limits
config = FetchConfig(
    max_markdown_length=200_000,  # 200k chars
    max_article_length=50_000,
    request_timeout=30.0,
)

result = await web_fetch("https://example.com", config=config)
```

## MCP Server

Run pvl-webtools as an MCP server for AI assistants:

```bash
# Set SearXNG URL
export SEARXNG_URL="http://localhost:8888"

# Run server
uvx pvl-webtools-mcp
```

Enable verbose logging (emitted on stderr so stdio transport stays valid) by setting
`VERBOSE=1` or specifying an explicit level such as
`LOG_LEVEL=DEBUG` before launching the server. Legacy `PVL_MCP_*` names
are still accepted.

### Available Tools

The MCP server exposes three tools:

| Tool | Description |
|------|-------------|
| `search` | Search the web via SearXNG |
| `fetch` | Fetch and extract content from URLs |
| `check_status` | Check service availability |

### Claude Desktop Integration

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "pvl-webtools": {
      "command": "uvx",
      "args": ["pvl-webtools-mcp"],
      "env": {
        "SEARXNG_URL": "http://localhost:8888"
      }
    }
  }
}
```
