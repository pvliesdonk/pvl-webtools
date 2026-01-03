"""
Web search via SearXNG metasearch engine.

Configuration:
- SEARXNG_URL environment variable: Base URL for SearXNG instance
  (e.g., http://localhost:8888)
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

# Valid recency values
RecencyType = Literal["all_time", "day", "week", "month", "year"]
VALID_RECENCY_VALUES: set[str] = {"all_time", "day", "week", "month", "year"}

# Domain filter validation pattern
DOMAIN_FILTER_PATTERN = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$"
)

# Default configuration
DEFAULT_TIMEOUT = 10.0  # seconds


@dataclass
class SearchResult:
    """A single search result."""

    title: str
    url: str
    snippet: str
    published_date: str | None = None


class WebSearchError(Exception):
    """Error during web search."""

    pass


class SearXNGClient:
    """
    Client for SearXNG metasearch engine.

    Args:
        url: SearXNG instance URL. Defaults to SEARXNG_URL env var.
        timeout: Request timeout in seconds. Defaults to 10.
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

    @property
    def is_configured(self) -> bool:
        """Check if SearXNG URL is configured."""
        return bool(self.url)

    def check_health(self) -> bool:
        """
        Check if SearXNG is reachable.

        Returns:
            True if healthy, False otherwise.
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
        return self._is_healthy

    async def search(
        self,
        query: str,
        max_results: int = 5,
        domain_filter: str | None = None,
        recency: RecencyType = "all_time",
    ) -> list[SearchResult]:
        """
        Perform a web search.

        Args:
            query: Search query string.
            max_results: Maximum results to return (1-20).
            domain_filter: Limit to specific domain (e.g., 'wikipedia.org').
            recency: Time filter - 'all_time', 'day', 'week', 'month', 'year'.

        Returns:
            List of SearchResult objects.

        Raises:
            WebSearchError: If search fails or SearXNG is not available.
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

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.url}/search", params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            raise WebSearchError(f"HTTP error: {e}") from e
        except Exception as e:
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

        return results


# Convenience function for simple usage
async def web_search(
    query: str,
    max_results: int = 5,
    domain_filter: str | None = None,
    recency: RecencyType = "all_time",
    searxng_url: str | None = None,
) -> list[SearchResult]:
    """
    Search the web using SearXNG.

    This is a convenience wrapper around SearXNGClient.

    Args:
        query: Search query string.
        max_results: Maximum results to return (1-20).
        domain_filter: Limit to specific domain (e.g., 'wikipedia.org').
        recency: Time filter - 'all_time', 'day', 'week', 'month', 'year'.
        searxng_url: SearXNG URL. Defaults to SEARXNG_URL env var.

    Returns:
        List of SearchResult objects.
    """
    client = SearXNGClient(url=searxng_url)
    return await client.search(
        query=query,
        max_results=max_results,
        domain_filter=domain_filter,
        recency=recency,
    )
