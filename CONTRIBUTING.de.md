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
  `https://api.i14y.admin.ch/api`, erzwungen durch die `ALLOWED_HOSTS`-Allow-List
  in `src/i14y_mcp/client.py` (siehe [`docs/network-egress.md`](docs/network-egress.md));
  keine nutzergesteuerten URLs, daher keine SSRF-Angriffsfläche.
- **Keine Secrets.** Die Lese-Endpunkte sind unauthentifiziert; keine
  Credential-Verarbeitung hinzufügen.

## Entwicklung

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

PYTHONPATH=src pytest tests/ -m "not live"   # offline, respx-gemockt
PYTHONPATH=src pytest tests/ -m live         # gegen die echte API
ruff check src/ tests/ scripts/               # Lint-Gate
ruff format --check src/ tests/ scripts/      # Format-Gate
```

Die Offline-Suite spielt echte Antworten aus `tests/fixtures/` ab, eine pro
externem Endpunkt, jede mit ihrem Aufnahmedatum versehen. Neu aufzeichnen gegen
die Live-API:

```bash
python scripts/record_fixtures.py
```

Erfolgs-Payloads nicht von Hand schreiben: ein Stub stimmt mit der eigenen
Annahme überein — so blieb ein umbenanntes Quellfeld durch die ganze Suite
grün. Fehlerpfade (404, Timeouts, maskierte 4xx) bleiben handgeschrieben, die
lassen sich nicht auf Zuruf aufzeichnen.

Das sind wörtlich die drei Gates der CI. Lint und Format sind getrennte
Prüfungen: `ruff check` belegt kein Format, ein grüner Linter neben einem roten
`ruff format --check` ist also ein gewöhnlicher Zustand, kein Widerspruch. Die
in `pyproject.toml` gepinnte ruff-Version verwenden — `pip install -e ".[dev]"`
installiert sie. Eine andere Version meldet Abweichungen, die niemand
verursacht hat.

## Pull Requests

- Tests für nutzersichtbare Änderungen ergänzen; beide ruff-Gates und die
  Offline-Suite grün halten.
- Einen `CHANGELOG.md`-Eintrag unter `[Unreleased]` hinzufügen.
- Bei Doku-Änderungen sowohl `README.md` als auch `README.de.md` aktualisieren.
- Für Release/Publishing siehe [`PUBLISHING.md`](PUBLISHING.md).

## Sicherheitsprobleme melden

Siehe [`SECURITY.md`](SECURITY.md) — bitte privat melden, keine öffentlichen Issues.
