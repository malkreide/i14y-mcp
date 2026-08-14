"""Every external endpoint, driven from a recorded response.

The handwritten stubs elsewhere in this suite test the *error* paths — a 404, a
timeout, a masked 400 — which cannot be recorded on demand and are fine as
inventions. What they cannot do is tell us the shape of a success payload: they
agree with whatever the author assumed. These tests replay real responses
instead, so a renamed field upstream fails here rather than in production.

Recorded by `scripts/record_fixtures.py`; each file carries its recording date.
"""

from __future__ import annotations

import datetime as dt

import httpx
import pytest
import respx
from conftest import all_recordings, load_body, load_recording, recorded_at

from i14y_mcp import client as c
from i14y_mcp import server

BASE = c.BASE_URL

# Every external endpoint this server calls, mapped to the recording that
# covers it. Adding a tool without a recording fails `test_every_endpoint_...`.
ENDPOINTS = {
    "/search": "search",
    "/datasets": "datasets_list",
    "/datasets/{id}": "dataset_detail",
    "/dataservices": "dataservices_list",
    "/dataservices/{id}": "dataservice_detail",
    "/publicservices": "publicservices_list",
    "/concepts": "concepts_list",
    "/concepts/{id}": "concept_detail",
    "/concepts/{id}/codelist-entries/search": "codelist_entries",
    "/agents": "agents_list",
    "/catalogs": "catalogs_list",
}


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    async def _instant(_seconds):
        return None

    monkeypatch.setattr(c, "_sleep", _instant)


def mount(name: str) -> None:
    """Serve recording `name` at the exact path it was recorded from."""
    rec = load_recording(name)["_recording"]
    respx.get(f"{BASE}{rec['endpoint']}").mock(
        return_value=httpx.Response(rec["status"], json=load_body(name))
    )


def records(name: str) -> list:
    data = load_body(name)["data"]
    return data if isinstance(data, list) else [data]


def path_of(name: str) -> str:
    return load_recording(name)["_recording"]["endpoint"]


# --------------------------------------------------------------------------
# Recording hygiene
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(set(ENDPOINTS.values())))
def test_every_recording_carries_a_usable_recording_date(name):
    """A fixture without a date is an undated claim about the source."""
    when = recorded_at(name)
    assert when.tzinfo is not None, f"{name}: recording date must be timezone-aware"
    assert when <= dt.datetime.now(dt.timezone.utc), f"{name}: recorded in the future"


def test_every_endpoint_the_server_calls_has_a_recording():
    """Guards the rule itself: one recorded response per external endpoint."""
    missing = sorted(set(ENDPOINTS.values()) - set(all_recordings()))
    assert not missing, f"endpoints without a recording: {missing}"


# --------------------------------------------------------------------------
# Collections
# --------------------------------------------------------------------------


@respx.mock
async def test_search_maps_recorded_hits():
    mount("search")
    result = await server.search_catalog(query="Sonderpädagogik")
    assert result.total_matched == len(records("search"))
    assert result.returned == result.total_matched
    assert all(h.title for h in result.hits), "recorded hits must map to a title"
    assert all(h.id for h in result.hits)


@respx.mock
async def test_list_datasets_maps_recorded_records():
    mount("datasets_list")
    result = await server.list_datasets(page_size=len(records("datasets_list")))
    assert result.returned == len(records("datasets_list"))
    assert all(d.title for d in result.datasets), "every recorded dataset has a title"
    assert any(d.publisher for d in result.datasets)


@respx.mock
async def test_list_data_services_maps_recorded_records():
    mount("dataservices_list")
    result = await server.list_data_services(page_size=len(records("dataservices_list")))
    assert result.returned == len(records("dataservices_list"))
    assert all(s.title for s in result.data_services)


@respx.mock
async def test_list_public_services_maps_recorded_records():
    """`/publicservices` labels records `name`, not `title` — see map_public_service."""
    mount("publicservices_list")
    result = await server.list_public_services(page_size=len(records("publicservices_list")))
    assert result.returned == len(records("publicservices_list"))
    assert all(p.title for p in result.public_services), (
        "public services carry their label in `name`; a mapper reading only "
        "`title` returns None for every record"
    )


@respx.mock
async def test_list_concepts_maps_recorded_records():
    """`/concepts` labels records `name`, not `title` — see map_concept."""
    mount("concepts_list")
    result = await server.list_concepts(page_size=len(records("concepts_list")))
    assert result.returned == len(records("concepts_list"))
    assert all(cc.title for cc in result.concepts), (
        "concepts carry their label in `name`; a mapper reading only `title` "
        "returns None for every record"
    )
    assert any(cc.concept_type for cc in result.concepts)


@respx.mock
async def test_list_publishers_maps_recorded_records():
    mount("agents_list")
    result = await server.list_publishers(page_size=len(records("agents_list")))
    assert result.returned == len(records("agents_list"))
    assert all(p.name for p in result.publishers)


@respx.mock
async def test_list_catalogs_maps_recorded_records():
    mount("catalogs_list")
    result = await server.list_catalogs(page_size=len(records("catalogs_list")))
    assert result.returned == len(records("catalogs_list"))
    assert all(cat.title for cat in result.catalogs)


# --------------------------------------------------------------------------
# Detail endpoints
# --------------------------------------------------------------------------


@respx.mock
async def test_get_dataset_maps_recorded_detail():
    mount("dataset_detail")
    dataset_id = path_of("dataset_detail").rsplit("/", 1)[-1]
    result = await server.get_dataset(dataset_id=dataset_id)
    assert result.dataset.id == dataset_id
    assert result.dataset.title


@respx.mock
async def test_get_dataset_distributions_maps_recorded_detail():
    mount("dataset_detail")
    dataset_id = path_of("dataset_detail").rsplit("/", 1)[-1]
    result = await server.get_dataset_distributions(dataset_id=dataset_id)
    recorded = load_body("dataset_detail")["data"].get("distributions") or []
    assert result.returned == len(recorded)


@respx.mock
async def test_get_data_service_maps_recorded_detail():
    mount("dataservice_detail")
    service_id = path_of("dataservice_detail").rsplit("/", 1)[-1]
    result = await server.get_data_service(data_service_id=service_id)
    assert result.data_service.id == service_id
    assert result.data_service.title


@respx.mock
async def test_get_concept_maps_recorded_detail():
    mount("concept_detail")
    concept_id = path_of("concept_detail").rsplit("/", 1)[-1]
    result = await server.get_concept(concept_id=concept_id)
    assert result.concept.id == concept_id
    assert result.concept.title, "concept detail carries its label in `name` too"


@respx.mock
async def test_search_codelist_entries_maps_recorded_entries():
    mount("codelist_entries")
    concept_id = path_of("codelist_entries").split("/")[2]
    result = await server.search_codelist_entries(
        concept_id=concept_id, page_size=len(records("codelist_entries"))
    )
    assert result.returned == len(records("codelist_entries"))
    assert all(e.code for e in result.entries)
    assert all(e.name for e in result.entries)
