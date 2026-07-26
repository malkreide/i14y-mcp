# Use Cases & Examples — i14y-mcp

Realitätsnahe Anfragen nach Zielgruppe. I14Y ist die nationale Metadaten-Plattform (DCAT-AP-CH / eCH-0200) des Bundesamts für Statistik. **API-Key nötig: Nein** — alle Lese-Endpunkte der I14Y-API sind ohne Authentifizierung erreichbar.

> Merksatz des Servers: «Katalog vor Regal.» Zuerst herausfinden, *wer* zu einem Thema Daten publiziert, über *welche* Schnittstelle und unter *welcher* Lizenz — dann erst abfragen.

## 🏫 Bildung & Schule

**«Wer publiziert Statistiken zur Sonderpädagogik, und darf ich die Daten weiterverwenden?»**
- **API-Key nötig:** Nein
- → `search_catalog(query="Sonderpädagogik", language="de")`
- → `get_dataset(dataset_id="<UUID aus der Suche>")`
- → `get_dataset_distributions(dataset_id="<UUID>")`
- Warum nützlich: Aus einem vagen Stichwort werden eine benannte Behörde, eine Download-URL und die konkrete Lizenz — die man vor jeder Weiterverwendung im Unterricht kennen muss.

**«Welche harmonisierten Codelisten des Bildungswesens gibt es, z. B. für Bildungsstufen?»**
- **API-Key nötig:** Nein
- → `list_concepts(language="de", page_size=50)`
- → `search_codelist_entries(concept_id="<UUID einer CodeList>", language="de")`
- Warum nützlich: Konzepte und Codelisten sind über die Freitextsuche nicht auffindbar; so bekommt eine Lehrperson die offiziellen, behördenübergreifend abgestimmten Code-Werte statt selbst gebastelter Kategorien.

**«Welche Datensätze stellt das Bundesamt für Statistik insgesamt bereit?»**
- **API-Key nötig:** Nein
- → `list_publishers(language="de")`
- → `list_datasets(publisher_identifier="<Identifier des BFS>", language="de")`
- Warum nützlich: `list_datasets` deckt das vollständige Register ab (die Suche nur rund die Hälfte) — ideal, um für ein Schulprojekt systematisch die verfügbaren amtlichen Datensätze eines Herausgebers zu sichten.

## 👨‍👩‍👧 Eltern & Schulgemeinde

**«Zu welchem Thema publiziert unsere Gemeinde oder unser Kanton amtliche Daten?»**
- **API-Key nötig:** Nein
- → `search_catalog(query="Gemeinde", language="de", limit=25)`
- → `get_dataset(dataset_id="<UUID>")`
- Warum nützlich: Eltern in einem Schulforum können prüfen, welche offiziellen Zahlen es zu einem lokalen Anliegen gibt, inklusive Kontaktstelle und Aktualität des Datensatzes.

**«Gibt es eine offizielle behördliche Dienstleistung (Public Service) zu einem Anliegen?»**
- **API-Key nötig:** Nein
- → `list_public_services(language="de", page_size=50)`
- Warum nützlich: Zeigt registrierte Verwaltungsangebote für Bürger:innen — nützlich, um von der «gefühlten» Zuständigkeit zur tatsächlich verzeichneten Amtsstelle zu kommen.

## 🗳️ Bevölkerung & öffentliches Interesse

**«Welche Behörde publiziert diesen Datensatz, und unter welcher Lizenz darf ich ihn nutzen?»**
- **API-Key nötig:** Nein
- → `search_catalog(query="<Thema>", language="de")`
- → `get_dataset_distributions(dataset_id="<UUID>")`
- Warum nützlich: Lizenzen unterscheiden sich je Distribution; viele tragen «Opendata BY ASK» (Namensnennung erforderlich, kommerzielle Nutzung nur mit Erlaubnis) — Transparenz vor der Weiterverwendung.

**«Existiert bereits eine offizielle API zu einem Thema, bevor jemand einen Scraper baut?»**
- **API-Key nötig:** Nein
- → `list_data_services(language="de", page_size=50)`
- → `get_data_service(data_service_id="<UUID>")`
- Warum nützlich: Das nationale Register offizieller Schnittstellen liefert Endpoint-URLs und — wo hinterlegt — OpenAPI-Spezifikationen; das spart doppelte Arbeit und erhöht die Nachvollziehbarkeit.

## 🤖 KI-Interessierte & Entwickler:innen

**«Ist die I14Y-Quelle gerade erreichbar, und welche Endpunkte antworten?»**
- **API-Key nötig:** Nein
- → `api_status()`
- Warum nützlich: Liefert immer einen auswertbaren Status statt eines stillen Leerergebnisses — ein Agent kann so «keine Treffer» von «Quelle nicht erreichbar» unterscheiden.

**«Welche Kataloge speisen I14Y, und lässt sich ein Herausgeber portfolioübergreifend verknüpfen?»**
- **API-Key nötig:** Nein
- → `list_catalogs(language="de")`
- → `list_publishers(uid="CHE-123.456.789")`
- Warum nützlich: Die Swiss UID (`Publisher.uid`) ist der Join-Schlüssel zum Handelsregister — z. B. via [`register-mcp`](https://github.com/malkreide/register-mcp) (Zefix). So wird der Metadaten-Katalog zum Bindeglied zwischen mehreren Portfolio-Servern.

## 🔧 Technische Referenz: Tool-Auswahl nach Anwendungsfall

| Ich möchte… | Tool(s) | Auth nötig? |
|---|---|---|
| Den Katalog per Freitext durchsuchen (Einstieg) | `search_catalog` | Nein |
| Das vollständige Datensatz-Register (paginiert) durchgehen | `list_datasets` | Nein |
| Den vollständigen Metadatensatz eines Datensatzes holen | `get_dataset` | Nein |
| Download-URLs, Formate und Lizenzen eines Datensatzes sehen | `get_dataset_distributions` | Nein |
| Das Register offizieller Schweizer APIs durchsehen | `list_data_services` | Nein |
| Den vollständigen Datensatz zu einer registrierten Schnittstelle holen | `get_data_service` | Nein |
| Verwaltungsdienstleistungen für Bürger:innen auflisten | `list_public_services` | Nein |
| Harmonisierte Konzepte und Codelisten auflisten | `list_concepts` | Nein |
| Eine einzelne Konzept-Definition abrufen | `get_concept` | Nein |
| Die Einträge (Codes) einer Codeliste auflösen | `search_codelist_entries` | Nein |
| Herausgebende Stellen inkl. Swiss UID auflisten | `list_publishers` | Nein |
| Beitragende Kataloge auflisten | `list_catalogs` | Nein |
| Erreichbarkeit der Quelle prüfen (mit Graceful Degradation) | `api_status` | Nein |
