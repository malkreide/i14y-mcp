"""Die ruff-Version steht an genau einer Stelle, und beide Gates reichen gleich weit.

Beides ist hier bereits so: `ruff==0.16.1` im `[dev]`-Extra, kein Workflow
nennt eine zweite Version, und `ruff check` wie `ruff format --check` laufen
ueber `src/ tests/ scripts/`. Dieser Test haelt den Zustand, statt ihn zu
behaupten — die CLAUDE.md tut Letzteres, und ein Satz faellt nicht um.

Der Rueckfall waere still. Ein `pip install ruff==<version>` in einem Workflow
liefe nach dem dev-Install und gewaenne gegen pyproject: Wer den Pin dort
anhebt, veraenderte die CI nicht. Kein Gate wird davon rot, die beiden Laeufe
sind sich nur ueber die Regeln uneinig. Dasselbe beim Umfang — faellt
`scripts/` aus einem der Gates, bleibt `classify_live_run.py` ungeprueft, und
das ist ausgerechnet das Skript, das entscheidet, ob ein roter Live-Lauf ein
Issue aufmacht.

Bewusst ohne `tomllib`: Die CI faehrt hier auch Python 3.10, und dort gibt es
das Modul noch nicht. Ein Test, der auf einer Matrix-Zeile mit
ModuleNotFoundError abbricht, prueft dort gar nichts.
"""

from __future__ import annotations

import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOWS = _ROOT / ".github" / "workflows"

# Formen, in denen ein Schritt ein Paket eigenstaendig installiert. Die erste
# Fassung dieses Tests kannte nur `pip install ruff` und liess damit
# `pip install --upgrade ruff==…`, `pip install "ruff==…"`, `pip3 install`,
# `uv tool install` und `uv run --with ruff==…` durch — allesamt Formen, die
# den Pin genauso ueberstimmen. Aufgefallen ist das in einem Codex-Review.
_INSTALL_FORM = re.compile(
    r"(?:pip3?\s+install|python\s+-m\s+pip\s+install|uv\s+pip\s+install"
    r"|uv\s+tool\s+install|uv\s+add|pipx\s+install|--with)\b"
)
# ruff als eigenes Paket-Argument. Anfuehrungszeichen sind erlaubt, ein
# vorangehendes Wort-, Pfad- oder Bindestrich-Zeichen nicht: sonst zaehlten
# `ruff-lsp` und `scripts/ruff_helper.py` mit.
_RUFF_PAKET = re.compile(r"""(?<![\w./-])["']?ruff(?![\w-])""")


def _installiert_ruff(zeile: str) -> bool:
    """Installiert diese Zeile ruff als benanntes Paket?

    `pip install -e ".[dev]"` zieht ruff ebenfalls herein — das ist aber der
    richtige Weg und darf nicht anschlagen. Entscheidend ist deshalb, ob nach
    dem Install-Befehl ein eigenes Argument `ruff` steht.
    """
    treffer = _INSTALL_FORM.search(zeile)
    return bool(treffer) and bool(_RUFF_PAKET.search(zeile[treffer.end() :]))


def _workflow_dateien() -> list[pathlib.Path]:
    """Beide Endungen: GitHub laedt `*.yml` UND `*.yaml`."""
    return sorted([*_WORKFLOWS.glob("*.yml"), *_WORKFLOWS.glob("*.yaml")])


# Eine ruff-Angabe in einer Abhaengigkeitsliste: `"ruff==0.16.1"`,
# `"ruff>=0.4.0"`, `"ruff"`. Die Anfuehrungszeichen im Muster halten die
# Sektion `[tool.ruff]` heraus; nach `ruff` darf nur ein Vergleichsoperator
# oder das schliessende Zeichen folgen, sonst zaehlte `"ruff-lsp"` mit.
_RUFF_SPEC = re.compile(r"""["']ruff((?:[<>=!~][^"']*)?)["']""")


def _ruff_angaben() -> list[str]:
    text = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return [m.group(0).strip("\"'") for m in _RUFF_SPEC.finditer(text)]


def _ohne_kommentare(pfad: pathlib.Path) -> list[str]:
    """Zeilen ohne YAML-Kommentare — sonst loest ein erklaerender Hinweis den Test aus."""
    return [
        z.strip()
        for z in pfad.read_text(encoding="utf-8").splitlines()
        if not z.lstrip().startswith("#")
    ]


