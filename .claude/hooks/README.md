# SessionStart-Hook: Klon-Aktualitätsprüfung

`session-start.sh` meldet beim Sessionstart, wie viele Commits der
ausgecheckte Stand hinter `origin/<Standard-Branch>` liegt. Liegt er nicht
zurück, sagt der Hook nichts.

## Warum

Ein veralteter Klon hat am 3.8.2026 zweimal eine rote CI erzeugt, deren
Ursache nicht im Diff stand — die fehlenden Commits waren jeweils genau die,
die das Gate einführten, an dem der Branch scheiterte. Man sucht den Fehler
dann in den geänderten Dateien, wo er nicht ist. Die Prüfung kostet eine
Sekunde und ersetzt eine Fehlersuche in den falschen Dateien.

Damit ist die erste Zeile von `CLAUDE.md` («Vor der Arbeit: Klon-Aktualität
prüfen») nicht mehr nur aufgeschrieben, sondern läuft.

## Die Regel über allem: der Hook blockiert nie

Kein Netz, kein Remote, detached HEAD, flatterndes DNS, fehlendes `timeout`,
gar kein Git-Repo — jeder dieser Fälle endet still mit `exit 0` und ohne
Ausgabe. Ein Hook, der bei Netzproblemen die Arbeit anhält, wird nach dem
zweiten Mal abgeschaltet und schützt danach gar nichts.

Konkret dagegen im Skript:

- **kein `set -e`** — ein einzelner fehlschlagender Befehl darf den Hook nicht
  rot machen; jeder Netzbefehl trägt sein eigenes `|| exit 0`.
- **`timeout ${NETZ_TIMEOUT}s`** auf jeden Netzbefehl (`ls-remote`, `fetch`).
  Fehlt `timeout` (macOS ohne coreutils), greift `gtimeout`, sonst die
  git-eigene Grenze `http.lowSpeedLimit`/`http.lowSpeedTime` — die fängt auch
  die Verbindung ab, die zwar Bytes liefert, aber zu langsam.
- **`GIT_TERMINAL_PROMPT=0`, `GIT_ASKPASS`, `SSH_ASKPASS`, `BatchMode=yes`,
  `credential.helper=`** — ein Passwort- oder Host-Key-Prompt wartet sonst
  ewig auf eine Eingabe, die im Hook-Kontext nie kommt. Ein Timeout allein
  hilft dagegen nicht: der Prompt hängt schon vor dem Netzzugriff.
- **`timeout: 15`** in `settings.json` als äusserer Riegel, falls das Skript
  doch einmal an einer unerwarteten Stelle steht.

## Der Standard-Branch wird ermittelt, nicht angenommen

Drei Server im Portfolio (`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`)
heissen ihren Standard-Branch `master`. Ein fest verdrahtetes `main` scheitert
dort mit «couldn't find remote ref main» — und wer das für ein Netzproblem
hält, arbeitet weiter auf genau dem veralteten Klon, vor dem der Hook warnen
soll. Genau diese Annahme hat schon einmal einen Branch 15 Commits alt werden
lassen.

Reihenfolge im Skript:

1. `git symbolic-ref refs/remotes/origin/HEAD` — lokal, kostet kein Netz.
2. Sonst `git ls-remote --symref origin HEAD`, mit Timeout.

Bleibt der Name leer, bricht der Hook ab, statt zu fetchen. Das ist dieselbe
Falle wie der `:?`-Schutz in `CLAUDE.md`: `git fetch origin` ohne Refspec holt
still den Remote-HEAD und endet mit 0 — die Prüfung liefe dann scheinbar
erfolgreich gegen etwas anderes als den Standard-Branch.

## Wann er läuft

`matcher: "startup|resume"` — nicht bei jedem `/clear` oder jeder
Kompaktierung. Ein Klon veraltet nicht mitten in einer Session.

## Prüfen

`tests/test_session_start_hook.py` fährt das Skript gegen echte Wegwerf-Repos
(lokale `file://`-Remotes, kein Netz): Rückstand wird gemeldet, aktueller Stand
schweigt, kaputtes Remote / kein Repo / detached HEAD gehen still durch. Ein
Repo dort heisst seinen Standard-Branch bewusst `master`, damit ein fest
verdrahtetes `main` den Test rot machen würde.

Von Hand:

```bash
CLAUDE_PROJECT_DIR="$PWD" .claude/hooks/session-start.sh; echo "exit=$?"
```
