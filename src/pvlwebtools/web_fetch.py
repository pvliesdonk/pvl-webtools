"""
Web page fetching and content extraction.

Uses trafilatura for high-quality extraction with regex fallback.
"""

from __future__ import annotations

import asyncio
import html
import logging
import re
import time
from dataclasses import dataclass
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

# Configuration
MIN_REQUEST_INTERVAL = 3.0  # seconds between requests
REQUEST_TIMEOUT = 15.0  # seconds
MAX_CONTENT_LENGTH = 1_000_000  # 1MB max
USER_AGENT = "pvl-webtools/1.0 (https://github.com/pvliesdonk/pvl-webtools)"

# Module-level rate limiting
_last_request_time: float = 0.0
_rate_limit_lock = asyncio.Lock()

ExtractMode = Literal["article", "raw", "metadata"]


@dataclass
class FetchResult:
    """Result from fetching a URL."""

    url: str
    content: str
    content_length: int
    extract_mode: ExtractMode


class WebFetchError(Exception):
    """Error during web fetch."""

    pass


async def _enforce_rate_limit() -> None:
    """Enforce minimum interval between requests."""
    global _last_request_time

    async with _rate_limit_lock:
        now = time.time()
        elapsed = now - _last_request_time

        if elapsed < MIN_REQUEST_INTERVAL:
            await asyncio.sleep(MIN_REQUEST_INTERVAL - elapsed)

        _last_request_time = time.time()


async def _fetch_url(url: str, timeout: float = REQUEST_TIMEOUT) -> str:
    """Fetch URL content."""
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

        # Check content length
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > MAX_CONTENT_LENGTH:
            raise WebFetchError(f"Content too large: {content_length} bytes")

        return response.text


def _extract_article(html_content: str) -> str:
    """
    Extract article text from HTML.

    Uses trafilatura if available, falls back to regex.
    """
    # Try trafilatura first
    try:
        import trafilatura  # type: ignore[import-not-found]

        result: str | None = trafilatura.extract(
            html_content,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
        )

        if result:
            return result

    except ImportError:
        logger.debug("trafilatura not available, using regex fallback")
    except Exception as e:
        logger.debug(f"trafilatura extraction failed: {e}")

    # Regex fallback
    return _regex_extract(html_content)


def _regex_extract(html_content: str) -> str:
    """Basic regex-based text extraction."""
    # Remove script and style elements
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html_content, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)

    # Remove HTML comments
    text = re.sub(r"<!--[\s\S]*?-->", "", text)

    # Remove all HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Decode HTML entities
    text = html.unescape(text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    # Truncate if too long
    if len(text) > 20000:
        text = text[:20000] + "..."

    return text


def _extract_metadata(html_content: str) -> str:
    """Extract page metadata (title, description, etc.)."""
    metadata: dict[str, str] = {}

    # Title
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
    if title_match:
        metadata["title"] = html.unescape(title_match.group(1).strip())

    # Meta description
    desc_match = re.search(
        r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
        html_content,
        re.IGNORECASE,
    )
    if desc_match:
        metadata["description"] = html.unescape(desc_match.group(1).strip())

    # Open Graph
    og_matches = re.findall(
        r'<meta[^>]*property=["\']og:(\w+)["\'][^>]*content=["\']([^"\']*)["\']',
        html_content,
        re.IGNORECASE,
    )
    for prop, value in og_matches:
        metadata[f"og_{prop}"] = html.unescape(value.strip())

    return "\n".join(f"{k}: {v}" for k, v in metadata.items())


async def web_fetch(
    url: str,
    extract_mode: ExtractMode = "article",
    rate_limit: bool = True,
    timeout: float = REQUEST_TIMEOUT,
) -> FetchResult:
    """
    Fetch and extract content from a URL.

    Args:
        url: URL to fetch (must be http:// or https://).
        extract_mode: Extraction mode:
            - 'article': Extract main article text (default).
            - 'raw': Return raw HTML (truncated to 50k chars).
            - 'metadata': Extract title, description, Open Graph tags.
        rate_limit: Whether to enforce rate limiting (default True).
        timeout: Request timeout in seconds.

    Returns:
        FetchResult with extracted content.

    Raises:
        WebFetchError: If fetch fails.
    """
    if not url.strip():
        raise WebFetchError("URL cannot be empty")

    if not url.startswith(("http://", "https://")):
        raise WebFetchError("URL must start with http:// or https://")

    if rate_limit:
        await _enforce_rate_limit()

    try:
        html_content = await _fetch_url(url, timeout)

        if extract_mode == "raw":
            content = html_content[:50000]
        elif extract_mode == "metadata":
            content = _extract_metadata(html_content)
        else:
            content = _extract_article(html_content)

        return FetchResult(
            url=url,
            content=content,
            content_length=len(content),
            extract_mode=extract_mode,
        )

    except httpx.HTTPError as e:
        raise WebFetchError(f"HTTP error: {e}") from e
    except Exception as e:
        raise WebFetchError(f"Fetch failed: {e}") from e
