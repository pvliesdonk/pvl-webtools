# web_search

Web search via SearXNG metasearch engine module.

## Overview

The `web_search` module provides async functions for performing web searches through a SearXNG metasearch instance. SearXNG aggregates results from multiple search engines while preserving user privacy.

## Configuration

Set the `SEARXNG_URL` environment variable:

```bash
export SEARXNG_URL="http://localhost:8888"
```

## Quick Example

```python
import asyncio
from pvlwebtools import web_search, SearXNGClient

async def main():
    # Simple search
    results = await web_search("python async", max_results=5)
    for r in results:
        print(f"{r.title}: {r.url}")

    # With domain filter
    results = await web_search(
        "machine learning",
        domain_filter="arxiv.org",
        recency="year",
    )

    # Using client directly
    client = SearXNGClient(url="http://localhost:8888")
    if client.check_health():
        results = await client.search("query")

asyncio.run(main())
```

## Recency Filters

| Value | Description |
|-------|-------------|
| `all_time` | No time restriction (default) |
| `day` | Last 24 hours |
| `week` | Last 7 days |
| `month` | Last 30 days |
| `year` | Last 365 days |

## API Reference

::: pvlwebtools.web_search
    options:
      members:
        - web_search
        - SearXNGClient
        - SearchResult
        - WebSearchError
        - RecencyType
