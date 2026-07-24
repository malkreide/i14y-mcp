# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/malkreide/i14y-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/malkreide/i14y-mcp/releases/tag/v0.1.0
