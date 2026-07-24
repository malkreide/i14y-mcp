# MCP-Server Audit-Report — `i14y-mcp`

**Audit-Datum:** 2026-07-23
**Skill-Version:** 1.0.0
**Catalog-Version:** ?

---

## 1. Executive Summary

Server `i14y-mcp` wurde gegen 44 anwendbare Best-Practice-Checks geprüft. 22 bestanden, 19 Findings dokumentiert (1 critical, 8 high, 10 medium, 0 low). Production-Readiness: NICHT erreicht — blockierend: SDK-001, SDK-004.

**Production-Readiness:** NO

---

## 2. Profil-Snapshot

| Feld | Wert |
|---|---|
| Server-Name | `i14y-mcp` |
| Audit-Datum | 2026-07-23 |
| Skill-Version | 1.0.0 |
| Catalog-Version | ? |

---

## 3. Applicability

### Status pro Kategorie

| Kategorie | Pass | Fail | Partial | Todo | N/A |
|---|---|---|---|---|---|
| ARCH | 7 | 0 | 4 | 0 | 0 |
| CH | 1 | 0 | 0 | 0 | 0 |
| OBS | 1 | 1 | 2 | 1 | 0 |
| OPS | 2 | 0 | 1 | 0 | 0 |
| SCALE | 1 | 0 | 2 | 2 | 0 |
| SDK | 1 | 2 | 1 | 0 | 0 |
| SEC | 9 | 0 | 6 | 0 | 0 |
| **Total** | **22** | **3** | **16** | **3** | **0** |

---

## 4. Findings-Übersicht

_Policy: `fail-or-partial`_

| ID | Category | Severity | Status |
|---|---|---|---|
| SEC-016 | SEC | critical | partial |
| OBS-001 | OBS | high | partial |
| OBS-002 | OBS | high | partial |
| OPS-003 | OPS | high | partial |
| SDK-001 | SDK | high | fail |
| SDK-004 | SDK | high | fail |
| SEC-018 | SEC | high | partial |
| SEC-021 | SEC | high | partial |
| SEC-022 | SEC | high | partial |
| ARCH-003 | ARCH | medium | partial |
| ARCH-007 | ARCH | medium | partial |
| ARCH-008 | ARCH | medium | partial |
| ARCH-012 | ARCH | medium | partial |
| OBS-003 | OBS | medium | fail |
| SCALE-004 | SCALE | medium | partial |
| SCALE-006 | SCALE | medium | partial |
| SDK-003 | SDK | medium | partial |
| SEC-014 | SEC | medium | partial |
| SEC-015 | SEC | medium | partial |

**Gesamt:** 19 Findings

---

## 5. Detail-Findings

### ARCH-003

## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `ARCH-003` |
| **PDF-Reference** | Sec 2.2 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

`search_catalog` liefert bei null Treffern ein strukturiertes `SearchResult` (`total_matched=0`, `truncated=false`) statt eines leeren Strings oder `[]` — das schlimmste Anti-Pattern wird also vermieden. Es fehlt jedoch jegliche Heuristik: kein `match_type`-Feld (exact/fuzzy/none), kein Vorschlag und kein Handlungshinweis, wenn die Suche leer bleibt.

### Expected Behavior

Bei leeren Treffern soll der Server dem Agenten einen verwertbaren nächsten Schritt geben — z. B. ein `match_type`-Feld und einen Hinweis wie «keine Volltext-Treffer; `list_datasets` deckt das vollständige Register ab» (der Server kennt diese Limitation bereits, siehe README).

### Evidence

- src/i14y_mcp/server.py:118-126 — empty search returns a structured SearchResult (total_matched/returned/truncated) not a bare '[]' or 'No results found' string, avoiding the worst anti-pattern
- src/i14y_mcp/server.py:489-521 — api_status deliberately returns an evaluable state so an agent can distinguish 'no data matched' from 'source down'

### Risk Description

Der Agent erhält bei null Treffern keine Orientierung und bricht die Recherche womöglich ab, obwohl `list_datasets` das vollständige Register abdeckt — vermeidbare Sackgasse.

### Remediation

1. `SearchResult` (models.py) um `hint: str | None` und optional `match_type` erweitern.
2. In `search_catalog` bei `total_matched == 0` einen Hinweis auf `list_datasets` setzen.
3. Unit-Test für den Leer-Treffer-Pfad ergänzen.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`ARCH-003`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### ARCH-007

## Finding: ARCH-007 — Capability-Aggregation: Composability intern, Atomarität extern

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `ARCH-007` |
| **PDF-Reference** | Sec 2.3 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Tools liefern gedanklich vollständige Objekte (Titel, Publisher, Themen, Landing-Page), nicht bloss IDs — das Fail-Pattern «nur ID zurückgeben» wird vermieden. Es gibt jedoch keine interne Aggregation mehrerer Quellen und kein `asyncio.gather`; die dokumentierte Anchor-Query braucht drei sequenzielle Calls (search → distributions → dataset).

