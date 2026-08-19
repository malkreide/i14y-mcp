#!/usr/bin/env bash
#
# SessionStart-Hook: meldet, wie viele Commits der ausgecheckte Stand hinter
# origin/<Standard-Branch> liegt. Bei 0 schweigt er.
#
# GRUND
# Ein veralteter Klon hat am 3.8.2026 zweimal eine rote CI erzeugt, deren
# Ursache nicht im Diff stand — die fehlenden Commits waren jeweils genau die,
# die das Gate einfuehrten, an dem der Branch scheiterte. Die Pruefung kostet
# eine Sekunde und ersetzt eine Fehlersuche in den falschen Dateien.
#
# OBERSTE REGEL: NIEMALS BLOCKIEREN.
# Kein Netz, kein Remote, detached HEAD, flatterndes DNS, fehlendes `timeout`,
# kein Git-Repo — jeder dieser Faelle geht still durch (exit 0, keine Ausgabe).
# Ein Hook, der bei Netzproblemen die Arbeit anhaelt, wird nach dem zweiten Mal
# abgeschaltet und schuetzt danach gar nichts. Deshalb steht hier bewusst KEIN
# `set -e`: ein einzelner fehlschlagender Befehl darf den Hook nicht rot machen.
set -u

# Sekunden fuer den Netzzugriff. Klein halten: der Sessionstart wartet darauf.
readonly NETZ_TIMEOUT=5

# Ein Credential- oder Host-Key-Prompt wuerde ewig auf eine Eingabe warten, die
# im Hook-Kontext nie kommt — das waere genau das Haengen, das oben verboten ist.
# Ein Timeout allein reicht dagegen nicht: der Prompt haengt schon vor dem Netz.
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=true
export SSH_ASKPASS=true
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh} -o BatchMode=yes -o ConnectTimeout=${NETZ_TIMEOUT}"

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

# Die Vorpruefungen sparen nicht nur Arbeit, sie sparen den Netzversuch: ohne
# sie wartet der Sessionstart in jedem dieser Faelle einen Timeout lang auf ein
# Ergebnis, das es nicht geben kann. Genau das haelt
# tests/test_session_start_hook.py fest (die *_kein_netzversuch-Tests) — am
# Schweigen allein waere der Unterschied nicht zu sehen.
command -v git >/dev/null 2>&1 || exit 0
# Kein Repo. Redundant zur Remote-Zeile unten, die ausserhalb eines Repos
# ebenfalls scheitert — steht hier, weil sie den Fall benennt, statt ihn als
# Nebenwirkung mitzunehmen.
git rev-parse --git-dir >/dev/null 2>&1 || exit 0
# Leeres Repo: es gibt kein HEAD, gegen das man zaehlen koennte.
git rev-parse --verify --quiet HEAD >/dev/null 2>&1 || exit 0
git remote get-url origin >/dev/null 2>&1 || exit 0

# Harte Obergrenze auf jeden Netzbefehl. Fehlt `timeout` (macOS ohne coreutils),
# laeuft der Befehl ohne Wrapper — die git-eigenen Grenzen unten fangen den Fall
# ab, statt dass die Pruefung hier ersatzlos ausfaellt.
netz() {
  if command -v timeout >/dev/null 2>&1; then
    timeout -k 1 "${NETZ_TIMEOUT}s" "$@"
  elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout -k 1 "${NETZ_TIMEOUT}s" "$@"
  else
    "$@"
  fi
}

# Zweiter Guertel fuer den Fall ohne `timeout`, und gegen die haengende
# Verbindung, die zwar Bytes liefert, aber zu langsam: eine Uebertragung unter
# 1 KB/s laenger als NETZ_TIMEOUT bricht git selbst ab.
readonly -a GIT_NETZ_OPTS=(
  -c "http.lowSpeedLimit=1000"
  -c "http.lowSpeedTime=${NETZ_TIMEOUT}"
  -c "credential.helper="
)

# Der Standard-Branch wird ermittelt, nicht als "main" angenommen: mindestens
# ein Repo im Portfolio nutzt "master", und genau diese Annahme hat schon einmal
# einen Branch 15 Commits alt werden lassen.
#
# Erst der lokale Weg (kostet kein Netz), dann der Remote-Weg.
standard_branch=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)
standard_branch=${standard_branch#origin/}

if [ -z "$standard_branch" ]; then
  standard_branch=$(
    netz git "${GIT_NETZ_OPTS[@]}" ls-remote --symref origin HEAD 2>/dev/null |
      sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p' |
      head -n 1
  )
fi

# Ohne Namen NICHT weiterfetchen: `git fetch origin` ohne Refspec holt still den
# Remote-HEAD und endet mit 0 — die Pruefung liefe dann scheinbar erfolgreich
# gegen etwas anderes als den Standard-Branch.
[ -n "$standard_branch" ] || exit 0

# Expliziter Refspec statt `fetch origin`: gezaehlt wird gegen
# refs/remotes/origin/<Branch>, eine benannte Ref, nicht gegen FETCH_HEAD.
# `--no-tags`, weil Tags fuer den Vergleich nichts beitragen.
netz git "${GIT_NETZ_OPTS[@]}" fetch --quiet --no-tags \
  origin "refs/heads/${standard_branch}:refs/remotes/origin/${standard_branch}" \
  >/dev/null 2>&1 || exit 0

rueckstand=$(git rev-list --count "HEAD..refs/remotes/origin/${standard_branch}" 2>/dev/null) || exit 0

# Alles ausser einer echten Zahl > 0 ist Schweigen wert.
case "$rueckstand" in
  '' | *[!0-9]*) exit 0 ;;
esac
[ "$rueckstand" -gt 0 ] || exit 0

hier=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
[ "$hier" = "HEAD" ] && hier="detached HEAD"

printf 'Klon veraltet: %s Commit(s) hinter origin/%s (ausgecheckt: %s).\n' \
  "$rueckstand" "$standard_branch" "${hier:-?}"
printf 'Vor der Arbeit nachziehen: git merge --ff-only origin/%s bzw. git rebase origin/%s\n' \
  "$standard_branch" "$standard_branch"
printf 'Sonst wird eine rote CI von Commits ausgeloest, die nicht im Diff stehen.\n'

exit 0
