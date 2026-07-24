# MCP-Server Audit-Report — `i14y-mcp`

**Audit-Datum:** 2026-07-24
**Skill-Version:** 1.0.0
**Catalog-Version:** ?

---

## 1. Executive Summary

Server `i14y-mcp` wurde gegen 44 anwendbare Best-Practice-Checks geprüft. 36 bestanden, 5 Findings dokumentiert (0 critical, 3 high, 2 medium, 0 low). Production-Readiness: erreicht.

**Production-Readiness:** YES

---

## 2. Profil-Snapshot

| Feld | Wert |
|---|---|
| Server-Name | `i14y-mcp` |
| Audit-Datum | 2026-07-24 |
| Skill-Version | 1.0.0 |
| Catalog-Version | ? |

---

## 3. Applicability

### Status pro Kategorie

| Kategorie | Pass | Fail | Partial | Todo | N/A |
|---|---|---|---|---|---|
| ARCH | 9 | 0 | 2 | 0 | 0 |
| CH | 1 | 0 | 0 | 0 | 0 |
| OBS | 3 | 0 | 1 | 1 | 0 |
| OPS | 3 | 0 | 0 | 0 | 0 |
| SCALE | 3 | 0 | 0 | 2 | 0 |
| SDK | 3 | 0 | 1 | 0 | 0 |
| SEC | 14 | 0 | 1 | 0 | 0 |
| **Total** | **36** | **0** | **5** | **3** | **0** |

---

## 4. Findings-Übersicht

_Policy: `fail-or-partial`_

| ID | Category | Severity | Status |
|---|---|---|---|
| OBS-002 | OBS | high | partial |
| SDK-004 | SDK | high | partial |
| SEC-022 | SEC | high | partial |
| ARCH-011 | ARCH | medium | partial |
| ARCH-012 | ARCH | medium | partial |

**Gesamt:** 5 Findings

---

## 5. Detail-Findings

### ARCH-011

## Finding: ARCH-011 — Standardisierte Repo-Struktur (src-Layout, tests, README.de.md)

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `ARCH-011` |
| **PDF-Reference** | Anhang A8 |
| **Audit-Datum** | 2026-07-24 |
| **Auditor** | Claude Code (mcp-audit skill, re-audit) |
| **Check-Status** | partial |

### Observed Behavior

Repo-Struktur, src-Layout, bilinguale READMEs, CI und `docs/roadmap.md` sind vollständig vorhanden. Alle 13 Tool-Bodies liegen jedoch weiterhin inline in einer ~730-zeiligen `server.py`; ab >5 Tools erwartet der Check eine Aufteilung in ein `tools/`-Subpackage (oder eine dokumentierte Begründung).

### Expected Behavior

Bei mehr als 5 Tools sollen die Tool-Definitionen in ein `tools/`-Subpackage aufgeteilt werden, damit `server.py` schlank bleibt.

### Evidence

