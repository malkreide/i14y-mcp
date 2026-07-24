## Finding: SDK-004 — CORS Mcp-Session-Id Exposure bei HTTP/SSE

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SDK-004` |
| **PDF-Reference** | Sec 3.1 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | fail |

### Observed Behavior

Bei aktivem HTTP/SSE-Transport (`I14Y_MCP_TRANSPORT=sse`) existiert **keinerlei** CORS-Konfiguration: grep nach `CORSMiddleware`/`expose_headers`/`allow_origins` ist leer. `Access-Control-Expose-Headers: Mcp-Session-Id` wird nicht gesetzt, sodass Browser-Clients die Session-ID nicht lesen können.

### Expected Behavior

Für HTTP/SSE soll `Mcp-Session-Id` via `Access-Control-Expose-Headers` (und in `allow_headers`) freigegeben werden, damit Cross-Origin-Browser-Clients Sessions führen können.

### Evidence

- Transport is dual: server.py main() honours `I14Y_MCP_TRANSPORT` and runs `mcp.run(transport="sse")` or `"streamable-http"` — so the HTTP/SSE applies_when is active.
- No CORS configuration exists: grep for `CORSMiddleware|cors|allow_origins|expose_headers|middleware` across src/ returns no matches.
- Server exposes HTTP/SSE via `mcp.run(...)` on `mcp.settings.host`/`port` directly — no custom Starlette/ASGI app, no CORSMiddleware, no `cors_expose_headers` passed to FastMCP.
- No `Access-Control-Expose-Headers: Mcp-Session-Id` is configured anywhere.

### Risk Description

Cross-Origin-Browser-Clients können die Session-ID nicht auslesen → SSE-Sessions brechen im Browser, obwohl serverseitige/stdio-Clients funktionieren (schwer zu diagnostizieren).

### Remediation

1. Beim SSE-/streamable-http-Start CORS so konfigurieren, dass `Mcp-Session-Id` in `expose_headers` und `allow_headers` steht (FastMCP-CORS-Option bzw. ASGI-Middleware).
2. Mit einem Browser-Client oder `curl -I` die `Access-Control-Expose-Headers`-Antwort prüfen.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`SDK-004`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)
