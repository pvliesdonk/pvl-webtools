"""MCP server for pvl-webtools.

This module provides an MCP (Model Context Protocol) server that exposes
web search and fetch capabilities to AI assistants and other MCP clients.

The server provides three tools:

- **search**: Search the web via SearXNG metasearch engine
- **fetch**: Fetch and extract content from URLs
- **check_status**: Check availability of configured services

Running the Server:
    Via command line::

        uvx pvl-webtools-mcp

    Or programmatically::

        from pvlwebtools.mcp_server import run_server
        run_server(transport="stdio")

Configuration:
    Set the ``SEARXNG_URL`` environment variable for web search::

        export SEARXNG_URL="http://localhost:8888"

Note:
    Requires the ``mcp`` extra: ``pip install pvl-webtools[mcp]``
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Literal

from fastmcp import FastMCP

from pvlwebtools.web_fetch import FetchResult, WebFetchError, web_fetch
from pvlwebtools.web_search import SearchResult, SearXNGClient, WebSearchError

__all__ = [
    "mcp",
    "run_server",
    "search",
    "fetch",
    "check_status",
]

LOG_LEVEL_ENV = "LOG_LEVEL"
VERBOSE_ENV = "VERBOSE"
LEGACY_LOG_LEVEL_ENV = "PVL_MCP_LOG_LEVEL"
LEGACY_VERBOSE_ENV = "PVL_MCP_VERBOSE"


def _get_env(name: str, legacy_name: str) -> tuple[str | None, str | None]:
    """Return env value and which variable provided it (prefers new names)."""

    value = os.environ.get(name)
    if value is not None:
        return value, name
    legacy_value = os.environ.get(legacy_name)
    if legacy_value is not None:
        return legacy_value, legacy_name
    return None, None


def _is_truthy(value: str) -> bool:
    """Return True if the string value represents a truthy flag."""

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _configure_logging() -> int | None:
    """Configure logging when verbose env vars are set.

    Returns the configured log level when logging is enabled, otherwise ``None``.
    """

    level_name, level_source = _get_env(LOG_LEVEL_ENV, LEGACY_LOG_LEVEL_ENV)
    verbose_flag, verbose_source = _get_env(VERBOSE_ENV, LEGACY_VERBOSE_ENV)

    level: int | None = None

    if level_name:
        candidate = level_name.strip().upper()
        level = getattr(logging, candidate, None)
        if level is None:
            print(
                f"pvl-webtools MCP: unknown log level '{level_name}', defaulting to INFO",
                file=sys.stderr,
            )
            level = logging.INFO
    elif verbose_flag and _is_truthy(verbose_flag):
        level = logging.DEBUG

    if level is None:
        return None

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if level_source and level_source != LOG_LEVEL_ENV:
        print(
            f"pvl-webtools MCP: {level_source} is deprecated; use {LOG_LEVEL_ENV} instead",
            file=sys.stderr,
        )
    if verbose_source and verbose_source != VERBOSE_ENV:
        print(
            f"pvl-webtools MCP: {verbose_source} is deprecated; use {VERBOSE_ENV} instead",
            file=sys.stderr,
        )

    return level


_configured_log_level = _configure_logging()

logger = logging.getLogger(__name__)

if _configured_log_level is not None:
    logger.info(
        "MCP verbose logging enabled (level=%s)",
        logging.getLevelName(_configured_log_level),
    )

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


def _truncate(value: str, limit: int = 200) -> str:
    """Truncate long strings for logging output."""

    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."


def get_searxng_client() -> SearXNGClient:
    """Get or create the singleton SearXNG client.

    Returns:
        The shared :class:`~pvlwebtools.web_search.SearXNGClient` instance.
    """
    global _searxng_client
    if _searxng_client is None:
        _searxng_client = SearXNGClient()
    return _searxng_client


@mcp.tool
async def search(
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

    logger.debug(
        "search(query=%r, max_results=%s, domain_filter=%s, recency=%s)",
        _truncate(query),
        max_results,
        domain_filter,
        recency,
    )

    if not client.is_configured:
        return [{"error": "SearXNG not configured. Set SEARXNG_URL environment variable."}]

    try:
        results: list[SearchResult] = await client.search(
            query=query,
            max_results=max_results,
            domain_filter=domain_filter,
            recency=recency,
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
        logger.warning("Search failed: %s", e)
        return [{"error": str(e)}]


@mcp.tool
async def fetch(
    url: str,
    extract_mode: Literal["markdown", "article", "raw", "metadata"] = "markdown",
) -> dict:
    """Fetch and extract content from a URL.

    Use this tool to retrieve the content of a web page. Supports
    multiple extraction modes optimized for different use cases.

    Args:
        url: URL to fetch (must start with http:// or https://).
        extract_mode: How to extract content:
            - 'markdown': Convert to LLM-friendly markdown (default).
              Preserves headings, lists, links, code blocks.
            - 'article': Extract main article text (uses trafilatura).
            - 'raw': Return raw HTML (truncated to 50k chars).
            - 'metadata': Extract title, description, Open Graph tags only.

    Returns:
        Dictionary with url, content, content_length, and extract_mode.

    Note:
        Rate-limited to 1 request per 3 seconds to avoid abuse.
    """
    logger.debug("fetch(url=%s, extract_mode=%s)", url, extract_mode)

    try:
        result: FetchResult = await web_fetch(url=url, extract_mode=extract_mode)

        return {
            "url": result.url,
            "content": result.content[:10000],  # Truncate for token efficiency
            "content_length": result.content_length,
            "extract_mode": result.extract_mode,
            "truncated": result.content_length > 10000,
        }

    except WebFetchError as e:
        logger.warning("Fetch failed for %s: %s", url, e)
        return {"error": str(e), "url": url}


@mcp.tool
def check_status() -> dict:
    """Check the status of web tools.

    Returns:
        Status information including SearXNG availability.
    """
    client = get_searxng_client()

    logger.debug("check_status invoked")

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

    Starts the MCP server with the specified transport. For integration
    with AI assistants like Claude, use ``stdio`` transport. For HTTP
    clients, use ``http`` transport.

    Args:
        transport: Transport protocol:

            - ``'stdio'``: Standard I/O (default, for Claude integration)
            - ``'http'``: HTTP server (for web clients)

        host: Host to bind to for HTTP transport. Default ``'127.0.0.1'``.
        port: Port to bind to for HTTP transport. Default ``8000``.

    Example:
        >>> from pvlwebtools.mcp_server import run_server
        >>> run_server()  # Runs with stdio transport

        Or with HTTP::

        >>> run_server(transport="http", host="0.0.0.0", port=8080)
    """
    if transport == "http":
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()


# Entry point for `uvx pvl-webtools-mcp` or `python -m pvlwebtools.mcp_server`
if __name__ == "__main__":
    mcp.run()
