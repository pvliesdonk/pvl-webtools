"""
Web page fetching and content extraction.

This module provides async functions for fetching web pages and extracting
their content in various formats optimized for different use cases.

Extraction Modes:
    - **markdown**: LLM-friendly markdown via markitdown (preserves structure)
    - **article**: Plain text article extraction via trafilatura
    - **raw**: Raw HTML content (truncated)
    - **metadata**: Page metadata (title, description, Open Graph tags)

Example:
    >>> import asyncio
    >>> from pvlwebtools import web_fetch
    >>>
    >>> async def main():
    ...     result = await web_fetch("https://example.com")
    ...     print(result.content)
    ...
    >>> asyncio.run(main())

Configuration:
    Use :class:`FetchConfig` to customize behavior:

    >>> from pvlwebtools.web_fetch import web_fetch, FetchConfig
    >>>
    >>> config = FetchConfig(max_markdown_length=50_000)
    >>> result = await web_fetch("https://example.com", config=config)
"""

from __future__ import annotations

import asyncio
import html
import io
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Literal

import httpx

__all__ = [
    "web_fetch",
    "FetchResult",
    "FetchConfig",
    "WebFetchError",
    "ExtractMode",
    "DEFAULT_CONFIG",
]

logger = logging.getLogger(__name__)

# Module-level rate limiting
_last_request_time: float = 0.0
_rate_limit_lock = asyncio.Lock()


def _truncate(value: str, limit: int = 120) -> str:
    """Truncate long strings for logging output."""

    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."


ExtractMode = Literal["markdown", "article", "raw", "metadata"]
"""Type alias for extraction mode options."""


@dataclass
class FetchConfig:
    """Configuration for web fetching behavior.

    This class allows customization of various limits and settings
    used during web page fetching and content extraction.

    Attributes:
        max_markdown_length: Maximum characters for markdown output.
            Content exceeding this limit is truncated with a notice.
            Default: 100,000 characters.
        max_article_length: Maximum characters for article text output.
            Default: 20,000 characters.
        max_raw_length: Maximum characters for raw HTML output.
            Default: 50,000 characters.
        max_content_length: Maximum bytes to download from a URL.
            Requests for larger content will raise WebFetchError.
            Default: 1,000,000 bytes (1 MB).
        request_timeout: HTTP request timeout in seconds.
            Default: 15.0 seconds.
        min_request_interval: Minimum seconds between requests (rate limiting).
            Default: 3.0 seconds.
        user_agent: User-Agent header for HTTP requests.

    Example:
        >>> config = FetchConfig(
        ...     max_markdown_length=50_000,
        ...     request_timeout=30.0,
        ... )
        >>> result = await web_fetch(url, config=config)
    """

    max_markdown_length: int = 100_000
    max_article_length: int = 20_000
    max_raw_length: int = 50_000
    max_content_length: int = 1_000_000
    request_timeout: float = 15.0
    min_request_interval: float = 3.0
    user_agent: str = field(default="pvl-webtools/1.0 (https://github.com/pvliesdonk/pvl-webtools)")


#: Default configuration instance used when no config is provided.
DEFAULT_CONFIG = FetchConfig()


@dataclass
class FetchResult:
    """Result from fetching and extracting content from a URL.

    Attributes:
        url: The URL that was fetched.
        content: The extracted content (format depends on extract_mode).
        content_length: Length of the extracted content in characters.
        extract_mode: The extraction mode that was actually used.
            May differ from requested mode if fallback occurred.

    Example:
        >>> result = await web_fetch("https://example.com")
        >>> print(f"Fetched {result.content_length} chars as {result.extract_mode}")
    """

    url: str
    content: str
    content_length: int
    extract_mode: ExtractMode