### Expected Behavior

Häufige Use-Cases sollen in möglichst wenige Tool-Calls (Ziel ≤2) gebündelt werden, indem der Server intern zusammengehörige Fetches aggregiert.

### Evidence

- src/i14y_mcp/server.py:71-126 — search_catalog returns thought-complete hits (title, publisher, themes, landing_page), not bare IDs, so it beats the 'returns only an ID' fail pattern
- src/i14y_mcp/server.py:190-213 — get_dataset_distributions internally re-shapes the dataset detail into a distributions-focused result

### Risk Description

Mehr Round-Trips erhöhen Latenz und Token-Verbrauch pro Recherche; bei vielen Nutzern summiert sich das spürbar.

### Remediation

1. Optional ein aggregierendes Tool `get_dataset_bundle(dataset_id)` anbieten, das Detail + Distributions in einem Call liefert (intern `asyncio.gather`).
2. Alternativ als bewusste Design-Entscheidung dokumentieren (Atomarität vor Bequemlichkeit) und als accepted-risk schliessen.

### Effort Estimate

**M** (1–3 Tage, mehrere Dateien / Tests)

### Verification After Fix

- Re-Audit dieses Checks (`ARCH-007`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### ARCH-008

## Finding: ARCH-008 — Drei Primitive nutzen: Tools, Resources und Prompts

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `ARCH-008` |
| **PDF-Reference** | Anhang A2 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Der Server nutzt ausschliesslich das Tools-Primitiv; `@mcp.resource` und `@mcp.prompt` kommen nicht vor. Alle 13 Tools sind read-only/idempotent und damit gute Resource-Kandidaten. Eine dokumentierte Begründung für die Tools-only-Wahl fehlt im README.

### Expected Behavior

Ein Server nutzt entweder ≥2 der drei Primitive (Tools, Resources, Prompts) oder begründet die Beschränkung explizit in der Doku.

### Evidence

- src/i14y_mcp/server.py — only the Tools primitive is used; grep for @mcp.resource and @mcp.prompt returns zero matches
- All 13 tools are read-only/idempotent/side-effect-free (server.py:50,71+), i.e. strong Resources-migration candidates

### Risk Description

Rein kosmetisch/architektonisch: reine Tools-Nutzung ist funktional korrekt, aber ohne dokumentierte Rationale bleibt unklar, ob es eine Design-Entscheidung oder ein Versäumnis ist.

### Remediation

1. Kurzen Abschnitt «MCP-Primitive — bewusst nur Tools» in README.md/README.de.md ergänzen (Begründung: dynamische Katalog-Abfragen passen schlecht auf statische Resources).
2. Optional stabile Einstiegspunkte (z. B. Theme-Liste) als Resource anbieten.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`ARCH-008`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### ARCH-012

## Finding: ARCH-012 — protocolVersion-Pinning + CHANGELOG + SDK-Update-Disziplin

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `ARCH-012` |
| **PDF-Reference** | Anhang A9 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

CHANGELOG (Keep-a-Changelog/SemVer) und Dependabot für den mcp-SDK sind vorhanden. Die MCP-`protocolVersion` wird jedoch nirgends gepinnt (`server.py:45` ist `FastMCP("i14y-mcp")` ohne Version), und README enthält keinen Abschnitt zur Protokoll-Version bzw. Update-Policy.

### Expected Behavior

Die unterstützte MCP-Protokoll-Version soll nachvollziehbar sein (Pin oder dokumentiert), und Spec-Bumps sollen im CHANGELOG als potenzielle Breaking-Changes geführt werden.

### Evidence

- CHANGELOG.md:1-5 — present and in Keep-a-Changelog + SemVer format with Unreleased/0.1.0 entries
- .github/dependabot.yml:4-10 — monthly pip updates active, comment explicitly names 'the mcp SDK — keep protocol support current'

### Risk Description

Bei einem MCP-Spec-Bump kann sich das Verhalten unbemerkt ändern; ohne dokumentierte Version ist die Kompatibilitäts-Matrix für Betreiber unklar.

### Remediation

1. In README einen Abschnitt «MCP Protocol Version» mit der getesteten SDK-/Spec-Version aufnehmen.
2. SDK-Bumps im CHANGELOG kennzeichnen, wenn sie die Spec-Version anheben.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`ARCH-012`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### OBS-001

## Finding: OBS-001 — Protocol vs. Execution Errors: korrekte Trennung

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `OBS-001` |
| **PDF-Reference** | Sec 6.1 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

`api_status` trennt Execution-Errors sauber und degradiert graziös; `client.py` unterscheidet `NotFoundError` (404) von `UpstreamError` (5xx/429/Netz). Die übrigen Tools lassen diese Exceptions jedoch propagieren und verlassen sich auf FastMCPs Default-`isError`-Wrapping statt explizit `isError:true` mit Handlungshinweis zurückzugeben; ein Protocol-Error-Test fehlt.

### Expected Behavior

Execution-Errors sollen als strukturierte `isError:true`-Ergebnisse mit verwertbarer Guidance zurückkommen, Protocol-Errors über die JSON-RPC-Fehlercodes — beide sauber getrennt und getestet.

### Evidence

- src/i14y_mcp/server.py:489-521 api_status catches UpstreamError/NotFoundError and degrades gracefully (returns StatusResult reachable=False) instead of raising — the correct execution-error pattern
- src/i14y_mcp/client.py:35-41,83-104 separates NotFoundError (404) from UpstreamError (5xx/429/network) — distinct, deterministic error taxonomy
- tests/test_tools.py:142-148 (test_api_status_reports_failure_gracefully) covers the execution-error/degradation path; tests/test_client.py:61-84 cover 404 vs 400 vs 429 handling

### Risk Description

Der Agent erhält bei Upstream-Fehlern eine generische Exception ohne Handlungshinweis, was Selbstheilung (Retry, Fallback auf `list_datasets`) erschwert.

### Remediation

1. In den Tools `UpstreamError`/`NotFoundError` fangen und ein strukturiertes Fehlerergebnis mit Hinweis zurückgeben (analog zu `api_status`).
2. Test ergänzen, der `isError:true` für einen fehlschlagenden Tool-Call assertet.

### Effort Estimate

**M** (1–3 Tage, mehrere Dateien / Tests)

### Verification After Fix

- Re-Audit dieses Checks (`OBS-001`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### OBS-002

## Finding: OBS-002 — Mask Error Details: keine Stacktraces / SQL ans LLM

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `OBS-002` |
| **PDF-Reference** | Sec 6.2 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Keine `traceback.format_exc()`/`sys.exc_info()`-Leaks im Code. FastMCP wird aber ohne `mask_error_details=True` initialisiert (`server.py:45`), und Fehlermeldungen betten rohe Upstream-Bodies ein (`client.py:95` `exc.response.text[:300]`, `server.py:509` `str(exc)[:160]`).

### Expected Behavior

Die primäre Masking-Kontrolle (`mask_error_details=True`) soll aktiv sein; rohe Upstream-Texte gehören nicht ungefiltert an den Client.

### Evidence

- No traceback.format_exc()/sys.exc_info() anywhere in src/ (grep returns nothing) — no stack-trace leakage into tool results
- Read-only, no-auth public-data server: no credentials/tokens exist to leak and no PII is handled, so the disclosure blast radius is minimal

### Risk Description

Geringes Risiko, da Upstream öffentlich und kein Secret/PII vorhanden ist — dennoch verletzt das rohe Durchreichen das Mask-Prinzip und kann interne Fehlerdetails der API exponieren.

### Remediation

1. `FastMCP("i14y-mcp", mask_error_details=True)` setzen.
2. Upstream-Bodies vor dem Weiterreichen kürzen/generalisieren (statt `response.text[:300]` einen kategorisierten Fehlertext).

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`OBS-002`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### OBS-003

## Finding: OBS-003 — Structured Logging mit RFC 5424 Severity-Stufen

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `OBS-003` |
| **PDF-Reference** | Sec 6.3 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | fail |

### Observed Behavior

Der Server hat **kein** Logging: `pyproject.toml` listet nur mcp/httpx/pydantic, und ein grep über `src/` findet weder `logging` noch `structlog`/`loguru`. Es gibt keine strukturierten Logs, keine RFC-5424-Severity-Stufen und keinen per-Tool-Kontext (Tool-Name, Session-, Correlation-ID).

### Expected Behavior

Der Server soll strukturierte Logs (JSON/logfmt) mit Severity-Stufen und per-Tool-gebundenem Kontext ausgeben — ausschliesslich auf stderr (stdout bleibt dem Protokoll vorbehalten).

### Evidence

- No structured-logging dependency: pyproject.toml:24-28 lists only mcp, httpx, pydantic — no structlog/loguru
- No logging at all in src/: grep for logging/structlog/logger/loguru across src/ returns nothing

### Risk Description

Ohne Logs ist keine Observability in Tool-Aufrufe möglich: Fehlerdiagnose, Nutzungsanalyse und Incident-Forensik im Cloud-Betrieb sind blind.

### Remediation

1. `structlog` (oder stdlib `logging` mit JSON-Formatter) als Dependency ergänzen.
2. Handler auf `sys.stderr` konfigurieren (nie stdout — siehe OBS-004).
3. Pro Tool-Call Name + Dauer + Ergebnisgrösse loggen, Level nach RFC 5424.

### Effort Estimate

**M** (1–3 Tage, mehrere Dateien / Tests)

### Verification After Fix

- Re-Audit dieses Checks (`OBS-003`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### OPS-003

## Finding: OPS-003 — Phasenarchitektur: Read-only First, dann Write, dann Multi-Agent

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `OPS-003` |
| **PDF-Reference** | Anhang C4 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Substanziell ein sauberer Phase-1-Read-only-Wrapper (alle Tools `readOnlyHint:true`, keine Write/Send/Filesystem-Tools). Eine **explizite** Phasen-Deklaration fehlt jedoch: kein Phase-Abschnitt/Status-Table im README, kein `docs/roadmap.md`, keine Phase-Verfolgung im CHANGELOG.

### Expected Behavior

Die Phasenarchitektur (Read-only First → Write → Multi-Agent) soll explizit dokumentiert sein, inkl. aktueller Phase und Voraussetzungen für den Übergang.

### Evidence

- Substantively a clean Phase-1 read-only wrapper: all 13 tools readOnlyHint:true/destructiveHint:false (server.py:50), zero write/send/filesystem tools; no destructiveHint:true anywhere
- README.md:119-120 and SECURITY.md:5,16-18 state the read-only, no-write posture; docs/probe-i14y.md:23 references the 'No-Auth-First-Prinzip für Phase 1'
- api_status note (server.py:517-520) documents that write operations are deliberately not exposed

### Risk Description

Ohne dokumentierte Phase ist für Betreiber/Contributor unklar, welche Erweiterungen zulässig sind und welche Sicherheits-Voraussetzungen ein Write-Modus hätte.

### Remediation

1. `docs/roadmap.md` mit Phasen-Definition und -Voraussetzungen anlegen.
2. Kurzen «Project phase: Phase 1 (read-only)»-Hinweis in README aufnehmen.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`OPS-003`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### SCALE-004

## Finding: SCALE-004 — Containerization mit Multi-Stage-Builds

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SCALE-004` |
| **PDF-Reference** | Sec 5.3 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Der Dockerfile ist ein sauberer Multi-Stage-Build (builder/runtime, `python:3.14-slim`, Non-Root-User `mcp`, venv-only Runtime). Es fehlt jedoch eine `HEALTHCHECK`-Direktive (weder im Dockerfile noch in compose.yaml), und die Ziel-Imagegrösse (<200 MB) ist nicht verifiziert.

### Expected Behavior

Container für LB-Integration sollen einen `HEALTHCHECK` definieren, damit Orchestratoren Unhealthy-Instanzen erkennen.

### Evidence

- Dockerfile:3,19 has two FROM stages named 'builder' and 'runtime' (multi-stage build)
- Dockerfile:3,19 both use python:3.14-slim base (slim, not full)
- Dockerfile:28-34 creates a dedicated system user 'mcp' and runs USER mcp (non-root); the venv is copied with --chown=mcp:mcp so the runtime ships no build tools

### Risk Description

Ohne Healthcheck kann ein Load Balancer / Orchestrator einen hängenden Container nicht aussteuern; Requests laufen weiter in eine tote Instanz.

### Remediation

1. `HEALTHCHECK` ergänzen, der den SSE-Endpunkt bzw. einen Liveness-Pfad prüft, oder
2. in compose.yaml einen `healthcheck:`-Block mit `test`/`interval`/`timeout` definieren.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`SCALE-004`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### SCALE-006

## Finding: SCALE-006 — Resource-Limits per Container (Memory, CPU, FDs)

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SCALE-006` |
| **PDF-Reference** | Sec 5.3 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

compose.yaml setzt `mem_limit: 256m`, `cpus: 0.5`, `pids_limit: 128` und `restart: unless-stopped` — gute Basis. Es fehlen ein FD-Limit (`ulimits.nofile`, empfohlen ≥4096 für ausgehende HTTP-Verbindungen) und Reservations/Requests (kein Burst-Headroom); OOM-/Restart-Verhalten ist nicht laufzeit-getestet.

### Expected Behavior

Container sollen zusätzlich zu Memory/CPU auch File-Descriptor-Limits und Reservations (requests < limits) definieren.

### Evidence

- compose.yaml:16-17 sets mem_limit: 256m and cpus: 0.5 — explicit memory and CPU limits
- compose.yaml:18 pids_limit: 128 caps process count and compose.yaml:19 restart: unless-stopped provides a restart policy for clean recovery after an OOM kill

### Risk Description

Unter Last können ausgehende HTTP-Verbindungen das Default-FD-Limit erschöpfen; ohne Reservations fehlt planbares Burst-Headroom.

### Remediation

1. `ulimits: { nofile: { soft: 4096, hard: 8192 } }` in compose.yaml ergänzen.
2. Optional `deploy.resources.reservations` (bzw. Plattform-Requests) definieren.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`SCALE-006`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### SDK-001

## Finding: SDK-001 — FastMCP Lifespan via @asynccontextmanager + AsyncExitStack

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SDK-001` |
| **PDF-Reference** | Sec 3.1 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | fail |

### Observed Behavior

`server.py:45` initialisiert `FastMCP("i14y-mcp")` **ohne** `lifespan=`. Jeder Tool-Call öffnet über `async with build_client()` einen frischen `httpx.AsyncClient` (`client.py:63-69`, Docstring «Caller owns the lifecycle»). Es gibt keinen `@asynccontextmanager`-Lifespan und kein Connection-Pooling über Requests hinweg — genau das vom Check markierte Anti-Pattern.

### Expected Behavior

Langlebige Ressourcen (HTTP-Client mit Connection-Pool) sollen einmalig in einem FastMCP-Lifespan via `@asynccontextmanager` (+ `AsyncExitStack`) aufgebaut und über `server.state` geteilt werden.

### Evidence

- server.py:53 `mcp = FastMCP("i14y-mcp")` — constructor receives no `lifespan=` argument.
- No `@asynccontextmanager` / `AsyncExitStack` anywhere in src/ (grep returned no matches).
- server.py:64-66 `_get()` does `async with build_client() as http:` — a fresh httpx.AsyncClient is created and torn down per tool call.
- client.py:63-69 `build_client()` returns a new `httpx.AsyncClient(...)` with docstring 'Caller owns the lifecycle.' — no shared/pooled client.
- server.py:api_status also opens its own `async with build_client() as http:` per call.

### Risk Description

Ein neuer Client pro Call verwirft den Connection-Pool und TLS-Session-Reuse: unnötige TCP-/TLS-Handshakes erhöhen Latenz und Ressourcenverbrauch, besonders im Cloud-/SSE-Betrieb mit vielen Aufrufen.

### Remediation

1. Lifespan-Funktion mit `@asynccontextmanager` definieren, die einen `httpx.AsyncClient` erzeugt und beim Shutdown schliesst.
2. `FastMCP("i14y-mcp", lifespan=lifespan)` setzen; Client aus `ctx.request_context.lifespan_context` beziehen statt pro Call neu zu bauen.
3. `build_client()` auf den Lifespan umstellen; Tests auf den geteilten Client anpassen.

### Effort Estimate

**M** (1–3 Tage, mehrere Dateien / Tests)

### Verification After Fix

- Re-Audit dieses Checks (`SDK-001`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### SDK-003

## Finding: SDK-003 — Context Injection für Progress Reports und Logging

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SDK-003` |
| **PDF-Reference** | Sec 3.1 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Kein Tool deklariert `ctx: Context`; `Context` wird nie importiert. Damit fehlen `ctx.report_progress`/`ctx.info`/`ctx.error` vollständig. Positiv: keine `print()`/stdlib-Logs in Tool-Bodies (stdio-sicher). Bei `TIMEOUT_S=60` + Backoff 2/4/8 s kann ein degradierter Call die 2-s-Progress-Schwelle ohne jedes Feedback überschreiten.

### Expected Behavior

Tools sollen `Context` injizieren, um clientseitige Logs und Progress-Reports für länger laufende Aufrufe zu liefern.

### Evidence

- No tool declares a `ctx: Context` parameter; `Context` is never imported from `mcp.server.fastmcp` in server.py.
- No `ctx.report_progress`, `ctx.info`, `ctx.warning`, `ctx.error`, `ctx.elicit`, or `ctx.sample` calls anywhere in src/.
- Positive: no `print()` or direct stdlib `logging` inside tool bodies — so the stdio-transport protocol-crash anti-pattern is avoided.
- Tools are single upstream GETs; the only loop is api_status over 3 fixed endpoints (server.py) — no long iteration / gather over many tasks.

### Risk Description

Bei langsamen Upstream-Antworten erhält der Client kein Feedback und kann den Call fälschlich als hängend interpretieren.

### Remediation

1. `ctx: Context` in die (potenziell langsamen) Tools aufnehmen.
2. Vor/zwischen Retries `await ctx.report_progress(...)` bzw. `ctx.info(...)` senden.

### Effort Estimate

**M** (1–3 Tage, mehrere Dateien / Tests)

### Verification After Fix

- Re-Audit dieses Checks (`SDK-003`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### SDK-004

## Finding: SDK-004 — CORS Mcp-Session-Id Exposure bei HTTP/SSE

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SDK-004` |
| **PDF-Reference** | Sec 3.1 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | fail |

### Observed Behavior

Bei aktivem HTTP/SSE-Transport (`I14Y_MCP_TRANSPORT=sse`) existiert **keinerlei** CORS-Konfiguration: grep nach `CORSMiddleware`/`expose_headers`/`allow_origins` ist leer. `Access-Control-Expose-Headers: Mcp-Session-Id` wird nicht gesetzt, sodass Browser-Clients die Session-ID nicht lesen können.

### Expected Behavior

Für HTTP/SSE soll `Mcp-Session-Id` via `Access-Control-Expose-Headers` (und in `allow_headers`) freigegeben werden, damit Cross-Origin-Browser-Clients Sessions führen können.

### Evidence

- Transport is dual: server.py main() honours `I14Y_MCP_TRANSPORT` and runs `mcp.run(transport="sse")` or `"streamable-http"` — so the HTTP/SSE applies_when is active.
- No CORS configuration exists: grep for `CORSMiddleware|cors|allow_origins|expose_headers|middleware` across src/ returns no matches.
- Server exposes HTTP/SSE via `mcp.run(...)` on `mcp.settings.host`/`port` directly — no custom Starlette/ASGI app, no CORSMiddleware, no `cors_expose_headers` passed to FastMCP.
- No `Access-Control-Expose-Headers: Mcp-Session-Id` is configured anywhere.

### Risk Description

Cross-Origin-Browser-Clients können die Session-ID nicht auslesen → SSE-Sessions brechen im Browser, obwohl serverseitige/stdio-Clients funktionieren (schwer zu diagnostizieren).

### Remediation

1. Beim SSE-/streamable-http-Start CORS so konfigurieren, dass `Mcp-Session-Id` in `expose_headers` und `allow_headers` steht (FastMCP-CORS-Option bzw. ASGI-Middleware).
2. Mit einem Browser-Client oder `curl -I` die `Access-Control-Expose-Headers`-Antwort prüfen.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`SDK-004`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### SEC-014

## Finding: SEC-014 — Tool-Allow-Listing via MCP-Gateway-Pattern

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SEC-014` |
| **PDF-Reference** | Sec 5.3 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Tool-Allow-Listing ist in SECURITY.md explizit als Gateway-/Host-Verantwortung dokumentiert; alle Tools sind `readOnlyHint`, es gibt kein Auth-Modell und keine serverseitigen Rollen. Ein Allow-List-Artefakt bzw. eine serverseitige Gruppenprüfung fehlt (bewusst deferiert).

### Expected Behavior

Tool-Zugriff soll — bei Aggregation hinter einem MCP-Gateway — über eine Allow-List steuerbar sein.

### Evidence

- SECURITY.md:39-41,56 — tool allow-listing / gateway controls explicitly documented as a gateway/host-layer responsibility (accepted portfolio-level risk)
- src/i14y_mcp/server.py:50,71+ — all 13 tools annotated readOnlyHint:true, destructiveHint:false; there are no sensitive/destructive tools to gate
- No auth model exists, so there are no roles/groups to build a server-side allow-list on

### Risk Description

Gering: Für einen read-only Single-Server ohne Auth ist das Risiko minimal; relevant erst bei Aggregation hinter einem gemeinsamen Gateway.

### Remediation

1. Als accepted-risk führen, solange kein Gateway im Einsatz ist (in SECURITY.md dokumentiert).
2. Bei Gateway-Aggregation die Tool-Allow-List des Gateways aktivieren.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`SEC-014`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### SEC-015

## Finding: SEC-015 — Pre-Flight Tool-Poisoning Detection

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SEC-015` |
| **PDF-Reference** | Sec 5.3 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Pre-Flight-Tool-Poisoning-Detection ist in SECURITY.md als Gateway-Aufgabe dokumentiert; Tool-Definitionen sind versioniert, in-repo und PR-reviewt, ohne dynamische/Remote-Registrierung. Eine Detection-Schicht im Repo fehlt (korrekt deferiert).

### Expected Behavior

Vor Tool-Ausführung sollen — auf Gateway-Ebene — Tool-Beschreibungen auf Injection-Marker geprüft werden.

### Evidence

- SECURITY.md:39-41 — tool-poisoning detection documented as a gateway/host responsibility; this server's tool definitions are version-controlled, in-repo, and PR-reviewed with no dynamic or remote tool registration
- src/i14y_mcp/server.py:71-521 — tool descriptions are static in-repo docstrings; no injection markers, no dynamic/remote registration
- This server is a single first-party trusted source, not a gateway aggregating untrusted servers (check's own note: low risk for own-server portfolios)

### Risk Description

Gering für einen First-Party-Single-Server ohne dynamische Tools; relevant bei Aggregation fremder Server hinter einem Gateway.

### Remediation

1. Als accepted-risk führen (dokumentiert in SECURITY.md).
2. Bei Gateway-Betrieb dessen Tool-Poisoning-Detection aktivieren.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`SEC-015`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### SEC-016

## Finding: SEC-016 — 0.0.0.0-Binding-Prevention (NeighborJack)

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SEC-016` |
| **PDF-Reference** | Sec 4 (Empirie 2025) |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Der Default-Transport ist `stdio` (kein Port). Bei SSE ist der **Code-Default** für den Bind jedoch `0.0.0.0` (`server.py:528`, `HOST=os.getenv("HOST", "0.0.0.0")`) statt `127.0.0.1`; `compose.yaml:5` publiziert zudem `8000:8000` auf allen Host-Interfaces. Es gibt keine Warnung, wenn ausserhalb eines Containers an `0.0.0.0` gebunden wird.

### Expected Behavior

Der SSE-Bind soll per Default auf `127.0.0.1` (Loopback) liegen; `0.0.0.0` nur als expliziter Opt-in für Container-Deployments, idealerweise mit stderr-Warnung ausserhalb eines Containers.

### Evidence

- src/i14y_mcp/server.py:526 — default transport is stdio (no port opened at all unless SSE is explicitly enabled), which removes the network surface in the default path
- Dockerfile:24-26 — MCP transport/HOST=0.0.0.0 set explicitly at the container layer (correct place)
- SECURITY.md:29,42-46 — documents that SSE/streamable-http binds HOST default 0.0.0.0, intended for container deployment behind a reverse proxy / gateway; default stdio has no network surface

### Risk Description

Bindet ein lokal (nicht containerisiert) gestarteter SSE-Server versehentlich an `0.0.0.0`, ist er im gesamten LAN erreichbar («NeighborJack») — ein read-only-Server exponiert dann zumindest ungewollt seinen Endpunkt.

### Remediation

1. In `server.py` den `HOST`-Default auf `127.0.0.1` setzen; `0.0.0.0` bleibt via Env expliziter Opt-in (der Dockerfile setzt `HOST=0.0.0.0` bereits bewusst).
2. Optional beim Binden an `0.0.0.0` ausserhalb eines Containers auf stderr warnen.
3. SECURITY.md entsprechend präzisieren.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`SEC-016`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### SEC-018

## Finding: SEC-018 — Input-Validation an Tool-Boundaries (Pydantic strict / Zod)

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SEC-018` |
| **PDF-Reference** | Sec 3 / Sec 4 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

`Language`/`ResourceType` sind `Literal`-Enums, und `_clamp()` begrenzt Pagination/Limits. Die übrigen Inputs sind jedoch einfache `str`/`int` ohne strikte Pydantic-Argument-Schemas: keine `min/max/pattern` auf `query`/UUID-Strings, keine `ge/le` (Zahlen werden geklammert statt abgelehnt), kein `extra=forbid` auf der Input-Seite.

### Expected Behavior

Tool-Inputs sollen an der Boundary strikt validiert werden (Pydantic mit `pattern`/`ge`/`le`, UUID-Typen), sodass ungültige Eingaben abgelehnt statt still korrigiert werden.

### Evidence

- src/i14y_mcp/server.py:47-48 — Language and ResourceType are Literal enums, so language/type args are enum-constrained in the FastMCP-generated JSON schema
- src/i14y_mcp/server.py:57-58,102,150,241,294,339,394,438,473 — _clamp() bounds every pagination/limit value into a valid range (1..100/200/SEARCH_HARD_CAP), preventing negative/huge-range abuse
- src/i14y_mcp/models.py:25 etc. — output models use ConfigDict(extra='forbid'); FastMCP derives input schemas from the typed tool signatures
- src/i14y_mcp/client.py:82 — params passed via httpx (URL-encoded); no SQL/shell sink

### Risk Description

Ohne strikte Boundary-Validierung können fehlerhafte IDs/Parameter unbemerkt an die Upstream-API durchgereicht werden; Defense-in-Depth fehlt eine Schicht.

### Remediation

1. Für Pfad-IDs `uuid.UUID`-Typ bzw. ein `pattern` verwenden statt freiem `str`.
2. Numerische Parameter mit `Field(ge=…, le=…)` typisieren (Reject statt Clamp, oder Clamp dokumentiert beibehalten).
3. Wo sinnvoll strikte Pydantic-Input-Modelle mit `extra='forbid'` einsetzen.

### Effort Estimate

**M** (1–3 Tage, mehrere Dateien / Tests)

### Verification After Fix

- Re-Audit dieses Checks (`SEC-018`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### SEC-021

## Finding: SEC-021 — Egress-Allow-List: Code-Layer und Network-Layer

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SEC-021` |
| **PDF-Reference** | Anhang B5 + B12 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Die feste Single-Host-`base_url` (`client.py:15`) wirkt de facto als Code-Layer-Egress auf genau ein Ziel, und SECURITY.md dokumentiert «Fixed HTTPS base URL only». Es fehlen jedoch eine explizite Allow-List (`frozenset` + `assert_host_allowed`), eine Network-Layer-Egress-Kontrolle (keine NetworkPolicy/Security-Group) und `docs/network-egress.md`; `follow_redirects=True` ist nicht host-beschränkt.

### Expected Behavior

Egress soll auf zwei Ebenen kontrolliert sein: Code-Layer (Host-Allow-List, geprüfte Redirects) und Network-Layer (NetworkPolicy/Egress-Firewall), plus Doku.

### Evidence

- src/i14y_mcp/client.py:15,57-58 — BASE_URL is hardcoded to a single host and set as httpx base_url; effectively a single-destination egress constraint at the code layer (no other host is reachable via user input)
- SECURITY.md:22 — documents 'Fixed HTTPS base URL to api.i14y.admin.ch only'
- server.py tools pass only relative paths, so egress targets are constrained to one host by construction

### Risk Description

Ein offener Redirect der Upstream-API könnte den Client (theoretisch) auf einen fremden Host lenken; ohne Network-Layer-Kontrolle gibt es keine zweite Verteidigungslinie.

### Remediation

1. Host-Allow-List als `frozenset({"api.i14y.admin.ch"})` einführen und Redirect-Ziele dagegen prüfen (oder `follow_redirects=False`).
2. `docs/network-egress.md` mit dem erlaubten Host dokumentieren.
3. Für Cloud-Deployments eine Egress-NetworkPolicy/Security-Group empfehlen.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`SEC-021`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


### SEC-022

## Finding: SEC-022 — Tool-Hash-Pinning + Namespace-Präfix gegen Rug Pull

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SEC-022` |
| **PDF-Reference** | Anhang B4 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Tool-Definitionen sind versioniert, in-repo und PR-reviewt (SECURITY.md), ohne dynamische/Remote-Registrierung. Es fehlt jedoch ein Namespace-Präfix auf den Tool-Namen (`search_catalog`, `list_datasets` … sind generisch → Shadowing-Gefahr im Multi-Server-Gateway), ein Tool-Definition-Hash-Snapshot in der Publish-Pipeline und eine CHANGELOG-Disziplin für Tool-Definition-Änderungen.

### Expected Behavior

Tool-Namen sollen namespaced sein und Tool-Definitionen gegen Rug-Pull über Hash-Pinning + Re-Approval-Disziplin abgesichert werden.

### Evidence

- SECURITY.md:39-41,55-57 — documents that tool definitions are version-controlled, authored in-repo and PR-reviewed, with no dynamic or remote tool registration (mitigates rug-pull); shadowing/allow-listing deferred to gateway
- src/i14y_mcp/server.py:45 — single FastMCP server identity 'i14y-mcp'; all tools declared statically in one reviewed file

### Risk Description

In einem gemeinsamen Gateway können generische Tool-Namen von einem bösartigen Server überschattet werden; ohne Hash-Pinning bleibt eine stille Tool-Definition-Änderung unbemerkt.

### Remediation

1. Optional Namespace-Präfix erwägen (Breaking-Change — nur mit Migrationsnotiz).
2. Einen Tool-Definition-Hash beim Release snapshotten und Änderungen im CHANGELOG kennzeichnen.
3. Für Single-Server-Betrieb als low-impact accepted-risk führen.

### Effort Estimate

**M** (1–3 Tage, mehrere Dateien / Tests)

### Verification After Fix

- Re-Audit dieses Checks (`SEC-022`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


---

## 6. Remediation-Plan

### Empfohlene Reihenfolge

1. **SEC-016** (critical, partial)
2. **OBS-001** (high, partial)
3. **OBS-002** (high, partial)
4. **OPS-003** (high, partial)
5. **SDK-001** (high, fail)
6. **SDK-004** (high, fail)
7. **SEC-018** (high, partial)
8. **SEC-021** (high, partial)
9. **SEC-022** (high, partial)
10. **ARCH-003** (medium, partial)
11. **ARCH-007** (medium, partial)
12. **ARCH-008** (medium, partial)
13. **ARCH-012** (medium, partial)
14. **OBS-003** (medium, fail)
15. **SCALE-004** (medium, partial)
16. **SCALE-006** (medium, partial)
17. **SDK-003** (medium, partial)
18. **SEC-014** (medium, partial)
19. **SEC-015** (medium, partial)

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|
| skill_version | `1.0.0` |
| applies_when_dsl_version | `1.0` |
| policy | `fail-or-partial` |
| audit_date | `2026-07-23` |


_Generated by tools/build_report.py — do not edit by hand._
