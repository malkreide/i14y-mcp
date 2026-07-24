"""Resilience tests: happy path, retry on 503, hard failure on timeout."""

from __future__ import annotations

import httpx
import pytest
import respx

from i14y_mcp import client as c

BASE = c.BASE_URL


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Collapse the exponential backoff so tests run instantly."""

    async def _instant(_seconds):
        return None

    monkeypatch.setattr(c.asyncio, "sleep", _instant)


@respx.mock
async def test_happy_path_returns_unwrapped_data():
    respx.get(f"{BASE}/datasets").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "abc"}]})
    )
    async with c.build_client() as http:
        payload = await c.fetch_json(http, "/datasets")
    assert c.unwrap(payload) == [{"id": "abc"}]


@respx.mock
async def test_retries_on_503_then_succeeds():
    route = respx.get(f"{BASE}/datasets").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(200, json={"data": []}),
        ]
    )
    async with c.build_client() as http:
        payload = await c.fetch_json(http, "/datasets")
    assert route.call_count == 3
    assert c.unwrap(payload) == []


@respx.mock
async def test_network_error_raises_upstream_error_with_context():
    respx.get(f"{BASE}/datasets").mock(side_effect=httpx.ConnectTimeout("timed out"))
    async with c.build_client() as http:
        with pytest.raises(c.UpstreamError) as exc:
            await c.fetch_json(http, "/datasets")
    message = str(exc.value)
    assert "unreachable after" in message
    assert "Last successful call" in message


@respx.mock
async def test_404_raises_not_found_without_retrying():
    route = respx.get(f"{BASE}/datasets/missing").mock(return_value=httpx.Response(404))
    async with c.build_client() as http:
        with pytest.raises(c.NotFoundError):
            await c.fetch_json(http, "/datasets/missing")
    assert route.call_count == 1


@respx.mock
async def test_400_is_not_retried():
    route = respx.get(f"{BASE}/concepts/x/codelist-entries/search").mock(
        return_value=httpx.Response(400, json={"title": "language is required"})
    )
    async with c.build_client() as http:
        with pytest.raises(c.UpstreamError):
            await c.fetch_json(http, "/concepts/x/codelist-entries/search")
    assert route.call_count == 1


@respx.mock
async def test_4xx_error_masks_raw_upstream_body():
    """OBS-002: the client-facing error must not leak the raw upstream body."""
    secret_body = "SECRET internal stack detail that must not reach the LLM"
    respx.get(f"{BASE}/datasets/x").mock(
        return_value=httpx.Response(400, text=secret_body)
    )
    async with c.build_client() as http:
        with pytest.raises(c.UpstreamError) as exc:
            await c.fetch_json(http, "/datasets/x")
    message = str(exc.value)
    assert secret_body not in message
    assert "HTTP 400" in message


async def test_client_session_reuses_shared_client():
    """SDK-001: with a shared client installed, client_session reuses it."""
    sentinel = object()
    c.set_shared_client(sentinel)  # type: ignore[arg-type]
    try:
        async with c.client_session() as http:
            assert http is sentinel
    finally:
        c.set_shared_client(None)
    assert c.get_shared_client() is None


@respx.mock
async def test_429_is_retried():
    route = respx.get(f"{BASE}/datasets").mock(
        side_effect=[httpx.Response(429), httpx.Response(200, json={"data": []})]
    )
    async with c.build_client() as http:
        await c.fetch_json(http, "/datasets")
    assert route.call_count == 2
