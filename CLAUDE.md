# CLAUDE.md

## Teil 1 — Portfolio-Konventionen

### Vor der Arbeit

Klon-Aktualität prüfen: `git fetch origin main && git rev-list --count HEAD..origin/main`
Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.

Gates lokal fahren, mit der GEPINNTEN ruff-Version aus der CI. Eine andere
Version meldet Abweichungen, die niemand verursacht hat.

### Tests

Gegenprobe ist Pflicht. Ein Test, der grün bleibt, wenn man die
Implementierung entfernt, prüft nichts. Jede neue Zusicherung einzeln
neutralisieren und zeigen, dass genau die zugehörigen Tests fallen.

Zwei Fallen, die beide grün blieben:

- Eine Fake-Uhr, die nur beim Schlafen vorrückt, kann eine Zusicherung über
  echte Zeit nicht widerlegen.
- `monkeypatch.setattr(modul.asyncio, "sleep", ...)` greift ins Modul
  `asyncio` selbst und entschärft die Mechanik im ganzen Prozess. Patche
  einen Modul-Alias (`_sleep = asyncio.sleep`), nicht das fremde Modul.

Handgeschriebene Fixtures kodieren die Annahme des Autors und können sie
nicht widerlegen. Mindestens eine aufgezeichnete Antwort pro externem
Endpunkt, mit Aufnahmedatum.

### Wenn etwas rot ist

Roter Live-Test: erst die Quelle abfragen, dann einordnen. Nicht aus der
Fehlermeldung schliessen. Am 3.8.2026 hiess "nicht gefunden" nicht, dass der
Datensatz weg war, sondern dass die Quelle die Schreibweise ihrer Kopfzeile
gewechselt hatte — vier von sechs Datensätzen produktiv kaputt, alle
Unit-Tests grün.

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

## Teil 2 — i14y-mcp

**ruff-Pin: `ruff==0.16.1`**, einzige Quelle ist `[project.optional-dependencies].dev`
in `pyproject.toml`; die CI erbt ihn über `pip install -e ".[dev]"`. Eine
`.pre-commit-config.yaml` existiert nicht — es gibt also keine zweite,
abweichende Version, aber auch kein lokales Gate vor dem Push.

Die drei CI-Gates, wörtlich aus `.github/workflows/ci.yml` (Matrix 3.10–3.13):

```bash
PYTHONPATH=src pytest tests/ -m "not live"
ruff check src/ tests/
ruff format --check src/ tests/
```

`ruff format --check` ist ein eigenständiges Gate: `ruff check` belegt kein
Format, ein grüner Linter neben einem roten Format-Gate ist kein Widerspruch.

**Live-Tests: geplanter Workflow vorhanden.** `.github/workflows/live.yml` läuft
per Cron (`17 5 * * 1`, Mo 05:17 UTC) plus `workflow_dispatch` gegen die echte
I14Y-API. DRIFT-005 ist damit erfüllt, nicht bloss per `-m "not live"` umgangen.

**Offener Befund:** alle Fixtures in `tests/` sind handgeschriebene Inline-respx-
Stubs ohne aufgezeichnete Antwort und ohne Aufnahmedatum — Teil 1 verlangt
mindestens eine Aufzeichnung pro externem Endpunkt.
