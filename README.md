> **Part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide/swiss-public-data-mcp)** — a collection of open-source MCP servers connecting AI agents to Swiss public and open data.
> This is a private project. It is not affiliated with, endorsed by, or operated on behalf of any employer or public authority.

# i14y-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-server-orange.svg)](https://modelcontextprotocol.io/)
[![Data: I14Y](https://img.shields.io/badge/data-I14Y%20%7C%20BFS-red.svg)](https://www.i14y.admin.ch)

**MCP server for the I14Y interoperability platform — Switzerland's national metadata catalogue.**

🇩🇪 [Deutsche Version](README.de.md)

---

## Why this server exists

The other servers in this portfolio answer *«what does the data say?»*.
This one answers the question that comes first: **«who publishes data on this
topic, through which interface, under which licence?»**

I14Y is the national data catalogue maintained by the Federal Statistical
Office. It describes datasets, registered APIs, public services and harmonised
concepts from the Confederation, cantons and communes, using the DCAT-AP-CH
profile (eCH-0200).

> **Mnemonic: «Catalogue before shelf.»** Without a catalogue, an agent has to
> already know a data source exists. With one, it can find it.

---

## 🎯 Anchor Demo Query

> *«Which authority publishes data on special needs education, through which
> interface is it available, and under which licence?»*

```
search_catalog(query="Sonderpädagogik")
  → «Statistik der Sonderpädagogik» — Federal Statistical Office (BFS), theme: Bildung

get_dataset_distributions(dataset_id=...)
  → 2 distributions, licence: «Opendata BY ASK — attribution required,
    commercial use only with permission from the data supplier»

get_dataset(dataset_id=...)
  → contact: auskunftsdienst@bfs.admin.ch
```

Three tool calls turn a vague topic into a named authority, a download URL and
a licence you can act on.

---

## Architecture

```
                 ┌──────────────────────────────┐
                 │      MCP Host (Claude)       │
                 └───────────────┬──────────────┘
                                 │ stdio | streamable-http
                 ┌───────────────▼──────────────┐
                 │          i14y-mcp            │
                 │  ┌────────────────────────┐  │
                 │  │ server.py  (13 tools)  │  │
                 │  ├────────────────────────┤  │
                 │  │ mappers.py             │  │  DCAT → flat, one language
                 │  ├────────────────────────┤  │
                 │  │ models.py  (Pydantic)  │  │  source + provenance envelope
                 │  ├────────────────────────┤  │
                 │  │ client.py              │  │  retry 2s/4s/8s, no-retry 4xx
                 │  └────────────────────────┘  │
                 └───────────────┬──────────────┘
                                 │ HTTPS, no auth
                 ┌───────────────▼──────────────┐
                 │  api.i14y.admin.ch/api       │
                 │  datasets · dataservices ·   │
                 │  concepts · publicservices · │
                 │  catalogs · agents · search  │
                 └──────────────────────────────┘
```

### Architecture decision

This server uses **Architecture A (live API only)**.

Rationale (verified live on 2026-07-21):
- All read endpoints respond without authentication and paginate correctly.
- No bulk download of catalogue metadata is offered, and none is needed.
- Error responses follow RFC 7807, so failure modes are distinguishable.

Consequences:
- Every HTTP call retries transient failures with 2 s / 4 s / 8 s backoff.
- `search_catalog` caps results client-side because the upstream ignores paging.
- `api_status` always returns an evaluable state instead of empty records.

Full probe report: [`docs/probe-i14y.md`](docs/probe-i14y.md).

---

## Tools

| Tool | Purpose |
|---|---|
| `search_catalog` | Free-text search across the catalogue. Entry point. |
| `list_datasets` | Paginated dataset register (complete, unlike search). |
| `get_dataset` | Full metadata record for one dataset. |
| `get_dataset_distributions` | Download URLs, formats and **licences**. |
| `list_data_services` | Register of official Swiss APIs with endpoint URLs. |
| `get_data_service` | Full record for one registered interface. |
| `list_public_services` | Administrative services for citizens. |
| `list_concepts` | Harmonised concepts and code lists. |
| `get_concept` | One concept definition. |
| `search_codelist_entries` | Individual codes of a code list. |
| `list_publishers` | Publishing bodies, with Swiss UID. |
| `list_catalogs` | Contributing catalogues. |
| `api_status` | Reachability check with graceful degradation. |

All tools are annotated `readOnlyHint: true`. Write operations exist in the
upstream API but are deliberately not exposed.

---

## Installation

```bash
uvx i14y-mcp
```

Or from source:

```bash
git clone https://github.com/malkreide/i14y-mcp
cd i14y-mcp
pip install -e ".[dev]"
```

### Claude Desktop

```json
{
  "mcpServers": {
    "i14y": {
      "command": "uvx",
      "args": ["i14y-mcp"]
    }
  }
}
```

### Remote deployment (Render, Railway)

```bash
I14Y_MCP_TRANSPORT=sse PORT=8000 i14y-mcp
```

`I14Y_MCP_TRANSPORT` accepts `stdio` (default), `sse` or `streamable-http`.

### Docker

```bash
docker compose up --build      # SSE transport on http://localhost:8000
```

The image is a hardened multi-stage build: it runs as a non-root user, ships no
build tools, and needs no secrets (the API is unauthenticated). See
[`Dockerfile`](Dockerfile) and [`compose.yaml`](compose.yaml).

---

## Join keys

I14Y is a connector layer. Two identifiers make it composable with the rest of
the portfolio:

| Key | Field | Joins to |
|---|---|---|
| Swiss UID | `Publisher.uid` | [`register-mcp`](https://github.com/malkreide/register-mcp) (Zefix) |
| Endpoint URL | `DataServiceSummary.endpoint_urls` | any portfolio server wrapping that API |

---

## Known limitations

Verified live on 2026-07-21.

1. **The search index covers roughly half the register.** `search_catalog`
   returns at most 1013 records; `list_datasets` reaches about 2003. Use
   `list_datasets` when completeness matters.
2. **Search returns Datasets only.** Filtering by `types=["Concept"]` or
   `types=["DataService"]` yields zero results even though those entities
   exist. Use `list_concepts` and `list_data_services` instead.
3. **The upstream ignores paging on search.** The full result set is always
   returned; this server caps it at 200 records and sets `truncated: true`.
4. **Licences vary per distribution**, not per dataset. Most carry
   «Opendata BY ASK», which requires attribution and restricts commercial use.
   Always read the `licence` field before reuse.
5. **Some metadata fields are simply empty.** Frequency, temporal coverage and
   distribution format are optional and frequently unset by publishers. This is
   a data-quality property of the catalogue, not a bug in this server.
6. **Not every entry with an endpoint has a URL.** Entries labelled only
   «OpenAPI Spezifikation» without a URI are surfaced as `(no URI) <label>`
   rather than dropped.

---

## Testing

```bash
PYTHONPATH=src pytest tests/ -m "not live"   # offline, used in CI
PYTHONPATH=src pytest tests/ -m "live"       # hits the real API
PYTHONPATH=src pytest tests/                 # everything
python -m ruff check src tests
```

The live tests are not decoration: fundstück 4 in the probe report — keywords
nesting their language object under `label` — was caught by a live test after
the unit tests were already green.

---

## Contributing & security

- [`CONTRIBUTING.md`](CONTRIBUTING.md) — ground rules (read-only, one egress
  host, no secrets) and the local dev loop.
- [`SECURITY.md`](SECURITY.md) — security posture and how to report a vulnerability.
- [`PUBLISHING.md`](PUBLISHING.md) — the PyPI / MCP Registry release process.

---

## Credits & related projects

- Data: [I14Y Interoperability Platform](https://www.i14y.admin.ch), Federal Statistical Office (BFS)
- Standard: [eCH-0200 / DCAT-AP-CH](https://www.ech.ch/de/ech/ech-0200/1.0)
- Source discovery inspired by [rnckp/awesome-ogd-switzerland](https://github.com/rnckp/awesome-ogd-switzerland)
- Portfolio: [swiss-public-data-mcp](https://github.com/malkreide/swiss-public-data-mcp)
- Protocol: [Model Context Protocol](https://modelcontextprotocol.io/)

Licence: MIT. The catalogue data remains subject to the terms declared by each
publisher.
