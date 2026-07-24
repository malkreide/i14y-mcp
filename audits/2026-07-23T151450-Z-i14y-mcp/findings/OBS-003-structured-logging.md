## Finding: OBS-003 — Structured Logging mit RFC 5424 Severity-Stufen

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `OBS-003` |
| **PDF-Reference** | Sec 6.3 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | fail |

### Observed Behavior

Der Server hat **kein** Logging: `pyproject.toml` listet nur mcp/httpx/pydantic, und ein grep über `src/` findet weder `logging` noch `structlog`/`loguru`. Es gibt keine strukturierten Logs, keine RFC-5424-Severity-Stufen und keinen per-Tool-Kontext (Tool-Name, Session-, Correlation-ID).

### Expected Behavior

Der Server soll strukturierte Logs (JSON/logfmt) mit Severity-Stufen und per-Tool-gebundenem Kontext ausgeben — ausschliesslich auf stderr (stdout bleibt dem Protokoll vorbehalten).

### Evidence

- No structured-logging dependency: pyproject.toml:24-28 lists only mcp, httpx, pydantic — no structlog/loguru
- No logging at all in src/: grep for logging/structlog/logger/loguru across src/ returns nothing

### Risk Description

Ohne Logs ist keine Observability in Tool-Aufrufe möglich: Fehlerdiagnose, Nutzungsanalyse und Incident-Forensik im Cloud-Betrieb sind blind.

### Remediation

1. `structlog` (oder stdlib `logging` mit JSON-Formatter) als Dependency ergänzen.
2. Handler auf `sys.stderr` konfigurieren (nie stdout — siehe OBS-004).
3. Pro Tool-Call Name + Dauer + Ergebnisgrösse loggen, Level nach RFC 5424.

### Effort Estimate

**M** (1–3 Tage, mehrere Dateien / Tests)

### Verification After Fix

- Re-Audit dieses Checks (`OBS-003`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)
