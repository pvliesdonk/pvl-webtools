# Docker Deployment

pvl-webtools provides a Docker image for running the MCP server with Streamable HTTP transport, suitable for production deployments and integration with AI assistants over the network.

## Quick Start

```bash
# Pull the latest image
docker pull ghcr.io/pvliesdonk/pvl-webtools:latest

# Run with SearXNG configured
docker run -d \
  --name pvl-webtools \
  -p 8000:8000 \
  -e SEARXNG_URL="http://your-searxng-instance:8888" \
  ghcr.io/pvliesdonk/pvl-webtools:latest
```

The MCP server is now available at `http://localhost:8000/mcp`.

## Image Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release |
| `vX.Y.Z` | Specific version (e.g., `v0.2.0`) |
| `vX.Y` | Latest patch for minor version (e.g., `v0.2`) |
| `vX` | Latest for major version (e.g., `v0`) |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARXNG_URL` | *(none)* | SearXNG instance URL for web search |
| `MCP_HOST` | `0.0.0.0` | Host to bind the server to |
| `MCP_PORT` | `8000` | Port to listen on |
| `LOG_LEVEL` | *(none)* | Optional logging level for the MCP server (`DEBUG`, `INFO`, etc.). Logs go to stderr. |
| `VERBOSE` | *(none)* | Convenience flag; set to `1`/`true` for debug logging. |

### Example: Custom Port

```bash
docker run -d \
  -p 9000:9000 \
  -e MCP_PORT=9000 \
  -e LOG_LEVEL=DEBUG \
  -e SEARXNG_URL="http://searxng:8888" \
  ghcr.io/pvliesdonk/pvl-webtools:latest
```

Legacy environment variables `PVL_MCP_LOG_LEVEL` and `PVL_MCP_VERBOSE` are still
recognized by the container but will be removed in a future release.

## Docker Compose

Here's a complete example with SearXNG:

```yaml
# docker-compose.yml
services:
  pvl-webtools:
    image: ghcr.io/pvliesdonk/pvl-webtools:latest
    ports:
      - "8000:8000"
    environment:
      - SEARXNG_URL=http://searxng:8888
    depends_on:
      - searxng
    restart: unless-stopped

  searxng:
    image: searxng/searxng:latest
    ports:
      - "8888:8080"
    volumes:
      - ./searxng:/etc/searxng:rw
    environment:
      - SEARXNG_BASE_URL=http://localhost:8888/
    restart: unless-stopped
```

```bash
docker compose up -d
```

## Connecting MCP Clients

### Claude Desktop

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "pvl-webtools": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### FastMCP Client

```python
from fastmcp import Client

async with Client("http://localhost:8000/mcp") as client:
    # Search the web
    results = await client.call_tool("search", {
        "query": "python best practices",
        "max_results": 5
    })

    # Fetch a URL
    content = await client.call_tool("fetch", {
        "url": "https://example.com",
        "extract_mode": "markdown"
    })
```

## Building Locally

```bash
# Clone the repository
git clone https://github.com/pvliesdonk/pvl-webtools.git
cd pvl-webtools

# Build the image
docker build -t pvl-webtools:local .

# Run locally built image
docker run -p 8000:8000 -e SEARXNG_URL="http://your-searxng:8888" pvl-webtools:local
```

## Multi-Architecture Support

The published images support both `linux/amd64` and `linux/arm64` architectures, making them compatible with:

- Standard x86_64 servers
- Apple Silicon Macs (M1/M2/M3)
- ARM-based cloud instances (AWS Graviton, etc.)

## Health Checks

The container includes a health check that verifies the MCP endpoint is responding:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' pvl-webtools
```

## Security Notes

- The container runs as a non-root user (`appuser`)
- Only the MCP port (8000 by default) is exposed
- No sensitive data is stored in the image
- Use environment variables for configuration (never bake secrets into images)

## Troubleshooting

### Search not working

Ensure `SEARXNG_URL` is set and the SearXNG instance is reachable from the container:

```bash
docker exec pvl-webtools python -c "from pvlwebtools.mcp_server import check_status; print(check_status())"
```

### Connection refused

Check if the container is running and healthy:

```bash
docker ps
docker logs pvl-webtools
```

### Port conflicts

If port 8000 is in use, map to a different port:

```bash
docker run -p 9000:8000 ghcr.io/pvliesdonk/pvl-webtools:latest
```
