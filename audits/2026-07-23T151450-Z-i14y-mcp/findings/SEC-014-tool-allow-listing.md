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
