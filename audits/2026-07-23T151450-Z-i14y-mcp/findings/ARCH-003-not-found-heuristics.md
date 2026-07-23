## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `ARCH-003` |
| **PDF-Reference** | Sec 2.2 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

`search_catalog` liefert bei null Treffern ein strukturiertes `SearchResult` (`total_matched=0`, `truncated=false`) statt eines leeren Strings oder `[]` — das schlimmste Anti-Pattern wird also vermieden. Es fehlt jedoch jegliche Heuristik: kein `match_type`-Feld (exact/fuzzy/none), kein Vorschlag und kein Handlungshinweis, wenn die Suche leer bleibt.

### Expected Behavior

Bei leeren Treffern soll der Server dem Agenten einen verwertbaren nächsten Schritt geben — z. B. ein `match_type`-Feld und einen Hinweis wie «keine Volltext-Treffer; `list_datasets` deckt das vollständige Register ab» (der Server kennt diese Limitation bereits, siehe README).

### Evidence

- src/i14y_mcp/server.py:118-126 — empty search returns a structured SearchResult (total_matched/returned/truncated) not a bare '[]' or 'No results found' string, avoiding the worst anti-pattern
- src/i14y_mcp/server.py:489-521 — api_status deliberately returns an evaluable state so an agent can distinguish 'no data matched' from 'source down'

### Risk Description

Der Agent erhält bei null Treffern keine Orientierung und bricht die Recherche womöglich ab, obwohl `list_datasets` das vollständige Register abdeckt — vermeidbare Sackgasse.

### Remediation

1. `SearchResult` (models.py) um `hint: str | None` und optional `match_type` erweitern.
2. In `search_catalog` bei `total_matched == 0` einen Hinweis auf `list_datasets` setzen.
3. Unit-Test für den Leer-Treffer-Pfad ergänzen.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`ARCH-003`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)