def test_ruff_ist_exakt_gepinnt() -> None:
    """Eine Spanne laesst lokalen Lauf und CI verschiedene Versionen fahren."""
    angaben = _ruff_angaben()
    assert len(angaben) == 1, f"genau eine ruff-Angabe erwartet, gefunden: {angaben}"
    assert re.fullmatch(r"ruff==\d+\.\d+\.\d+", angaben[0]), (
        f"ruff muss als ruff==X.Y.Z gepinnt sein, gefunden {angaben[0]!r}."
    )


def test_der_pin_ist_die_einzige_versionsquelle() -> None:
    """Kein Workflow darf ruff selbst installieren."""
    for workflow in _workflow_dateien():
        treffer = [z for z in _ohne_kommentare(workflow) if _installiert_ruff(z)]
        assert not treffer, (
            f"{workflow.name} installiert ruff direkt ({treffer}). Dieser Schritt "
            "laeuft nach dem dev-Install und ueberstimmt den Pin in pyproject."
        )


def test_beide_ruff_gates_haben_denselben_umfang() -> None:
    """Ein Verzeichnis, das nur eines der beiden Gates sieht, ist ungeprueft."""
    zeilen = _ohne_kommentare(_WORKFLOWS / "ci.yml")
    check = [z for z in zeilen if "ruff check" in z]
    formatieren = [z for z in zeilen if "ruff format" in z]
    assert len(check) == 1 and len(formatieren) == 1, (
        f"je genau einen Aufruf erwartet, gefunden check={check} format={formatieren}"
    )
    umfang_check = check[0].split("ruff check", 1)[1].split()
    umfang_format = [t for t in formatieren[0].split("ruff format", 1)[1].split() if t != "--check"]
    assert umfang_check == umfang_format, (
        f"ruff check prueft {umfang_check}, ruff format prueft {umfang_format} — "
        "ein Verzeichnis faellt damit aus einem der beiden Gates."
    )
    assert "scripts/" in umfang_check, (
        f"`scripts/` fehlt im Gate-Umfang ({umfang_check}); die Skripte dort "
        "werden dann von ruff nie gesehen."
    )


def test_der_workflow_scan_findet_ueberhaupt_etwas() -> None:
    """Sichert die Pruefungen oben gegen ein leeres Verzeichnis ab."""
    workflows = _workflow_dateien()
    assert len(workflows) >= 2, f"Workflow-Scan findet fast nichts: {workflows}"
    assert any("ruff check" in w.read_text() for w in workflows), (
        "kein Workflow ruft ruff auf — der Scan sucht am falschen Ort"
    )


def test_unter_scripts_liegt_ueberhaupt_python() -> None:
    """Sonde: Ohne Dateien dort waere die Umfang-Forderung oben folgenlos."""
    skripte = sorted((_ROOT / "scripts").glob("*.py"))
    assert skripte, "keine Python-Dateien unter scripts/ — dann prueft der Umfang dort nichts"


def test_der_erkenner_kennt_die_gaengigen_installationsformen() -> None:
    """Der Scan ist nur so gut wie das, was er als Install erkennt.

    Ohne diese Tabelle ist die Zusicherung oben gruen, weil sie die Form nicht
    kennt — nicht, weil sie fehlt. Genau so war es: Die erste Fassung suchte
    woertlich nach `pip install ruff` und uebersah fuenf von sieben geprueften
    Schreibweisen.
    """
    muss_treffen = [
        "run: pip install ruff==0.16.1",
        "run: pip install --upgrade ruff==0.16.1",
        'run: pip install "ruff==0.16.1"',
        "run: pip install 'ruff==0.16.1'",
        "run: pip3 install ruff==0.16.1",
        "run: python -m pip install ruff==0.16.1",
        "run: uv pip install ruff==0.16.1 --system",
        "run: uv tool install ruff==0.16.1",
        "run: uv add ruff==0.16.1",
        "run: pipx install ruff==0.16.1",
        "run: uv run --with ruff==0.16.1 ruff check src/",
        "run: pip install ruff",
        "run: pip install pytest ruff==0.16.1",
        "run: pip install ruff[extra]==0.16.1",
    ]
    darf_nicht_treffen = [
        'run: pip install -e ".[dev]"',
        'run: uv pip install -e ".[dev]" --system',
        "run: ruff check src/ tests/ scripts/",
        "run: ruff format --check src/ tests/",
        "run: pip install ruff-lsp",
        "run: pip install uv",
        "run: python -m pip install --upgrade pip",
        "run: pip install build hatchling",
        "run: uv run --with pip-audit pip-audit",
        "run: python scripts/ruff_helper.py",
        "run: pip install -r requirements.txt",
        "name: Lint mit ruff",
    ]
    uebersehen = [z for z in muss_treffen if not _installiert_ruff(z)]
    assert not uebersehen, f"Erkenner uebersieht: {uebersehen}"
    fehlalarm = [z for z in darf_nicht_treffen if _installiert_ruff(z)]
    assert not fehlalarm, f"Erkenner schlaegt faelschlich an: {fehlalarm}"


