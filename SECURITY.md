# Security Policy & Posture

[🇩🇪 Deutsche Version](SECURITY.de.md)

`i14y-mcp` is a **read-only**, **no-auth**, **public-open-data** MCP server.
This document summarises its security posture and how to report a vulnerability.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository, or contact the
maintainer listed in `README.md`. Do not file public issues for exploitable
vulnerabilities.

## Posture summary

All 13 tools only issue read requests against the public I14Y API
(`api.i14y.admin.ch`); there are no write, send, or filesystem capabilities, and
no personal data is processed — the server exposes catalogue metadata only.

| Area | Control |
|---|---|
| Egress | Code-layer allow-list (`frozenset({"api.i14y.admin.ch"})`, not env-configurable) checked before the client is built; `follow_redirects=False` refuses any off-host redirect; no user-supplied URLs, so no SSRF surface. See [`docs/network-egress.md`](docs/network-egress.md) |
| TLS | httpx certificate verification is on by default and never disabled in code |
| Auth / secrets | Unauthenticated public read API — no API keys, tokens or secrets are stored or forwarded. Upstream write endpoints require a Bearer token and are deliberately not exposed |
| Input | Pydantic v2 validation at all tool boundaries; query parameters are URL-encoded and numeric ranges are clamped |
| Tools | All annotated `readOnlyHint: true`, `destructiveHint: false`; no dynamic or remote tool registration |
| Errors | Upstream RFC 7807 error bodies are surfaced as structured data, never silently swallowed; `api_status` always returns an evaluable state |
| Stdout | Reserved for the JSON-RPC stream; the server emits no stray stdout logging |
| Binding | `stdio` by default (no network surface). SSE / streamable-http binds to `HOST`, **default `127.0.0.1` (loopback)**; `0.0.0.0` is an explicit opt-in (the container image sets it deliberately) and prints a stderr warning outside a container |

## Accepted risks (portfolio-level controls)

The following are handled at the MCP gateway / host layer rather than inside
this single server. Residual risk here is low because the server is read-only,
unauthenticated, and reaches only one trusted public-data provider.

- **Session crypto-binding** — not applicable: there is no user identity to bind,
  as the server exposes public data with no authentication.
- **Tool allow-listing & cross-server tool-poisoning detection** (SEC-014,
  SEC-015) — a gateway/host responsibility, accepted as a portfolio-level control.
  This server has no auth model and no roles, so there is nothing to gate
  server-side; its tool definitions are version-controlled, authored in-repo, and
  reviewed via PR, with no dynamic or remote tool registration. As a rug-pull
  guard, a hash snapshot of every tool name, description and input schema is
  committed to [`tool-definitions.lock.json`](tool-definitions.lock.json) and
  checked in CI (SEC-022), so any silent change to a tool definition fails the
  build. When aggregated behind a shared gateway, enable the gateway's tool
  allow-listing and tool-poisoning detection.
- **Network binding for hosted deployments** — the SSE / streamable-http
  transport binds to `HOST`, defaulting to `127.0.0.1` (loopback). Binding to
  `0.0.0.0` is an explicit opt-in (the container image sets it on purpose) and
  emits a stderr warning outside a container. Front any `0.0.0.0` deployment with
  a reverse proxy / gateway that enforces TLS and access control; the default
  transport (`stdio`) has no network surface at all. When served over HTTP, CORS
  exposes only the `Mcp-Session-Id` response header (required by browser MCP
  clients).

## Re-evaluation triggers

Revisit these acceptances if the server ever:

- gains **write** capability or starts processing **PII**, or
- adds an **authentication** model (then implement bound, TTL'd,
  server-side-invalidated session IDs and re-audit before merge), or
- registers tools **dynamically** / from remote sources, or
- is aggregated behind a shared MCP gateway (then enable the gateway's tool
  allow-listing and tool-poisoning detection).
