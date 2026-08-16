"""Every external endpoint, driven from a recorded response.

The handwritten stubs elsewhere in this suite test the *error* paths — a 404, a
timeout, a masked 400 — which cannot be recorded on demand and are fine as
inventions. What they cannot do is tell us the shape of a success payload: they
agree with whatever the author assumed. These tests replay real responses
instead, so a renamed field upstream fails here rather than in production.

Herkunft, Datum, Auswahlregel und SHA-256 je Datei stehen in
`tests/fixtures/PROVENANCE.md`; neu aufzeichnen mit
`python scripts/record_fixtures.py`.
"""

from __future__ import annotations

import datetime as dt
import re

import httpx
import pytest
import respx
from fixture_data import fixture_json, fixture_records, provenance, recorded_names

from i14y_mcp import client as c
from i14y_mcp import server

BASE = c.BASE_URL

# Jeder externe Endpunkt, den dieser Server aufruft, und die Fixture dazu. Ein
# Tool ohne Aufzeichnung faellt in `test_jeder_endpunkt_hat_eine_aufzeichnung`.
ENDPOINTS = {
    "/search": "search.json",
    "/datasets": "datasets_list.json",
    "/datasets/{id}": "dataset_detail.json",
    "/dataservices": "dataservices_list.json",
    "/dataservices/{id}": "dataservice_detail.json",
    "/publicservices": "publicservices_list.json",
    "/concepts": "concepts_list.json",
    "/concepts/{id}": "concept_detail.json",
    "/concepts/{id}/codelist-entries/search": "codelist_entries.json",
    "/agents": "agents_list.json",
    "/catalogs": "catalogs_list.json",
}


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    async def _instant(_seconds):
        return None

    monkeypatch.setattr(c, "_sleep", _instant)


def detail_id(name: str) -> str:
    """Die ID des aufgezeichneten Detail-Datensatzes, aus der Fixture selbst.

    Aus der Aufzeichnung gelesen statt danebengeschrieben: eine zweite Stelle
    mit derselben UUID waere beim naechsten Aufzeichnen still veraltet.
    """
    return fixture_json(name)["data"]["id"]


def mount(path: str, name: str) -> None:
    """Serviert Fixture `name` unter `path`. Aufgezeichnet wurde durchweg 200."""
    respx.get(f"{BASE}{path}").mock(return_value=httpx.Response(200, json=fixture_json(name)))


# --------------------------------------------------------------------------
# Herkunft
# --------------------------------------------------------------------------


def test_provenance_nennt_ein_brauchbares_aufnahmedatum():
    """Eine Aufzeichnung ohne Datum ist eine undatierte Behauptung ueber die Quelle."""
    match = re.search(r"Aufgezeichnet am \*\*(\d{4}-\d{2}-\d{2})\*\*", provenance())
    assert match, "PROVENANCE.md nennt kein Aufnahmedatum im erwarteten Format"
    when = dt.date.fromisoformat(match.group(1))
    assert when <= dt.datetime.now(dt.timezone.utc).date(), "Aufnahmedatum liegt in der Zukunft"


def test_jede_fixture_steht_in_der_provenance():
    """Sonst waechst der Ordner und der Nachweis bleibt zurueck."""
    text = provenance()
    fehlend = [n for n in recorded_names() if f"## `{n}`" not in text]
    assert not fehlend, f"ohne Eintrag in PROVENANCE.md: {fehlend}"


def test_jeder_endpunkt_hat_eine_aufzeichnung():
    """Bewacht die Regel selbst: eine aufgezeichnete Antwort je externem Endpunkt."""
    fehlend = sorted(set(ENDPOINTS.values()) - set(recorded_names()))
    assert not fehlend, f"Endpunkte ohne Aufzeichnung: {fehlend}"


# --------------------------------------------------------------------------
# Sammlungen
# --------------------------------------------------------------------------


@respx.mock
async def test_search_maps_recorded_hits():
    mount("/search", "search.json")
    result = await server.search_catalog(query="Sonderpädagogik")
    assert result.total_matched == len(fixture_records("search.json"))
    assert result.returned == result.total_matched
    assert all(h.title for h in result.hits), "recorded hits must map to a title"
    assert all(h.id for h in result.hits)


@respx.mock
async def test_list_datasets_maps_recorded_records():
    rows = fixture_records("datasets_list.json")
    mount("/datasets", "datasets_list.json")
    result = await server.list_datasets(page_size=len(rows))
    assert result.returned == len(rows)
    assert all(d.title for d in result.datasets), "every recorded dataset has a title"
    assert any(d.publisher for d in result.datasets)


@respx.mock
async def test_list_data_services_maps_recorded_records():
    rows = fixture_records("dataservices_list.json")
    mount("/dataservices", "dataservices_list.json")
    result = await server.list_data_services(page_size=len(rows))
    assert result.returned == len(rows)
    assert all(s.title for s in result.data_services)


