# Mitwirken

[🇬🇧 English Version](CONTRIBUTING.md)

Danke für dein Interesse an `i14y-mcp`. Dies ist ein Read-only-MCP-Server über
die öffentliche I14Y-API; Beiträge sollen das so belassen.

## Grundregeln

- **Read-only.** Jedes Tool bleibt mit `readOnlyHint: true` und
  `destructiveHint: false` annotiert. Keine Schreib-, Sende- oder
  Dateisystem-Fähigkeit. Schreib-Endpunkte existieren in der Quell-API, werden
  hier aber bewusst nicht exponiert.
- **Nur ein Egress-Host.** Anfragen gehen ausschliesslich an die fixe Basis-URL
  `https://api.i14y.admin.ch/api` (siehe `src/i14y_mcp/client.py`); keine
  nutzergesteuerten URLs, daher keine SSRF-Angriffsfläche.
- **Keine Secrets.** Die Lese-Endpunkte sind unauthentifiziert; keine
  Credential-Verarbeitung hinzufügen.

## Entwicklung

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

PYTHONPATH=src pytest tests/ -m "not live"   # offline, respx-gemockt
PYTHONPATH=src pytest tests/ -m live         # gegen die echte API
ruff check src tests
```

## Pull Requests

- Tests für nutzersichtbare Änderungen ergänzen; `ruff check` und die
  Offline-Suite grün halten.
- Einen `CHANGELOG.md`-Eintrag unter `[Unreleased]` hinzufügen.
- Bei Doku-Änderungen sowohl `README.md` als auch `README.de.md` aktualisieren.
- Für Release/Publishing siehe [`PUBLISHING.md`](PUBLISHING.md).

## Sicherheitsprobleme melden

Siehe [`SECURITY.md`](SECURITY.md) — bitte privat melden, keine öffentlichen Issues.
