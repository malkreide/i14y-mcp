"""Der User-Agent muss die Version tragen, die das Paket tatsaechlich ist.

Bis 0.3.1 sendete dieser Server ein nacktes Produkt-Token:

    USER_AGENT = "i14y-mcp (+https://github.com/malkreide/i14y-mcp)"

Nichts daran war falsch — es behauptete keine falsche Zahl. Aber der Betreiber
der Datenquelle konnte nicht erkennen, welches Release ihn anruft, und eine
portfolioweite Sonde konnte den Wert nicht gegen die installierte Version
pruefen: sie meldete `unverified`, was ausdruecklich kein Bestehen ist.

Geprueft wird die Eigenschaft, nicht der Wert: unten steht keine erwartete
Versionsnummer.
"""

from __future__ import annotations

import re
from importlib.metadata import version as pkg_version
from pathlib import Path

import i14y_mcp
from i14y_mcp.client import USER_AGENT

SRC = Path(__file__).parent.parent / "src" / "i14y_mcp"


def test_user_agent_carries_the_installed_version() -> None:
    assert USER_AGENT.startswith(f"i14y-mcp/{pkg_version('i14y-mcp')} ")


def test_dunder_version_is_the_installed_version() -> None:
    """Vorher ein Literal in `__init__.py` neben dem in `pyproject.toml`.

    Zwei Kopien derselben Zahl; genau diese Konstellation hat in
    hn-tech-signal-mcp dazu gefuehrt, dass `__version__` 0.2.1 meldete, waehrend
    das Paket als 0.2.4 ausgeliefert wurde.
    """
    assert i14y_mcp.__version__ == pkg_version("i14y-mcp")


def test_the_user_agent_names_a_version_at_all() -> None:
    """Das nackte Token darf nicht zurueckkehren."""
    assert re.match(r"^i14y-mcp/\d+\.\d+", USER_AGENT), USER_AGENT


def test_no_version_literal_under_src() -> None:
    """Ein handgeschriebenes Release unter `src/` ist der Fehler von vorn.

    Der Rueckfall `0.0.0+source` ist ausgenommen und als solcher erkennbar: ein
    PEP-440-Local-Segment nach `+` laesst sich nicht als Release lesen.
    """
    assignment = re.compile(
        r"""^\s*[A-Za-z_]*VERSION[A-Za-z_]*\s*(?::\s*[^=]+)?=\s*["'](\d+\.\d+[^"']*)["']""",
        re.IGNORECASE,
    )
    ua_literal = re.compile(r"""i14y-mcp/(\d+\.\d+[^\s"']*)""")

    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            for pattern in (assignment, ua_literal):
                m = pattern.search(line)
                if m and "+" not in m.group(1):
                    offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, "Versions-Literal unter src/:\n  " + "\n  ".join(offenders)


def test_that_the_scan_would_catch_the_regression() -> None:
    """Ein Test, der nur bestehen kann, beweist nichts."""
    assignment = re.compile(
        r"""^\s*[A-Za-z_]*VERSION[A-Za-z_]*\s*(?::\s*[^=]+)?=\s*["'](\d+\.\d+[^"']*)["']""",
        re.IGNORECASE,
    )
    assert assignment.search('__version__ = "0.3.1"')  # der reale Vorzustand
    m = assignment.search('__version__ = "0.0.0+source"')
    assert m and "+" in m.group(1)  # Rueckfall: erkannt, aber ausgenommen
