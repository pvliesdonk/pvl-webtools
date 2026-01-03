# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

pvl-webtools is a Python library providing web search (via SearXNG) and web fetch/extraction tools, with an optional MCP (Model Context Protocol) server interface.

## Commands

```bash
# Install dependencies (uses uv)
uv sync --all-extras

# Run tests
uv run pytest tests/ -v

# Run single test file
uv run pytest tests/test_web_fetch.py -v

# Run tests with coverage
uv run pytest tests/ -v --cov=pvlwebtools --cov-report=xml

# Lint
uv run ruff check src/ tests/

# Format check
uv run ruff format --check src/ tests/

# Auto-format
uv run ruff format src/ tests/

# Build package
uv build

# Run MCP server (requires SEARXNG_URL env var for search)
SEARXNG_URL="http://localhost:8888" uv run pvl-webtools-mcp
```

## Architecture

The library has three main modules in `src/pvlwebtools/`:

- **web_search.py**: `SearXNGClient` for metasearch via SearXNG instances. The `web_search()` convenience function wraps the client. Requires `SEARXNG_URL` environment variable.

- **web_fetch.py**: `web_fetch()` fetches URLs and extracts content. Extraction hierarchy: markitdown (LLM-friendly markdown) → trafilatura (article text) → regex fallback. Includes rate limiting (3s between requests).

- **mcp_server.py**: FastMCP 2 server exposing `search`, `fetch`, and `check_status` tools. Entry point is `pvl-webtools-mcp` CLI command.

All functions are async-first. The MCP server wraps them synchronously for tool compatibility.

## Testing

Tests use pytest-asyncio with `asyncio_mode = "auto"`. No mocking infrastructure - tests validate input handling and extraction logic without network calls.
