## Finding: SCALE-004 — Containerization mit Multi-Stage-Builds

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SCALE-004` |
| **PDF-Reference** | Sec 5.3 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Der Dockerfile ist ein sauberer Multi-Stage-Build (builder/runtime, `python:3.14-slim`, Non-Root-User `mcp`, venv-only Runtime). Es fehlt jedoch eine `HEALTHCHECK`-Direktive (weder im Dockerfile noch in compose.yaml), und die Ziel-Imagegrösse (<200 MB) ist nicht verifiziert.

### Expected Behavior

Container für LB-Integration sollen einen `HEALTHCHECK` definieren, damit Orchestratoren Unhealthy-Instanzen erkennen.

### Evidence

- Dockerfile:3,19 has two FROM stages named 'builder' and 'runtime' (multi-stage build)
- Dockerfile:3,19 both use python:3.14-slim base (slim, not full)
- Dockerfile:28-34 creates a dedicated system user 'mcp' and runs USER mcp (non-root); the venv is copied with --chown=mcp:mcp so the runtime ships no build tools

### Risk Description

Ohne Healthcheck kann ein Load Balancer / Orchestrator einen hängenden Container nicht aussteuern; Requests laufen weiter in eine tote Instanz.

### Remediation

1. `HEALTHCHECK` ergänzen, der den SSE-Endpunkt bzw. einen Liveness-Pfad prüft, oder
2. in compose.yaml einen `healthcheck:`-Block mit `test`/`interval`/`timeout` definieren.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`SCALE-004`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)
