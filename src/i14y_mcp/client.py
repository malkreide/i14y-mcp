"""HTTP client for the I14Y interoperability platform API.

Resilience defaults follow the Swiss Public Data MCP Portfolio standard:
exponential backoff, no retry on deterministic 4xx, graceful degradation.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import random
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
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


# --- Retry policy ------------------------------------------------------------
# Adopted from the mcp-data-source-probe reference template (repaired
# 2026-08-07). Three questions: *what* is retried, *how fast*, and *how long*.
# The first is settled in the retry loop (4xx except 429 fails fast); these
# settle the other two.

RETRY_BASE_DELAY = 2.0  # ladder before jitter: 2, 4, 8

# Ceiling on the WHOLE call — every attempt and every wait together. An attempt
# count is not a bound: four attempts against an upstream that takes 30s to time
# out is two minutes inside one tool call, and the number never says so. The
# anchor is measured, not guessed: the Python MCP SDK ships
# MCP_DEFAULT_TIMEOUT = 30.0, so 25s leaves headroom for framing and parsing.
RETRY_TOTAL_BUDGET = 25.0

# Ceiling for a single wait. Bounds the exponential ladder, and bounds a
# `Retry-After` the source may send but we are not obliged to sit through.
RETRY_MAX_DELAY = 20.0

# Jitter spread. Without it every client that hit the same outage retries in
# lockstep, and the load returns as a wave exactly when the source recovers —
# the retry storm extends the outage it was meant to bridge.
RETRY_JITTER_SPREAD = 0.5  # exponential delays land in [0.5x, 1.5x]

# On a `Retry-After`, deliberately one-sided: the source said when to come back,
# so coming back later is fine and coming back earlier is not.
RETRY_AFTER_JITTER = 0.25  # lands in [1.0x, 1.25x]

# Statuses that carry a meaningful `Retry-After` (RFC 9110 section 10.2.3).
RETRY_AFTER_STATUSES = frozenset({429, 503})


class UpstreamUnavailableError(Exception):
    """No request was attempted — the budget was gone before the first try.

    A named type rather than ``RuntimeError``: a caller can branch on this, and
    cannot tell a bare ``RuntimeError`` apart from a bug in this server's own
    code. Raised only when there is no upstream exception to re-raise.
    """


def parse_retry_after(resp: httpx.Response | None) -> float | None:
    """Seconds to wait per the response's ``Retry-After``, or ``None``.

    RFC 9110 section 10.2.3 allows two forms — delta-seconds (``120``) and an
    HTTP-date (``Wed, 21 Oct 2026 07:28:00 GMT``). Both appear in the wild, so
    both are read. Anything unparseable yields ``None`` and the caller falls
    back to its own curve: a malformed header must not become a crash on the
    error path, which is the one path already going badly.
    """
    if resp is None or resp.status_code not in RETRY_AFTER_STATUSES:
        return None
    raw = (resp.headers.get("retry-after") or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return float(raw)
    try:
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:  # RFC 9110 dates are GMT; a naive one means UTC
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - datetime.now(UTC)).total_seconds())


def compute_delay(attempt: int, last_error: Exception | None) -> float:
    """Seconds to wait before ``attempt`` (1-based for the first retry).

    The source's own answer beats our guess: a ``Retry-After`` on a 429 or 503
    wins over the exponential curve. Everything is spread, then capped.

    The cap wraps the jitter and not the other way round. ``min(cap, base) *
    jitter`` and ``min(cap, base * jitter)`` both contain a cap and a jitter;
    only the second is bounded — a value capped at 20s and then multiplied by
    up to 1.5 lands at 30s, and the constant would claim a ceiling it does not
    hold.
    """
    hinted = parse_retry_after(getattr(last_error, "response", None))
    if hinted is not None:
        return min(
            hinted * (1.0 + random.random() * RETRY_AFTER_JITTER),
            RETRY_MAX_DELAY,
        )
    return min(
        RETRY_BASE_DELAY
        * 2 ** (attempt - 1)
        * (1.0 - RETRY_JITTER_SPREAD + random.random() * 2 * RETRY_JITTER_SPREAD),
        RETRY_MAX_DELAY,
    )


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
    deadline = time.monotonic() + RETRY_TOTAL_BUDGET
    attempts = 0

    for attempt in range(MAX_ATTEMPTS):
        if attempt > 0:
            delay = compute_delay(attempt, last_error)
            # A wait that outlasts the budget is a wait for nobody: the caller
            # has given up by the time it ends. Stop instead of sleeping.
            if delay >= deadline - time.monotonic():
                break
            logger.debug("i14y.retry", path=path, attempt=attempt, delay_s=round(delay, 2))
            await asyncio.sleep(delay)

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        attempts += 1
        started = time.perf_counter()
        try:
            # `time.perf_counter` here times the call for the log line — it
            # bounds nothing. The budget is the `asyncio.timeout` below: httpx
            # limits each operation and restarts its read timeout with every
            # chunk, so a slowly trickling response outlives a per-operation
            # limit without any single read expiring.
            async with asyncio.timeout(remaining):
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
        except TimeoutError as exc:  # the budget is gone, not just this try
            last_error = exc
            logger.warning("i14y.budget_spent", path=path, attempt=attempt)
            break
        except httpx.RequestError as exc:
            last_error = exc
            logger.warning(
                "i14y.network_error",
                path=path,
                error=type(exc).__name__,
                attempt=attempt,
            )

    host = urlsplit(str(http.base_url)).hostname or "unknown"
    if last_error is None:
        raise UpstreamUnavailableError(
            f"No request to I14Y was attempted for {path}: the "
            f"{RETRY_TOTAL_BUDGET:g}s budget was already spent (host={host})."
        )

    logger.error(
        "i14y.unreachable",
        path=path,
        attempts=attempts,
        error=type(last_error).__name__,
        host=host,
    )
    # Still wrapped, deliberately: OBS-002 keeps raw upstream detail away from
    # the model, and `UpstreamError` is a type a caller can branch on. What
    # changed is WHAT the message carries. It used to interpolate
    # `{last_error}` alone — and `httpx.ConnectTimeout`, `ReadTimeout` and
    # `ConnectError` all have an EMPTY `str()`, which is precisely the set an
    # outage produces. The sentence read "Last error: ." and named neither the
    # failure mode nor the host. Anyone who wraps has to name the type.
    why = (
        f"all {MAX_ATTEMPTS} attempts used"
        if attempts >= MAX_ATTEMPTS
        else f"the {RETRY_TOTAL_BUDGET:g}s budget ran out after {attempts}"
    )
    detail = str(last_error) or "no further detail"
    raise UpstreamError(
        f"I14Y unreachable for {path} after {attempts} attempt(s) — {why}. "
        f"Last error: {type(last_error).__name__}: {detail} (host={host}). "
        f"Last successful call: {last_success() or 'none in this session'}. "
        "Call api_status to check whether the source is down before retrying."
    )


def unwrap(payload: Any) -> Any:
    """I14Y wraps every response in a `data` envelope. Strip it."""
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload
