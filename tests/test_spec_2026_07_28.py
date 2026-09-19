"""Was «nativ auf Spec 2026-07-28» an diesem Server heisst — gemessen.

`tests/test_protocol_version.py` haelt fest, *welche* Revisionen dieser Server
bedient. Diese Datei prueft, ob er auf der modernen Revision auch etwas
*sagt*. Das ist nicht dieselbe Frage: die moderne Aera lief hier schon
vollstaendig, und trotzdem antwortete `server/discover` bis zu diesem Commit mit

    {"name": "i14y-mcp", "version": ""}   und   "instructions": null

— ein Katalogeintrag ohne Version und ohne ein Wort darueber, wofuer er gut
ist. Die 162 Tests davor blieben dabei alle gruen, weil keiner von ihnen je
hingesehen hat. Genau das ist der Grund fuer diese Datei.

Drei Flaechen, die die Revision `2026-07-28` neu belastet:

* **Identitaet.** Das SDK stempelt `serverInfo` unter *jede* moderne Antwort
  (`_meta["io.modelcontextprotocol/serverInfo"]`), nicht nur unter die
  Erkennung. Eine leere Version steht damit auf jedem Response.
* **`server/discover`.** Tritt an die Stelle von `initialize`; `instructions`
  ist dort die einzige Stelle, an der ein Server im Ganzen erklaert wird.
* **Frischehinweise (SEP-2549).** Jede cachebare Methode traegt `ttlMs` und
  `cacheScope`; ohne gesetzten Hinweis lautet die Antwort «sofort veraltet,
  nie teilen».

Gemessen wird durchgehend an der Antwort, nie an der Konfiguration: ein Blick
in `CACHE_HINTS` oder auf `SERVER_TITLE` waere auch dann gruen, wenn das
Argument am Konstruktor verlorenginge. Der stdio-Fall faehrt dafuer einen
echten Unterprozess — `Client(mcp)` verbindet in-process und umgeht die
JSON-RPC-Rahmung ganz (`_connect_inproc` im SDK), kann ueber den Transport,
den `uvx i14y-mcp` startet, also nichts aussagen.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys
from importlib.metadata import version as _dist_version
from typing import Any

import httpx
from mcp import Client, StdioServerParameters
from mcp.server.caching import CACHEABLE_METHODS
from mcp.server.mcpserver import MCPServer
from mcp_types import (
    CLIENT_CAPABILITIES_META_KEY,
    CLIENT_INFO_META_KEY,
    PROTOCOL_VERSION_META_KEY,
    SERVER_INFO_META_KEY,
)
from mcp_types.version import LATEST_MODERN_VERSION, MODERN_PROTOCOL_VERSIONS

from i14y_mcp.client import USER_AGENT
from i14y_mcp.server import (
    LIST_CACHE_TTL_MS,
    SERVER_DESCRIPTION,
    SERVER_WEBSITE_URL,
    build_http_app,
)

REPO = pathlib.Path(__file__).resolve().parents[1]

# Aus dem SDK, nicht als zweites Literal: dass diese Revision «2026-07-28»
# heisst, pinnt `tests/test_protocol_version.py` an genau einer Stelle. Ein
# Datum auch hier waere die Kopie, die beim naechsten Bump halb nachgezogen wird.
MODERN = LATEST_MODERN_VERSION

# Der Envelope, der eine moderne Verbindung oeffnet. Die drei Schluessel sind
# Pflicht — fehlt einer, antwortet der Server mit -32602 statt mit einem
# Resultat, und ein Test, der nur auf HTTP 200 prueft, haelt das fuer ein Nein.
_ENVELOPE: dict[str, Any] = {
    PROTOCOL_VERSION_META_KEY: MODERN,
    CLIENT_INFO_META_KEY: {"name": "spec-2026-07-28-test", "version": "1"},
    CLIENT_CAPABILITIES_META_KEY: {},
}
_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Host": "127.0.0.1:8000",
}


async def modern_call(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Eine moderne Anfrage durch den zusammengebauten ASGI-Stack.

    Gibt den JSON-RPC-Umschlag zurueck, nicht nur `result`: ob eine Methode
    geantwortet oder abgelehnt hat, ist bei mehreren Tests unten die eigentliche
    Frage.
    """
    app = build_http_app("streamable-http")
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": {**(params or {}), "_meta": _ENVELOPE},
    }
    headers = {**_HEADERS, "Mcp-Protocol-Version": MODERN, "Mcp-Method": method}
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://127.0.0.1:8000"
        ) as client:
            response = await client.post("/mcp", headers=headers, json=body)
    text = response.text
    for line in text.splitlines():  # SSE-Rahmen abstreifen, falls vorhanden
        if line.startswith("data: "):
            text = line[len("data: ") :]
    return json.loads(text)


