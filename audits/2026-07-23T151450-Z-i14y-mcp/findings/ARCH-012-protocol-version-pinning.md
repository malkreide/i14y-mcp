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
