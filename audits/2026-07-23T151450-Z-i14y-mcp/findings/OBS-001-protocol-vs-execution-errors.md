## Finding: OBS-001 — Protocol vs. Execution Errors: korrekte Trennung

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `OBS-001` |
| **PDF-Reference** | Sec 6.1 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

`api_status` trennt Execution-Errors sauber und degradiert graziös; `client.py` unterscheidet `NotFoundError` (404) von `UpstreamError` (5xx/429/Netz). Die übrigen Tools lassen diese Exceptions jedoch propagieren und verlassen sich auf FastMCPs Default-`isError`-Wrapping statt explizit `isError:true` mit Handlungshinweis zurückzugeben; ein Protocol-Error-Test fehlt.

### Expected Behavior

Execution-Errors sollen als strukturierte `isError:true`-Ergebnisse mit verwertbarer Guidance zurückkommen, Protocol-Errors über die JSON-RPC-Fehlercodes — beide sauber getrennt und getestet.

### Evidence

- src/i14y_mcp/server.py:489-521 api_status catches UpstreamError/NotFoundError and degrades gracefully (returns StatusResult reachable=False) instead of raising — the correct execution-error pattern
- src/i14y_mcp/client.py:35-41,83-104 separates NotFoundError (404) from UpstreamError (5xx/429/network) — distinct, deterministic error taxonomy
- tests/test_tools.py:142-148 (test_api_status_reports_failure_gracefully) covers the execution-error/degradation path; tests/test_client.py:61-84 cover 404 vs 400 vs 429 handling

### Risk Description

Der Agent erhält bei Upstream-Fehlern eine generische Exception ohne Handlungshinweis, was Selbstheilung (Retry, Fallback auf `list_datasets`) erschwert.

### Remediation

1. In den Tools `UpstreamError`/`NotFoundError` fangen und ein strukturiertes Fehlerergebnis mit Hinweis zurückgeben (analog zu `api_status`).
2. Test ergänzen, der `isError:true` für einen fehlschlagenden Tool-Call assertet.

### Effort Estimate

**M** (1–3 Tage, mehrere Dateien / Tests)

### Verification After Fix

- Re-Audit dieses Checks (`OBS-001`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)
