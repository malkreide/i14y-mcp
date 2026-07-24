"""Mapper and tool-level tests, plus live probes excluded from CI."""

from __future__ import annotations

import httpx
import pytest
import respx

from i14y_mcp import client as c
from i14y_mcp import server
from i14y_mcp.mappers import map_data_service, map_dataset_detail
from i14y_mcp.models import pick_lang

BASE = c.BASE_URL


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    async def _instant(_seconds):
        return None

    monkeypatch.setattr(c.asyncio, "sleep", _instant)


# --------------------------------------------------------------------------
# Mappers
# --------------------------------------------------------------------------


def test_pick_lang_falls_back_when_requested_language_missing():
    value = {"fr": "Ecole", "it": "Scuola"}
    assert pick_lang(value, "de") == "Ecole"
    assert pick_lang({}, "de") is None
    assert pick_lang(None, "de") is None
    assert pick_lang("plain string", "de") == "plain string"


def test_dataset_detail_collapses_multilanguage_and_distributions():
    raw = {
        "id": "d1",
        "identifiers": ["ID-1"],
        "title": {"de": "Statistik der Sonderpaedagogik", "fr": "Statistique"},
        "description": {"de": "Beschreibung"},
        "publisher": {"name": {"de": "Bundesamt für Statistik (BFS)"}},
        "themes": [{"name": {"de": "Bildung"}, "code": "EDUC"}],
        "keywords": [{"de": "Schule"}],
        "accessRights": {"code": "PUBLIC", "name": {"de": "Öffentlich"}},
        "contactPoints": [{"fn": {"de": "BFS"}, "hasEmail": "info@bfs.admin.ch"}],
        "temporalCoverage": [{"start": "2010-01-01", "end": "2024-12-31"}],
        "distributions": [
            {
                "id": "dist1",
                "format": {"code": "CSV", "name": {"de": "CSV"}},
                "downloadUrl": {"uri": "https://example.ch/data.csv"},
                "license": {"name": {"de": "Opendata BY"}},
            }
        ],
    }
    ds = map_dataset_detail(raw, "de")
    assert ds.title == "Statistik der Sonderpaedagogik"
    assert ds.publisher == "Bundesamt für Statistik (BFS)"
    assert ds.themes == ["Bildung"]
    assert ds.contact_email == "info@bfs.admin.ch"
    assert ds.temporal_coverage == "2010-01-01 – 2024-12-31"
    assert ds.distribution_count == 1
    assert ds.distributions[0].download_url == "https://example.ch/data.csv"
    assert ds.distributions[0].licence == "Opendata BY"


def test_data_service_handles_label_only_endpoints():
    """Regression guard for a real quirk: some endpoint entries carry no URI."""
    raw = {
        "id": "s1",
        "title": {"de": "Pension API"},
        "endpointUrls": [
            {"uri": "https://api.example.ch/v1"},
            {"label": {"de": "OpenAPI Spezifikation"}},
        ],
    }
    svc = map_data_service(raw, "de")
    assert svc.endpoint_urls == [
        "https://api.example.ch/v1",
        "(no URI) OpenAPI Spezifikation",
    ]


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------


@respx.mock
async def test_search_caps_result_set_and_flags_truncation():
    """Upstream ignores pageSize, so the server must cap client-side."""
    records = [
        {"id": str(i), "type": "Dataset", "title": {"de": f"Datensatz {i}"}} for i in range(40)
    ]
    respx.get(f"{BASE}/search").mock(return_value=httpx.Response(200, json={"data": records}))
    result = await server.search_catalog(query="schule", limit=10)
    assert result.total_matched == 40
    assert result.returned == 10
    assert result.truncated is True
    assert result.provenance == "live_api"
    assert "I14Y" in result.source


@respx.mock
async def test_search_empty_result_is_not_truncated():
    respx.get(f"{BASE}/search").mock(return_value=httpx.Response(200, json={"data": []}))
    result = await server.search_catalog(query="zzzznonexistent")
    assert result.returned == 0
    assert result.truncated is False


@respx.mock
async def test_get_dataset_distributions_surfaces_licence():
    respx.get(f"{BASE}/datasets/d1").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "id": "d1",
                    "title": {"de": "Testdatensatz"},
                    "distributions": [
                        {
                            "id": "x",
                            "format": {"code": "CSV"},
                            "downloadUrl": {"uri": "https://example.ch/a.csv"},
                            "license": {"name": {"de": "Opendata BY ASK"}},
                        }
                    ],
                }
            },
        )
    )
    result = await server.get_dataset_distributions(dataset_id="d1")
    assert result.returned == 1
    assert result.distributions[0].licence == "Opendata BY ASK"


