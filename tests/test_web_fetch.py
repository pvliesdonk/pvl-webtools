"""Tests for web_fetch module."""

import pytest

from pvlwebtools.web_fetch import (
    WebFetchError,
    _extract_markdown,
    _extract_metadata,
    _regex_extract,
    web_fetch,
)


class TestRegexExtract:
    """Tests for regex-based extraction."""

    def test_removes_scripts(self) -> None:
        html = "<html><script>alert('x')</script><body>content</body></html>"
        result = _regex_extract(html)
        assert "alert" not in result
        assert "content" in result

    def test_removes_styles(self) -> None:
        html = "<html><style>.x{color:red}</style><body>text</body></html>"
        result = _regex_extract(html)
        assert "color" not in result
        assert "text" in result

    def test_removes_comments(self) -> None:
        html = "<html><!-- hidden comment --><body>visible</body></html>"
        result = _regex_extract(html)
        assert "hidden" not in result
        assert "visible" in result

    def test_decodes_entities(self) -> None:
        html = "<p>Tom &amp; Jerry &lt;3 each other</p>"
        result = _regex_extract(html)
        assert "Tom & Jerry <3 each other" in result

    def test_truncates_long_content(self) -> None:
        html = "<p>" + "x" * 25000 + "</p>"
        result = _regex_extract(html)
        assert len(result) <= 20003  # 20000 + "..."


class TestExtractMarkdown:
    """Tests for markdown extraction via markitdown."""

    def test_converts_headings(self) -> None:
        html = "<html><body><h1>Main Title</h1><p>Content here.</p></body></html>"
        result = _extract_markdown(html)
        assert result is not None
        assert "Main Title" in result
        assert "#" in result  # Markdown heading

    def test_converts_lists(self) -> None:
        html = "<html><body><ul><li>Item 1</li><li>Item 2</li></ul></body></html>"
        result = _extract_markdown(html)
        assert result is not None
        assert "Item 1" in result
        assert "Item 2" in result

    def test_preserves_links(self) -> None:
        html = '<html><body><a href="https://example.com">Link text</a></body></html>'
        result = _extract_markdown(html)
        assert result is not None
        assert "Link text" in result
        assert "example.com" in result

    def test_handles_empty_html(self) -> None:
        html = "<html><body></body></html>"
        result = _extract_markdown(html)
        # Should return empty string or None, not crash
        assert result is None or result.strip() == ""


class TestExtractMetadata:
    """Tests for metadata extraction."""

    def test_extracts_title(self) -> None:
        html = "<html><head><title>Test Title</title></head></html>"
        result = _extract_metadata(html)
        assert "title: Test Title" in result

    def test_extracts_description(self) -> None:
        html = '<meta name="description" content="A test description">'
        result = _extract_metadata(html)
        assert "description: A test description" in result

    def test_extracts_og_tags(self) -> None:
        html = '<meta property="og:title" content="OG Title">'
        result = _extract_metadata(html)
        assert "og_title: OG Title" in result


class TestWebFetch:
    """Tests for web_fetch function."""

    @pytest.mark.asyncio
    async def test_empty_url_raises(self) -> None:
        with pytest.raises(WebFetchError, match="cannot be empty"):
            await web_fetch("")

    @pytest.mark.asyncio
    async def test_invalid_scheme_raises(self) -> None:
        with pytest.raises(WebFetchError, match="must start with"):
            await web_fetch("ftp://example.com")

    @pytest.mark.asyncio
    async def test_invalid_url_raises(self) -> None:
        with pytest.raises(WebFetchError):
            await web_fetch("http://invalid.test.local.nonexistent", rate_limit=False)