- All mandatory top-level files present: README.md, README.de.md, CHANGELOG.md, LICENSE, pyproject.toml.
- Mandatory directories present: src/, tests/, .github/workflows/.
- Correct src-layout: code under src/i14y_mcp/, and pyproject declares packages = ['src/i14y_mcp'] (pyproject.toml:49-50).
- CI workflows present beyond the minimum: ci.yml (test+lint, 3.10-3.13 matrix), publish.yml (PyPI), live.yml (nightly live).
- README.de.md holds the same top-level section inventory as README.md (verified: matching ## headings for Why/Architecture/Tools/Installation/Join keys/Known limitations/Testing/Contributing/Credits).

### Risk Description

Rein wartungsbezogen: eine grosse Datei erschwert Navigation und Review, ist aber kein Laufzeit- oder Sicherheitsrisiko.

### Remediation

1. Tools thematisch in `src/i14y_mcp/tools/{discovery,services,semantics,actors,ops}.py` aufteilen und in `server.py` registrieren, oder
2. die bewusste Single-File-Struktur (klar sektioniert, 13 kohärente Read-Tools) kurz in `docs/roadmap.md` als Design-Entscheidung festhalten.

### Effort Estimate

**M** (1–3 Tage, mehrere Dateien / Tests)

### Verification After Fix

- Re-Audit dieses Checks (`ARCH-011`) gegen den Katalog
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
| **Audit-Datum** | 2026-07-24 |
| **Auditor** | Claude Code (mcp-audit skill, re-audit) |
| **Check-Status** | partial |

### Observed Behavior

CHANGELOG (Keep-a-Changelog), README-Abschnitt «MCP protocol version», Update-Policy, Dependabot und ein auf `mcp>=1.28.1` gepinnter SDK-Floor sind vorhanden. Eine **literal** in `FastMCP(...)` gepinnte `protocolVersion` gibt es bewusst nicht — der Server verlässt sich auf die SDK-Aushandlung plus den getesteten Floor.

### Expected Behavior

Der Check verlangt eine explizit im Code gepinnte `protocolVersion`. FastMCP handelt die Protokoll-Version jedoch zur Initialize-Zeit mit dem Client aus; ein hartes Pin ist im FastMCP-Modell nicht vorgesehen.

### Evidence

- CHANGELOG.md present and in Keep-a-Changelog format with SemVer statement and Unreleased/0.1.0 sections (CHANGELOG.md:1-105).
- README has an 'MCP protocol version' section describing the SDK floor pin and update policy (README.md:137-143).
- SDK floor pinned in pyproject (mcp>=1.28.1, pyproject.toml:25) and Dependabot configured for monthly pip + actions update PRs (.github/dependabot.yml).
- Update policy documented: monthly Dependabot PRs and CHANGELOG call-out on any negotiated-spec change (README.md:139-143).

### Risk Description

Gering: bei einem Spec-Bump könnte sich das Verhalten ändern — abgefedert durch den gepinnten SDK-Floor, Dependabot-PRs und die dokumentierte Update-Policy.

### Remediation

1. Als bewusste Design-Entscheidung führen (SDK-Aushandlung + SDK-Floor-Pin) und in der README-Sektion so benennen, oder
2. sobald FastMCP ein explizites Protokoll-Pin unterstützt, dieses setzen und im CHANGELOG als Spec-Version-Zeile führen.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`ARCH-012`) gegen den Katalog
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
| **Audit-Datum** | 2026-07-24 |
| **Auditor** | Claude Code (mcp-audit skill, re-audit) |
| **Check-Status** | partial |

### Observed Behavior

Rohe Upstream-Bodies werden bereits an der Quelle maskiert (kategorisierte `HTTP <status>`-Meldungen, keine Stacktraces, stderr-only-Logging). Der namensgebende Schalter `mask_error_details=True` ist jedoch nicht gesetzt — er existiert im `FastMCP(...)`-Konstruktor von `mcp 1.28.1` **nicht** (verifiziert), sodass ein unbehandelter Bug theoretisch noch über `str(exc)` an den Client gelangen könnte.

### Expected Behavior

FastMCP soll mit `mask_error_details=True` initialisiert werden, damit unerwartete Exceptions nicht im Klartext an den Client gehen.

### Evidence

- No raw upstream body, stacktrace, SQL or path leaks: fetch_json categorises 4xx/5xx into clean UpstreamError text (client.py:163-172, OBS-002 comment at :168-169); no traceback.format_exc / sys.exc_info anywhere in src/
- Execution errors carry user-friendly, internals-free messages (client.py:148-151, 184-189)
- Logs are stderr-only structured JSON with no tokens/PII (no-auth server; logging_config.py)

### Risk Description

Gering für diesen Server: read-only, no-auth, keine Secrets/PII. Das Restrisiko ist eine mögliche Offenlegung interner Fehlertexte bei einem unerwarteten Bug.

### Remediation

1. Sobald die verwendete mcp-SDK-Version `mask_error_details` unterstützt, im `FastMCP(...)`-Aufruf setzen.
2. Bis dahin bleibt die Quell-Maskierung (client.py) die wirksame Kontrolle; ggf. einen dünnen Exception-Wrapper um die Tools ergänzen.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`OBS-002`) gegen den Katalog
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
| **Audit-Datum** | 2026-07-24 |
| **Auditor** | Claude Code (mcp-audit skill, re-audit) |
| **Check-Status** | partial |

### Observed Behavior

