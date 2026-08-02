# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.1] - 2026-08-02

### Fixed

- **`structlog` carried no upper bound, and the index already serves a major past
  the floor.** The declared range was `structlog>=24.1`; PyPI has been serving
  `26.1.0`. The artefact does not change — the resolver's answer to the next
  fresh install does, and that is exactly how `swiss-energy-mcp` 0.3.3 became
  uninstallable when `mcp` 2.0.0 removed the module it imported.

  Now `structlog>=24.1,<27`. The bound is measured rather than guessed: this package
  installs and imports against `structlog 26.1.0` today, so the cap admits what
  demonstrably works and stops only the next, unknown major.

A dependency range only reaches users through a new release, hence the
version bump. No code changed.

## [0.3.0] — 2026-08-02

This release exists so that a repair reaches the people running the server:
**the published `0.2.1` cannot be installed any more.** It declares `mcp` with
no upper bound, and `mcp` 2.0.0 removed `mcp.server.fastmcp` — so a fresh
`pip install i14y-mcp` resolves to 2.0.0 and the console script dies on
startup with `ModuleNotFoundError`. Measured against the real artefact in an
empty venv, cold and warm interpreter alike.

The repository has carried the fix since the 2.x migration was merged; it was
simply never released, and `main` kept the same version number as the broken
artefact — so nothing contradicted it.

### Changed (breaking)

- **Migrated to the `mcp` Python SDK 2.x.** The server API moved from
  `mcp.server.fastmcp` to `mcp.server.mcpserver` with no compatibility shim,
  and the dependency is now `mcp>=2.0.0,<3`. The tool surface is unchanged —
  what breaks is embedding this server's Python API and the dependency floor.
  Anyone who must stay on `mcp` 1.x should stay on 0.2.x, and pin an upper
  bound themselves, because the published 0.2.1 has none.

### Fixed

- The dependency on `mcp` carries an upper bound at all. The previous
  unbounded range is what let a new major reach an unchanged artefact: the
  package did not change, the resolver's answer did.

## [0.2.1] — 2026-07-25

Patch release to complete the MCP Registry publish (0.2.0 shipped to PyPI but its
registry entry failed validation).

### Fixed
- Shortened the `server.json` description to ≤100 characters so the MCP Registry
  publish passes its metadata validation (the v0.2.0 registry publish had failed
  on this; PyPI publish succeeded).
- Added the `mcp-name: io.github.malkreide/i14y-mcp` ownership marker to
  `README.md` (the PyPI long-description) so the MCP Registry can validate that
  the PyPI package and the GitHub namespace share an owner. PyPI READMEs are
  immutable per version, so this required a new release to reach PyPI.

### Changed
- `publish.yml` now also accepts `workflow_dispatch`, so the MCP Registry publish
  can be re-run manually (PyPI upload is a no-op via `skip-existing`).

## [0.2.0] — 2026-07-24

First production-ready release. Aligns the repository with the Swiss Public Data
MCP portfolio, runs a full MCP best-practice audit, and remediates all findings.

**Audit verification:** production-ready ✅ — run-id
`2026-07-24T091742-Z-i14y-mcp`, catalog hash `091f446b2796…`, results 36 pass ·
0 fail · 5 non-blocking partials · 3 todo. Details under
[`audits/`](audits/2026-07-24T091742-Z-i14y-mcp/audit-report.md).

### Added
- Portfolio-standard repository scaffolding to align with the other Swiss Public
  Data MCP servers: `Dockerfile`, `compose.yaml`, `claude_desktop_config.json`,
  `.dockerignore`, `.gitignore`, and a `server.json` manifest for the MCP Registry.
- GitHub Actions workflows: `ci.yml` (matrix 3.10–3.13), `live.yml` (scheduled
  live API suite), `publish.yml` (PyPI + MCP Registry via OIDC Trusted Publishing),
  plus `.github/dependabot.yml`.
- Contributor and security documentation: `CONTRIBUTING.md` / `CONTRIBUTING.de.md`,
  `SECURITY.md` / `SECURITY.de.md`, and `PUBLISHING.md`.
- MCP best-practice audit results under `audits/` (44 checks, 19 findings).
- `docs/roadmap.md` documenting the Read-only-First phase architecture (OPS-003).
- `HEALTHCHECK` in the Docker image so orchestrators can detect an unhealthy
  container (SCALE-004).
- Structured JSON logging on stderr via `structlog`, with per-request severity
  levels (OBS-003).
- `Context` injection across all tools for client-visible progress/logging, with
  per-endpoint progress in `api_status` (SDK-003).
- `search_catalog` now returns a `match_type` and an actionable `hint` on an empty
  result instead of a bare empty list (ARCH-003).
- `docs/network-egress.md` documenting the code- and network-layer egress
  controls (SEC-021).
