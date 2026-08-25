"""Inbound Host/Origin validation on the HTTP/SSE transports (SEC-005).

Passing ``transport_security`` is not the difference between protection and
none — it is the difference between the right allow-list and a loopback-only
one, and this file said otherwise.

"This server never set it, so there was no Host check at all" was wrong twice
over. ``sse_app`` / ``streamable_http_app`` synthesise a loopback-only list
when ``transport_security`` is unset and ``host`` is loopback — and ``host``
defaults to ``"127.0.0.1"``. The unwired server therefore had a Host check; it
was simply the wrong one, rejecting every real hostname with 421 and every
configured origin with 403. Only ``TransportSecurityMiddleware(None)``,
constructed directly, disables the check outright — that is the layer the SDK's
"backwards compatibility" note is about.

``test_the_sdk_default_is_loopback_only`` measures both layers rather than
restating them, so the correction cannot rot the way the claim it replaces did.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from i14y_mcp.server import build_transport_security, mcp

_INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
}
_HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


def test_loopback_bind_enables_protection(monkeypatch):
    monkeypatch.delenv("I14Y_MCP_ALLOWED_HOSTS", raising=False)
    sec = build_transport_security("127.0.0.1", 8000)
    assert sec is not None
    assert sec.enable_dns_rebinding_protection is True
    assert "127.0.0.1:8000" in sec.allowed_hosts
    assert "localhost:8000" in sec.allowed_hosts


def test_non_local_bind_without_allowlist_stays_off(monkeypatch):
    """0.0.0.0 with no allow-list: the reachable name is unknowable here, so a
    guess would reject every real request. Protection stays off; caller warns."""
    monkeypatch.delenv("I14Y_MCP_ALLOWED_HOSTS", raising=False)
    assert build_transport_security("0.0.0.0", 8000) is None


def test_non_local_bind_with_allowlist_enables_protection(monkeypatch):
    monkeypatch.setenv("I14Y_MCP_ALLOWED_HOSTS", "mcp.example.ch,mcp.example.ch:443")
    sec = build_transport_security("0.0.0.0", 8000)
    assert sec is not None
    assert "mcp.example.ch" in sec.allowed_hosts
    # Loopback stays in, otherwise container health checks break.
    assert "127.0.0.1:8000" in sec.allowed_hosts


def test_port_is_honoured(monkeypatch):
    monkeypatch.delenv("I14Y_MCP_ALLOWED_HOSTS", raising=False)
    sec = build_transport_security("127.0.0.1", 9443)
    assert "127.0.0.1:9443" in sec.allowed_hosts
    assert "127.0.0.1:8000" not in sec.allowed_hosts


def test_wildcard_is_not_copied_into_allowed_origins(monkeypatch):
    """ "*" is matched literally by the SDK, so copying it would look like a
    wildcard while doing nothing."""
    monkeypatch.delenv("I14Y_MCP_ALLOWED_HOSTS", raising=False)
    sec = build_transport_security("127.0.0.1", 8000)
    assert "*" not in sec.allowed_origins
    # The derived loopback origins must still be present, or a same-host
    # browser request would be refused.
    assert "http://127.0.0.1:8000" in sec.allowed_origins


def _post_with_host(host_header: str):
    # mcp 2.x: transport_security is a per-app kwarg, not a setting.
    with TestClient(
        mcp.streamable_http_app(transport_security=build_transport_security("127.0.0.1", 8000))
    ) as client:
        return client.post("/mcp", headers={"Host": host_header, **_HEADERS}, json=_INIT)


def test_allowed_host_is_served():
    assert _post_with_host("127.0.0.1:8000").status_code == 200


def test_foreign_host_is_rejected():
    assert _post_with_host("evil.example.com").status_code == 421


def test_right_host_wrong_port_is_rejected():
    """The load-bearing case: a fallback localhost policy would also reject
    ``evil.example.com``, so only right-hostname/wrong-port proves the
    port-precise allow-list is really installed."""
    assert _post_with_host("127.0.0.1:9999").status_code == 421


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_all_loopback_forms_are_local(host, monkeypatch):
    monkeypatch.delenv("I14Y_MCP_ALLOWED_HOSTS", raising=False)
    assert build_transport_security(host, 8000) is not None


def test_the_sdk_default_is_loopback_only() -> None:
    """Both layers, measured — the claim this file used to make in prose.

    An unwired app is *not* unprotected. `streamable_http_app` with no
    `transport_security` and no `host` gets the SDK's synthesised loopback-only
    list, so a real hostname is refused with 421 while `127.0.0.1` passes. That
    is what makes an unwired server look fine in local testing and reject every
    browser client in production.

    The second assertion pins the layer the SDK's "backwards compatibility"
    note actually describes: the middleware constructed with `None` really does
    turn the check off. Both are asserted here because conflating them is what
    produced the wrong docstring in the first place.

    A fresh app per request: a `StreamableHTTPSessionManager` starts once per
    app object, and a second lifespan on the same one dies of its own
    RuntimeError rather than on the Host header.
    """
    from mcp.server.transport_security import TransportSecurityMiddleware

    def status(base_url: str) -> int:
        with TestClient(mcp.streamable_http_app(), base_url=base_url) as c:
            return c.post("/mcp", json=_INIT, headers=_HEADERS).status_code

    assert status("http://testserver") == 421, "unwired app accepted a foreign Host"
    assert status("http://127.0.0.1:8000") == 200, "unwired app refused loopback"

    # The other layer, and the one the SDK quote is about.
    assert TransportSecurityMiddleware(None).settings.enable_dns_rebinding_protection is False
