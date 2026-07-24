"""HTTP client for the I14Y interoperability platform API.

Resilience defaults follow the Swiss Public Data MCP Portfolio standard:
exponential backoff, no retry on deterministic 4xx, graceful degradation.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx

BASE_URL = "https://api.i14y.admin.ch/api"

ATTRIBUTION = (
    "Data: I14Y Interoperability Platform, Swiss Federal Statistical Office (BFS) "
    "— https://www.i14y.admin.ch. Licence terms are declared per distribution; "
    "check the `licence` field before reuse."
)

USER_AGENT = "i14y-mcp (+https://github.com/malkreide/i14y-mcp)"

# Retry policy: 3 retries, 2s / 4s / 8s.
MAX_ATTEMPTS = 4
TIMEOUT_S = 60.0

# Search returns the *complete* result set regardless of pageSize (verified
# 2026-07-21: pageSize=5 returned 36 records). We therefore cap the payload
# client-side to keep the model context usable.
SEARCH_HARD_CAP = 200


class UpstreamError(RuntimeError):
    """Raised when I14Y is unreachable after all retries."""


class NotFoundError(RuntimeError):
    """Raised when I14Y returns 404 for a requested resource."""


_LAST_SUCCESS: dict[str, str] = {}


def last_success() -> str | None:
    """Timestamp of the most recent successful upstream call, if any."""
    return _LAST_SUCCESS.get("ts")


def _record_success() -> None:
    _LAST_SUCCESS["ts"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def build_client() -> httpx.AsyncClient:
    """Create a configured AsyncClient. Caller owns the lifecycle."""
    return httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=TIMEOUT_S,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        follow_redirects=True,
    )


# A single client is installed by the server lifespan (SDK-001). When present,
# tools reuse it instead of building a fresh client per call, so the httpx
# connection pool and TLS sessions survive across requests.
_SHARED: dict[str, httpx.AsyncClient] = {}


def set_shared_client(client: httpx.AsyncClient | None) -> None:
    """Install (or, with None, remove) the process-wide shared client."""
    if client is None:
        _SHARED.pop("client", None)
    else:
        _SHARED["client"] = client


def get_shared_client() -> httpx.AsyncClient | None:
    return _SHARED.get("client")


@asynccontextmanager
async def client_session() -> AsyncIterator[httpx.AsyncClient]:
    """Yield the shared client if the lifespan installed one, otherwise a
    short-lived client.

    This lets tools run both under the server lifespan (pooled, long-lived
    client) and in direct unit tests that call them without a running lifespan
    (fresh client per call).
    """
    shared = get_shared_client()
    if shared is not None:
        yield shared
        return
    async with build_client() as http:
        yield http


async def fetch_json(
    http: httpx.AsyncClient,
    path: str,
    params: dict[str, Any] | None = None,
) -> Any:
    """GET `path` and return parsed JSON, retrying transient failures.

    Retries on 5xx, 429 and network errors with 2s/4s/8s backoff. Deterministic
    4xx responses are raised immediately — retrying them only wastes time.
    """
    clean = {k: v for k, v in (params or {}).items() if v is not None}
    last_error: Exception | None = None

    for attempt in range(MAX_ATTEMPTS):
        if attempt > 0:
            await asyncio.sleep(2**attempt)
        try:
            resp = await http.get(path, params=clean)
            if resp.status_code == 404:
                raise NotFoundError(f"I14Y returned 404 for {path}")
            resp.raise_for_status()
            _record_success()
            return resp.json()
        except NotFoundError:
            raise
        except httpx.HTTPStatusError as exc:
            last_error = exc
            status = exc.response.status_code
            if 400 <= status < 500 and status != 429:
                # OBS-002: surface a categorised error, not the raw upstream
                # response body — the LLM never sees stray provider internals.
                raise UpstreamError(
                    f"I14Y rejected the request with HTTP {status} for {path}."
                ) from exc
        except httpx.RequestError as exc:
            last_error = exc

    raise UpstreamError(
        f"I14Y unreachable after {MAX_ATTEMPTS} attempts for {path}. "
        f"Last error: {last_error}. "
        f"Last successful call: {last_success() or 'none in this session'}."
    )


def unwrap(payload: Any) -> Any:
    """I14Y wraps every response in a `data` envelope. Strip it."""
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload
