"""Web search via SearXNG metasearch engine.

This module provides async functions for performing web searches through
a SearXNG metasearch instance. SearXNG aggregates results from multiple
search engines while preserving user privacy.

Example:
    >>> import asyncio
    >>> from pvlwebtools import web_search
    >>>
    >>> async def main():
    ...     results = await web_search("python async", max_results=5)
    ...     for r in results:
    ...         print(f"{r.title}: {r.url}")
    ...
    >>> asyncio.run(main())

Configuration:
    Set the ``SEARXNG_URL`` environment variable to your SearXNG instance::

        export SEARXNG_URL="http://localhost:8888"

    Alternatively, pass the URL directly to :class:`SearXNGClient` or
    the :func:`web_search` function.
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Literal

import httpx

__all__ = [
    "web_search",
    "SearchResult",
    "SearXNGClient",
    "WebSearchError",
    "RecencyType",
]

logger = logging.getLogger(__name__)

RecencyType = Literal["all_time", "day", "week", "month", "year"]
"""Type alias for valid recency filter options."""

VALID_RECENCY_VALUES: set[str] = {"all_time", "day", "week", "month", "year"}

# Domain filter validation pattern
DOMAIN_FILTER_PATTERN = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$"
)

# Default configuration
DEFAULT_TIMEOUT = 10.0  # seconds


def _truncate(value: str, limit: int = 120) -> str:
    """Truncate long values for safe logging output."""

    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."


@dataclass
class SearchResult:
    """A single search result from a web search query.

    Attributes:
        title: The title of the search result page.
        url: The URL of the search result.
        snippet: A text snippet or excerpt from the page content.
        published_date: Publication date if available (format varies).

    Example:
        >>> result = SearchResult(
        ...     title="Python Tutorial",
        ...     url="https://python.org/tutorial",
        ...     snippet="Learn Python programming...",
        ... )
        >>> print(f"{result.title}: {result.url}")
        Python Tutorial: https://python.org/tutorial
    """

    title: str
    url: str
    snippet: str
    published_date: str | None = None


class WebSearchError(Exception):
    """Exception raised when web search fails.

    This exception is raised for various failure conditions including:

    - SearXNG not configured (missing ``SEARXNG_URL``)
    - Empty search query
    - Invalid domain filter format
    - HTTP errors from SearXNG
    - Network timeouts or connection failures

    Example:
        >>> try:
        ...     results = await web_search("")
        ... except WebSearchError as e:
        ...     print(f"Search failed: {e}")
    """

    pass


class SearXNGClient:
    """Client for SearXNG metasearch engine.

    Provides methods for searching the web through a SearXNG instance.
    SearXNG is a privacy-respecting metasearch engine that aggregates
    results from multiple search engines.

    Args:
        url: SearXNG instance URL. If not provided, reads from
            ``SEARXNG_URL`` environment variable.
        timeout: Request timeout in seconds. Default 10.0.

    Attributes:
        url: The configured SearXNG instance URL.
        timeout: Request timeout in seconds.

    Example:
        >>> client = SearXNGClient(url="http://localhost:8888")
        >>> if client.check_health():
        ...     results = await client.search("python tutorial")
        ...     for r in results:
        ...         print(r.title)
    """

    def __init__(
        self,
        url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.url = url or os.environ.get("SEARXNG_URL", "")
        self.timeout = timeout
        self._health_checked = False
        self._is_healthy = False

        logger.debug(
            "Initialized SearXNGClient(url=%s, timeout=%s)",
            self.url or "<not set>",
            timeout,
        )

    @property
    def is_configured(self) -> bool:
        """Check if SearXNG URL is configured.

        Returns:
            ``True`` if a URL is set, ``False`` otherwise.
        """
        return bool(self.url)

    def check_health(self) -> bool:
        """Check if SearXNG instance is reachable and healthy.

        Makes a request to the ``/healthz`` endpoint. Results are
        cached after the first check.

        Returns:
            ``True`` if healthy, ``False`` otherwise.
        """
        if not self.url:
            return False

        if self._health_checked:
            return self._is_healthy

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.url}/healthz")
                self._is_healthy = response.status_code == 200
        except Exception as e:
            logger.debug(f"SearXNG health check failed: {e}")
            self._is_healthy = False

        self._health_checked = True
        logger.debug(
            "SearXNG health check completed (healthy=%s)",
            self._is_healthy,
        )
        return self._is_healthy

    async def search(
        self,
        query: str,
        max_results: int = 5,
        domain_filter: str | None = None,
        recency: RecencyType = "all_time",
    ) -> list[SearchResult]:
        """Perform a web search via SearXNG.

        Args:
            query: Search query string. Cannot be empty.
            max_results: Maximum number of results to return (1-20).
                Default 5.
            domain_filter: Limit search to a specific domain.
                Examples: ``'wikipedia.org'``, ``'github.com'``, ``'gov'``.
                Must be a valid domain format.
            recency: Time filter for results:

                - ``'all_time'``: No time restriction (default)
                - ``'day'``: Last 24 hours
                - ``'week'``: Last 7 days
                - ``'month'``: Last 30 days
                - ``'year'``: Last 365 days

        Returns:
            List of :class:`SearchResult` objects, up to ``max_results``.

        Raises:
            WebSearchError: If SearXNG is not configured, query is empty,
                domain filter is invalid, or the request fails.

        Example:
            >>> results = await client.search(
            ...     "climate change",
            ...     domain_filter="nature.com",
            ...     recency="year",
            ... )
        """
        if not self.url:
            raise WebSearchError("SearXNG URL not configured (set SEARXNG_URL env var)")

        if not query.strip():
            raise WebSearchError("Search query cannot be empty")

        # Validate domain filter
        if domain_filter and not DOMAIN_FILTER_PATTERN.match(domain_filter):
            raise WebSearchError(
                f"Invalid domain_filter: '{domain_filter}'. "
                "Must be a valid domain (e.g., 'wikipedia.org', 'gov')."
            )

        # Validate recency
        if recency not in VALID_RECENCY_VALUES:
            logger.warning(f"Invalid recency '{recency}', defaulting to 'all_time'")
            recency = "all_time"

        # Build query with domain filter
        search_query = f"site:{domain_filter} {query}" if domain_filter else query

        # Map recency to SearXNG time_range
        time_range_map: dict[str, str | None] = {
            "all_time": None,
            "day": "day",
            "week": "week",
            "month": "month",
            "year": "year",
        }
        time_range = time_range_map[recency]

        params: dict[str, str | int] = {
            "q": search_query,
            "format": "json",
            "categories": "general",
        }
        if time_range:
            params["time_range"] = time_range

        logger.debug(
            "SearXNG search start query=%r domain=%s recency=%s max=%s",
            _truncate(query, 80),
            domain_filter,
            recency,
            max_results,
        )

        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.url}/search", params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            logger.warning("SearXNG HTTP error: %s", e)
            raise WebSearchError(f"HTTP error: {e}") from e
        except Exception as e:
            logger.warning("SearXNG search failed: %s", e)
            raise WebSearchError(f"Search failed: {e}") from e

        # Extract results
        results: list[SearchResult] = []
        for item in data.get("results", [])[:max_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    published_date=item.get("publishedDate"),
                )
            )

        duration = time.perf_counter() - start_time
        logger.debug(
            "SearXNG search complete in %.2fs with %d results",
            duration,
            len(results),
        )

        return results


async def web_search(
    query: str,
    max_results: int = 5,
    domain_filter: str | None = None,
    recency: RecencyType = "all_time",
    searxng_url: str | None = None,
) -> list[SearchResult]:
    """Search the web using SearXNG.

    This is a convenience function that creates a :class:`SearXNGClient`
    and performs a single search. For multiple searches, create a client
    instance directly to avoid repeated initialization.

    Args:
        query: Search query string. Cannot be empty.
        max_results: Maximum number of results to return (1-20).
            Default 5.
        domain_filter: Limit search to a specific domain.
            Examples: ``'wikipedia.org'``, ``'github.com'``.
        recency: Time filter for results. One of:
            ``'all_time'`` (default), ``'day'``, ``'week'``,
            ``'month'``, ``'year'``.
        searxng_url: SearXNG instance URL. If not provided,
            reads from ``SEARXNG_URL`` environment variable.

    Returns:
        List of :class:`SearchResult` objects.

    Raises:
        WebSearchError: If search fails.

    Example:
        >>> import asyncio
        >>> from pvlwebtools import web_search
        >>>
        >>> async def main():
        ...     results = await web_search(
        ...         "python async best practices",
        ...         max_results=5,
        ...     )
        ...     for r in results:
        ...         print(f"{r.title}: {r.url}")
        ...
        >>> asyncio.run(main())
    """
    logger.debug(
        "web_search convenience wrapper invoked (url=%s)",
        searxng_url or "<env>",
    )
    client = SearXNGClient(url=searxng_url)
    return await client.search(
        query=query,
        max_results=max_results,
        domain_filter=domain_filter,
        recency=recency,
    )
