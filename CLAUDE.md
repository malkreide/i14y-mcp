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

Fällt dabei kein Test, sondern zeigt sich nur ein Symptom — Laufzeit,
Log-Rauschen, leere Felder —, dann fehlt die Zusicherung noch. Ein 29× längerer
Lauf ist kein Signal, das jemand liest.

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

Keine zweite Version in die Workflows schreiben: ein solcher Schritt liefe nach
dem dev-Install und überstimmte den Pin still. `tests/test_werkzeug_versionen.py`
hält das fest, statt es zu behaupten — dieser Absatz kann nicht umfallen, ein
Test schon. Er kennt dabei alle gängigen Installationsformen (`--upgrade`,
Anführungszeichen, `pip3`, `uv tool install`, `uv run --with`) und beide
Workflow-Endungen; eine engere Fassung war grün, weil sie nicht hinsah.

Die drei CI-Gates, wörtlich aus `.github/workflows/ci.yml` (Matrix 3.10–3.13):

```bash
PYTHONPATH=src pytest tests/ -m "not live"
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
```

`ruff format --check` ist ein eigenständiges Gate: `ruff check` belegt kein
Format, ein grüner Linter neben einem roten Format-Gate ist kein Widerspruch.

**Drei ist die ganze Liste** — und das ist hier die wichtigere Hälfte der
Aussage. Es gibt keinen Import-Test, keinen Manifest-Hash und vor allem
**kein Versions-Sync-Gate**: `scripts/` enthält nur `classify_live_run.py`
und `record_fixtures.py`. `pyproject.toml` und die zwei Stellen in
`server.json` stehen heute alle auf `0.3.2`, gehalten wird das von nichts.
Die Schwester-Server fahren dafür `scripts/check_version_sync.py`. Beim
Anheben also alle drei Stellen von Hand — ein Auseinanderlaufen macht kein
Gate rot.

Die Matrix setzt **kein** `fail-fast: false`, es gilt also der Standard: Eine
rote 3.10 bricht 3.11–3.13 ab, bevor sie etwas sagen. Ein einzelnes rotes
Feld heisst dann nicht «nur dort kaputt», sondern «der Rest kam nicht dazu».

**Beide ruff-Gates decken dieselben drei Verzeichnisse ab, und das gehört so.**
Fällt `scripts/` aus einem der beiden, bleibt `classify_live_run.py` ungeprüft —
ausgerechnet das Skript, das entscheidet, ob ein roter Live-Lauf ein Issue
aufmacht. Zwei Gates mit zwei Reichweiten sehen aus wie ein Gate; auch das hält
`test_werkzeug_versionen.py` fest. Kein `include` unter `[tool.ruff]` setzen —
das hebt die Pfadangabe der Gates still wieder auf.

**Live-Tests: geplanter Workflow vorhanden.** `.github/workflows/live.yml` läuft
per Cron (`17 5 * * 1`, Mo 05:17 UTC) plus `workflow_dispatch` gegen die echte
I14Y-API. DRIFT-005 ist damit erfüllt, nicht bloss per `-m "not live"` umgangen.

**Fixtures: aufgezeichnet.** `tests/fixtures/` hält eine echte Antwort je
externem Endpunkt; Herkunft, Datum, Auswahlregel und SHA-256 stehen je Datei in
`tests/fixtures/PROVENANCE.md` — Portfolio-Konvention, gleich wie in
`meteoswiss-mcp` und `swiss-statistics-mcp`. Neu aufzeichnen mit
`python scripts/record_fixtures.py`, geladen wird über `tests/fixture_data.py`. Erfolgs-Payloads nicht mehr von Hand
schreiben — die erste Aufzeichnung deckte auf, dass `/concepts` und
`/publicservices` ihr Label `name` nennen, nicht `title`: drei Tools lieferten
leere Titel, die Suite blieb grün. Fehlerpfade bleiben handgeschrieben.

Der Backoff-Schlaf wird über den Modul-Alias `client._sleep` gepatcht, nie über
`c.asyncio.sleep` — siehe Teil 1.
