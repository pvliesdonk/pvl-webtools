"""
MCP server for pvl-webtools.

Exposes web_search and web_fetch as tools via FastMCP 2.
"""

from __future__ import annotations

import asyncio
from typing import Literal

from fastmcp import FastMCP

from pvlwebtools.web_fetch import FetchResult, WebFetchError, web_fetch
from pvlwebtools.web_search import SearchResult, SearXNGClient, WebSearchError

# Initialize FastMCP server
mcp = FastMCP(
    name="PVL Web Tools",
    instructions="""
    This server provides web search and fetch capabilities:
    - web_search: Search the web via SearXNG metasearch engine
    - web_fetch: Fetch and extract content from URLs

    Requires SEARXNG_URL environment variable for web_search.
    """,
)

# Global SearXNG client (lazy initialized)
_searxng_client: SearXNGClient | None = None


def get_searxng_client() -> SearXNGClient:
    """Get or create the SearXNG client."""
    global _searxng_client
    if _searxng_client is None:
        _searxng_client = SearXNGClient()
    return _searxng_client


@mcp.tool
def search(
    query: str,
    max_results: int = 5,
    domain_filter: str | None = None,
    recency: Literal["all_time", "day", "week", "month", "year"] = "all_time",
) -> list[dict]:
    """Search the web using SearXNG metasearch engine.

    Use this tool to search the web for information on any topic.
    Results include title, URL, snippet, and optionally published date.

    Args:
        query: Search query string. Be specific for better results.
               Examples: "python async best practices", "climate change 2024 report".
        max_results: Maximum number of results to return (1-20, default 5).
        domain_filter: Optional domain to limit search to.
                       Examples: "wikipedia.org", "github.com", "arxiv.org".
        recency: Time filter for results. One of:
                 'all_time' (default), 'day', 'week', 'month', 'year'.

    Returns:
        List of search results with title, url, snippet, and published_date.

    Note:
        Requires SEARXNG_URL environment variable to be set.
    """
    max_results = max(1, min(20, max_results))

    client = get_searxng_client()

    if not client.is_configured:
        return [{"error": "SearXNG not configured. Set SEARXNG_URL environment variable."}]

    try:
        # Run async search in sync context
        results: list[SearchResult] = asyncio.get_event_loop().run_until_complete(
            client.search(
                query=query,
                max_results=max_results,
                domain_filter=domain_filter,
                recency=recency,
            )
        )

        return [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "published_date": r.published_date,
            }
            for r in results
        ]

    except WebSearchError as e:
        return [{"error": str(e)}]


@mcp.tool
def fetch(
    url: str,
    extract_mode: Literal["article", "raw", "metadata"] = "article",
) -> dict:
    """Fetch and extract content from a URL.

    Use this tool to retrieve the content of a web page. Supports
    multiple extraction modes for different use cases.

    Args:
        url: URL to fetch (must start with http:// or https://).
        extract_mode: How to extract content:
            - 'article': Extract main article text (default, uses trafilatura).
            - 'raw': Return raw HTML (truncated to 50k chars).
            - 'metadata': Extract title, description, Open Graph tags only.

    Returns:
        Dictionary with url, content, content_length, and extract_mode.

    Note:
        Rate-limited to 1 request per 3 seconds to avoid abuse.
    """
    try:
        # Run async fetch in sync context
        result: FetchResult = asyncio.get_event_loop().run_until_complete(
            web_fetch(url=url, extract_mode=extract_mode)
        )

        return {
            "url": result.url,
            "content": result.content[:10000],  # Truncate for token efficiency
            "content_length": result.content_length,
            "extract_mode": result.extract_mode,
            "truncated": result.content_length > 10000,
        }

    except WebFetchError as e:
        return {"error": str(e), "url": url}


@mcp.tool
def check_status() -> dict:
    """Check the status of web tools.

    Returns:
        Status information including SearXNG availability.
    """
    client = get_searxng_client()

    return {
        "searxng_configured": client.is_configured,
        "searxng_url": client.url if client.is_configured else None,
        "searxng_healthy": client.check_health() if client.is_configured else False,
        "web_fetch_available": True,
    }


def run_server(
    transport: Literal["stdio", "http"] = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Run the MCP server.

    Args:
        transport: Transport protocol ('stdio' or 'http').
        host: Host to bind to (for http transport).
        port: Port to bind to (for http transport).
    """
    if transport == "http":
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()


# Entry point for `uvx pvl-webtools-mcp` or `python -m pvlwebtools.mcp_server`
if __name__ == "__main__":
    mcp.run()
