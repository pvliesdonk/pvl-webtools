"""
pvl-webtools: Web search and fetch tools with MCP server.

Usage:
    # Direct usage
    from pvlwebtools import web_search, web_fetch
    results = await web_search("python async")
    page = await web_fetch("https://example.com")

    # With SearXNG client
    from pvlwebtools import SearXNGClient
    client = SearXNGClient(url="http://localhost:8888")
    results = await client.search("query")

    # As MCP server
    uvx pvl-webtools-mcp
"""

from pvlwebtools.web_fetch import (
    ExtractMode,
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
    "WebFetchError",
    "ExtractMode",
    # Version
    "__version__",
]