# --------------------------------------------------------------------------
# Identitaet
# --------------------------------------------------------------------------


async def test_jede_moderne_antwort_traegt_die_installierte_version() -> None:
    """Der lasttragende Fall: `version` war leer, auf *jeder* Antwort.

    Geprueft an `tools/list` und nicht an `server/discover`, weil der Stempel
    gerade nicht auf die Erkennung beschraenkt ist — eine Zusicherung nur auf
    `server/discover` liesse offen, ob er ueberall steht.
    """
    envelope = await modern_call("tools/list")
    info = envelope["result"]["_meta"][SERVER_INFO_META_KEY]

    assert info["version"] == _dist_version("i14y-mcp"), (
        f"serverInfo meldet {info['version']!r}, installiert ist {_dist_version('i14y-mcp')!r}"
    )
    assert info["version"], "serverInfo traegt eine leere Version — der Ausgangsbefund"
    assert info["name"] == "i14y-mcp"


async def test_ein_server_ohne_identitaet_bleibt_stumm() -> None:
    """Negativkontrolle, gleiches SDK: ohne die Argumente ist `version` leer.

    Ohne sie liesse der Test oben offen, ob das SDK die Version inzwischen von
    selbst aus den Paket-Metadaten zieht — dann pruefte er nicht mehr, dass
    *wir* sie setzen.
    """
    kontrolle = MCPServer("kontrolle")
    assert kontrolle.version == ""
    assert kontrolle.instructions is None
    assert kontrolle.description is None
    assert kontrolle.title is None
    assert kontrolle.website_url is None


async def test_die_identitaet_traegt_einen_anzeigenamen() -> None:
    """`name` ist der Bezeichner, `title` der Anzeigename — dieselbe Trennung
    wie bei den Werkzeugen, eine Ebene hoeher.

    Diese Zusicherung fehlte in der ersten Fassung: die Gegenprobe entfernte
    `title=SERVER_TITLE` und kein einziger Test fiel. Aufgeschrieben war die
    Absicht damit, gedeckt nicht.
    """
    envelope = await modern_call("server/discover")
    info = envelope["result"]["_meta"][SERVER_INFO_META_KEY]

    assert info.get("title"), "serverInfo traegt keinen Anzeigenamen"
    assert info["title"] != info["name"], (
        "der Anzeigename wiederholt nur den Bezeichner und sagt einem Leser nichts"
    )


async def test_protokoll_und_user_agent_nennen_dieselbe_version() -> None:
    """Zwei Stellen, an denen dieser Server seine Version nennt — I14Y
    gegenueber im `User-Agent`, dem Client gegenueber im `serverInfo`. Beide
    kommen aus `importlib.metadata`; faellt eine auf ein Literal zurueck,
    trennen sie sich hier und nicht erst im Log einer fremden Behoerde."""
    envelope = await modern_call("server/discover")
    version = envelope["result"]["_meta"][SERVER_INFO_META_KEY]["version"]

    # Nicht `f"i14y-mcp/{version}" in USER_AGENT`: das war die erste Fassung,
    # und mit `version == ""` steht dort `"i14y-mcp/" in "i14y-mcp/0.3.2 ..."`
    # — also genau im Ausgangsbefund gruen. Die Gegenprobe hat es gezeigt.
    ua_version = re.fullmatch(r"i14y-mcp/(\S+) \(\+\S+\)", USER_AGENT)
    assert ua_version is not None, f"User-Agent hat eine andere Form: {USER_AGENT!r}"
    assert ua_version.group(1) == version, (
        f"serverInfo sagt {version!r}, der User-Agent {ua_version.group(1)!r}"
    )