Der ursprüngliche Blocker ist behoben: `build_http_app()` exponiert `Mcp-Session-Id` via CORS, sodass Browser-Clients ihre Session behalten. `allow_origins=["*"]` ist jedoch hartkodiert und nicht env-gesteuert/produktiv einschränkbar — dieses Pass-Kriterium bleibt offen (abgefedert dadurch, dass der Server no-auth ist und kein `allow_credentials` setzt).

### Expected Behavior

Die erlaubten CORS-Origins sollen konfigurierbar sein, damit produktive Deployments sie einschränken können.

### Evidence

- build_http_app() (server.py:674-693) builds the SSE/streamable-http ASGI app itself and adds CORSMiddleware because FastMCP.run() serves without CORS.
- expose_headers=["Mcp-Session-Id"] is set (server.py:691) — the critical header exposure that lets browser clients read the session id is present.
- allow_headers=["*", "Mcp-Session-Id"] includes Mcp-Session-Id for follow-up requests; allow_methods includes GET/POST/DELETE/OPTIONS.
- No allow_credentials=True is set and the server is no-auth, so the wildcard-origin + credentials CORS-spec violation does not arise.

### Risk Description

Gering: ohne Auth/Credentials ist ein permissiver CORS-Origin für öffentliche Read-Daten unkritisch; in geschlossenen Deployments ist eine Einschränkung dennoch wünschenswert.

### Remediation

1. Origins aus einer Env-Var lesen (z. B. `I14Y_MCP_CORS_ORIGINS`, Default `*`) und an `allow_origins` übergeben.
2. In README/SECURITY dokumentieren, wie produktive Deployments die Origins einschränken.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`SDK-004`) gegen den Katalog
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
| **Audit-Datum** | 2026-07-24 |
| **Auditor** | Claude Code (mcp-audit skill, re-audit) |
| **Check-Status** | partial |

### Observed Behavior

Hash-Pinning ist sauber umgesetzt: `tool-definitions.lock.json` + CI-Test schützen vor stillen Signatur-Änderungen. Zwei Rest-Gaps bleiben: (1) die Tool-Namen tragen **kein** Server-Identity-Präfix (`get_dataset`, `search_catalog` statt `i14y__…`), sodass Shadowing hinter einem gemeinsamen Gateway nicht strukturell verhindert wird; (2) der Lock-Hash schliesst die Descriptions bewusst aus (Stabilität über SDK-Versionen), sodass ein reiner Description-Rug-Pull nur per PR-Review erkannt wird.

### Expected Behavior

Tool-Namen sollen namespaced sein (`<server>__<tool>`) und Tool-Definitionen gegen Rug-Pull abgesichert werden.

### Evidence

- Hash-pinning is implemented and enforced: tool_manifest() produces a deterministic sha256 over tool name + argument names + required set, committed to tool-definitions.lock.json (13 tools) and checked in CI by test_tool_manifest_matches_committed_lock (server.py:625-666; tests/test_tools.py).
- CHANGELOG documents the lock and the rug-pull guard rationale (CHANGELOG SEC-022 entry); SECURITY.md describes it as the rug-pull control.
- Tool definitions are static/in-repo with no dynamic or remote registration.

### Risk Description

Gering im Single-Server-Betrieb; relevant erst bei Aggregation fremder Server hinter einem gemeinsamen Gateway (dann greift dessen Namespacing/Allow-Listing).

### Remediation

1. Optional Namespace-Präfix (`i14y__…`) einführen — Breaking-Change, nur mit Major-Bump + Migrationsnotiz im CHANGELOG.
2. Für Single-Server-Betrieb als low-impact accepted-risk führen (der Lock deckt Namen + Argument-Vertrag bereits ab; Description-Änderungen laufen über PR-Review).

### Effort Estimate

**M** (1–3 Tage, mehrere Dateien / Tests)

### Verification After Fix

- Re-Audit dieses Checks (`SEC-022`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)


---

## 6. Remediation-Plan

### Empfohlene Reihenfolge

1. **OBS-002** (high, partial)
2. **SDK-004** (high, partial)
3. **SEC-022** (high, partial)
4. **ARCH-011** (medium, partial)
5. **ARCH-012** (medium, partial)

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|
| skill_version | `1.0.0` |
| applies_when_dsl_version | `1.0` |
| policy | `fail-or-partial` |
| audit_date | `2026-07-24` |


_Generated by tools/build_report.py — do not edit by hand._