# --- Der Gate-Block in CLAUDE.md ------------------------------------------
#
# Die CLAUDE.md zitiert die CI-Gates woertlich. Genau das war einmal falsch:
# der Block nannte vier Befehle, der Fliesstext sprach von «drei», und
# `check_version_sync.py` lief in der CI, ohne irgendwo aufzutauchen — der
# Absatz behauptete sogar ausdruecklich, es gebe kein Versions-Sync-Gate.
# Wer danach arbeitet, prueft lokal weniger als die CI und sucht den
# Unterschied spaeter im Diff.
#
# Ein Zitat, das niemand nachschlaegt, ist eine Behauptung. Dieser Test
# schlaegt nach.

_CLAUDE_MD = _ROOT / "CLAUDE.md"

# `pip install -e ".[dev]"` ist die Vorbereitung, kein Gate: der Schritt
# stellt die Umgebung her, in der die anderen laufen.
_KEIN_GATE = re.compile(r"^pip install -e")


def _ci_gate_befehle() -> list[str]:
    """Die `run:`-Befehle aus ci.yml, in Reihenfolge, ohne den Install-Schritt.

    Von Hand geparst statt mit PyYAML: das Paket ist keine Abhaengigkeit
    dieses Projekts, und ein Test, der eine neue Abhaengigkeit mitbringt,
    laeuft irgendwo nicht.
    """
    befehle: list[str] = []
    block_einzug: int | None = None

    for zeile in (_WORKFLOWS / "ci.yml").read_text(encoding="utf-8").splitlines():
        if block_einzug is not None:
            if not zeile.strip():
                continue
            einzug = len(zeile) - len(zeile.lstrip())
            if einzug >= block_einzug:
                inhalt = zeile.strip()
                if not inhalt.startswith("#") and not _KEIN_GATE.match(inhalt):
                    befehle.append(inhalt)
                continue
            block_einzug = None

        treffer = re.match(r"^(\s*)run:\s*(.*)$", zeile)
        if treffer:
            rest = treffer.group(2).strip()
            if rest in {"|", ">", "|-", ">-"}:
                block_einzug = len(treffer.group(1)) + 1
            elif rest and not _KEIN_GATE.match(rest):
                befehle.append(rest)

    return befehle


def _claude_md_gate_block() -> list[str]:
    """Die Zeilen des ```bash-Blocks, der auf die Gate-Ueberschrift folgt."""
    zeilen = _CLAUDE_MD.read_text(encoding="utf-8").splitlines()
    for i, zeile in enumerate(zeilen):
        if "CI-Gates" in zeile and "ci.yml" in zeile:
            start = next(j for j in range(i, len(zeilen)) if zeilen[j].startswith("```"))
            ende = next(j for j in range(start + 1, len(zeilen)) if zeilen[j].startswith("```"))
            return [z.strip() for z in zeilen[start + 1 : ende] if z.strip()]
    raise AssertionError("Kein Absatz in CLAUDE.md, der die CI-Gates aus ci.yml zitiert")


def test_claude_md_zitiert_die_ci_gates_vollstaendig() -> None:
    doku = _claude_md_gate_block()
    echt = _ci_gate_befehle()

    fehlt = [b for b in echt if b not in doku]
    zuviel = [b for b in doku if b not in echt]
    assert not fehlt, f"CLAUDE.md nennt diese Gates nicht: {fehlt}"
    assert not zuviel, f"CLAUDE.md nennt Gates, die ci.yml nicht faehrt: {zuviel}"
    assert doku == echt, f"Reihenfolge weicht ab:\n  CLAUDE.md: {doku}\n  ci.yml:    {echt}"


def test_der_ci_parser_findet_ueberhaupt_etwas() -> None:
    """Gegenprobe zum Parser: faende er nichts, waere der Vergleich oben leer
    und damit immer gruen — genau die Sorte Test, die nichts prueft."""
    befehle = _ci_gate_befehle()
    assert len(befehle) >= 4, befehle
    assert any("pytest" in b for b in befehle), befehle


def test_jedes_genannte_skript_existiert() -> None:
    """`python scripts/x.py` in einem Gate muss auch da liegen."""
    for befehl in _ci_gate_befehle():
        for pfad in re.findall(r"\bscripts/\S+\.py\b", befehl):
            assert (_ROOT / pfad).is_file(), f"{befehl!r} ruft {pfad} auf, das es nicht gibt"