@respx.mock
async def test_api_status_reports_failure_gracefully():
    respx.get(f"{BASE}/datasets").mock(return_value=httpx.Response(500))
    respx.get(f"{BASE}/dataservices").mock(return_value=httpx.Response(500))
    respx.get(f"{BASE}/concepts").mock(return_value=httpx.Response(500))
    status = await server.api_status()
    assert status.reachable is False
    assert all("failed" in v for v in status.checked_endpoints.values())


@respx.mock
async def test_page_size_is_clamped():
    route = respx.get(f"{BASE}/datasets").mock(return_value=httpx.Response(200, json={"data": []}))
    await server.list_datasets(page_size=9999, page=0)
    request = route.calls[0].request
    assert "pageSize=100" in str(request.url)
    assert "page=1" in str(request.url)


# --------------------------------------------------------------------------
# Live probes (excluded from CI via -m "not live")
# --------------------------------------------------------------------------


@pytest.mark.live
async def test_live_search_finds_education_datasets():
    result = await server.search_catalog(query="schule", language="de", limit=5)
    assert result.returned > 0
    assert all(h.title for h in result.hits)


@pytest.mark.live
async def test_live_data_services_expose_endpoints():
    result = await server.list_data_services(page_size=20)
    assert result.returned > 0
    assert any(s.endpoint_urls for s in result.data_services)


@pytest.mark.live
async def test_live_status_is_reachable():
    status = await server.api_status()
    assert status.reachable is True


def test_keywords_unwrap_the_label_envelope():
    """Regression guard: keywords nest their language object under `label`."""
    from i14y_mcp.mappers import _keywords

    raw = {"keywords": [{"label": {"de": "Vorsorge", "fr": "Retraite"}}, {"de": "Schule"}]}
    assert _keywords(raw, "de") == ["Vorsorge", "Schule"]
    assert _keywords(raw, "fr") == ["Retraite", "Schule"]


@pytest.mark.parametrize("transport", ["sse", "streamable-http"])
def test_http_app_exposes_session_id_via_cors(transport):
    """SDK-004: browser MCP clients can only keep a session if CORS exposes
    the Mcp-Session-Id response header."""
    from starlette.middleware.cors import CORSMiddleware

    app = server.build_http_app(transport)
    cors = [m for m in app.user_middleware if m.cls is CORSMiddleware]
    assert cors, "CORS middleware is not configured on the HTTP app"
    assert "Mcp-Session-Id" in cors[0].kwargs.get("expose_headers", [])


@respx.mock
async def test_search_empty_returns_actionable_hint():
    """ARCH-003: a zero-match search returns match_type=none plus a hint,
    never a bare empty list."""
    respx.get(f"{BASE}/search").mock(return_value=httpx.Response(200, json={"data": []}))
    result = await server.search_catalog(query="zzznotathing", language="de")
    assert result.total_matched == 0
    assert result.match_type == "none"
    assert result.hint and "list_datasets" in result.hint


async def test_invalid_id_is_rejected_at_the_boundary():
    """SEC-018 / OBS-001: a malformed id is rejected by the schema before the
    tool body runs, surfaced as a protocol-level tool error."""
    from mcp.server.fastmcp.exceptions import ToolError

    with pytest.raises(ToolError):
        await server.mcp.call_tool("get_dataset", {"dataset_id": "../etc/passwd"})


async def test_unknown_tool_is_a_protocol_error():
    """OBS-001: calling an unknown tool is a protocol error, not a crash."""
    from mcp.server.fastmcp.exceptions import ToolError

    with pytest.raises(ToolError):
        await server.mcp.call_tool("does_not_exist", {})


@respx.mock
async def test_execution_error_surfaces_not_swallowed():
    """OBS-001: an upstream failure is surfaced as an error, not swallowed."""
    respx.get(f"{BASE}/datasets/abc").mock(return_value=httpx.Response(500))
    with pytest.raises(c.UpstreamError):
        await server.get_dataset("abc")


async def test_tool_manifest_matches_committed_lock():
    """SEC-022: the live tool definitions must match tool-definitions.lock.json
    so a silent rug-pull fails CI until the lock is regenerated and reviewed."""
    import json
    from pathlib import Path

    lock_path = Path(__file__).resolve().parent.parent / "tool-definitions.lock.json"
    assert lock_path.exists(), "tool-definitions.lock.json is missing"
    committed = json.loads(lock_path.read_text(encoding="utf-8"))
    live = await server.tool_manifest()
    assert live["combined_sha256"] == committed["combined_sha256"], (
        "Tool definitions changed. Regenerate tool-definitions.lock.json and "
        "note the change in CHANGELOG.md (SEC-022)."
    )
