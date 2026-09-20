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

import pathlib
import re
from typing import Any

import pytest
from mcp.server.mcpserver.server import Settings

from i14y_mcp import server

_ROOT = pathlib.Path(__file__).resolve().parents[1]


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


# ---------------------------------------------------------------------------
# Der Transport, den das Container-Image vorgibt
# ---------------------------------------------------------------------------
#
# Das Image setzte `I14Y_MCP_TRANSPORT=sse`, und genau dieser Wert ist der eine,
# den ein gehosteter Betrieb nicht brauchen kann: Ein Claude.ai-Custom-Connector
# spricht Streamable HTTP und holt den Server unter `/mcp` ab; die SSE-App
# serviert `/sse` und `/messages` und hat `/mcp` gar nicht. Am 20.9.2026 im
# Railway-Deployment aufgefallen.
#
# Die Tests unten setzen nicht an der Zeichenkette an, sondern am gebauten Stack:
# Sie lesen den Vorgabewert aus dem Dockerfile, fahren `main()` damit und sehen
# nach, welche Pfade herauskommen. Ein Vergleich `wert == "streamable-http"`
# waere gruen geblieben, wenn das SDK den Pfad verschoben haette — und genau das
# ist die Zusicherung, auf die es hier ankommt.
#
# Zweitens faengt das den stillen Ausfall: `main()` nimmt nur `sse`,
# `streamable-http` und `http`; jede andere Schreibweise — ein `streamable_http`
# mit Unterstrich etwa — faellt in den stdio-Zweig. Der Container startet dann,
# oeffnet nie einen Port, und der Health-Check ist das Einzige, was rot wird.

_DOCKERFILE = _ROOT / "Dockerfile"
_COMPOSE = _ROOT / "compose.yaml"

# `I14Y_MCP_TRANSPORT=<wert>` im Dockerfile-ENV bzw. `I14Y_MCP_TRANSPORT: <wert>`
# in der Compose-Umgebung. Kommentarzeilen sind ausgenommen — die Begruendung
# im Dockerfile nennt `sse` im Fliesstext, und ohne diesen Ausschluss haette der
# Parser den alten Wert aus einem Kommentar gelesen.
_TRANSPORT_ZEILE = re.compile(r"""^\s*I14Y_MCP_TRANSPORT\s*[=:]\s*["']?([^"'\s\\]+)""")


def _transport_vorgabe(pfad: pathlib.Path) -> str:
    """Den in dieser Datei gesetzten Transport lesen — genau einen."""
    treffer = [
        m.group(1)
        for zeile in pfad.read_text(encoding="utf-8").splitlines()
        if not zeile.lstrip().startswith("#")
        for m in [_TRANSPORT_ZEILE.match(zeile)]
        if m
    ]
    assert len(treffer) == 1, (
        f"{pfad.name} setzt I14Y_MCP_TRANSPORT {len(treffer)}x ({treffer}); "
        "erwartet wird genau eine Stelle"
    )
    return treffer[0]


def _pfade(app: Any) -> set[str]:
    """Die Pfade, die eine gebaute ASGI-App bedient (Routen und Mounts)."""
    return {p for r in app.routes if (p := getattr(r, "path", None)) is not None}


def test_der_parser_findet_die_vorgaben_ueberhaupt() -> None:
    """Gegenprobe zu allem, was unten den Parser benutzt.

    Ohne diesen Fall koennte `_transport_vorgabe` an der Kommentarzeile oder an
    einer geaenderten Schreibweise vorbeilesen — die Tests darunter wuerden dann
    nicht etwa rot, sie kaemen gar nicht erst dazu, etwas zu pruefen.
    """
    assert _DOCKERFILE.exists() and _COMPOSE.exists()
    assert _transport_vorgabe(_DOCKERFILE)
    assert _transport_vorgabe(_COMPOSE)


def test_der_image_default_erreicht_uvicorn(
    uvicorn_stub: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der Wert aus dem Dockerfile ist einer, den `main()` als HTTP erkennt.

    Faellt dieser Test, startet der Container in den stdio-Zweig und oeffnet nie
    einen Port — ohne Traceback, ohne Logzeile, die es benennt.
    """
    monkeypatch.setenv("I14Y_MCP_TRANSPORT", _transport_vorgabe(_DOCKERFILE))
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "8000")
    monkeypatch.delenv("I14Y_MCP_ALLOWED_HOSTS", raising=False)

    server.main()

    assert len(uvicorn_stub) == 1, "der Image-Default landete nicht bei uvicorn"


def test_der_image_default_serviert_den_connector_pfad(
    uvicorn_stub: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Die lasttragende Zusicherung: Das Image serviert `/mcp`, nicht `/sse`.

    Gemessen an der App, die `main()` tatsaechlich an uvicorn uebergibt — nicht
    an einem direkt gerufenen `build_http_app`. Der Weg dazwischen ist genau der,
    auf dem der Befund entstanden ist.
    """
    monkeypatch.setenv("I14Y_MCP_TRANSPORT", _transport_vorgabe(_DOCKERFILE))
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "8000")
    monkeypatch.delenv("I14Y_MCP_ALLOWED_HOSTS", raising=False)

    server.main()
    pfade = _pfade(uvicorn_stub[0]["app"])

    assert "/mcp" in pfade, (
        f"Das Image serviert {sorted(pfade)}; ein Claude.ai-Custom-Connector "
        "verbindet sich auf /mcp"
    )
    assert "/sse" not in pfade


def test_die_beiden_transporte_sind_an_ihren_pfaden_unterscheidbar() -> None:
    """Gegenprobe zum Test darueber.

    Servierten beide Apps `/mcp`, waere jene Zusicherung auch gegen ein Image
    mit `sse` gruen — sie saehe richtig aus und pruefte nichts. Dieser Fall haelt
    fest, dass der Pfad die Transporte wirklich trennt; verschiebt das SDK ihn,
    faellt er hier und nicht in einem Deployment.
    """
    assert "/mcp" in _pfade(server.build_http_app("streamable-http", None, "127.0.0.1"))
    sse = _pfade(server.build_http_app("sse", None, "127.0.0.1"))
    assert "/sse" in sse
    assert "/mcp" not in sse


def test_compose_ueberstimmt_das_image_nicht() -> None:
    """`compose.yaml` setzte die Variable eigenstaendig auf `sse`.

    Eine Aenderung allein am Dockerfile haette `docker compose up` deshalb auf
    genau dem Transport gelassen, der abgeloest werden sollte — im Diff
    vollstaendig aussehend, im Betrieb nicht. Dieselbe Klasse wie die drei
    `mcp.settings`-Zeilen oben.
    """
    assert _transport_vorgabe(_COMPOSE) == _transport_vorgabe(_DOCKERFILE)