- `tool-definitions.lock.json`, a committed hash snapshot of the tool set and
  each tool's argument surface (names + required), verified by a test as a
  rug-pull guard that is stable across SDK patch upgrades (SEC-022).
- README sections on MCP primitives (tools-only rationale, ARCH-008) and the MCP
  protocol version / update policy (ARCH-012).
- Container FD `ulimits` and a memory reservation in `compose.yaml` (SCALE-006).
- All tool annotations now also set `idempotentHint: true` and
  `openWorldHint: true` (every tool is a side-effect-free GET against an external
  API), alongside the existing `readOnlyHint`/`destructiveHint` (ARCH-009).
- Second audit run under `audits/` confirming production-readiness (36 pass, 5
  residual non-blocking partials, 0 fail).
- Tests for the shared client, error masking, CORS session-header exposure, empty
  search hints, boundary input rejection, egress control and tool-lock integrity.

### Changed
- **HTTP transports now default to `HOST=127.0.0.1` (loopback)** instead of
  `0.0.0.0`; binding to all interfaces is an explicit opt-in and warns on stderr
  outside a container (SEC-016). The Docker image sets `HOST=0.0.0.0` on purpose;
  remote/PaaS deployments must set it explicitly.
- A single pooled `httpx.AsyncClient` is now created once in a FastMCP lifespan and
  reused across tool calls instead of being rebuilt per call (SDK-001).
- Tool arguments now carry strict schema constraints (`ge`/`le`, `min_length`,
  whitelist `pattern` on IDs), so malformed input is rejected at the boundary
  instead of silently clamped (SEC-018).
- The anchor demo query is now answered in two tool calls; `get_dataset` is
  documented as the aggregated detail tool (ARCH-007).

### Fixed
- SSE / streamable-http now sets CORS to expose the `Mcp-Session-Id` header, so
  browser MCP clients keep their session (SDK-004).
- Upstream failures surface actionable execution errors (pointing at
  `api_status` / `search_catalog`), covered by execution- and protocol-error
  tests (OBS-001).

### Security
- Upstream 4xx error bodies are no longer embedded verbatim in client-facing
  errors; a categorised message (HTTP status + path) is surfaced instead (OBS-002).
- Code-layer egress allow-list (`ALLOWED_HOSTS` frozenset) with
  `follow_redirects=False`, refusing any off-host redirect (SEC-021).

## [0.1.0] — 2026-07-21

### Added
- Initial release. 13 read-only tools over the I14Y interoperability platform:
  `search_catalog`, `list_datasets`, `get_dataset`, `get_dataset_distributions`,
  `list_data_services`, `get_data_service`, `list_public_services`,
  `list_concepts`, `get_concept`, `search_codelist_entries`, `list_publishers`,
  `list_catalogs`, `api_status`.
- Dual transport: stdio and streamable-http/SSE via `I14Y_MCP_TRANSPORT`.
- Retry with exponential backoff (2s/4s/8s); 4xx other than 429 fail fast.
- Pydantic v2 response envelope carrying `source` and `provenance`.
- Bilingual documentation (EN/DE) and full probe report in `docs/probe-i14y.md`.

### Known findings
Discovered during the live probe on 2026-07-21. Recorded here so the next
server in the portfolio does not have to rediscover them.

- **The search parameter is `query`, not `q`.** Unknown query parameters are
  silently discarded and the endpoint returns the entire index — a 15 MB
  response with HTTP 200. The API never says no; it says everything.
- **`page` and `pageSize` are ignored on `/api/search`.** The complete result
  set is always returned. Capping must happen client-side.
- **The `types` filter on search only works for `Dataset`.** `Concept`,
  `DataService`, `PublicService` and `MappingTable` are accepted without error
  but yield zero results, although those entities exist.
- **The search index covers about 51 % of the register** (1013 of ~2003
  datasets). Search is the entry point, `list_datasets` the completeness
  guarantee.
- **Multilingual nesting is inconsistent.** Themes wrap their language object
  under `name`, keywords under `label`, titles sit directly as
  `{de, fr, it, en}`. A naive extractor leaks a dict into a string field.
  Caught by a live test, not by unit tests.
- **`endpointUrls` may contain entries without a URI**, carrying only a label
  such as «OpenAPI Spezifikation». These are surfaced, not dropped.
- **`/api/concepts/{id}/codelist-entries` returns 405.** Only the `/search`
  subpath exists, and it requires `language` (HTTP 400 otherwise).
- **Read endpoints need no authentication**, despite the OpenAPI document
  declaring a Bearer scheme. Write endpoints do.

[Unreleased]: https://github.com/malkreide/i14y-mcp/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/malkreide/i14y-mcp/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/malkreide/i14y-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/malkreide/i14y-mcp/releases/tag/v0.1.0
