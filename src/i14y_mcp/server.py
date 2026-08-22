"""MCP server for the I14Y interoperability platform — Switzerland's national
metadata catalogue.

I14Y is the discovery layer of Swiss public data: it describes *which* body
publishes *what*, through *which* interface, under *which* licence. This server
turns that catalogue into tools, so an agent can find a data source before
trying to query it.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json as _json
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from mcp.server.caching import CacheableMethod, CacheHint
from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from . import mappers
from .client import (
    BASE_URL,
    SEARCH_HARD_CAP,
    NotFoundError,
    UpstreamError,
    build_client,
    client_session,
    fetch_json,
    last_success,
    set_shared_client,
    unwrap,
)
from .logging_config import configure_logging, logger
from .models import (
    CatalogListResult,
    CodeListResult,
    ConceptDetailResult,
    ConceptListResult,
    DataServiceDetailResult,
    DataServiceListResult,
    DatasetDetailResult,
    DatasetListResult,
    DistributionsResult,
    PublicServiceListResult,
    PublisherListResult,
    SearchResult,
    StatusResult,
)


@asynccontextmanager
async def _lifespan(_server: MCPServer) -> AsyncIterator[None]:
    """Build one shared httpx client for the whole process (SDK-001).

    A single pooled client keeps TCP connections and TLS sessions alive across
    tool calls instead of paying a fresh handshake per request.
    """
    async with build_client() as http:
        set_shared_client(http)
        logger.info("server.start", transport=os.getenv("I14Y_MCP_TRANSPORT", "stdio"))
        try:
            yield
        finally:
            set_shared_client(None)
            logger.info("server.stop")


# SEP-2549, Spec 2026-07-28: die auflistenden Methoden tragen `ttlMs` und
# `cacheScope`. Das SDK setzt beides auf «sofort veraltet, nie geteilt» — ein
# Server ohne `cache_hints` verhaelt sich also nicht neutral, sondern laesst
# jeden Client bei jeder Verbindung neu auflisten, fuer Verzeichnisse, die beim
# Import feststehen und sich zur Laufzeit des Prozesses nicht aendern koennen.
#
# `public` folgt aus der Sache, nicht aus Bequemlichkeit: die 13 Tools werden
# per Dekorator beim Import registriert, es gibt keine Filterung nach Aufrufer.
# Sobald eine Liste vom Aufrufer abhaengt, muss der Scope im selben Commit auf
# `private` wechseln.
#
# `prompts/list` und `resources/list` bleiben ungesetzt: dieser Server
# registriert weder Prompts noch Ressourcen, und ein Hinweis darauf beschriebe
# eine Flaeche, die es nicht gibt.
LIST_CACHE_TTL_MS = 300_000

# Annotiert, nicht inferiert: `MCPServer` nimmt
# `Mapping[CacheableMethod, CacheHint]`, und ein Dict-Literal ohne Annotation
# inferiert mypy als `str`. Zur Laufzeit stimmt beides — ein `mypy src/`-Gate
# meldet den Unterschied, die Tests nicht.
CACHE_HINTS: dict[CacheableMethod, CacheHint] = {
    "tools/list": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
    "server/discover": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
}

mcp = MCPServer("i14y-mcp", lifespan=_lifespan, cache_hints=CACHE_HINTS)

Language = Literal["de", "fr", "it", "rm", "en"]
ResourceType = Literal["Dataset", "DataService", "PublicService", "Concept", "MappingTable"]

# ARCH-009: every tool is a side-effect-free GET (idempotent) that reaches an
# external HTTP API (open world). All four hints are set explicitly.
READ_ONLY: dict[str, Any] = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}

# SEC-018: strict, whitelist-based argument constraints applied at the tool
# boundary. Pydantic (via MCPServer) rejects out-of-range, oversized or malformed
# input *before* a tool body runs; `_clamp()` stays as defence in depth for
# direct/programmatic calls that bypass the schema layer.
PathId = Annotated[
    str,
    Field(
        min_length=1,
        max_length=128,
        # Whitelist: catalogue IDs are UUID-like. No slash/space/dot-dot, which
        # also removes any path-traversal surface in the interpolated URL.
        pattern=r"^[A-Za-z0-9._\-]+$",
    ),
]
FilterStr = Annotated[str, Field(min_length=1, max_length=256)]
QueryStr = Annotated[str, Field(max_length=256)]
Page = Annotated[int, Field(ge=1, le=100_000)]
PageSize100 = Annotated[int, Field(ge=1, le=100)]
PageSize200 = Annotated[int, Field(ge=1, le=200)]
Limit = Annotated[int, Field(ge=1, le=SEARCH_HARD_CAP)]


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


async def _get(
    path: str,
    params: dict[str, Any] | None = None,
    ctx: Context | None = None,
) -> Any:
    if ctx is not None:
        await ctx.debug(f"Querying I14Y {path}")
    async with client_session() as http:
        return unwrap(await fetch_json(http, path, params))


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def search_catalog(
    query: QueryStr,
    language: Language = "de",
    types: list[ResourceType] | None = None,
    themes: list[str] | None = None,
    publishers: list[str] | None = None,
    limit: Limit = 25,
    ctx: Context | None = None,
) -> SearchResult:
    """Search Switzerland's national metadata catalogue for data resources.

    The primary entry point: use this to find out *who* publishes data on a
    topic before looking for a specific dataset. Returns titles, publishers,
    themes and portal permalinks.

    Known limitation (verified live 2026-07-21): the upstream search index
    covers Datasets only. Filtering by `types=["Concept"]` or
    `types=["DataService"]` returns zero results even though those entities
    exist — use `list_concepts` and `list_data_services` for those.

    Args:
        query: Free-text search term, e.g. "Sonderpaedagogik" or "Bildung".
            An empty string returns the full index (over 1000 records) and is
            not recommended.
        language: Language for titles and descriptions.
        types: Restrict to resource types. Effectively only "Dataset" works.
        themes: Filter by theme identifiers.
        publishers: Filter by publisher identifiers.
        limit: Maximum records to return (1-200). Upstream ignores paging, so
            capping happens in this server.
    """
    limit = _clamp(limit, 1, SEARCH_HARD_CAP)
    params: dict[str, Any] = {
        "query": query,
        "language": language,
        "structure": "WithoutStructure",
    }
    if types:
        params["types"] = list(types)
    if themes:
        params["themes"] = list(themes)
    if publishers:
        params["publishers"] = list(publishers)

    raw = await _get("/search", params, ctx=ctx) or []
    total = len(raw)
    hits = [mappers.map_search_hit(r, language) for r in raw[:limit]]
    # ARCH-003: never hand back a bare empty result. Tell the agent whether the
    # term matched and, when it did not, where to look next.
    if total == 0:
        match_type = "none"
        hint = (
            "No catalogue entries matched. The search index covers Datasets only "
            "and about half the register — try broader or German terms, or call "
            "list_datasets / list_concepts / list_data_services for the complete "
            "registers."
        )
    else:
        match_type = "exact"
        hint = None
    return SearchResult(
        retrieved_at=_now(),
        query=query or None,
        language=language,
        total_matched=total,
        returned=len(hits),
        truncated=total > len(hits),
        match_type=match_type,
        hint=hint,
        hits=hits,
    )


@mcp.tool(annotations=READ_ONLY)
async def list_datasets(
    publisher_identifier: FilterStr | None = None,
    access_rights: FilterStr | None = None,
    language: Language = "de",
    page: Page = 1,
    page_size: PageSize100 = 25,
    ctx: Context | None = None,
) -> DatasetListResult:
    """List registered datasets, optionally filtered by publisher.

    Unlike `search_catalog`, this endpoint paginates correctly and covers the
    complete register (roughly 2000 datasets as of July 2026), including
    records the search index misses.

    Args:
        publisher_identifier: Publisher identifier from `list_publishers`.
        access_rights: e.g. "PUBLIC", "NON_PUBLIC", "RESTRICTED".
        language: Language for titles and descriptions.
        page: 1-based page number.
        page_size: Records per page (1-100).
    """
    page_size = _clamp(page_size, 1, 100)
    raw = (
        await _get(
            "/datasets",
            {
                "publisherIdentifier": publisher_identifier,
                "accessRights": access_rights,
                "page": max(page, 1),
                "pageSize": page_size,
            },
            ctx=ctx,
        )
        or []
    )
    return DatasetListResult(
        retrieved_at=_now(),
        page=max(page, 1),
        page_size=page_size,
        returned=len(raw),
        datasets=[mappers.map_dataset_summary(r, language) for r in raw],
    )


@mcp.tool(annotations=READ_ONLY)
async def get_dataset(
    dataset_id: PathId, language: Language = "de", ctx: Context | None = None
) -> DatasetDetailResult:
    """Retrieve the full, aggregated metadata record for one dataset.

    This is the aggregated detail tool: a single call returns the contact
    point, temporal and spatial coverage, documentation links *and* every
    distribution with its licence — so `search_catalog` → `get_dataset`
    answers «who publishes it, through which interface, under which licence»
    in two calls, without a separate distributions or contact lookup.

    Args:
        dataset_id: UUID from `search_catalog` or `list_datasets`.
        language: Language for titles and descriptions.
    """
    raw = await _get(f"/datasets/{dataset_id}", ctx=ctx)
    return DatasetDetailResult(
        retrieved_at=_now(),
        dataset=mappers.map_dataset_detail(raw or {}, language),
    )


@mcp.tool(annotations=READ_ONLY)
async def get_dataset_distributions(
    dataset_id: PathId, language: Language = "de", ctx: Context | None = None
) -> DistributionsResult:
    """Get the downloadable files and access URLs for a dataset.

    This is the «where do I actually get the data» tool. Each distribution
    carries its own format, licence and download URL — licences differ between
    distributions of the same dataset, so always read the `licence` field
    before reusing the data. (`get_dataset` returns these same distributions
    alongside the rest of the record.)

    Args:
        dataset_id: UUID from `search_catalog` or `list_datasets`.
        language: Language for titles and descriptions.
    """
    raw = await _get(f"/datasets/{dataset_id}", ctx=ctx) or {}
    detail = mappers.map_dataset_detail(raw, language)
    return DistributionsResult(
        retrieved_at=_now(),
        dataset_id=dataset_id,
        dataset_title=detail.title,
        returned=len(detail.distributions),
        distributions=detail.distributions,
    )


# --------------------------------------------------------------------------
# Interfaces and services
# --------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def list_data_services(
    publisher_identifier: FilterStr | None = None,
    language: Language = "de",
    page: Page = 1,
    page_size: PageSize100 = 25,
    ctx: Context | None = None,
) -> DataServiceListResult:
    """List machine interfaces (APIs) registered by Swiss public bodies.

    The strategic payload of this server: the national register of official
    APIs, with endpoint URLs and OpenAPI specification links where the
    publisher supplied them. Use this to discover whether an interface already
    exists before building a scraper.

    Args:
        publisher_identifier: Publisher identifier from `list_publishers`.
        language: Language for titles and descriptions.
        page: 1-based page number.
        page_size: Records per page (1-100).
    """
    page_size = _clamp(page_size, 1, 100)
    raw = (
        await _get(
            "/dataservices",
            {
                "publisherIdentifier": publisher_identifier,
                "page": max(page, 1),
                "pageSize": page_size,
            },
            ctx=ctx,
        )
        or []
    )
    return DataServiceListResult(
        retrieved_at=_now(),
        page=max(page, 1),
        page_size=page_size,
        returned=len(raw),
        data_services=[mappers.map_data_service(r, language) for r in raw],
    )


@mcp.tool(annotations=READ_ONLY)
async def get_data_service(
    data_service_id: PathId, language: Language = "de", ctx: Context | None = None
) -> DataServiceDetailResult:
    """Retrieve the full record for one registered API, including endpoints.

    Args:
        data_service_id: UUID from `list_data_services`.
        language: Language for titles and descriptions.
    """
    raw = await _get(f"/dataservices/{data_service_id}", ctx=ctx)
    return DataServiceDetailResult(
        retrieved_at=_now(),
        data_service=mappers.map_data_service(raw or {}, language),
    )


@mcp.tool(annotations=READ_ONLY)
async def list_public_services(
    publisher_identifier: FilterStr | None = None,
    language: Language = "de",
    page: Page = 1,
    page_size: PageSize100 = 25,
    ctx: Context | None = None,
) -> PublicServiceListResult:
    """List registered public services (administrative offerings for citizens).

    Args:
        publisher_identifier: Publisher identifier from `list_publishers`.
        language: Language for titles and descriptions.
        page: 1-based page number.
        page_size: Records per page (1-100).
    """
    page_size = _clamp(page_size, 1, 100)
    raw = (
        await _get(
            "/publicservices",
            {
                "publisherIdentifier": publisher_identifier,
                "page": max(page, 1),
                "pageSize": page_size,
            },
            ctx=ctx,
        )
        or []
    )
    return PublicServiceListResult(
        retrieved_at=_now(),
        page=max(page, 1),
        page_size=page_size,
        returned=len(raw),
        public_services=[mappers.map_public_service(r, language) for r in raw],
    )


# --------------------------------------------------------------------------
# Semantics: concepts and code lists
# --------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def list_concepts(
    publisher_identifier: FilterStr | None = None,
    language: Language = "de",
    page: Page = 1,
    page_size: PageSize100 = 25,
    ctx: Context | None = None,
) -> ConceptListResult:
    """List harmonised concepts and code lists of the Swiss administration.

    Concepts are the semantic backbone of interoperability: shared definitions
    and code lists that different bodies agree to use. Note that these are not
    reachable through `search_catalog`.

    Args:
        publisher_identifier: Publisher identifier from `list_publishers`.
        language: Language for titles and descriptions.
        page: 1-based page number.
        page_size: Records per page (1-100).
    """
    page_size = _clamp(page_size, 1, 100)
    raw = (
        await _get(
            "/concepts",
            {
                "publisherIdentifier": publisher_identifier,
                "page": max(page, 1),
                "pageSize": page_size,
            },
            ctx=ctx,
        )
        or []
    )
    return ConceptListResult(
        retrieved_at=_now(),
        page=max(page, 1),
        page_size=page_size,
        returned=len(raw),
        concepts=[mappers.map_concept(r, language) for r in raw],
    )


@mcp.tool(annotations=READ_ONLY)
async def get_concept(
    concept_id: PathId, language: Language = "de", ctx: Context | None = None
) -> ConceptDetailResult:
    """Retrieve one concept definition, including its value type and version.

    Args:
        concept_id: UUID from `list_concepts`.
        language: Language for titles and descriptions.
    """
    raw = await _get(f"/concepts/{concept_id}", ctx=ctx)
    return ConceptDetailResult(
        retrieved_at=_now(),
        concept=mappers.map_concept(raw or {}, language),
    )


@mcp.tool(annotations=READ_ONLY)
async def search_codelist_entries(
    concept_id: PathId,
    language: Language = "de",
    page: Page = 1,
    page_size: PageSize200 = 50,
    ctx: Context | None = None,
) -> CodeListResult:
    """List the individual codes of a code-list concept.

    Use this to resolve official code values — for example the canonical list
    of a classification used across several federal datasets. Only concepts
    with `concept_type == "CodeList"` return entries.

    Args:
        concept_id: UUID of a code-list concept from `list_concepts`.
        language: Language for entry names. Required by the upstream API.
        page: 1-based page number.
        page_size: Records per page (1-200).
    """
    page_size = _clamp(page_size, 1, 200)
    raw = (
        await _get(
            f"/concepts/{concept_id}/codelist-entries/search",
            {"language": language, "page": max(page, 1), "pageSize": page_size},
            ctx=ctx,
        )
        or []
    )
    return CodeListResult(
        retrieved_at=_now(),
        concept_id=concept_id,
        language=language,
        page=max(page, 1),
        page_size=page_size,
        returned=len(raw),
        entries=[mappers.map_codelist_entry(r, language) for r in raw],
    )


# --------------------------------------------------------------------------
# Actors and catalogues
# --------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def list_publishers(
    identifier: FilterStr | None = None,
    uid: FilterStr | None = None,
    language: Language = "de",
    page: Page = 1,
    page_size: PageSize100 = 50,
    ctx: Context | None = None,
) -> PublisherListResult:
    """List the public bodies that publish into I14Y.

    Returns publisher identifiers needed by the other tools, plus the Swiss UID
    where available — the UID is the join key to `register-mcp` (Zefix).

    Args:
        identifier: Filter by exact publisher identifier.
        uid: Filter by Swiss UID, e.g. "CHE-123.456.789".
        language: Language for names.
        page: 1-based page number.
        page_size: Records per page (1-100).
    """
    page_size = _clamp(page_size, 1, 100)
    raw = (
        await _get(
            "/agents",
            {
                "identifier": identifier,
                "uid": uid,
                "page": max(page, 1),
                "pageSize": page_size,
            },
            ctx=ctx,
        )
        or []
    )
    return PublisherListResult(
        retrieved_at=_now(),
        page=max(page, 1),
        page_size=page_size,
        returned=len(raw),
        publishers=[mappers.map_publisher(r, language) for r in raw],
    )


@mcp.tool(annotations=READ_ONLY)
async def list_catalogs(
    language: Language = "de",
    page: Page = 1,
    page_size: PageSize100 = 50,
    ctx: Context | None = None,
) -> CatalogListResult:
    """List the catalogues that feed into I14Y.

    Each catalogue represents one contributing organisation's data collection.

    Args:
        language: Language for titles.
        page: 1-based page number.
        page_size: Records per page (1-100).
    """
    page_size = _clamp(page_size, 1, 100)
    raw = await _get("/catalogs", {"page": max(page, 1), "pageSize": page_size}, ctx=ctx) or []
    return CatalogListResult(
        retrieved_at=_now(),
        page=max(page, 1),
        page_size=page_size,
        returned=len(raw),
        catalogs=[mappers.map_catalog(r, language) for r in raw],
    )


# --------------------------------------------------------------------------
# Operations
# --------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def api_status(ctx: Context | None = None) -> StatusResult:
    """Check whether the I14Y API is reachable and which endpoints respond.

    Always returns an evaluable status rather than an empty result, so an agent
    can distinguish «no data matched» from «the source is down».
    """
    checks: dict[str, str] = {}
    reachable = False
    endpoints = (
        ("datasets", "/datasets"),
        ("dataservices", "/dataservices"),
        ("concepts", "/concepts"),
    )
    async with client_session() as http:
        for index, (name, path) in enumerate(endpoints, start=1):
            if ctx is not None:
                await ctx.report_progress(index, len(endpoints), f"checking {name}")
            try:
                payload = unwrap(await fetch_json(http, path, {"page": 1, "pageSize": 1}))
                checks[name] = f"ok ({len(payload or [])} record)"
                reachable = True
            except (UpstreamError, NotFoundError) as exc:
                checks[name] = f"failed: {str(exc)[:160]}"

    return StatusResult(
        retrieved_at=_now(),
        reachable=reachable,
        base_url=BASE_URL,
        last_successful_call=last_success(),
        checked_endpoints=checks,
        note=(
            "I14Y read endpoints require no authentication. Write operations "
            "need a Bearer token and are deliberately not exposed by this server."
        ),
    )


# --------------------------------------------------------------------------
# Tool-definition integrity (SEC-022)
# --------------------------------------------------------------------------


def _stable_signature(schema: dict[str, Any]) -> dict[str, Any]:
    """Project a tool's input schema to its rug-pull-relevant surface.

    Deliberately captures only the *contract* — the argument names and which are
    required — and not pydantic/mcp-version-specific serialisation of constraints
    (minimum/maximum/pattern/title/anyOf), so the lock is stable across SDK patch
    upgrades. Argument-level constraints live in the reviewed source and CHANGELOG.
    """
    props = schema.get("properties", {}) if isinstance(schema, dict) else {}
    return {
        "arguments": sorted(props),
        "required": sorted(schema.get("required", []) if isinstance(schema, dict) else []),
    }


async def tool_manifest() -> dict[str, Any]:
    """Return a deterministic hash snapshot of the registered tool definitions.

    Committed as `tool-definitions.lock.json` and checked in CI so a silent
    change to the tool set, a tool's name, or its argument surface (a rug-pull)
    fails the build until the lock is regenerated and reviewed.

    The snapshot deliberately covers only what is derived from the *source
    function signatures* — tool name, argument names, and which are required —
    because that is stable across mcp/pydantic patch upgrades. Descriptions
    (docstrings) are normalised differently by different SDK versions, so they
    are governed by PR review + CHANGELOG rather than by this hash.
    """
    tools = sorted(await mcp.list_tools(), key=lambda t: t.name)
    entries = [{"name": tool.name, **_stable_signature(tool.input_schema or {})} for tool in tools]
    combined = hashlib.sha256(
        _json.dumps(entries, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return {
        "server": "i14y-mcp",
        "tool_count": len(entries),
        "combined_sha256": combined,
        "tools": entries,
    }


# --------------------------------------------------------------------------
# Transport
# --------------------------------------------------------------------------


def build_transport_security(host: str, port: int):
    """Host/Origin allow-list for the HTTP/SSE transports (SEC-005, inbound).

    The SDK leaves DNS-rebinding protection OFF while ``transport_security`` is
    unset — its own source says "If not specified, disable DNS rebinding
    protection by default for backwards compatibility". Unset therefore means
    no Host and no Origin validation at all.

    Returns ``None`` when no allow-list can be derived: a non-loopback bind
    with no ``I14Y_MCP_ALLOWED_HOSTS``. The server is then reached under a
    service or public DNS name this process does not know, and a guessed list
    would reject every real request with HTTP 421. The caller warns instead.
    """
    from mcp.server.transport_security import TransportSecuritySettings

    allowed = [h.strip() for h in os.getenv("I14Y_MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    loopback = {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}
    if allowed:
        # Loopback stays reachable for container health checks and debugging.
        hosts = set(allowed) | loopback
    elif host in ("127.0.0.1", "localhost", "::1"):
        hosts = loopback | {f"{host}:{port}"}
    else:
        return None

    # Configured CORS origins must also pass the transport check, or the server
    # rejects exactly the browser clients CORS permits. "*" cannot be expressed
    # here (origins are matched literally, only a trailing ":*" port wildcard
    # exists), so it is not copied across.
    origins = {o for o in [] if o != "*"}
    origins |= {f"http://{h}" for h in hosts}
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=sorted(hosts),
        allowed_origins=sorted(origins),
    )


def build_http_app(transport: str) -> Any:
    """Build the SSE / streamable-http ASGI app with CORS configured.

    MCPServer.run() serves the ASGI app without CORS, so browser clients cannot
    read the `Mcp-Session-Id` response header and lose their session (SDK-004).
    We build the app ourselves and expose that header via CORS.
    """
    from starlette.middleware.cors import CORSMiddleware

    app = mcp.sse_app() if transport == "sse" else mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*", "Mcp-Session-Id"],
        # The critical line: browsers only read a response header if it is
        # listed here, and MCP clients need Mcp-Session-Id to keep a session.
        expose_headers=["Mcp-Session-Id"],
    )
    return app


def _run_http(transport: str, host: str, port: int) -> None:
    """Serve the CORS-wrapped SSE / streamable-http app with uvicorn."""
    import uvicorn

    security = build_transport_security(host, port)
    if security is None:
        logger.warning(
            "dns_rebinding_protection_off",
            host=host,
            hint="Set I14Y_MCP_ALLOWED_HOSTS to the hostnames this server is "
            "reachable under; without it the Host header is not checked at all.",
        )
    mcp.settings.transport_security = security
    uvicorn.run(build_http_app(transport), host=host, port=port, log_level="info")


def main() -> None:
    """Entry point. Transport is selected via the I14Y_MCP_TRANSPORT env var."""
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))
    transport = os.getenv("I14Y_MCP_TRANSPORT", "stdio").lower()
    if transport in {"sse", "streamable-http", "http"}:
        # SEC-016: default to loopback. Binding to all interfaces is an
        # explicit opt-in (the container image sets HOST=0.0.0.0 on purpose).
        host = os.getenv("HOST", "127.0.0.1")
        port = int(os.getenv("PORT", "8000"))
        if host == "0.0.0.0":  # noqa: S104 — intentional, warned about below
            print(
                "i14y-mcp: binding to 0.0.0.0 exposes the server on all network "
                "interfaces; run it only behind a reverse proxy / firewall.",
                file=sys.stderr,
            )
        mcp.settings.host = host
        mcp.settings.port = port
        _run_http("sse" if transport == "sse" else "streamable-http", host, port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