@respx.mock
async def test_list_public_services_maps_recorded_records():
    """`/publicservices` labels records `name`, not `title` — see map_public_service."""
    rows = fixture_records("publicservices_list.json")
    mount("/publicservices", "publicservices_list.json")
    result = await server.list_public_services(page_size=len(rows))
    assert result.returned == len(rows)
    assert all(p.title for p in result.public_services), (
        "public services carry their label in `name`; a mapper reading only "
        "`title` returns None for every record"
    )


@respx.mock
async def test_list_concepts_maps_recorded_records():
    """`/concepts` labels records `name`, not `title` — see map_concept."""
    rows = fixture_records("concepts_list.json")
    mount("/concepts", "concepts_list.json")
    result = await server.list_concepts(page_size=len(rows))
    assert result.returned == len(rows)
    assert all(cc.title for cc in result.concepts), (
        "concepts carry their label in `name`; a mapper reading only `title` "
        "returns None for every record"
    )
    assert any(cc.concept_type for cc in result.concepts)


@respx.mock
async def test_list_publishers_maps_recorded_records():
    rows = fixture_records("agents_list.json")
    mount("/agents", "agents_list.json")
    result = await server.list_publishers(page_size=len(rows))
    assert result.returned == len(rows)
    assert all(p.name for p in result.publishers)


@respx.mock
async def test_list_catalogs_maps_recorded_records():
    rows = fixture_records("catalogs_list.json")
    mount("/catalogs", "catalogs_list.json")
    result = await server.list_catalogs(page_size=len(rows))
    assert result.returned == len(rows)
    assert all(cat.title for cat in result.catalogs)


# --------------------------------------------------------------------------
# Detail-Endpunkte
# --------------------------------------------------------------------------


@respx.mock
async def test_get_dataset_maps_recorded_detail():
    ds_id = detail_id("dataset_detail.json")
    mount(f"/datasets/{ds_id}", "dataset_detail.json")
    result = await server.get_dataset(dataset_id=ds_id)
    assert result.dataset.id == ds_id
    assert result.dataset.title


@respx.mock
async def test_get_dataset_distributions_maps_recorded_detail():
    ds_id = detail_id("dataset_detail.json")
    mount(f"/datasets/{ds_id}", "dataset_detail.json")
    result = await server.get_dataset_distributions(dataset_id=ds_id)
    recorded = fixture_json("dataset_detail.json")["data"].get("distributions") or []
    assert result.returned == len(recorded)


@respx.mock
async def test_get_data_service_maps_recorded_detail():
    svc_id = detail_id("dataservice_detail.json")
    mount(f"/dataservices/{svc_id}", "dataservice_detail.json")
    result = await server.get_data_service(data_service_id=svc_id)
    assert result.data_service.id == svc_id
    assert result.data_service.title


@respx.mock
async def test_get_concept_maps_recorded_detail():
    concept_id = detail_id("concept_detail.json")
    mount(f"/concepts/{concept_id}", "concept_detail.json")
    result = await server.get_concept(concept_id=concept_id)
    assert result.concept.id == concept_id
    assert result.concept.title, "concept detail carries its label in `name` too"


@respx.mock
async def test_search_codelist_entries_maps_recorded_entries():
    entries = fixture_records("codelist_entries.json")
    # Die Konzept-ID steht in den Eintraegen selbst — kein zweiter Ort, der
    # beim naechsten Aufzeichnen veralten koennte.
    concept_id = entries[0]["conceptId"]
    mount(f"/concepts/{concept_id}/codelist-entries/search", "codelist_entries.json")
    result = await server.search_codelist_entries(concept_id=concept_id, page_size=len(entries))
    assert result.returned == len(entries)
    assert all(e.code for e in result.entries)
    assert all(e.name for e in result.entries)


# --------------------------------------------------------------------------
# Der Nachweis, nachgerechnet
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted(n for n in recorded_names() if n != "PROVENANCE.md"))
def test_die_pruefsumme_im_nachweis_stimmt(name):
    """Eine Pruefsumme, die niemand nachrechnet, ist Zierde.

    Sie steht im Nachweis, um genau einen Fall zu fangen: eine Aufzeichnung,
    die nach dem Lauf von Hand nachgebessert wurde. Eine korrigierte Antwort
    ist wieder eine erfundene — und von aussen ist ihr das nicht anzusehen.
    Ohne diesen Test faengt die Summe nichts.

    Gerechnet wird ueber die Bytes auf der Platte, nicht ueber den Loader:
    genau die hat der Recorder gehasht, und ein Loader, der unterwegs dekodiert
    oder normalisiert, wuerde die Pruefung gegen sich selbst fuehren.
    """
    import hashlib
    import re
    from pathlib import Path

    teile = provenance().split(f"## `{name}`", 1)
    assert len(teile) == 2, f"{name} hat keinen Block in PROVENANCE.md"
    treffer = re.search(r"\*\*SHA-256:\*\*\s*`([0-9a-f]{64})`", teile[1].split("## ", 1)[0])
    assert treffer, f"{name} steht ohne Pruefsumme im Nachweis"
    roh = (Path(__file__).resolve().parent / "fixtures" / name).read_bytes()
    assert hashlib.sha256(roh).hexdigest() == treffer.group(1), (
        f"{name} weicht vom Nachweis ab — von Hand nachgebessert? Neu aufzeichnen."
    )
