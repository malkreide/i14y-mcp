# Herkunft der Fixtures

**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**

Aufgezeichnet am **2026-08-14** von der einzigen Quelle dieses Servers:
`https://api.i14y.admin.ch/api`.

Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht
mehr zu unterscheiden — die Datei sieht gleich aus.

**Es sind Ausschnitte, keine Vollabzuege.** Die Auswahlregel steht je
Datei dabei; Feldstruktur und Schluesselnamen sind unangetastet. Eine
Fixture belegt damit die *Form* der Antwort und einen datierten
Ausschnitt ihres Inhalts — nicht den Bestand. Aussagen ueber
Vollstaendigkeit gehoeren in Live-Tests.

**`/concepts` und `/publicservices` nennen ihr Label `name`,** waehrend
Datasets und Data Services `title` verwenden. Die erste Aufzeichnung hat
das aufgedeckt: `list_concepts`, `get_concept` und `list_public_services`
lieferten fuer jeden Datensatz einen leeren Titel, bei gruener Suite, weil
die handgeschriebenen Vorgaenger einen `title`-Schluessel erfunden hatten.

Fehlerpfade — 404, Timeouts, maskierte 4xx — bleiben handgeschrieben.
Die lassen sich nicht auf Zuruf aufzeichnen.

## `datasets_list.json`

- **Quelle:** `https://api.i14y.admin.ch/api/datasets?page=1&pageSize=2`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** Seite 1, 2 von rund 2000 Datensaetzen
- **Groesse:** 53499 B
- **SHA-256:** `10d50db8cd7f6e2b745ccfcd0e475cb9edff8e804fb6b08bd9d9cd633b9da71d`

## `dataservices_list.json`

- **Quelle:** `https://api.i14y.admin.ch/api/dataservices?page=1&pageSize=3`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** Seite 1, 3 Datensaetze
- **Groesse:** 22488 B
- **SHA-256:** `d209ee0da1956c2db2ed91ec2a32f41fc4b8aafa210a0d523f17802a0e8b9d46`

## `publicservices_list.json`

- **Quelle:** `https://api.i14y.admin.ch/api/publicservices?page=1&pageSize=2`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** Seite 1, 2 Datensaetze; Label in `name`
- **Groesse:** 29417 B
- **SHA-256:** `4d6ec51097425c4c36d298c2f139afd20e3db0ea6a1ddc4057abe338b4f8b0ea`

## `concepts_list.json`

- **Quelle:** `https://api.i14y.admin.ch/api/concepts?page=1&pageSize=3`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** Seite 1, 3 Datensaetze; Label in `name`
- **Groesse:** 12336 B
- **SHA-256:** `e29b9b580b83c7f35c48293acd22e5f9afa8f218ffdeeaa79c4654be465e3860`

## `agents_list.json`

- **Quelle:** `https://api.i14y.admin.ch/api/agents?page=1&pageSize=3`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** Seite 1, 3 Datensaetze
- **Groesse:** 9354 B
- **SHA-256:** `68e9dae9783ee9572dbb84bac6a5a9797675e0f7a10af2407d5807202abcfbef`

## `catalogs_list.json`

- **Quelle:** `https://api.i14y.admin.ch/api/catalogs?page=1&pageSize=3`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** Seite 1, 3 Datensaetze
- **Groesse:** 7757 B
- **SHA-256:** `a91eb91fbe85f788e426ae304eb39ef164448fa4c3c0d7559b45f4de385b6030`

## `search.json`

- **Quelle:** `https://api.i14y.admin.ch/api/search?query=Sonderp%C3%A4dagogik&language=de&structure=WithoutStructure`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendige Treffermenge zu «Sonderpaedagogik» (1)
- **Groesse:** 7492 B
- **SHA-256:** `5a4625cadd91489595914080e69ad7d59e9ef3aaee5a4223645e1d69741f0f58`

## `dataset_detail.json`

- **Quelle:** `https://api.i14y.admin.ch/api/datasets/0091031d-c82c-4861-9ea9-42b9e23451f7`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; erster Datensatz aus datasets_list
- **Groesse:** 14598 B
- **SHA-256:** `ca0ca3aaac19f733c92e95a3d98d787c784a45b55420c3c165a64d42121c9164`

## `dataservice_detail.json`

- **Quelle:** `https://api.i14y.admin.ch/api/dataservices/019f3d36-5cb9-7f2f-8128-7a0175a512c8`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; erster Eintrag aus dataservices_list
- **Groesse:** 7882 B
- **SHA-256:** `a9fb769006263c1570721e409444dbef078476037e87b1cdc8bedadecad82d41`

## `concept_detail.json`

- **Quelle:** `https://api.i14y.admin.ch/api/concepts/08dd632d-a98d-34ff-9252-123e46d6f053`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; erstes CodeList-Konzept
- **Groesse:** 3365 B
- **SHA-256:** `be55fccba7b3a506fb7df0fdd15a53f7593bdc340d0b0764f2b2e3fa16b38f90`

## `codelist_entries.json`

- **Quelle:** `https://api.i14y.admin.ch/api/concepts/08dd632d-a98d-34ff-9252-123e46d6f053/codelist-entries/search?language=de&page=1&pageSize=5`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** Seite 1, 5 Eintraege des Konzepts oben
- **Groesse:** 10602 B
- **SHA-256:** `021474826fb2aaf3e350aa3707587274a22c2ea567a4e1cf08ff1a2f715939e7`
