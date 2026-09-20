# syntax=docker/dockerfile:1.7
# Multi-stage build: install deps with pip into a venv, then ship a slim runtime.
FROM python:3.14-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
# LICENSE must be copied — pyproject.toml declares `license = { file = "LICENSE" }`,
# so the wheel build fails without it.
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN python -m venv /app/.venv \
    && /app/.venv/bin/pip install --no-cache-dir .

# ---------------------------------------------------------------------------

FROM python:3.14-slim AS runtime

# I14Y_MCP_TRANSPORT was `sse`, and that is the one value a hosted deployment
# cannot use: the SSE app serves /sse + /messages, while a Claude.ai custom
# connector speaks Streamable HTTP and reaches the server at /mcp. Measured
# through the assembled app, not read off the transport name —
# `tests/test_entrypoint.py` pins both route sets, so the day the SDK moves the
# path it fails there instead of in a deployment.
#
# stdio is unaffected: it is still the default of `main()` itself, and only
# this image overrides it. Anyone running `uvx i14y-mcp` for Claude Desktop
# never passes through here.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    I14Y_MCP_TRANSPORT=streamable-http \
    HOST=0.0.0.0 \
    PORT=8000

RUN groupadd --system mcp \
    && useradd --system --gid mcp --home-dir /app --shell /usr/sbin/nologin mcp

WORKDIR /app
COPY --from=builder --chown=mcp:mcp /app/.venv /app/.venv

USER mcp
EXPOSE 8000

# SCALE-004: let orchestrators/load balancers detect an unhealthy container.
# The HTTP runtime opens PORT; a successful TCP connect means the server is up.
# Deliberately a TCP connect and not a request to the MCP path: the check must
# not go stale when the transport — and with it the path — changes.
# Uses stdlib only (no curl in the slim image).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,socket; socket.create_connection(('127.0.0.1', int(os.getenv('PORT','8000'))), 3).close()" || exit 1

# Read-only, no-auth public-data server — no secrets required at runtime.
CMD ["python", "-m", "i14y_mcp.server"]
