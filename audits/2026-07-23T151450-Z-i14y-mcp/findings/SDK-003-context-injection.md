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
