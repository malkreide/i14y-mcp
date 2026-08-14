#!/usr/bin/env python3
"""Record live I14Y responses into `tests/fixtures/`.

Why this exists: a handwritten fixture encodes the author's assumption about the
payload and therefore cannot refute it. When `/concepts` and `/publicservices`
turned out to label their records `name` rather than `title`, three tools
returned empty titles in production and the whole suite stayed green — the
stubs had invented a `title` key and agreed with the mapper instead of with the
source.

Herkunft, Datum, Auswahlregel und SHA-256 je Datei schreibt dieses Skript nach
`tests/fixtures/PROVENANCE.md`. Neu aufzeichnen:

    python scripts/record_fixtures.py

Braucht Netzzugang zu `api.i14y.admin.ch`. Entwicklungswerkzeug; weder das
Paket noch die Testsuite importieren es.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://api.i14y.admin.ch/api"
FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

# Weniger Datensaetze, volle Satzform. Die *Anzahl* zu kuerzen haelt die Dateien
# lesbar; *Felder* zu kuerzen wuerde genau das wegwerfen, wofuer eine
# Aufzeichnung da ist — die Teile der Antwort, die niemand erwartet haette.
SMALL = 2
MEDIUM = 3
ENTRIES = 5


def get(path: str, params: dict[str, Any] | None = None) -> tuple[str, Any, str]:
    """GET `path`; liefert (roher Text, geparstes JSON, vollstaendige URL)."""
    url = f"{BASE}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "i14y-mcp-recorder"})
    with urlopen(req, timeout=60) as resp:  # noqa: S310 - fester Host, keine Nutzereingabe
        raw = resp.read().decode("utf-8")
    return raw, json.loads(raw), url


def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    recorded_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entries: list[dict[str, Any]] = []
    print(f"Zeichne auf von {BASE}")

    def write(name: str, text: str, url: str, rule: str) -> None:
        # Eingerueckt speichern: ein Diff nach dem naechsten Aufzeichnen soll
        # zeigen, welches Feld sich geaendert hat, nicht eine einzige lange Zeile.
        text = json.dumps(json.loads(text), ensure_ascii=False, indent=2) + "\n"
        (FIXTURES / name).write_text(text, encoding="utf-8")
        blob = text.encode("utf-8")
        entries.append(
            {
                "name": name,
                "url": url,
                "rule": rule,
                "bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(),
            }
        )
        print(f"  ok  {name:<26} {len(blob):>7} B")

    # --- Sammel-Endpunkte ------------------------------------------------
    p = {"page": 1, "pageSize": SMALL}
    raw, datasets, url = get("/datasets", p)
    write("datasets_list.json", raw, url, f"Seite 1, {SMALL} von rund 2000 Datensaetzen")

    p = {"page": 1, "pageSize": MEDIUM}
    raw, services, url = get("/dataservices", p)
    write("dataservices_list.json", raw, url, f"Seite 1, {MEDIUM} Datensaetze")

    p = {"page": 1, "pageSize": SMALL}
    raw, public, url = get("/publicservices", p)
    write("publicservices_list.json", raw, url, f"Seite 1, {SMALL} Datensaetze; Label in `name`")

    p = {"page": 1, "pageSize": MEDIUM}
    raw, concepts, url = get("/concepts", p)
    write("concepts_list.json", raw, url, f"Seite 1, {MEDIUM} Datensaetze; Label in `name`")

    raw, agents, url = get("/agents", p)
    write("agents_list.json", raw, url, f"Seite 1, {MEDIUM} Datensaetze")

    raw, catalogs, url = get("/catalogs", p)
    write("catalogs_list.json", raw, url, f"Seite 1, {MEDIUM} Datensaetze")

    # --- Suche -----------------------------------------------------------
    # Enger Suchbegriff mit Absicht: `/search` ignoriert Paging und liefert die
    # ganze Treffermenge — deshalb deckelt der Server sie clientseitig.
    sp = {"query": "Sonderpädagogik", "language": "de", "structure": "WithoutStructure"}
    raw, search, url = get("/search", sp)
    n = len(search.get("data") or [])
    write("search.json", raw, url, f"vollstaendige Treffermenge zu «Sonderpaedagogik» ({n})")

    # --- Detail-Endpunkte, IDs aus den Listen oben -----------------------
    def first_id(body: Any) -> str | None:
        rows = body.get("data") if isinstance(body, dict) else None
        return rows[0].get("id") if isinstance(rows, list) and rows else None

    ds_id = first_id(datasets)
    if not ds_id:
        print("!! keine Dataset-ID in der Listenantwort")
        return 1
    raw, _, url = get(f"/datasets/{ds_id}")
    write("dataset_detail.json", raw, url, "vollstaendig; erster Datensatz aus datasets_list")

    svc_id = first_id(services)
    if not svc_id:
        print("!! keine DataService-ID in der Listenantwort")
        return 1
    raw, _, url = get(f"/dataservices/{svc_id}")
    write("dataservice_detail.json", raw, url, "vollstaendig; erster Eintrag aus dataservices_list")

    # Ein CodeList-Konzept, nicht irgendeines: nur solche haben Eintraege, die
    # ID muss also gewaehlt und nicht von Position 0 genommen werden.
    _, wide, _ = get("/concepts", {"page": 1, "pageSize": 100})
    code_id = next(
        (r.get("id") for r in (wide.get("data") or []) if r.get("conceptType") == "CodeList"),
        None,
    )
    if not code_id:
        print("!! kein CodeList-Konzept unter den ersten 100 — Suche verbreitern")
        return 1

    raw, _, url = get(f"/concepts/{code_id}")
    write("concept_detail.json", raw, url, "vollstaendig; erstes CodeList-Konzept")

    cp = {"language": "de", "page": 1, "pageSize": ENTRIES}
    raw, _, url = get(f"/concepts/{code_id}/codelist-entries/search", cp)
    write("codelist_entries.json", raw, url, f"Seite 1, {ENTRIES} Eintraege des Konzepts oben")

    _write_provenance(recorded_at, entries)
    print(f"\nPROVENANCE.md geschrieben, Aufzeichnungsdatum {recorded_at}")
    return 0


def _write_provenance(recorded_at: str, entries: list[dict[str, Any]]) -> None:
    lines = [
        "# Herkunft der Fixtures",
        "",
        "**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**",
        "",
        f"Aufgezeichnet am **{recorded_at}** von der einzigen Quelle dieses Servers:",
        f"`{BASE}`.",
        "",
        "Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht",
        "mehr zu unterscheiden — die Datei sieht gleich aus.",
        "",
        "**Es sind Ausschnitte, keine Vollabzuege.** Die Auswahlregel steht je",
        "Datei dabei; Feldstruktur und Schluesselnamen sind unangetastet. Eine",
        "Fixture belegt damit die *Form* der Antwort und einen datierten",
        "Ausschnitt ihres Inhalts — nicht den Bestand. Aussagen ueber",
        "Vollstaendigkeit gehoeren in Live-Tests.",
        "",
        "**`/concepts` und `/publicservices` nennen ihr Label `name`,** waehrend",
        "Datasets und Data Services `title` verwenden. Die erste Aufzeichnung hat",
        "das aufgedeckt: `list_concepts`, `get_concept` und `list_public_services`",
        "lieferten fuer jeden Datensatz einen leeren Titel, bei gruener Suite, weil",
        "die handgeschriebenen Vorgaenger einen `title`-Schluessel erfunden hatten.",
        "",
        "Fehlerpfade — 404, Timeouts, maskierte 4xx — bleiben handgeschrieben.",
        "Die lassen sich nicht auf Zuruf aufzeichnen.",
        "",
    ]
    for e in entries:
        lines += [
            f"## `{e['name']}`",
            "",
            f"- **Quelle:** `{e['url']}`",
            f"- **Aufgezeichnet:** {recorded_at}",
            f"- **Auswahl:** {e['rule']}",
            f"- **Groesse:** {e['bytes']} B",
            f"- **SHA-256:** `{e['sha256']}`",
            "",
        ]
    (FIXTURES / "PROVENANCE.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
