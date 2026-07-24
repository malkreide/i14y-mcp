## Finding: ARCH-011 — Standardisierte Repo-Struktur (src-Layout, tests, README.de.md)

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `ARCH-011` |
| **PDF-Reference** | Anhang A8 |
| **Audit-Datum** | 2026-07-24 |
| **Auditor** | Claude Code (mcp-audit skill, re-audit) |
| **Check-Status** | partial |

### Observed Behavior

Repo-Struktur, src-Layout, bilinguale READMEs, CI und `docs/roadmap.md` sind vollständig vorhanden. Alle 13 Tool-Bodies liegen jedoch weiterhin inline in einer ~730-zeiligen `server.py`; ab >5 Tools erwartet der Check eine Aufteilung in ein `tools/`-Subpackage (oder eine dokumentierte Begründung).

### Expected Behavior

Bei mehr als 5 Tools sollen die Tool-Definitionen in ein `tools/`-Subpackage aufgeteilt werden, damit `server.py` schlank bleibt.

### Evidence

- All mandatory top-level files present: README.md, README.de.md, CHANGELOG.md, LICENSE, pyproject.toml.
- Mandatory directories present: src/, tests/, .github/workflows/.
- Correct src-layout: code under src/i14y_mcp/, and pyproject declares packages = ['src/i14y_mcp'] (pyproject.toml:49-50).
- CI workflows present beyond the minimum: ci.yml (test+lint, 3.10-3.13 matrix), publish.yml (PyPI), live.yml (nightly live).
- README.de.md holds the same top-level section inventory as README.md (verified: matching ## headings for Why/Architecture/Tools/Installation/Join keys/Known limitations/Testing/Contributing/Credits).

### Risk Description

Rein wartungsbezogen: eine grosse Datei erschwert Navigation und Review, ist aber kein Laufzeit- oder Sicherheitsrisiko.

### Remediation

1. Tools thematisch in `src/i14y_mcp/tools/{discovery,services,semantics,actors,ops}.py` aufteilen und in `server.py` registrieren, oder
2. die bewusste Single-File-Struktur (klar sektioniert, 13 kohärente Read-Tools) kurz in `docs/roadmap.md` als Design-Entscheidung festhalten.

### Effort Estimate

**M** (1–3 Tage, mehrere Dateien / Tests)

### Verification After Fix

- Re-Audit dieses Checks (`ARCH-011`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)
