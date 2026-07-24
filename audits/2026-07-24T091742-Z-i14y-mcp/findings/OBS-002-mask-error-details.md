## Finding: OBS-002 — Mask Error Details: keine Stacktraces / SQL ans LLM

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `OBS-002` |
| **PDF-Reference** | Sec 6.2 |
| **Audit-Datum** | 2026-07-24 |
| **Auditor** | Claude Code (mcp-audit skill, re-audit) |
| **Check-Status** | partial |

### Observed Behavior

Rohe Upstream-Bodies werden bereits an der Quelle maskiert (kategorisierte `HTTP <status>`-Meldungen, keine Stacktraces, stderr-only-Logging). Der namensgebende Schalter `mask_error_details=True` ist jedoch nicht gesetzt — er existiert im `FastMCP(...)`-Konstruktor von `mcp 1.28.1` **nicht** (verifiziert), sodass ein unbehandelter Bug theoretisch noch über `str(exc)` an den Client gelangen könnte.

### Expected Behavior

FastMCP soll mit `mask_error_details=True` initialisiert werden, damit unerwartete Exceptions nicht im Klartext an den Client gehen.

### Evidence

- No raw upstream body, stacktrace, SQL or path leaks: fetch_json categorises 4xx/5xx into clean UpstreamError text (client.py:163-172, OBS-002 comment at :168-169); no traceback.format_exc / sys.exc_info anywhere in src/
- Execution errors carry user-friendly, internals-free messages (client.py:148-151, 184-189)
- Logs are stderr-only structured JSON with no tokens/PII (no-auth server; logging_config.py)

### Risk Description

Gering für diesen Server: read-only, no-auth, keine Secrets/PII. Das Restrisiko ist eine mögliche Offenlegung interner Fehlertexte bei einem unerwarteten Bug.

### Remediation

1. Sobald die verwendete mcp-SDK-Version `mask_error_details` unterstützt, im `FastMCP(...)`-Aufruf setzen.
2. Bis dahin bleibt die Quell-Maskierung (client.py) die wirksame Kontrolle; ggf. einen dünnen Exception-Wrapper um die Tools ergänzen.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`OBS-002`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)
