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
