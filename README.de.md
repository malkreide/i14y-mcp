> **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide/swiss-public-data-mcp)** — einer Sammlung quelloffener MCP-Server, die KI-Agenten mit Schweizer öffentlichen und offenen Daten verbinden.
> Dies ist ein privates Projekt. Es steht in keiner Verbindung zu einem Arbeitgeber oder einer Behörde und wird nicht in deren Auftrag betrieben.

# i14y-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-server-orange.svg)](https://modelcontextprotocol.io/)
[![Daten: I14Y](https://img.shields.io/badge/Daten-I14Y%20%7C%20BFS-red.svg)](https://www.i14y.admin.ch)

**MCP-Server für die Interoperabilitätsplattform I14Y — den nationalen Metadatenkatalog der Schweiz.**

🇬🇧 [English version](README.md)

---

## Wozu dieser Server

Die übrigen Server dieses Portfolios beantworten die Frage *«Was sagen die
Daten?»*. Dieser hier beantwortet die Frage, die davor kommt: **«Wer publiziert
zu diesem Thema Daten, über welche Schnittstelle, und unter welcher Lizenz?»**

I14Y ist der nationale Datenkatalog, betrieben vom Bundesamt für Statistik. Er
beschreibt Datensätze, registrierte Schnittstellen, öffentliche Dienstleistungen
und harmonisierte Konzepte von Bund, Kantonen und Gemeinden nach dem
DCAT-AP-CH-Profil (eCH-0200).

> **Eselsbrücke: «Erst der Katalog, dann das Regal.»** Ohne Katalog muss ein
> Agent bereits wissen, dass eine Datenquelle existiert. Mit Katalog findet er sie.

---

## 🎯 Anchor Demo Query

> *«Welche Behörde publiziert Daten zur Sonderpädagogik, über welche
> Schnittstelle sind sie abrufbar, und unter welcher Lizenz?»*

```
search_catalog(query="Sonderpädagogik")
  → «Statistik der Sonderpädagogik» — Bundesamt für Statistik (BFS), Thema: Bildung

get_dataset(dataset_id=...)
  → 2 Distributionen, Lizenz: «Opendata BY ASK — Quellenangabe ist Pflicht,
    kommerzielle Nutzung nur mit Bewilligung des Datenlieferanten»
  → Kontakt: auskunftsdienst@bfs.admin.ch
```

Zwei Tool-Aufrufe verwandeln ein vages Thema in eine benannte Behörde, eine
Download-URL und eine handlungsrelevante Lizenz — `get_dataset` aggregiert
Distributionen, Lizenzen und Kontaktstelle in einem Datensatz.

---

## Architektur

```
                 ┌──────────────────────────────┐
                 │      MCP Host (Claude)       │
                 └───────────────┬──────────────┘
                                 │ stdio | streamable-http
                 ┌───────────────▼──────────────┐
                 │          i14y-mcp            │
                 │  ┌────────────────────────┐  │
                 │  │ server.py  (13 Tools)  │  │
                 │  ├────────────────────────┤  │
                 │  │ mappers.py             │  │  DCAT → flach, eine Sprache
                 │  ├────────────────────────┤  │
                 │  │ models.py  (Pydantic)  │  │  source-/provenance-Envelope
                 │  ├────────────────────────┤  │
                 │  │ client.py              │  │  Retry 2s/4s/8s, 4xx ohne Retry
                 │  └────────────────────────┘  │
                 └───────────────┬──────────────┘
                                 │ HTTPS, ohne Auth
                 ┌───────────────▼──────────────┐
                 │  api.i14y.admin.ch/api       │
                 │  datasets · dataservices ·   │
                 │  concepts · publicservices · │
                 │  catalogs · agents · search  │
                 └──────────────────────────────┘
```

### Architektur-Entscheid

Dieser Server verwendet **Architektur A (nur Live-API)**.

Begründung (live verifiziert am 21. Juli 2026):
- Alle lesenden Endpunkte antworten ohne Authentifizierung und paginieren korrekt.
- Ein Bulk-Download der Katalogmetadaten wird nicht angeboten und ist nicht nötig.
- Fehlerantworten folgen RFC 7807, Fehlerzustände sind damit unterscheidbar.

Konsequenzen:
- Jeder HTTP-Aufruf wiederholt transiente Fehler mit 2 s / 4 s / 8 s Backoff.
- `search_catalog` deckelt clientseitig, weil die Quelle Paginierung ignoriert.
- `api_status` liefert immer einen auswertbaren Zustand statt leerer Records.

Vollständiger Probe-Report: [`docs/probe-i14y.md`](docs/probe-i14y.md).

### Projektphase

Dieser Server ist in **Phase 1 (read-only)** der «Read-only First»-Phasen­architektur
des Portfolios: alle Tools sind lesend, es gibt keine Authentifizierung und keine
Personendaten. Siehe [`docs/roadmap.md`](docs/roadmap.md) für das Phasenmodell und
die Voraussetzungen für eine allfällige spätere Schreibfähigkeit.

---

## Tools

| Tool | Zweck |
|---|---|
| `search_catalog` | Volltextsuche über den Katalog. Einstiegspunkt. |
| `list_datasets` | Paginiertes Datensatz-Register (vollständig, anders als die Suche). |
| `get_dataset` | Vollständiger Metadatensatz zu einem Datensatz. |
| `get_dataset_distributions` | Download-URLs, Formate und **Lizenzen**. |
| `list_data_services` | Register amtlicher Schnittstellen mit Endpunkt-URLs. |
| `get_data_service` | Vollständiger Datensatz zu einer Schnittstelle. |
| `list_public_services` | Öffentliche Dienstleistungen für Bürgerinnen und Bürger. |
| `list_concepts` | Harmonisierte Konzepte und Codelisten. |
| `get_concept` | Eine Konzeptdefinition. |
| `search_codelist_entries` | Einzelne Codes einer Codeliste. |
| `list_publishers` | Publizierende Stellen, inklusive UID. |
| `list_catalogs` | Beitragende Kataloge. |
| `api_status` | Erreichbarkeitsprüfung mit Graceful Degradation. |

Alle Tools sind mit `readOnlyHint: true` annotiert. Schreibende Operationen
existieren in der Quell-API, werden hier aber bewusst nicht exponiert.

### MCP-Primitive

Dieser Server exponiert **ausschliesslich Tools** — keine Resources, keine
Prompts. Das ist eine bewusste Entscheidung, kein Versäumnis: I14Y wird per
Volltextsuche und über opake UUIDs abgefragt, es gibt also keinen kleinen,
stabilen Satz adressierbarer URIs, der sich sauberer auf MCP-Resources abbilden
liesse; und der Server liefert keine vorgefertigten Prompt-Templates. Alle Tools
sind read-only und idempotent; entsteht künftig ein stabiler Einstiegspunkt (z. B.
eine feste Themenliste), ist er ein Kandidat für eine Resource.

### MCP-Protokoll-Version

Gebaut gegen das MCP-Python-SDK (`mcp >= 1.28.1`), das die Protokoll-Version beim
Initialize mit dem Client aushandelt. Der getestete SDK-Floor ist in
`pyproject.toml` gepinnt; [Dependabot](.github/dependabot.yml) öffnet monatliche
SDK-Update-PRs, und jede Änderung, die die ausgehandelte Spec-Version anhebt, wird
in [`CHANGELOG.md`](CHANGELOG.md) vermerkt.

---

## Installation

```bash
uvx i14y-mcp
```

Oder aus dem Quellcode:

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

### Remote-Betrieb (Render, Railway)

```bash
I14Y_MCP_TRANSPORT=sse HOST=0.0.0.0 PORT=8000 i14y-mcp
```

`I14Y_MCP_TRANSPORT` akzeptiert `stdio` (Standard), `sse` oder `streamable-http`.
Die HTTP-Transporte binden an `HOST`, standardmässig `127.0.0.1` (Loopback);
für ein PaaS `HOST=0.0.0.0` setzen (das Docker-Image tut das bereits). CORS
exponiert den `Mcp-Session-Id`-Header, damit Browser-MCP-Clients ihre Session behalten.

### Docker

```bash
docker compose up --build      # SSE-Transport auf http://localhost:8000
```

Das Image ist ein gehärteter Multi-Stage-Build: Es läuft als Nicht-Root-Benutzer,
enthält keine Build-Tools und benötigt keine Secrets (die API ist
unauthentifiziert). Siehe [`Dockerfile`](Dockerfile) und [`compose.yaml`](compose.yaml).

---

## Join Keys

I14Y ist eine Verbindungsschicht. Zwei Identifikatoren machen sie mit dem
übrigen Portfolio kombinierbar:

| Schlüssel | Feld | Verbindet zu |
|---|---|---|
| UID | `Publisher.uid` | [`register-mcp`](https://github.com/malkreide/register-mcp) (Zefix) |
| Endpunkt-URL | `DataServiceSummary.endpoint_urls` | jedem Portfolio-Server, der diese API kapselt |

---

## Bekannte Einschränkungen

Live verifiziert am 21. Juli 2026.

1. **Der Suchindex deckt rund die Hälfte des Registers ab.** `search_catalog`
   liefert maximal 1013 Records, `list_datasets` erreicht rund 2003. Wo
   Vollständigkeit zählt, ist `list_datasets` zu verwenden.
2. **Die Suche liefert ausschliesslich Datensätze.** Ein Filter
   `types=["Concept"]` oder `types=["DataService"]` ergibt null Treffer, obwohl
   diese Entitäten existieren. Stattdessen `list_concepts` und
   `list_data_services` verwenden.
3. **Die Quelle ignoriert Paginierung bei der Suche.** Es wird immer das
   vollständige Resultatset geliefert; dieser Server deckelt bei 200 Records
   und setzt `truncated: true`.
4. **Lizenzen gelten pro Distribution**, nicht pro Datensatz. Die meisten tragen
   «Opendata BY ASK» — Quellenangabe ist Pflicht, kommerzielle Nutzung nur mit
   Bewilligung. Vor jeder Weiterverwendung das Feld `licence` lesen.
5. **Manche Metadatenfelder sind schlicht leer.** Frequenz, zeitliche Abdeckung
   und Distributionsformat sind optional und werden von Publizierenden häufig
   nicht gesetzt. Das ist eine Datenqualitätseigenschaft des Katalogs, kein
   Fehler dieses Servers.
6. **Nicht jeder Eintrag mit Endpunkt hat eine URL.** Einträge, die nur mit
   «OpenAPI Spezifikation» ohne URI beschriftet sind, erscheinen als
   `(no URI) <Label>` statt zu verschwinden.

---

## Tests

```bash
PYTHONPATH=src pytest tests/ -m "not live"   # offline, in der CI verwendet
PYTHONPATH=src pytest tests/ -m "live"       # gegen die echte API
PYTHONPATH=src pytest tests/                 # alles
python -m ruff check src tests
```

Die Live-Tests sind kein Zierrat: Fundstück 4 im Probe-Report — Keywords, die
ihr Sprachobjekt unter `label` verschachteln — wurde von einem Live-Test
gefunden, nachdem die Unit-Tests bereits grün waren.

---

## Mitwirken & Sicherheit

- [`CONTRIBUTING.de.md`](CONTRIBUTING.de.md) — Grundregeln (read-only, ein
  Egress-Host, keine Secrets) und der lokale Entwicklungs-Loop.
- [`SECURITY.de.md`](SECURITY.de.md) — Sicherheits-Posture und wie Schwachstellen
  gemeldet werden.
- [`PUBLISHING.md`](PUBLISHING.md) — der Release-Prozess für PyPI / MCP-Registry.

---

## Credits & verwandte Projekte

- Daten: [Interoperabilitätsplattform I14Y](https://www.i14y.admin.ch), Bundesamt für Statistik (BFS)
- Standard: [eCH-0200 / DCAT-AP-CH](https://www.ech.ch/de/ech/ech-0200/1.0)
- Quellenrecherche inspiriert von [rnckp/awesome-ogd-switzerland](https://github.com/rnckp/awesome-ogd-switzerland)
- Portfolio: [swiss-public-data-mcp](https://github.com/malkreide/swiss-public-data-mcp)
- Protokoll: [Model Context Protocol](https://modelcontextprotocol.io/)

Lizenz: MIT. Die Katalogdaten unterliegen weiterhin den Bedingungen der
jeweiligen Publizierenden.
