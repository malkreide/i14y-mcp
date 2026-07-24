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
