"""`main()` — der Einstiegspunkt, den `uvx i14y-mcp` und das Container-Image starten.

Diese Datei existiert, weil genau hier eine Luecke war. `tests/test_cors.py`
prueft `build_http_app` gruendlich, `tests/test_transport_security.py` die
Host-Allow-List — beide setzen aber *unterhalb* von `main()` an. Die Funktion
selbst rief kein Test je auf, und dort standen drei Zuweisungen an
`mcp.settings`, die es in mcp 2.x nicht mehr gibt.

Eine davon (`transport_security`) wurde behoben und mit einem Test versehen,
der wieder bei `build_http_app` ansetzt. Die beiden anderen (`host`, `port`)
blieben stehen. Der HTTP-Transport war damit weiterhin tot:

    ValueError: "Settings" object has no field "host"

Gemessen nicht am Quellbaum, sondern am gebauten Rad in einer frischen venv —
`i14y-mcp` mit `I14Y_MCP_TRANSPORT=streamable-http` beendete sich sofort mit
diesem Traceback, ohne je einen Port zu oeffnen. Eine Reparatur, die eine von
drei gleichartigen Zeilen entfernt und den Rest stehen laesst, sieht im Diff
vollstaendig aus; im Betrieb ist sie es nicht.

Zur Patch-Stelle: `uvicorn.run` wird ersetzt, also ein fremdes Modul. Das ist
hier die richtige Grenze und nicht die Falle aus CLAUDE.md — die Mechanik, um
die es geht, laeuft *vor* diesem Aufruf. Ein Stub am Ende der Kette kann einen
Fehlschlag davor nicht verdecken; er verhindert nur, dass der Test einen Port
oeffnet. `uvicorn` ist ausserdem eine harte Abhaengigkeit von `mcp` selbst, der
Test kann also nicht still uebersprungen werden.
"""

from __future__ import annotations

from typing import Any

import pytest
from mcp.server.mcpserver.server import Settings

from i14y_mcp import server


@pytest.fixture
def uvicorn_stub(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Faengt den Serve-Aufruf ab und haelt fest, womit er gerufen wurde."""
    import uvicorn

    aufrufe: list[dict[str, Any]] = []

    def fake_run(app: Any, **kwargs: Any) -> None:
        aufrufe.append({"app": app, **kwargs})

    monkeypatch.setattr(uvicorn, "run", fake_run)
    return aufrufe


@pytest.mark.parametrize("transport", ["streamable-http", "http", "sse"])
def test_der_http_einstiegspunkt_erreicht_uvicorn(
    transport: str, uvicorn_stub: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der lasttragende Fall: `main()` laeuft bis zum Serve-Aufruf durch.

    Alle drei Schreibweisen der Umgebungsvariablen gehen denselben Weg; eine
    davon zu pruefen liesse offen, ob die anderen zwei noch irgendwo abbiegen.
    """
    monkeypatch.setenv("I14Y_MCP_TRANSPORT", transport)
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "8123")
    monkeypatch.delenv("I14Y_MCP_ALLOWED_HOSTS", raising=False)

    server.main()

    assert len(uvicorn_stub) == 1, f"{transport} erreichte uvicorn nicht"
    aufruf = uvicorn_stub[0]
    assert aufruf["host"] == "127.0.0.1"
    assert aufruf["port"] == 8123
    assert aufruf["app"] is not None


def test_host_und_port_kommen_aus_der_umgebung(
    uvicorn_stub: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Gegenstueck zum Test oben: ohne diesen Fall waere er auch gegen ein
    `main()` gruen, das Umgebungswerte liest und dann Konstanten weiterreicht."""
    monkeypatch.setenv("I14Y_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("HOST", "0.0.0.0")  # noqa: S104 — Testwert, kein Bind
    monkeypatch.setenv("PORT", "9001")
    monkeypatch.setenv("I14Y_MCP_ALLOWED_HOSTS", "mcp.example.ch")

    server.main()

    assert uvicorn_stub[0]["host"] == "0.0.0.0"  # noqa: S104
    assert uvicorn_stub[0]["port"] == 9001


def test_die_vorgabe_ist_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ohne gesetzte Variable faehrt `main()` stdio — der Weg, den ein
    Desktop-Client nimmt. Ohne diesen Fall koennte die HTTP-Verzweigung alles
    einfangen, ohne dass ein Test es merkt."""
    gerufen: list[str] = []
    monkeypatch.delenv("I14Y_MCP_TRANSPORT", raising=False)
    monkeypatch.setattr(server.mcp, "run", lambda transport: gerufen.append(transport))

    server.main()

    assert gerufen == ["stdio"]


def test_settings_fuehrt_die_felder_nicht_die_hier_einmal_gesetzt_wurden() -> None:
    """Die Vorgabe lesen, bevor man einem Objekt ein Feld zuschreibt.

    Alle drei Namen wurden einmal auf `mcp.settings` gesetzt, weil die 1.x-API
    sie dort fuehrte. In 2.x sind sie weg, und pydantic wirft auf eine Zuweisung
    an ein nicht deklariertes Feld — kein stilles Ignorieren, sondern ein
    sofortiger Abbruch.

    Faellt dieser Test, hat das SDK ein Feld zurueckgebracht. Dann ist neu zu
    entscheiden, ob die Zuweisung wieder etwas bewirkt — nicht sie blind
    einzufuegen, weil das Feld existiert.
    """
    verboten = {"host", "port", "transport_security"} & set(Settings.model_fields)
    assert not verboten, (
        f"`Settings` fuehrt jetzt {sorted(verboten)}; die Entscheidung in `main()` "
        "und `_run_http` ist neu zu bewerten"
    )
