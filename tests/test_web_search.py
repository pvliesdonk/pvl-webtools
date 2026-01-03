"""Tests for web_search module."""

import pytest

from pvlwebtools.web_search import (
    DOMAIN_FILTER_PATTERN,
    SearXNGClient,
    WebSearchError,
)


class TestDomainFilterValidation:
    """Tests for domain filter pattern."""

    @pytest.mark.parametrize(
        "domain",
        [
            "example.com",
            "sub.example.com",
            "wikipedia.org",
            "github.com",
            "gov",
            "edu",
            "a.b.c.d.e",
        ],
    )
    def test_valid_domains(self, domain: str) -> None:
        assert DOMAIN_FILTER_PATTERN.match(domain) is not None

    @pytest.mark.parametrize(
        "domain",
        [
            "",
            "example.com/path",
            "http://example.com",
            "example..com",
            "-example.com",
            "example-.com",
            "exam ple.com",
            "example.com?query=1",
        ],
    )
    def test_invalid_domains(self, domain: str) -> None:
        assert DOMAIN_FILTER_PATTERN.match(domain) is None


class TestSearXNGClient:
    """Tests for SearXNGClient."""

    def test_not_configured_by_default(self) -> None:
        """Client should not be configured without URL."""
        client = SearXNGClient(url="")
        assert client.is_configured is False

    def test_configured_with_url(self) -> None:
        """Client should be configured with URL."""
        client = SearXNGClient(url="http://localhost:8888")
        assert client.is_configured is True
        assert client.url == "http://localhost:8888"

    @pytest.mark.asyncio
    async def test_search_without_config_raises(self) -> None:
        """Search should raise without configuration."""
        client = SearXNGClient(url="")
        with pytest.raises(WebSearchError, match="not configured"):
            await client.search("test query")

    @pytest.mark.asyncio
    async def test_search_empty_query_raises(self) -> None:
        """Search should raise on empty query."""
        client = SearXNGClient(url="http://localhost:8888")
        with pytest.raises(WebSearchError, match="cannot be empty"):
            await client.search("")

    @pytest.mark.asyncio
    async def test_search_invalid_domain_raises(self) -> None:
        """Search should raise on invalid domain filter."""
        client = SearXNGClient(url="http://localhost:8888")
        with pytest.raises(WebSearchError, match="Invalid domain_filter"):
            await client.search("test", domain_filter="http://example.com")
