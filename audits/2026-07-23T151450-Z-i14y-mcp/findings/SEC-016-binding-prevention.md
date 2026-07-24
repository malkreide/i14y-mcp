## Finding: SEC-016 — 0.0.0.0-Binding-Prevention (NeighborJack)

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SEC-016` |
| **PDF-Reference** | Sec 4 (Empirie 2025) |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Der Default-Transport ist `stdio` (kein Port). Bei SSE ist der **Code-Default** für den Bind jedoch `0.0.0.0` (`server.py:528`, `HOST=os.getenv("HOST", "0.0.0.0")`) statt `127.0.0.1`; `compose.yaml:5` publiziert zudem `8000:8000` auf allen Host-Interfaces. Es gibt keine Warnung, wenn ausserhalb eines Containers an `0.0.0.0` gebunden wird.

### Expected Behavior

Der SSE-Bind soll per Default auf `127.0.0.1` (Loopback) liegen; `0.0.0.0` nur als expliziter Opt-in für Container-Deployments, idealerweise mit stderr-Warnung ausserhalb eines Containers.

### Evidence

- src/i14y_mcp/server.py:526 — default transport is stdio (no port opened at all unless SSE is explicitly enabled), which removes the network surface in the default path
- Dockerfile:24-26 — MCP transport/HOST=0.0.0.0 set explicitly at the container layer (correct place)
- SECURITY.md:29,42-46 — documents that SSE/streamable-http binds HOST default 0.0.0.0, intended for container deployment behind a reverse proxy / gateway; default stdio has no network surface

### Risk Description

Bindet ein lokal (nicht containerisiert) gestarteter SSE-Server versehentlich an `0.0.0.0`, ist er im gesamten LAN erreichbar («NeighborJack») — ein read-only-Server exponiert dann zumindest ungewollt seinen Endpunkt.

### Remediation

1. In `server.py` den `HOST`-Default auf `127.0.0.1` setzen; `0.0.0.0` bleibt via Env expliziter Opt-in (der Dockerfile setzt `HOST=0.0.0.0` bereits bewusst).
2. Optional beim Binden an `0.0.0.0` ausserhalb eines Containers auf stderr warnen.
3. SECURITY.md entsprechend präzisieren.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`SEC-016`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)
