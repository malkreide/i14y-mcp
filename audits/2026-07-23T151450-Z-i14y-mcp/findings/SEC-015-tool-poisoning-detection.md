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
