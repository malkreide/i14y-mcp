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