async def test_registry_manifest_und_protokoll_beschreiben_denselben_server() -> None:
    """`server.json` und der Draht sind die zwei Stellen, an denen ein Client
    diesen Server beschrieben sieht — im Verzeichnis und in der Verbindung.
    Sie werden getrennt gepflegt und koennen deshalb auseinanderlaufen."""
    manifest = json.loads((REPO / "server.json").read_text(encoding="utf-8"))
    envelope = await modern_call("server/discover")
    info = envelope["result"]["_meta"][SERVER_INFO_META_KEY]

    assert info["description"] == manifest["description"] == SERVER_DESCRIPTION
    assert info["websiteUrl"] == manifest["websiteUrl"] == SERVER_WEBSITE_URL


# --------------------------------------------------------------------------
# server/discover
# --------------------------------------------------------------------------


async def test_discover_nennt_genau_die_modernen_revisionen() -> None:
    """`supportedVersions` ist die Liste, aus der ein Client waehlt. Sie kommt
    aus dem SDK; ein Bump, der sie erweitert, gehoert gesehen."""
    envelope = await modern_call("server/discover")
    assert envelope["result"]["supportedVersions"] == list(MODERN_PROTOCOL_VERSIONS)


async def test_der_server_erklaert_sich_auf_der_modernen_aera() -> None:
    """`instructions` war `null`. Auf 2026-07-28 ist das die einzige Stelle,
    an der ein Server als Ganzes erklaert wird — Tool-Beschreibungen erklaeren
    je ein Werkzeug, nicht die Quelle.

    Geprueft wird nicht die Laenge, sondern der eine Satz, ohne den Aufrufer
    nachweislich auflaufen: dass der Suchindex oben nur Datasets fuehrt. Der
    Befund steht seit dem 21.7.2026 in `search_catalog`, aber wer nicht schon
    dort ist, sieht ihn nie.
    """
    envelope = await modern_call("server/discover")
    instructions = envelope["result"].get("instructions")

    assert instructions, "server/discover liefert keine instructions"
    assert "Datasets only" in instructions, (
        "die instructions nennen die Dataset-Beschraenkung des Suchindex nicht — "
        "genau den Punkt, an dem Aufrufer auflaufen"
    )
    assert "list_concepts" in instructions, "kein Hinweis, womit Konzepte stattdessen gehen"


async def test_die_angekuendigten_faehigkeiten_stehen_gemessen_fest() -> None:
    """Pin, kein Wunsch: so sieht die Ankuendigung heute aus.

    Auf 2026-07-28 leiten sich `listChanged` und `resources.subscribe`
    ausschliesslich daraus ab, ob `subscriptions/listen` bedient wird
    (`Server.get_capabilities`) — und `MCPServer` verdrahtet den Handler
    bedingungslos. Dieser Server kuendigt damit eine Abo-Flaeche an, die er
    nicht benutzt: die 13 Tools stehen beim Import fest, eine
    `listChanged`-Benachrichtigung schickt er nie.

    Das ist nicht ueber die oeffentliche Oberflaeche abstellbar — nur ein
    vollstaendig ersetzter `server/discover`-Handler koennte es, und der waere
    eine zweite Wahrheit ueber die eigenen Faehigkeiten. Deshalb festgehalten
    statt geaendert: aendert das SDK die Ableitung, faellt es hier auf.
    """
    envelope = await modern_call("server/discover")
    assert envelope["result"]["capabilities"] == {
        "prompts": {"listChanged": True},
        "resources": {"listChanged": True, "subscribe": True},
        "tools": {"listChanged": True},
    }


# --------------------------------------------------------------------------
# Frischehinweise (SEP-2549)
# --------------------------------------------------------------------------


