## Finding: SEC-018 — Input-Validation an Tool-Boundaries (Pydantic strict / Zod)

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SEC-018` |
| **PDF-Reference** | Sec 3 / Sec 4 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

`Language`/`ResourceType` sind `Literal`-Enums, und `_clamp()` begrenzt Pagination/Limits. Die übrigen Inputs sind jedoch einfache `str`/`int` ohne strikte Pydantic-Argument-Schemas: keine `min/max/pattern` auf `query`/UUID-Strings, keine `ge/le` (Zahlen werden geklammert statt abgelehnt), kein `extra=forbid` auf der Input-Seite.

### Expected Behavior

Tool-Inputs sollen an der Boundary strikt validiert werden (Pydantic mit `pattern`/`ge`/`le`, UUID-Typen), sodass ungültige Eingaben abgelehnt statt still korrigiert werden.

### Evidence

- src/i14y_mcp/server.py:47-48 — Language and ResourceType are Literal enums, so language/type args are enum-constrained in the FastMCP-generated JSON schema
- src/i14y_mcp/server.py:57-58,102,150,241,294,339,394,438,473 — _clamp() bounds every pagination/limit value into a valid range (1..100/200/SEARCH_HARD_CAP), preventing negative/huge-range abuse
- src/i14y_mcp/models.py:25 etc. — output models use ConfigDict(extra='forbid'); FastMCP derives input schemas from the typed tool signatures
- src/i14y_mcp/client.py:82 — params passed via httpx (URL-encoded); no SQL/shell sink

### Risk Description

Ohne strikte Boundary-Validierung können fehlerhafte IDs/Parameter unbemerkt an die Upstream-API durchgereicht werden; Defense-in-Depth fehlt eine Schicht.

### Remediation

1. Für Pfad-IDs `uuid.UUID`-Typ bzw. ein `pattern` verwenden statt freiem `str`.
2. Numerische Parameter mit `Field(ge=…, le=…)` typisieren (Reject statt Clamp, oder Clamp dokumentiert beibehalten).
3. Wo sinnvoll strikte Pydantic-Input-Modelle mit `extra='forbid'` einsetzen.

### Effort Estimate

**M** (1–3 Tage, mehrere Dateien / Tests)

### Verification After Fix

- Re-Audit dieses Checks (`SEC-018`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)
