## Finding: SDK-004 — CORS Mcp-Session-Id Exposure bei HTTP/SSE

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SDK-004` |
| **PDF-Reference** | Sec 3.1 |
| **Audit-Datum** | 2026-07-24 |
| **Auditor** | Claude Code (mcp-audit skill, re-audit) |
| **Check-Status** | partial |

### Observed Behavior

Der ursprüngliche Blocker ist behoben: `build_http_app()` exponiert `Mcp-Session-Id` via CORS, sodass Browser-Clients ihre Session behalten. `allow_origins=["*"]` ist jedoch hartkodiert und nicht env-gesteuert/produktiv einschränkbar — dieses Pass-Kriterium bleibt offen (abgefedert dadurch, dass der Server no-auth ist und kein `allow_credentials` setzt).

### Expected Behavior

Die erlaubten CORS-Origins sollen konfigurierbar sein, damit produktive Deployments sie einschränken können.

### Evidence

- build_http_app() (server.py:674-693) builds the SSE/streamable-http ASGI app itself and adds CORSMiddleware because FastMCP.run() serves without CORS.
- expose_headers=["Mcp-Session-Id"] is set (server.py:691) — the critical header exposure that lets browser clients read the session id is present.
- allow_headers=["*", "Mcp-Session-Id"] includes Mcp-Session-Id for follow-up requests; allow_methods includes GET/POST/DELETE/OPTIONS.
- No allow_credentials=True is set and the server is no-auth, so the wildcard-origin + credentials CORS-spec violation does not arise.

### Risk Description

Gering: ohne Auth/Credentials ist ein permissiver CORS-Origin für öffentliche Read-Daten unkritisch; in geschlossenen Deployments ist eine Einschränkung dennoch wünschenswert.

### Remediation

1. Origins aus einer Env-Var lesen (z. B. `I14Y_MCP_CORS_ORIGINS`, Default `*`) und an `allow_origins` übergeben.
2. In README/SECURITY dokumentieren, wie produktive Deployments die Origins einschränken.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`SDK-004`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)
