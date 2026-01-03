# Multi-stage build for pvl-webtools MCP server
# Optimized for size and security

# =============================================================================
# Stage 1: Build
# =============================================================================
FROM python:3.12-slim AS builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml .
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
    useradd --uid 1000 --gid 1000 --shell /bin/bash appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY src/ src/

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
    CMD python -c "import httpx; r = httpx.get('http://localhost:${MCP_PORT}/mcp', timeout=5); exit(0 if r.status_code in [200, 405] else 1)" || exit 1

# Run MCP server with streamable HTTP transport
CMD ["python", "-c", "from pvlwebtools.mcp_server import mcp; import os; mcp.run(transport='http', host=os.environ.get('MCP_HOST', '0.0.0.0'), port=int(os.environ.get('MCP_PORT', '8000')))"]
