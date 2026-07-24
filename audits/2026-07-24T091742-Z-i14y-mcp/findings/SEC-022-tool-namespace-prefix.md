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