class WebFetchError(Exception):
    """Exception raised when web fetching fails.

    This exception is raised for various failure conditions including:
    - Invalid URLs (empty or wrong scheme)
    - HTTP errors (4xx, 5xx responses)
    - Content too large
    - Network timeouts
    - Connection failures

    Attributes:
        message: Human-readable error description.

    Example:
        >>> try:
        ...     result = await web_fetch("https://invalid.example")
        ... except WebFetchError as e:
        ...     print(f"Fetch failed: {e}")
    """

    pass


async def _enforce_rate_limit(min_interval: float) -> None:
    """Enforce minimum interval between requests.

    This provides basic rate limiting to avoid overwhelming servers
    or triggering anti-bot protections.

    Args:
        min_interval: Minimum seconds to wait between requests.
    """
    global _last_request_time

    async with _rate_limit_lock:
        now = time.time()
        elapsed = now - _last_request_time

        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            logger.debug("Rate limiting: sleeping for %.2fs", wait_time)
            await asyncio.sleep(wait_time)

        _last_request_time = time.time()


async def _fetch_url(url: str, config: FetchConfig) -> str:
    """Fetch URL content with configured limits.

    Args:
        url: The URL to fetch.
        config: Configuration for request behavior.

    Returns:
        The response text content.

    Raises:
        WebFetchError: If content exceeds max_content_length.
        httpx.HTTPError: For HTTP-level errors.
    """
    logger.debug("Fetching URL %s", _truncate(url))
    start_time = time.perf_counter()

    async with httpx.AsyncClient(
        timeout=config.request_timeout,
        follow_redirects=True,
        headers={"User-Agent": config.user_agent},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

        # Check content length
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > config.max_content_length:
            raise WebFetchError(f"Content too large: {content_length} bytes")

        duration = time.perf_counter() - start_time
        logger.debug(
            "Fetched %s in %.2fs (status=%s, content_length=%s)",
            _truncate(url),
            duration,
            response.status_code,
            content_length or "unknown",
        )

        return response.text


def _extract_markdown(html_content: str, max_length: int) -> str | None:
    """Convert HTML to LLM-friendly markdown using markitdown.

    This produces well-structured markdown that preserves document
    structure including headings, lists, links, and code blocks.

    Args:
        html_content: Raw HTML content to convert.
        max_length: Maximum characters for output (truncated with notice).

    Returns:
        Markdown string, or None if markitdown is not available or fails.

    Note:
        Requires the ``markitdown`` package. Install with::

            pip install pvl-webtools[markdown]
    """
    try:
        from markitdown import MarkItDown, StreamInfo

        md = MarkItDown()
        stream_info = StreamInfo(mimetype="text/html", extension=".html")
        data = io.BytesIO(html_content.encode("utf-8", errors="replace"))
        result = md.convert_stream(data, stream_info=stream_info)

        if result.markdown is not None:
            text = result.markdown
            # Truncate if too long
            if len(text) > max_length:
                text = text[:max_length] + "\n\n[Content truncated...]"
            return text

    except ImportError:
        logger.debug("markitdown not available")
    except Exception as e:
        logger.debug(f"markitdown extraction failed: {e}")

    return None


def _extract_article(html_content: str, max_length: int) -> str:
    """Extract article text from HTML content.

    Uses trafilatura for intelligent article extraction if available,
    falling back to regex-based extraction otherwise.

    Args:
        html_content: Raw HTML content to extract from.
        max_length: Maximum characters for output (truncated with ellipsis).

    Returns:
        Extracted article text as plain string.

    Note:
        For best results, install trafilatura::

            pip install pvl-webtools[extraction]
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
            if len(result) > max_length:
                return result[:max_length] + "..."
            return result

    except ImportError:
        logger.debug("trafilatura not available, using regex fallback")
    except Exception as e:
        logger.debug(f"trafilatura extraction failed: {e}")

    # Regex fallback
    return _regex_extract(html_content, max_length)


def _regex_extract(html_content: str, max_length: int) -> str:
    """Extract text from HTML using regex patterns.

    This is a fallback method when trafilatura is not available.
    It removes scripts, styles, comments, and HTML tags, then
    normalizes whitespace.

    Args:
        html_content: Raw HTML content to extract from.
        max_length: Maximum characters for output.

    Returns:
        Plain text extracted from HTML.
    """
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
    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text


def _extract_metadata(html_content: str) -> str:
    """Extract page metadata from HTML.

    Extracts structured metadata including:

    - ``<title>`` tag content
    - Meta description
    - Open Graph (``og:``) tags

    Args:
        html_content: Raw HTML content to extract from.

    Returns:
        Formatted string with one "key: value" pair per line.

    Example:
        >>> html = '<title>Example</title><meta property="og:type" content="website">'
        >>> print(_extract_metadata(html))
        title: Example
        og_type: website
    """
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
    extract_mode: ExtractMode = "markdown",
    rate_limit: bool = True,
    config: FetchConfig | None = None,
) -> FetchResult:
    """Fetch and extract content from a URL.

    This is the main entry point for web content fetching. It handles
    the full lifecycle of fetching a URL and extracting its content
    in a format suitable for various use cases.

    Args:
        url: URL to fetch. Must start with ``http://`` or ``https://``.
        extract_mode: How to extract and format content:

            - ``'markdown'``: Convert to LLM-friendly markdown (default).
              Preserves document structure. Falls back to ``'article'``
              if markitdown is not installed.
            - ``'article'``: Extract main article text via trafilatura.
              Good for news articles and blog posts.
            - ``'raw'``: Return raw HTML (truncated per config).
            - ``'metadata'``: Extract only title, description, OG tags.

        rate_limit: Whether to enforce minimum interval between requests.
            Default ``True``. Disable for batch operations with external
            rate limiting.
        config: Configuration for limits and timeouts. Uses
            :data:`DEFAULT_CONFIG` if not provided.

    Returns:
        :class:`FetchResult` with extracted content and metadata.

    Raises:
        WebFetchError: If the URL is invalid, the request fails,
            or content exceeds configured limits.

    Example:
        >>> result = await web_fetch("https://example.com")
        >>> print(result.content[:100])

        With custom config:

        >>> config = FetchConfig(max_markdown_length=50_000)
        >>> result = await web_fetch("https://example.com", config=config)
    """
    if config is None:
        config = DEFAULT_CONFIG

    if not url.strip():
        raise WebFetchError("URL cannot be empty")

    if not url.startswith(("http://", "https://")):
        raise WebFetchError("URL must start with http:// or https://")

    logger.debug(
        "web_fetch start url=%s mode=%s rate_limit=%s",
        _truncate(url),
        extract_mode,
        rate_limit,
    )

    if rate_limit:
        await _enforce_rate_limit(config.min_request_interval)

    try:
        html_content = await _fetch_url(url, config)
        actual_mode = extract_mode

        if extract_mode == "raw":
            content = html_content[: config.max_raw_length]
        elif extract_mode == "metadata":
            content = _extract_metadata(html_content)
        elif extract_mode == "markdown":
            result = _extract_markdown(html_content, config.max_markdown_length)
            if result is not None:
                content = result
            else:
                # Fallback to article extraction
                logger.debug("markitdown unavailable; falling back to article extraction")
                content = _extract_article(html_content, config.max_article_length)
                actual_mode = "article"
        else:  # article
            content = _extract_article(html_content, config.max_article_length)

        fetch_result = FetchResult(
            url=url,
            content=content,
            content_length=len(content),
            extract_mode=actual_mode,
        )

        logger.debug(
            "web_fetch success url=%s mode=%s length=%s",
            _truncate(url),
            fetch_result.extract_mode,
            fetch_result.content_length,
        )

        return fetch_result

    except httpx.HTTPError as e:
        logger.warning("HTTP error fetching %s: %s", _truncate(url), e)
        raise WebFetchError(f"HTTP error: {e}") from e
    except Exception as e:
        logger.warning("Fetch failed for %s: %s", _truncate(url), e)
        raise WebFetchError(f"Fetch failed: {e}") from e
