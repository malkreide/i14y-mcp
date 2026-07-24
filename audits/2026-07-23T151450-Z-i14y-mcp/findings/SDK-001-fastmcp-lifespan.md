## Finding: SDK-001 — FastMCP Lifespan via @asynccontextmanager + AsyncExitStack

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SDK-001` |
| **PDF-Reference** | Sec 3.1 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | fail |

### Observed Behavior

`server.py:45` initialisiert `FastMCP("i14y-mcp")` **ohne** `lifespan=`. Jeder Tool-Call öffnet über `async with build_client()` einen frischen `httpx.AsyncClient` (`client.py:63-69`, Docstring «Caller owns the lifecycle»). Es gibt keinen `@asynccontextmanager`-Lifespan und kein Connection-Pooling über Requests hinweg — genau das vom Check markierte Anti-Pattern.

### Expected Behavior

Langlebige Ressourcen (HTTP-Client mit Connection-Pool) sollen einmalig in einem FastMCP-Lifespan via `@asynccontextmanager` (+ `AsyncExitStack`) aufgebaut und über `server.state` geteilt werden.

### Evidence

- server.py:53 `mcp = FastMCP("i14y-mcp")` — constructor receives no `lifespan=` argument.
- No `@asynccontextmanager` / `AsyncExitStack` anywhere in src/ (grep returned no matches).
- server.py:64-66 `_get()` does `async with build_client() as http:` — a fresh httpx.AsyncClient is created and torn down per tool call.
- client.py:63-69 `build_client()` returns a new `httpx.AsyncClient(...)` with docstring 'Caller owns the lifecycle.' — no shared/pooled client.
- server.py:api_status also opens its own `async with build_client() as http:` per call.

### Risk Description

Ein neuer Client pro Call verwirft den Connection-Pool und TLS-Session-Reuse: unnötige TCP-/TLS-Handshakes erhöhen Latenz und Ressourcenverbrauch, besonders im Cloud-/SSE-Betrieb mit vielen Aufrufen.

### Remediation

1. Lifespan-Funktion mit `@asynccontextmanager` definieren, die einen `httpx.AsyncClient` erzeugt und beim Shutdown schliesst.
2. `FastMCP("i14y-mcp", lifespan=lifespan)` setzen; Client aus `ctx.request_context.lifespan_context` beziehen statt pro Call neu zu bauen.
3. `build_client()` auf den Lifespan umstellen; Tests auf den geteilten Client anpassen.

### Effort Estimate

**M** (1–3 Tage, mehrere Dateien / Tests)

### Verification After Fix

- Re-Audit dieses Checks (`SDK-001`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)
