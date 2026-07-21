# Live-Probe: I14Y Interoperabilitätsplattform

**Datum:** 21. Juli 2026
**Prüfer:** `mcp-data-source-probe` (Schritt 1)
**Quelle:** https://www.i14y.admin.ch — Betrieb: Bundesamt für Statistik (BFS)

---

## 1.1 Dokumentation

| Aspekt | Befund |
|---|---|
| OpenAPI-Spec | `https://api.i14y.admin.ch/swagger/v1/swagger.json` (536 kB, OpenAPI 3.0.1) |
| Spec-Titel | «IOP Partner (PRD)», Version v1 |
| Basis-URL | `https://api.i14y.admin.ch/api` |
| Security-Scheme | `Bearer` — deklariert, **für GET-Operationen aber nicht erzwungen** |
| Pfade gesamt | 51 (GET, POST, PUT, DELETE) |
| Entitäten | Datasets, Concepts, DataServices, PublicServices, MappingTables, Catalogs, Agents |
| Fehlerformat | RFC 7807 `application/problem+json` mit `traceId` |

**Wichtig:** Es gibt keine separate «Public API». Die Partner-API ist dieselbe
Schnittstelle; lesende Operationen sind ohne Token offen, schreibende nicht.
Das erfüllt das No-Auth-First-Prinzip für Phase 1.

---

## 1.2/1.3 Befund-Tabelle

| Endpoint | HTTP | Status | Records | Bemerkung |
|---|---|---|---|---|
| `GET /api/datasets` | 200 | ✅ funktioniert | ~2003 | Paginierung korrekt, keine Überlappung p1/p2 |
| `GET /api/datasets/{id}` | 200 | ✅ funktioniert | 1 | vollständiges DCAT-AP-CH-Record |
| `GET /api/concepts` | 200 | ✅ funktioniert | ~616 | |
| `GET /api/concepts/{id}` | 200 | ✅ funktioniert | 1 | |
| `GET /api/concepts/{id}/codelist-entries/search` | 200 | ⚠️ funktioniert | n | `language` ist **Pflicht**, sonst HTTP 400 |
| `GET /api/concepts/{id}/codelist-entries` | 405 | ❌ existiert nicht | – | nur der `/search`-Unterpfad ist implementiert |
| `GET /api/dataservices` | 200 | ✅ funktioniert | ~77 | Register der amtlichen APIs |
| `GET /api/publicservices` | 200 | ✅ funktioniert | ~134 | |
| `GET /api/catalogs` | 200 | ✅ funktioniert | ~137 | |
| `GET /api/agents` | 200 | ✅ funktioniert | ~163 | Publisher inkl. UID |
| `GET /api/search` | 200 | ⚠️ eingeschränkt | max. 1013 | siehe Fundstücke 1–3 |
| `GET /api/datasets/{ungültige-uuid}` | 404 | ✅ sauber | – | RFC-7807-Body |
| `GET /api/datasets/not-a-uuid` | 404 | ✅ sauber | – | kein 500er bei Formatfehler |

**Auth-Probe:** Alle obigen Aufrufe ohne `Authorization`-Header → HTTP 200.

---

## 1.4 Reality-Check

| Vergleich | Zahl |
|---|---|
| Datasets über `/api/datasets` | ~2003 |
| Datasets über `/api/search` (leere Query) | 1013 |
| **Abdeckung des Suchindex** | **~51 %** |

Der Suchindex deckt rund die Hälfte des Registers ab. Konsequenz für das
Tool-Design: `search_catalog` ist der Einstieg, `list_datasets` die
Vollständigkeitsgarantie. Beide Tools werden benötigt, keines ersetzt das andere.

---

## Fundstücke

**1 — Der Suchparameter heisst `query`, nicht `q`.**
Unbekannte Query-Parameter werden stillschweigend verworfen. `?q=schule`
liefert HTTP 200 mit **15 MB** — dem gesamten Index inklusive Strukturen.
Ein Server, der diesen Parameter falsch schreibt, funktioniert scheinbar,
sprengt aber jedes Kontextfenster.

> *Eselsbrücke: «Die API sagt nie Nein, sie sagt einfach Alles.»*

**2 — `page` und `pageSize` werden auf `/api/search` ignoriert.**
`pageSize=5` lieferte 36 Records. Die Suche gibt immer das komplette
Resultatset zurück. Deckelung muss clientseitig erfolgen → `SEARCH_HARD_CAP`.

**3 — Der `types`-Filter der Suche wirkt nur für `Dataset`.**
Die Enum-Werte `Concept`, `DataService`, `PublicService`, `MappingTable` sind
gültig und werden ohne Fehler akzeptiert — liefern aber konsistent 0 Treffer,
obwohl 616 Concepts und 77 DataServices existieren. Auch die ungefilterte
Suche gibt ausschliesslich `type: "Dataset"` zurück.

**4 — Mehrsprachigkeit ist uneinheitlich verschachtelt.**
Themes verpacken ihr Sprachobjekt unter `name`, Keywords unter `label`,
Titel und Beschreibungen liegen direkt als `{de, fr, it, en}` vor. Ein
naiver Sprach-Extraktor gibt bei Keywords ein Dict statt eines Strings zurück
— gefunden erst durch den Live-Test, nicht durch die Unit-Tests.

> *Metapher: «Schweizer Mehrsprachigkeit im JSON — jede Ebene spricht Dialekt.»*

**5 — `endpointUrls` enthält Einträge ohne URI.**
Manche Einträge tragen nur ein `label` («OpenAPI Spezifikation») ohne
tatsächliche URL. Diese dürfen nicht stillschweigend verschwinden, sonst
erscheint eine Schnittstelle im Portal, aber nicht in der Tool-Antwort.

**6 — `structure=WithStructure` ist der Default und teuer.**
Ohne explizites `structure=WithoutStructure` liefert die Suche zusätzlich
vollständige Datenstrukturen. Der Server setzt den sparsamen Wert fest.

---

## 1.5 Dump-Verfügbarkeit

Kein Bulk-Download der Katalogmetadaten auffindbar. Da alle Listen-Endpunkte
korrekt paginieren und stabil antworten, ist kein Dump-Fallback nötig.

---

## Lizenz

Die Katalog-Metadaten selbst sind ohne Zugangsbeschränkung abrufbar. Die
**Nutzungsrechte der beschriebenen Daten** werden pro Distribution deklariert.
Stichprobe über 100 Datasets:

| Lizenz | Anteil |
|---|---|
| «Opendata BY ASK» (Quellenangabe Pflicht, kommerziell nur mit Bewilligung) | 344 Distributionen |
| «Opendata BY» (Quellenangabe Pflicht) | 1 |
| nicht deklariert | 6 |

**Konsequenz:** Die Lizenz gehört zwingend in jede Tool-Antwort, die eine
Download-URL enthält. «Öffentlich auffindbar» ist nicht «frei verwendbar».

---

## Architektur-Entscheid

**ARCH A — Live-API-only.**

Begründung: Alle benötigten Endpunkte antworten stabil, ohne Auth, mit
korrekter Paginierung und sauberem Fehlerverhalten. Kein Dump vorhanden,
aber auch keiner nötig.

Konsequenzen:
- Retry mit 2 s / 4 s / 8 s für alle Aufrufe; 4xx ausser 429 ohne Retry.
- `search_catalog` deckelt clientseitig und meldet `truncated`.
- `api_status` liefert immer einen auswertbaren Zustand statt leerer Records.