async def test_jede_beantwortete_cachebare_methode_traegt_einen_hinweis() -> None:
    """Die Liste kommt aus dem SDK, nicht aus unserem Dict.

    `CACHE_HINTS` gegen sich selbst zu pruefen kann nie zeigen, dass ein
    Eintrag fehlt. Hier wird jede Methode gefragt, die die Spec fuer cachebar
    erklaert; wer mit einem Resultat antwortet, muss auch einen Hinweis
    tragen. Genau so faellt der urspruengliche Fehlbefund auf: `prompts/list`,
    `resources/list` und `resources/templates/list` galten als «nicht
    registriert», antworten aber mit HTTP 200 und einer leeren Liste — und
    taten das ohne Hinweis, also dreimal dasselbe Nichts bei jeder Verbindung.

    Eine neu bediente cachebare Methode faellt ab jetzt hier auf, statt still
    mit `ttlMs: 0` zu antworten.
    """
    beantwortet: dict[str, dict[str, Any]] = {}
    for method in sorted(CACHEABLE_METHODS):
        envelope = await modern_call(method)
        if "result" in envelope:
            beantwortet[method] = envelope["result"]

    assert set(beantwortet) == {
        "tools/list",
        "prompts/list",
        "resources/list",
        "resources/templates/list",
        "server/discover",
    }, f"anderes Methoden-Set als erwartet: {sorted(beantwortet)}"

    ohne_hinweis = {m: r.get("ttlMs") for m, r in beantwortet.items() if not r.get("ttlMs")}
    assert not ohne_hinweis, (
        f"cachebar, aber «sofort veraltet»: {ohne_hinweis} — jeder Client fragt sie "
        "bei jeder Verbindung neu ab"
    )
    for method, result in beantwortet.items():
        assert result["ttlMs"] == LIST_CACHE_TTL_MS, method
        assert result["cacheScope"] == "public", method


async def test_die_inhalts_methode_traegt_keinen_hinweis() -> None:
    """Gegenstueck zum Test oben, und der Grund, warum er nicht einfach «alle
    cachebaren Methoden» verlangt: `resources/read` liefert Inhalt statt eines
    Verzeichnisses. Es steht in `CACHEABLE_METHODS`, wird von diesem Server
    aber nicht beantwortet — faellt es eines Tages doch an, ist der Scope neu
    zu entscheiden und nicht mitzukopieren."""
    envelope = await modern_call("resources/read", {"uri": "file:///nichts"})
    assert "result" not in envelope


# --------------------------------------------------------------------------
# Werkzeug-Metadaten
# --------------------------------------------------------------------------


async def test_jedes_werkzeug_traegt_einen_eigenen_titel() -> None:
    """`title` ist der Anzeigename, `name` der Bezeichner. Ohne Titel zeigt ein
    Client `search_codelist_entries`.

    Auf Eindeutigkeit geprueft, nicht nur auf Vorhandensein: zwei Werkzeuge
    unter demselben Titel sind fuer den Lesenden dasselbe Werkzeug, und ein
    per Copy-Paste uebernommener Titel faellt sonst niemandem auf.
    """
    envelope = await modern_call("tools/list")
    tools = envelope["result"]["tools"]

    ohne = sorted(t["name"] for t in tools if not t.get("title"))
    assert not ohne, f"ohne Titel: {ohne}"

    titel = [t["title"] for t in tools]
    doppelte = sorted({t for t in titel if titel.count(t) > 1})
    assert not doppelte, f"mehrfach vergebene Titel: {doppelte}"
    assert len(tools) == 13


# --------------------------------------------------------------------------
# stdio — der Transport, den `uvx i14y-mcp` startet
# --------------------------------------------------------------------------


async def test_der_stdio_transport_bedient_die_moderne_aera() -> None:
    """Ein echter Unterprozess, wie ein Desktop-Client ihn startet.

    Der einzige Test hier, der nicht ueber HTTP laeuft — und er kostet die
    Startzeit eines Interpreters. Das ist er wert: die HTTP-Tests messen den
    Pfad durch `StreamableHTTPSessionManager`, stdio faehrt durch
    `serve_dual_era_loop`. Dass die eine Aera bedient, belegt fuer die andere
    nichts, und stdio ist die Vorgabe (`I14Y_MCP_TRANSPORT` ungesetzt).

    `mode="auto"` statt eines festen `"2026-07-28"`: so sendet der Client ein
    echtes `server/discover` und uebernimmt dessen Antwort, statt die Revision
    zu behaupten. Mit festem Modus bleibt `server_info` leer — die Zusicherung
    unten waere dann nicht falsch, sondern unpruefbar.
    """
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "i14y_mcp"],
        env={**os.environ, "I14Y_MCP_TRANSPORT": "stdio", "LOG_LEVEL": "CRITICAL"},
    )
    async with Client(params, mode="auto") as client:
        assert client.protocol_version == MODERN
        assert client.server_info is not None
        assert client.server_info.version == _dist_version("i14y-mcp")
        assert client.instructions
        result = await client.list_tools()

    assert len(result.tools) == 13
    assert result.ttl_ms == LIST_CACHE_TTL_MS
