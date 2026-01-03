# Multi-stage build for pvl-webtools MCP server
# Optimized for size and security

# =============================================================================
# Stage 1: Build
# =============================================================================
FROM python:3.12-slim AS builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml README.md ./
COPY src/ src/

# Create virtual environment and install dependencies
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python ".[mcp,markdown,extraction]"

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.12-slim AS runtime

# Security: Run as non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid 1000 --shell /sbin/nologin appuser

WORKDIR /app

# Copy virtual environment from builder (includes installed package)
COPY --from=builder /app/.venv /app/.venv

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# MCP server configuration
ENV MCP_HOST="0.0.0.0"
ENV MCP_PORT="8000"

# Switch to non-root user
USER appuser

# Expose MCP server port
EXPOSE 8000

# Health check - verify the MCP endpoint is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:${MCP_PORT}/mcp', timeout=5); exit(0 if r.status_code in [200, 405] else 1)"

# Run MCP server with streamable HTTP transport
CMD ["python", "-c", "from pvlwebtools.mcp_server import mcp; import os; mcp.run(transport='http', host=os.environ['MCP_HOST'], port=int(os.environ['MCP_PORT']))"]
