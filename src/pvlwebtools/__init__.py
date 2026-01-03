"""pvl-webtools: Web search and fetch tools with MCP server.

This package provides async functions for web searching via SearXNG
metasearch engine and fetching web page content with various extraction
modes optimized for LLM consumption.

Example:
    Basic usage with async/await::

        import asyncio
        from pvlwebtools import web_search, web_fetch

        async def main():
            # Search the web (requires SEARXNG_URL env var)
            results = await web_search("python async", max_results=5)
            for r in results:
                print(f"{r.title}: {r.url}")

            # Fetch and extract page content
            page = await web_fetch("https://example.com")
            print(page.content)

        asyncio.run(main())

    With custom configuration::

        from pvlwebtools import web_fetch, FetchConfig

        config = FetchConfig(max_markdown_length=50_000)
        result = await web_fetch("https://example.com", config=config)

    Using SearXNG client directly::

        from pvlwebtools import SearXNGClient

        client = SearXNGClient(url="http://localhost:8888")
        if client.check_health():
            results = await client.search("query")

MCP Server:
    Run as an MCP server for AI assistants::

        uvx pvl-webtools-mcp

    Or programmatically::

        from pvlwebtools.mcp_server import run_server
        run_server()
"""

from pvlwebtools.web_fetch import (
    DEFAULT_CONFIG,
    ExtractMode,
    FetchConfig,
    FetchResult,
    WebFetchError,
    web_fetch,
)
from pvlwebtools.web_search import (
    RecencyType,
    SearchResult,
    SearXNGClient,
    WebSearchError,
    web_search,
)

__version__ = "0.1.0"

__all__ = [
    # Web search
    "web_search",
    "SearXNGClient",
    "SearchResult",
    "WebSearchError",
    "RecencyType",
    # Web fetch
    "web_fetch",
    "FetchResult",
    "FetchConfig",
    "DEFAULT_CONFIG",
    "WebFetchError",
    "ExtractMode",
    # Version
    "__version__",
]
