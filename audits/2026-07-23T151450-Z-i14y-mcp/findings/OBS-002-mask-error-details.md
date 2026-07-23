## Finding: OBS-002 — Mask Error Details: keine Stacktraces / SQL ans LLM

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `OBS-002` |
| **PDF-Reference** | Sec 6.2 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Keine `traceback.format_exc()`/`sys.exc_info()`-Leaks im Code. FastMCP wird aber ohne `mask_error_details=True` initialisiert (`server.py:45`), und Fehlermeldungen betten rohe Upstream-Bodies ein (`client.py:95` `exc.response.text[:300]`, `server.py:509` `str(exc)[:160]`).

### Expected Behavior

Die primäre Masking-Kontrolle (`mask_error_details=True`) soll aktiv sein; rohe Upstream-Texte gehören nicht ungefiltert an den Client.

### Evidence

- No traceback.format_exc()/sys.exc_info() anywhere in src/ (grep returns nothing) — no stack-trace leakage into tool results
- Read-only, no-auth public-data server: no credentials/tokens exist to leak and no PII is handled, so the disclosure blast radius is minimal

### Risk Description

Geringes Risiko, da Upstream öffentlich und kein Secret/PII vorhanden ist — dennoch verletzt das rohe Durchreichen das Mask-Prinzip und kann interne Fehlerdetails der API exponieren.

### Remediation

1. `FastMCP("i14y-mcp", mask_error_details=True)` setzen.
2. Upstream-Bodies vor dem Weiterreichen kürzen/generalisieren (statt `response.text[:300]` einen kategorisierten Fehlertext).

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`OBS-002`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)
