"""Resilience tests: happy path, retry on 503, hard failure on timeout."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

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

    monkeypatch.setattr(c, "_sleep", _instant)


async def test_the_backoff_patch_stops_at_this_module():
    """The autouse patch above must not reach the `asyncio` module itself.

    `monkeypatch.setattr(c.asyncio, "sleep", ...)` reads as a local override but
    replaces `sleep` on the shared module object, for httpx, respx, pytest-asyncio
    and every other importer in the process. A wait that should have been asserted
    then never happens, and the test that was supposed to catch it passes.

    Real clock on purpose: a fake one that only advances when something sleeps
    cannot tell a genuine wait from a disarmed one.
    """
    assert c._sleep.__name__ == "_instant", "the autouse fixture should have patched the alias"
    assert asyncio.sleep is not c._sleep, "the patch leaked into the asyncio module"

    started = time.perf_counter()
    await asyncio.sleep(0.05)
    assert time.perf_counter() - started >= 0.04, "asyncio.sleep no longer waits"


@respx.mock
async def test_retry_asks_for_the_backoff_ladder(monkeypatch):
    """Record the delays the retry requests instead of waiting them out.

    This pins the seam itself. Collapsing the backoff makes the suite fast but
    asserts nothing about it: if `fetch_json` stopped going through the module
    alias, every test here would still pass and only the wall clock would show
    it — 47s instead of 2s, which nobody reads. Here, nothing gets recorded and
    this fails.
    """
    seen: list[float] = []

    async def _record(seconds):
        seen.append(seconds)

    monkeypatch.setattr(c, "_sleep", _record)
    respx.get(f"{BASE}/datasets").mock(return_value=httpx.Response(503))

    async with c.build_client() as http:
        with pytest.raises(c.UpstreamError):
            await c.fetch_json(http, "/datasets")

    assert len(seen) == c.MAX_ATTEMPTS - 1, "one wait between each pair of attempts"
    for i, delay in enumerate(seen):
        base = c.RETRY_BASE_DELAY * 2**i  # 2, 4, 8 before jitter
        low = base * (1.0 - c.RETRY_JITTER_SPREAD)
        high = min(base * (1.0 + c.RETRY_JITTER_SPREAD), c.RETRY_MAX_DELAY)
        assert low <= delay <= high, f"wait {i} was {delay}s, outside [{low}, {high}]"


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
    assert "unreachable" in message
    assert "Last successful call" in message
    assert "ConnectTimeout" in message, "the failure mode has to be named"
    assert "api.i14y.admin.ch" in message, "the host has to be named"


@respx.mock
async def test_an_empty_error_message_still_names_type_and_host():
    """The case that made the old message stop at the colon.

    ``httpx.ConnectTimeout``, ``ReadTimeout`` and ``ConnectError`` all carry an
    EMPTY ``str()`` in the wild — and they are the only errors a real outage
    produces. The message used to interpolate ``{last_error}`` alone and so
    read "Last error: ." naming neither the failure mode nor the host. The test
    above passes ``"timed out"`` as the message, which is exactly why it could
    never catch this: informative in the test, blank in production.
    """
    respx.get(f"{BASE}/datasets").mock(side_effect=httpx.ConnectTimeout(""))
    async with c.build_client() as http:
        with pytest.raises(c.UpstreamError) as exc:
            await c.fetch_json(http, "/datasets")
    message = str(exc.value)
    assert "ConnectTimeout" in message
    assert "api.i14y.admin.ch" in message
    assert "Last error: ." not in message, "the sentence that used to stop short"


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
    respx.get(f"{BASE}/datasets/x").mock(return_value=httpx.Response(400, text=secret_body))
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


def test_egress_allow_list_rejects_foreign_host():
    """SEC-021: only the allow-listed host may be reached."""
    c.assert_host_allowed(c.BASE_URL)  # does not raise
    with pytest.raises(c.UpstreamError):
        c.assert_host_allowed("https://evil.example.com/api")


def test_build_client_does_not_follow_redirects():
    """SEC-021: a redirect must never carry the client off the allow-listed host."""
    client = c.build_client()
    assert client.follow_redirects is False


@respx.mock
async def test_redirect_is_refused():
    """SEC-021: a 3xx from upstream is surfaced as an error, not followed."""
    respx.get(f"{BASE}/datasets").mock(
        return_value=httpx.Response(302, headers={"Location": "https://evil.example.com"})
    )
    async with c.build_client() as http:
        with pytest.raises(c.UpstreamError):
            await c.fetch_json(http, "/datasets")


@respx.mock
async def test_429_is_retried():
    route = respx.get(f"{BASE}/datasets").mock(
        side_effect=[httpx.Response(429), httpx.Response(200, json={"data": []})]
    )
    async with c.build_client() as http:
        await c.fetch_json(http, "/datasets")
    assert route.call_count == 2


# --- Retry policy: Retry-After, jitter, and the cap --------------------------
# Adopted together with the hardened retry from the mcp-data-source-probe
# reference template. These assert the behaviour, not the constants: a
# deterministic ladder and an unread `Retry-After` are what a sweep across
# eleven servers found on 2026-08-03, and every one of them looked fine.


def _retry_after_error(value: str) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.invalid/")
    return httpx.HTTPStatusError(
        "",
        request=request,
        response=httpx.Response(429, headers={"Retry-After": value}, request=request),
    )


def test_retry_after_reads_both_rfc9110_forms() -> None:
    def resp(status: int, headers: dict[str, str]) -> httpx.Response:
        request = httpx.Request("GET", "https://example.invalid/")
        return httpx.Response(status, headers=headers, request=request)

    assert c.parse_retry_after(resp(429, {"Retry-After": "120"})) == 120.0

    later = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=90))
    seconds = c.parse_retry_after(resp(503, {"Retry-After": later}))
    assert seconds is not None and 80 < seconds <= 90

    # A date in the past means "now", never a negative wait.
    past = "Wed, 21 Oct 2020 07:28:00 GMT"
    assert c.parse_retry_after(resp(503, {"Retry-After": past})) == 0.0

    # Unparseable falls back to the curve. It must not crash on the error path,
    # which is the one path already going badly.
    assert c.parse_retry_after(resp(429, {"Retry-After": "bald"})) is None
    assert c.parse_retry_after(resp(429, {})) is None

    # 500 does not carry a meaningful Retry-After.
    assert c.parse_retry_after(resp(500, {"Retry-After": "120"})) is None
    assert c.parse_retry_after(None) is None


def test_backoff_is_jittered() -> None:
    delays = {c.compute_delay(3, None) for _ in range(300)}
    # attempt 3 -> 2 * 2**2 = 8s, spread into [0.5x, 1.5x]
    assert len(delays) > 1, "a deterministic ladder synchronises every client"
    assert min(delays) >= 4.0
    assert max(delays) <= 12.0


def test_cap_binds_after_the_jitter() -> None:
    # Capping first and then multiplying by up to 1.5 would land at 30s, and
    # the constant would claim a ceiling it does not hold.
    deep = {c.compute_delay(9, None) for _ in range(200)}
    assert max(deep) <= c.RETRY_MAX_DELAY

    hinted = _retry_after_error("600")
    assert {c.compute_delay(1, hinted) for _ in range(100)} == {c.RETRY_MAX_DELAY}


def test_retry_after_jitter_is_one_sided() -> None:
    """The source said when. Later is polite; earlier ignores the value read."""
    delays = {c.compute_delay(1, _retry_after_error("4")) for _ in range(300)}
    assert min(delays) >= 4.0, "never earlier than the source asked for"
    assert max(delays) <= 5.0  # 4 * 1.25
