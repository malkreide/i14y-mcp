## Finding: ARCH-007 — Capability-Aggregation: Composability intern, Atomarität extern

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `ARCH-007` |
| **PDF-Reference** | Sec 2.3 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Tools liefern gedanklich vollständige Objekte (Titel, Publisher, Themen, Landing-Page), nicht bloss IDs — das Fail-Pattern «nur ID zurückgeben» wird vermieden. Es gibt jedoch keine interne Aggregation mehrerer Quellen und kein `asyncio.gather`; die dokumentierte Anchor-Query braucht drei sequenzielle Calls (search → distributions → dataset).

### Expected Behavior

Häufige Use-Cases sollen in möglichst wenige Tool-Calls (Ziel ≤2) gebündelt werden, indem der Server intern zusammengehörige Fetches aggregiert.

### Evidence

- src/i14y_mcp/server.py:71-126 — search_catalog returns thought-complete hits (title, publisher, themes, landing_page), not bare IDs, so it beats the 'returns only an ID' fail pattern
- src/i14y_mcp/server.py:190-213 — get_dataset_distributions internally re-shapes the dataset detail into a distributions-focused result

### Risk Description

Mehr Round-Trips erhöhen Latenz und Token-Verbrauch pro Recherche; bei vielen Nutzern summiert sich das spürbar.

### Remediation

1. Optional ein aggregierendes Tool `get_dataset_bundle(dataset_id)` anbieten, das Detail + Distributions in einem Call liefert (intern `asyncio.gather`).
2. Alternativ als bewusste Design-Entscheidung dokumentieren (Atomarität vor Bequemlichkeit) und als accepted-risk schliessen.

### Effort Estimate

**M** (1–3 Tage, mehrere Dateien / Tests)

### Verification After Fix

- Re-Audit dieses Checks (`ARCH-007`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)
