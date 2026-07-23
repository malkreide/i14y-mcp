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
