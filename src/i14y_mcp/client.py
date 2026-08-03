"""HTTP client for the I14Y interoperability platform API.

Resilience defaults follow the Swiss Public Data MCP Portfolio standard:
exponential backoff, no retry on deterministic 4xx, graceful degradation.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlsplit

import httpx

from ._version import __version__
from .logging_config import logger

BASE_URL = "https://api.i14y.admin.ch/api"

# SEC-021: code-layer egress allow-list. A `frozenset` (not env-configurable) is
# the single destination this server may ever reach. `assert_host_allowed` runs
# before the client is built, and redirects off this host are refused in
# `fetch_json`. The network-layer counterpart is documented in
# `docs/network-egress.md`.
ALLOWED_HOSTS: frozenset[str] = frozenset({"api.i14y.admin.ch"})

ATTRIBUTION = (
    "Data: I14Y Interoperability Platform, Swiss Federal Statistical Office (BFS) "
    "— https://www.i14y.admin.ch. Licence terms are declared per distribution; "
    "check the `licence` field before reuse."
)

# Mit Version, damit der Betreiber der Datenquelle erkennt, welches Release ihn
# anruft. Vorher stand hier ein nacktes Produkt-Token: nichts daran war falsch,
# aber bei Fehlverhalten liess sich nicht sagen, welche Fassung es zeigt.
# Interpoliert aus den Paket-Metadaten, nie aus einem Literal.
USER_AGENT = f"i14y-mcp/{__version__} (+https://github.com/malkreide/i14y-mcp)"

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


def assert_host_allowed(url: str) -> None:
    """Raise UpstreamError if `url`'s host is not on the egress allow-list."""
    host = urlsplit(url).hostname or ""
    if host not in ALLOWED_HOSTS:
        raise UpstreamError(
            f"Egress to {host!r} is not allowed (allow-list: {sorted(ALLOWED_HOSTS)})."
        )


def build_client() -> httpx.AsyncClient:
    """Create a configured AsyncClient. Caller owns the lifecycle."""
    assert_host_allowed(BASE_URL)
    return httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=TIMEOUT_S,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        # SEC-021: never auto-follow a redirect off the allow-listed host. The
        # read endpoints return JSON directly; a 3xx is treated as an error.
        follow_redirects=False,
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
            logger.debug("i14y.retry", path=path, attempt=attempt)
            await asyncio.sleep(2**attempt)
        started = time.perf_counter()
        try:
            resp = await http.get(path, params=clean)
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            if resp.status_code == 404:
                logger.info("i14y.not_found", path=path, ms=elapsed_ms)
                raise NotFoundError(
                    f"I14Y has no resource at {path} (HTTP 404). "
                    "Verify the identifier via search_catalog or list_datasets."
                )
            if 300 <= resp.status_code < 400:
                # SEC-021: a redirect would leave the allow-listed host.
                raise UpstreamError(
                    f"I14Y returned an unexpected redirect ({resp.status_code}) for {path}."
                )
            resp.raise_for_status()
            _record_success()
            logger.info("i14y.ok", path=path, status=resp.status_code, ms=elapsed_ms)
            return resp.json()
        except NotFoundError:
            raise
        except httpx.HTTPStatusError as exc:
            last_error = exc
            status = exc.response.status_code
            if 400 <= status < 500 and status != 429:
                # OBS-002: surface a categorised error, not the raw upstream
                # response body — the LLM never sees stray provider internals.
                logger.warning("i14y.client_error", path=path, status=status)
                raise UpstreamError(
                    f"I14Y rejected the request with HTTP {status} for {path}."
                ) from exc
            logger.warning("i14y.server_error", path=path, status=status, attempt=attempt)
        except httpx.RequestError as exc:
            last_error = exc
            logger.warning(
                "i14y.network_error",
                path=path,
                error=type(exc).__name__,
                attempt=attempt,
            )

    logger.error("i14y.unreachable", path=path, attempts=MAX_ATTEMPTS)
    raise UpstreamError(
        f"I14Y unreachable after {MAX_ATTEMPTS} attempts for {path}. "
        f"Last error: {last_error}. "
        f"Last successful call: {last_success() or 'none in this session'}. "
        "Call api_status to check whether the source is down before retrying."
    )


def unwrap(payload: Any) -> Any:
    """I14Y wraps every response in a `data` envelope. Strip it."""
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload
