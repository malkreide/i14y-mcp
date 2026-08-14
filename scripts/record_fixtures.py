#!/usr/bin/env python3
"""Record live I14Y responses into `tests/fixtures/`.

Why this exists: a handwritten fixture encodes the author's assumption about
the payload and therefore cannot refute it. When the source renamed a field in
production, every handwritten test stayed green. A recorded response is the
only fixture that can disagree with us.

Each file carries a `_recording` block with the recording date, so a reader can
tell how old the evidence is instead of guessing. Re-run to refresh:

    python scripts/record_fixtures.py

Requires network access to `api.i14y.admin.ch`. This script is a development
tool; it is not imported by the package or the test suite.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://api.i14y.admin.ch/api"
OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

# Fewer records, full record shape. Trimming the *number* of records keeps the
# files readable; trimming *fields* would throw away the one thing a recording
# is for — the parts of the payload nobody thought to imagine.
SMALL = 2
MEDIUM = 3


def get(path: str, params: dict[str, Any] | None = None) -> tuple[int, Any]:
    url = f"{BASE}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "i14y-mcp-recorder"})
    with urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed host, no user input
        return resp.status, json.loads(resp.read().decode("utf-8"))


def write(name: str, path: str, params: dict[str, Any] | None, status: int, body: Any) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    doc = {
        "_recording": {
            "recorded_at": stamp,
            "source": BASE,
            "endpoint": path,
            "params": params or {},
            "status": status,
            "recorded_by": "scripts/record_fixtures.py",
        },
        "body": body,
    }
    target = OUT / f"{name}.json"
    target.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Collections wrap a list, detail endpoints wrap a single object. Counting
    # `len()` blindly reports a detail record's field count as a record count.
    data = body.get("data") if isinstance(body, dict) else None
    shape = f"{len(data)} record(s)" if isinstance(data, list) else "1 object"
    print(f"  {target.name:<34} {status}  {shape:<14} {target.stat().st_size:>7} bytes")


def first_id(body: Any) -> str | None:
    data = body.get("data") if isinstance(body, dict) else None
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0].get("id")
    return None


def main() -> int:
    print(f"Recording from {BASE}")

    # --- Collection endpoints -------------------------------------------
    status, datasets = get("/datasets", {"page": 1, "pageSize": SMALL})
    write("datasets_list", "/datasets", {"page": 1, "pageSize": SMALL}, status, datasets)

    status, services = get("/dataservices", {"page": 1, "pageSize": MEDIUM})
    write("dataservices_list", "/dataservices", {"page": 1, "pageSize": MEDIUM}, status, services)

    status, public = get("/publicservices", {"page": 1, "pageSize": SMALL})
    write("publicservices_list", "/publicservices", {"page": 1, "pageSize": SMALL}, status, public)

    status, concepts = get("/concepts", {"page": 1, "pageSize": MEDIUM})
    write("concepts_list", "/concepts", {"page": 1, "pageSize": MEDIUM}, status, concepts)

    status, agents = get("/agents", {"page": 1, "pageSize": MEDIUM})
    write("agents_list", "/agents", {"page": 1, "pageSize": MEDIUM}, status, agents)

    status, catalogs = get("/catalogs", {"page": 1, "pageSize": MEDIUM})
    write("catalogs_list", "/catalogs", {"page": 1, "pageSize": MEDIUM}, status, catalogs)

    # --- Search ---------------------------------------------------------
    # A narrow query on purpose: `/search` ignores paging and returns the whole
    # match set, which is why the server caps it client-side.
    sp = {"query": "Sonderpädagogik", "language": "de", "structure": "WithoutStructure"}
    status, search = get("/search", sp)
    write("search", "/search", sp, status, search)

    # --- Detail endpoints, ids resolved from the lists above -------------
    ds_id = first_id(datasets)
    if not ds_id:
        print("!! no dataset id in the list response — cannot record /datasets/{id}")
        return 1
    status, dataset = get(f"/datasets/{ds_id}")
    write("dataset_detail", f"/datasets/{ds_id}", None, status, dataset)

    svc_id = first_id(services)
    if not svc_id:
        print("!! no data service id — cannot record /dataservices/{id}")
        return 1
    status, service = get(f"/dataservices/{svc_id}")
    write("dataservice_detail", f"/dataservices/{svc_id}", None, status, service)

    # A code-list concept, not just any concept: only `CodeList` concepts have
    # entries, so the id has to be chosen rather than taken from position 0.
    status, wide = get("/concepts", {"page": 1, "pageSize": 100})
    code_id = None
    for row in wide.get("data", []):
        if row.get("conceptType") == "CodeList":
            code_id = row.get("id")
            break
    if not code_id:
        print("!! no CodeList concept found in the first 100 — widen the scan")
        return 1

    status, concept = get(f"/concepts/{code_id}")
    write("concept_detail", f"/concepts/{code_id}", None, status, concept)

    cp = {"language": "de", "page": 1, "pageSize": 5}
    status, entries = get(f"/concepts/{code_id}/codelist-entries/search", cp)
    write(
        "codelist_entries",
        f"/concepts/{code_id}/codelist-entries/search",
        cp,
        status,
        entries,
    )

    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
