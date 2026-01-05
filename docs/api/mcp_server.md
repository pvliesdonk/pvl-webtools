# MCP Server

Model Context Protocol server for AI assistant integration.

## Overview

The MCP server exposes pvl-webtools functionality to AI assistants like Claude via the Model Context Protocol. It provides tools for web searching and content fetching.

## Running the Server

### Command Line

```bash
# Set SearXNG URL for search
export SEARXNG_URL="http://localhost:8888"

# Run with uvx
uvx pvl-webtools-mcp
```

### Verbose Logging

Set `LOG_LEVEL` (e.g., `DEBUG`, `INFO`, `TRACE`) or the convenience flag
`VERBOSE=1` to emit detailed MCP server logs to stderr without
interfering with stdio transport. `TRACE` removes dependency filtering
so every FastMCP/Docket message continues to appear.

### Programmatic

```python
from pvlwebtools.mcp_server import run_server

# Standard I/O transport (for Claude integration)
run_server()

# HTTP transport (for web clients)
run_server(transport="http", host="0.0.0.0", port=8080)
```

## Available Tools

### search

Search the web via SearXNG metasearch engine.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `query` | string | required | Search query |
| `max_results` | int | 5 | Maximum results (1-20) |
| `domain_filter` | string | null | Limit to domain |
| `recency` | string | "all_time" | Time filter |

### fetch

Fetch and extract content from a URL.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `url` | string | required | URL to fetch |
| `extract_mode` | string | "markdown" | Extraction mode |

**Extract Modes:** `markdown`, `article`, `raw`, `metadata`

### check_status

Check the status of web tools.

**Returns:** Status information including SearXNG availability.

## Claude Desktop Integration

Add to your Claude Desktop configuration (`~/.config/claude/mcp.json`):

```json
{
  "mcpServers": {
    "pvl-webtools": {
      "command": "uvx",
      "args": ["pvl-webtools-mcp"],
      "env": {
        "SEARXNG_URL": "http://localhost:8888"
      }
    }
  }
}
```

## API Reference

::: pvlwebtools.mcp_server
    options:
      members:
        - run_server
        - search
        - fetch
        - check_status
