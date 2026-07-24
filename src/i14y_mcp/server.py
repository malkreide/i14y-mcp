"""MCP server for the I14Y interoperability platform — Switzerland's national
metadata catalogue.

I14Y is the discovery layer of Swiss public data: it describes *which* body
publishes *what*, through *which* interface, under *which* licence. This server
turns that catalogue into tools, so an agent can find a data source before
trying to query it.
"""

from __future__ import annotations

import datetime as _dt
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

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
async def _lifespan(_server: FastMCP) -> AsyncIterator[None]:
    """Build one shared httpx client for the whole process (SDK-001).

    A single pooled client keeps TCP connections and TLS sessions alive across
    tool calls instead of paying a fresh handshake per request.
    """
    async with build_client() as http:
        set_shared_client(http)
        try:
            yield
        finally:
            set_shared_client(None)


mcp = FastMCP("i14y-mcp", lifespan=_lifespan)

Language = Literal["de", "fr", "it", "rm", "en"]
ResourceType = Literal["Dataset", "DataService", "PublicService", "Concept", "MappingTable"]

READ_ONLY: dict[str, Any] = {"readOnlyHint": True, "destructiveHint": False}


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    async with client_session() as http:
        return unwrap(await fetch_json(http, path, params))


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def search_catalog(
    query: str,
    language: Language = "de",
    types: list[ResourceType] | None = None,
    themes: list[str] | None = None,
    publishers: list[str] | None = None,
    limit: int = 25,
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

    raw = await _get("/search", params) or []
    total = len(raw)
    hits = [mappers.map_search_hit(r, language) for r in raw[:limit]]
    return SearchResult(
        retrieved_at=_now(),
        query=query or None,
        language=language,
        total_matched=total,
        returned=len(hits),
        truncated=total > len(hits),
        hits=hits,
    )


@mcp.tool(annotations=READ_ONLY)
async def list_datasets(
    publisher_identifier: str | None = None,
    access_rights: str | None = None,
    language: Language = "de",
    page: int = 1,
    page_size: int = 25,
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
async def get_dataset(dataset_id: str, language: Language = "de") -> DatasetDetailResult:
    """Retrieve the full metadata record for one dataset.

    Includes contact point, temporal and spatial coverage, documentation links
    and all distributions with their licences.

    Args:
        dataset_id: UUID from `search_catalog` or `list_datasets`.
        language: Language for titles and descriptions.
    """
    raw = await _get(f"/datasets/{dataset_id}")
    return DatasetDetailResult(
        retrieved_at=_now(),
        dataset=mappers.map_dataset_detail(raw or {}, language),
    )


@mcp.tool(annotations=READ_ONLY)
async def get_dataset_distributions(
    dataset_id: str, language: Language = "de"
) -> DistributionsResult:
    """Get the downloadable files and access URLs for a dataset.

    This is the «where do I actually get the data» tool. Each distribution
    carries its own format, licence and download URL — licences differ between
    distributions of the same dataset, so always read the `licence` field
    before reusing the data.

    Args:
        dataset_id: UUID from `search_catalog` or `list_datasets`.
        language: Language for titles and descriptions.
    """
    raw = await _get(f"/datasets/{dataset_id}") or {}
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
    publisher_identifier: str | None = None,
    language: Language = "de",
    page: int = 1,
    page_size: int = 25,
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
    data_service_id: str, language: Language = "de"
) -> DataServiceDetailResult:
    """Retrieve the full record for one registered API, including endpoints.

    Args:
        data_service_id: UUID from `list_data_services`.
        language: Language for titles and descriptions.
    """
    raw = await _get(f"/dataservices/{data_service_id}")
    return DataServiceDetailResult(
        retrieved_at=_now(),
        data_service=mappers.map_data_service(raw or {}, language),
    )


@mcp.tool(annotations=READ_ONLY)
async def list_public_services(
    publisher_identifier: str | None = None,
    language: Language = "de",
    page: int = 1,
    page_size: int = 25,
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
    publisher_identifier: str | None = None,
    language: Language = "de",
    page: int = 1,
    page_size: int = 25,
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
async def get_concept(concept_id: str, language: Language = "de") -> ConceptDetailResult:
    """Retrieve one concept definition, including its value type and version.

    Args:
        concept_id: UUID from `list_concepts`.
        language: Language for titles and descriptions.
    """
    raw = await _get(f"/concepts/{concept_id}")
    return ConceptDetailResult(
        retrieved_at=_now(),
        concept=mappers.map_concept(raw or {}, language),
    )


@mcp.tool(annotations=READ_ONLY)
async def search_codelist_entries(
    concept_id: str,
    language: Language = "de",
    page: int = 1,
    page_size: int = 50,
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
    identifier: str | None = None,
    uid: str | None = None,
    language: Language = "de",
    page: int = 1,
    page_size: int = 50,
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
    language: Language = "de", page: int = 1, page_size: int = 50
) -> CatalogListResult:
    """List the catalogues that feed into I14Y.

    Each catalogue represents one contributing organisation's data collection.

    Args:
        language: Language for titles.
        page: 1-based page number.
        page_size: Records per page (1-100).
    """
    page_size = _clamp(page_size, 1, 100)
    raw = await _get("/catalogs", {"page": max(page, 1), "pageSize": page_size}) or []
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
async def api_status() -> StatusResult:
    """Check whether the I14Y API is reachable and which endpoints respond.

    Always returns an evaluable status rather than an empty result, so an agent
    can distinguish «no data matched» from «the source is down».
    """
    checks: dict[str, str] = {}
    reachable = False
    async with client_session() as http:
        for name, path in (
            ("datasets", "/datasets"),
            ("dataservices", "/dataservices"),
            ("concepts", "/concepts"),
        ):
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


def build_http_app(transport: str) -> Any:
    """Build the SSE / streamable-http ASGI app with CORS configured.

    FastMCP.run() serves the ASGI app without CORS, so browser clients cannot
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

    uvicorn.run(build_http_app(transport), host=host, port=port, log_level="info")


def main() -> None:
    """Entry point. Transport is selected via the I14Y_MCP_TRANSPORT env var."""
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
