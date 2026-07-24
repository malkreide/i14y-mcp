## Finding: SCALE-006 — Resource-Limits per Container (Memory, CPU, FDs)

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SCALE-006` |
| **PDF-Reference** | Sec 5.3 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

compose.yaml setzt `mem_limit: 256m`, `cpus: 0.5`, `pids_limit: 128` und `restart: unless-stopped` — gute Basis. Es fehlen ein FD-Limit (`ulimits.nofile`, empfohlen ≥4096 für ausgehende HTTP-Verbindungen) und Reservations/Requests (kein Burst-Headroom); OOM-/Restart-Verhalten ist nicht laufzeit-getestet.

### Expected Behavior

Container sollen zusätzlich zu Memory/CPU auch File-Descriptor-Limits und Reservations (requests < limits) definieren.

### Evidence

- compose.yaml:16-17 sets mem_limit: 256m and cpus: 0.5 — explicit memory and CPU limits
- compose.yaml:18 pids_limit: 128 caps process count and compose.yaml:19 restart: unless-stopped provides a restart policy for clean recovery after an OOM kill

### Risk Description

Unter Last können ausgehende HTTP-Verbindungen das Default-FD-Limit erschöpfen; ohne Reservations fehlt planbares Burst-Headroom.

### Remediation

1. `ulimits: { nofile: { soft: 4096, hard: 8192 } }` in compose.yaml ergänzen.
2. Optional `deploy.resources.reservations` (bzw. Plattform-Requests) definieren.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`SCALE-006`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)
