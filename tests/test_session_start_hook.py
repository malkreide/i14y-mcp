"""Verhalten des SessionStart-Hooks `.claude/hooks/session-start.sh`.

Der Hook meldet beim Sessionstart den Rueckstand gegenueber
origin/<Standard-Branch>. Zwei Zusicherungen tragen ihn, und beide kann man
nicht durch Hinsehen pruefen:

1. Er blockiert nie. Kein Remote, kein Netz, kein Repo, detached HEAD — alles
   endet still mit exit 0.
2. Er ermittelt den Standard-Branch, statt "main" anzunehmen.

Darum heissen die Wegwerf-Repos hier ihren Standard-Branch `master`: ein fest
verdrahtetes `main` im Hook wuerde diese Datei rot machen, ein stiller Ausfall
der Ermittlung ebenfalls.

Kein Netz noetig — die Remotes sind lokale Verzeichnisse.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "session-start.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("bash") is None,
    reason="Hook braucht git und bash",
)


def _git(cwd: Path, *args: str) -> str:
    """Git im Wegwerf-Repo, unabhaengig von der Konfiguration des Laufenden."""
    ergebnis = subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=cwd,
        env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull},
        capture_output=True,
        text=True,
        check=True,
    )
    return ergebnis.stdout


def _commit(repo: Path, text: str) -> None:
    (repo / "datei.txt").write_text(text, encoding="utf-8")
    _git(repo, "add", "datei.txt")
    _git(repo, "commit", "-m", text)


@pytest.fixture
def upstream(tmp_path: Path) -> Path:
    """Ein Repo, dessen Standard-Branch bewusst `master` heisst."""
    repo = tmp_path / "upstream"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=master", "--quiet")
    _commit(repo, "start")
    return repo


@pytest.fixture
def klon(tmp_path: Path, upstream: Path) -> Path:
    ziel = tmp_path / "klon"
    _git(tmp_path, "clone", "--quiet", str(upstream), str(ziel))
    return ziel


@pytest.fixture
def haengendes_git(tmp_path: Path) -> Path:
    """Ein `git`, das bei `fetch`/`ls-remote` nie zurueckkommt.

    Steht fuer die Verbindung, die weder gelingt noch scheitert — flatterndes
    DNS, haengender Proxy. Alle anderen git-Aufrufe reicht der Stub durch.
    """
    echtes_git = shutil.which("git")
    assert echtes_git is not None

    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    stub = stub_dir / "git"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        'for arg in "$@"; do\n'
        '  case "$arg" in\n'
        "    fetch | ls-remote) sleep 120; exit 0 ;;\n"
        "  esac\n"
        "done\n"
        f'exec {echtes_git} "$@"\n',
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub_dir


def _hook_mit_haengendem_netz(
    arbeitsverzeichnis: Path, stub_dir: Path
) -> tuple[subprocess.CompletedProcess[str], float]:
    start = time.monotonic()
    ergebnis = subprocess.run(
        ["bash", str(HOOK)],
        cwd=arbeitsverzeichnis,
        env={
            **os.environ,
            "PATH": f"{stub_dir}{os.pathsep}{os.environ['PATH']}",
            "CLAUDE_PROJECT_DIR": str(arbeitsverzeichnis),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
        },
        capture_output=True,
        text=True,
        timeout=110,
    )
    return ergebnis, time.monotonic() - start


def _hook(arbeitsverzeichnis: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(HOOK)],
        cwd=arbeitsverzeichnis,
        env={
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(arbeitsverzeichnis),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
        },
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_meldet_rueckstand_mit_zahl_und_branchname(klon: Path, upstream: Path) -> None:
    for i in range(3):
        _commit(upstream, f"neu-{i}")

    ergebnis = _hook(klon)

    assert ergebnis.returncode == 0
    assert "3" in ergebnis.stdout
    # Der ermittelte Name muss dastehen, nicht "main".
    assert "origin/master" in ergebnis.stdout
    assert "origin/main" not in ergebnis.stdout


def test_schweigt_wenn_aktuell(klon: Path) -> None:
    ergebnis = _hook(klon)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_schweigt_wenn_nur_lokale_commits_vorausliegen(klon: Path) -> None:
    """Voraus ist kein Rueckstand — `HEAD..origin` zaehlt nur die fehlende Richtung."""
    _commit(klon, "eigener")

    ergebnis = _hook(klon)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_ermittelt_branch_auch_ohne_lokales_origin_head(klon: Path, upstream: Path) -> None:
    """Ohne refs/remotes/origin/HEAD bleibt nur der Remote-Weg (ls-remote --symref)."""
    _commit(upstream, "neu")
    _git(klon, "remote", "set-head", "origin", "--delete")

    ergebnis = _hook(klon)

    assert ergebnis.returncode == 0
    assert "origin/master" in ergebnis.stdout


def test_meldet_auch_bei_detached_head(klon: Path, upstream: Path) -> None:
    _commit(upstream, "neu")
    _git(klon, "checkout", "--quiet", "--detach", "HEAD")

    ergebnis = _hook(klon)

    assert ergebnis.returncode == 0
    assert "origin/master" in ergebnis.stdout


def test_unerreichbares_remote_geht_still_durch(klon: Path, tmp_path: Path) -> None:
    """Der Fall «kein Netz»: nichts auf stdout, exit 0, und zwar zuegig."""
    _git(klon, "remote", "set-url", "origin", str(tmp_path / "gibt-es-nicht"))
    _git(klon, "remote", "set-head", "origin", "--delete")

    start = time.monotonic()
    ergebnis = _hook(klon)
    dauer = time.monotonic() - start

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""
    # Zwei Netzversuche a 5s plus Startzeit; alles darueber hiesse haengen.
    assert dauer < 30


def test_ohne_netz_wird_nicht_aus_veralteten_refs_gemeldet(klon: Path, tmp_path: Path) -> None:
    """Scheitert der Fetch, schweigt der Hook — statt eine Zahl zu melden, die er
    nicht belegen kann.

    Aufbau: die lokale Remote-Ref zeigt auf einen Stand, den HEAD nicht hat
    (alter Fetch), und das Remote ist weg. Wer den Fetch-Fehler durchreicht,
    zaehlt gegen genau diese veraltete Ref und meldet eine Zahl, die von nichts
    gedeckt ist — upstream kann laengst weiter sein oder umgeschrieben.
    """
    _git(klon, "fetch", "--quiet", "origin")
    _commit(klon, "spaeter")
    _git(klon, "update-ref", "refs/remotes/origin/master", "HEAD")
    _git(klon, "reset", "--hard", "--quiet", "HEAD~1")
    # Gegenprobe zum Aufbau: die veraltete Ref liegt jetzt wirklich vorn.
    assert _git(klon, "rev-list", "--count", "HEAD..refs/remotes/origin/master").strip() == "1"

    _git(klon, "remote", "set-url", "origin", str(tmp_path / "gibt-es-nicht"))

    ergebnis = _hook(klon)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_haengendes_netz_wird_abgeschnitten(klon: Path, haengendes_git: Path) -> None:
    """Der Fall «flatterndes DNS»: das Netz antwortet nie.

    Ein `git`, das bei `fetch`/`ls-remote` schlaeft, steht hier fuer die
    Verbindung, die weder gelingt noch scheitert. Ohne Timeout haengt der
    Sessionstart daran — und ein Hook, der das zweimal tut, wird abgeschaltet.
    """
    ergebnis, dauer = _hook_mit_haengendem_netz(klon, haengendes_git)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""
    # Ein Netzversuch a 5s plus Startzeit. 120s waere der ungebremste Stub.
    assert dauer < 30, f"Hook lief {dauer:.1f}s — der Timeout greift nicht"


def test_ohne_remote_geht_still_durch(klon: Path) -> None:
    _git(klon, "remote", "remove", "origin")

    ergebnis = _hook(klon)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_ausserhalb_eines_repos_geht_still_durch(tmp_path: Path) -> None:
    kein_repo = tmp_path / "kein-repo"
    kein_repo.mkdir()

    ergebnis = _hook(kein_repo)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_leeres_repo_geht_still_durch(tmp_path: Path) -> None:
    """Ohne HEAD-Commit gibt es nichts zu zaehlen — kein Fehler, kein Wort."""
    leer = tmp_path / "leer"
    leer.mkdir()
    _git(leer, "init", "--initial-branch=master", "--quiet")

    ergebnis = _hook(leer)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_hook_ist_ausfuehrbar_und_in_settings_registriert() -> None:
    """Ein Hook, der nicht registriert ist, laeuft nie — und faellt sonst niemandem auf."""
    import json

    assert os.access(HOOK, os.X_OK), "Hook ist nicht ausfuehrbar"

    settings = json.loads((HOOK.parents[1] / "settings.json").read_text(encoding="utf-8"))
    befehle = [
        h["command"]
        for eintrag in settings["hooks"]["SessionStart"]
        for h in eintrag["hooks"]
        if h.get("type") == "command"
    ]
    assert any("session-start.sh" in b for b in befehle), befehle


# Ohne Remote, ohne Repo, ohne HEAD-Commit gibt es nichts zu vergleichen. Dass
# der Hook dann schweigt, faellt schon oben auf — dass er dafuer gar nicht erst
# ans Netz geht, sieht man nur an der Laufzeit. Die drei Vorpruefungen im
# Skript sind sonst von den spaeteren `|| exit 0` verdeckt: man koennte sie
# entfernen, ohne dass ein Test faellt, und der Sessionstart haette danach bei
# jedem dieser Faelle einen Timeout lang gewartet.
#
# NETZ_TIMEOUT im Hook ist 5s; die Schranke hier trennt «gar kein Versuch» von
# «ein abgeschnittener Versuch».
KEIN_NETZVERSUCH_S = 3.0


def test_ohne_remote_kein_netzversuch(klon: Path, haengendes_git: Path) -> None:
    _git(klon, "remote", "remove", "origin")

    ergebnis, dauer = _hook_mit_haengendem_netz(klon, haengendes_git)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""
    assert dauer < KEIN_NETZVERSUCH_S, f"Hook lief {dauer:.1f}s — er hat trotzdem gefetcht"


def test_ausserhalb_eines_repos_kein_netzversuch(tmp_path: Path, haengendes_git: Path) -> None:
    kein_repo = tmp_path / "kein-repo-schnell"
    kein_repo.mkdir()

    ergebnis, dauer = _hook_mit_haengendem_netz(kein_repo, haengendes_git)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""
    assert dauer < KEIN_NETZVERSUCH_S, f"Hook lief {dauer:.1f}s — er hat trotzdem gefetcht"


def test_leeres_repo_mit_remote_kein_netzversuch(
    tmp_path: Path, upstream: Path, haengendes_git: Path
) -> None:
    """Remote vorhanden, aber kein HEAD-Commit: der Vergleich hat keine linke Seite."""
    leer = tmp_path / "leer-mit-remote"
    leer.mkdir()
    _git(leer, "init", "--initial-branch=master", "--quiet")
    _git(leer, "remote", "add", "origin", str(upstream))

    ergebnis, dauer = _hook_mit_haengendem_netz(leer, haengendes_git)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""
    assert dauer < KEIN_NETZVERSUCH_S, f"Hook lief {dauer:.1f}s — er hat trotzdem gefetcht"
