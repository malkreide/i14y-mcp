# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **`railway.json`** — Konfiguration als Code für den Railway-Betrieb, geschrieben
  gegen das echte Schema (`https://railway.com/railway.schema.json`, am
  20.9.2026 abgerufen und validiert), nicht aus dem Gedächtnis.

  Die Datei hält genau eine Einstellung fest: `builder: DOCKERFILE`. Mit jedem
  anderen Builder sieht Railway das Dockerfile nicht an, leitet den Startbefehl
  selbst ab, und `I14Y_MCP_TRANSPORT` ist nirgends gesetzt — `main()` fällt dann
  in den stdio-Zweig. Der Container läuft, öffnet nie einen Port, und die
  einzige Spur ist ein fehlschlagender Health-Check. Damit schliesst sie die
  Lücke zwischen dem Image-Default aus dem letzten Eintrag und dem, was im
  Betrieb tatsächlich startet.

  **Was sie bewusst nicht trägt, und warum das der wichtigere Teil ist.** Das
  Schema führt auf keiner Ebene einen Schlüssel für Umgebungsvariablen. Es prüft
  aber nur *Werte*: `builder: NIXPACKS_TYPO` und
  `restartPolicyType: SOMETIMES` werden abgewiesen, ein erfundenes
  `"variables": {…}` oder `deploy.env` validiert sauber durch. Wer die
  Allow-List dort hineinschreibt, bekommt keine Fehlermeldung und keine
  Wirkung — dieselbe Klasse wie ein Schlüssel, dessen Vorgabe niemand gelesen
  hat. `I14Y_MCP_ALLOWED_HOSTS` und `I14Y_MCP_TRANSPORT` gehören in die
  Service-Variablen.

  Ebenso fehlt `healthcheckPath`, und zwar gemessen statt vergessen: Durch den
  zusammengebauten Stack antwortet **kein** Pfad auf ein GET mit 2xx — `/` und
  `/health` sind 404, `/mcp` ist 400 ohne Session und 421 unter fremdem `Host`.
  Ein darauf gerichteter Health-Check hätte das Deployment als ungesund
  markiert und zurückgerollt. Der TCP-Check im Dockerfile prüft stattdessen den
  Port und bleibt dadurch vom Transport unabhängig.

  Drei Tests in `tests/test_entrypoint.py` halten das fest, bei den
  Transport-Tests, weil es dieselbe Kette ist: `railway.json` → Dockerfile →
  `main()` → `/mcp`. Der dritte verbietet `healthcheckPath` nicht, er verlangt
  einen Beleg — ist der Schlüssel gesetzt, wird der Pfad durch den gebauten
  Stack abgefragt und muss 2xx liefern. Gegenproben: Builder auf `NIXPACKS`,
  `dockerfilePath` ins Leere, `variables` am Wurzelknoten, `deploy.env` eine
  Ebene tiefer, `healthcheckPath: "/"` — jede fällt genau auf dem zugehörigen
  Test, und die letzte lässt den sonst übersprungenen Fall wirklich anlaufen.

### Documentation

- **Beide READMEs beschreiben `railway.json`**, samt der zwei Fallen: dass
  Umgebungsvariablen dort nicht hingehören, obwohl das Schema sie durchwinkt,
  und warum `healthcheckPath` leer bleibt.

### Changed

- **Das Container-Image fährt jetzt Streamable HTTP statt SSE.**
  `I14Y_MCP_TRANSPORT` stand im `Dockerfile` auf `sse` — dem einen Wert, den ein
  gehosteter Betrieb nicht brauchen kann. Ein Claude.ai-Custom-Connector spricht
  Streamable HTTP und holt den Server unter `/mcp` ab; die SSE-App serviert
  `/sse` und `/messages` und hat `/mcp` gar nicht. Am zusammengebauten Stack
  gemessen, nicht aus dem Transportnamen geschlossen:

  ```
  sse              POST /mcp -> 404
  streamable-http  POST /mcp -> 200
  ```

  Aufgefallen ist es im Railway-Deployment vom 20.9.2026: Der Container lief,
  der Health-Check war grün, der Port war offen — und der Connector kam nie zum
  Handshake, weil er einen 404 bekam. Ein TCP-Health-Check kann das nicht sehen,
  und er soll es auch nicht: Er prüft bewusst den Port und keinen MCP-Pfad, der
  mit dem Transport wandert.

  `main()` bleibt unverändert und nimmt weiterhin `sse`, `streamable-http` und
  `http`; `stdio` bleibt die Vorgabe des Einstiegspunkts selbst. Wer
  `uvx i14y-mcp` für Claude Desktop startet, ist von der Änderung nicht
  betroffen — sie betrifft nur das Image.

- **`compose.yaml` setzt denselben Wert.** Die Datei setzte
  `I14Y_MCP_TRANSPORT: sse` eigenständig und überstimmte damit das Image. Eine
  Änderung allein am `Dockerfile` hätte `docker compose up` deshalb auf genau
  dem Transport gelassen, der abgelöst werden sollte — im Diff vollständig
  aussehend, im Betrieb nicht. Dieselbe Klasse wie die drei
  `mcp.settings`-Zeilen aus `0.4.0`, von denen eine repariert wurde und zwei
  stehen blieben.

  `tests/test_entrypoint.py` hält beide Stellen jetzt fest und misst dabei nicht
  die Zeichenkette, sondern die Pfade der App, die `main()` an uvicorn übergibt.
  Ein Vergleich auf `"streamable-http"` wäre grün geblieben, wenn das SDK den
  Pfad verschöbe. Ein zusätzlicher Fall hält fest, dass `/mcp` die beiden
  Transporte überhaupt trennt — ohne ihn wäre die Zusicherung auch gegen ein
  Image mit `sse` grün, sobald beide Apps denselben Pfad servierten.

### Fixed

- **Der HEALTHCHECK-Kommentar im `Dockerfile` beschrieb den falschen Transport.**
  «The SSE runtime opens PORT» stimmte nach dem Wechsel nicht mehr und wäre
  genau die Sorte Satz, die beim nächsten Mal als Beleg gelesen wird. Jetzt
  transportneutral, mit der Begründung, warum der Check ein TCP-Connect ist und
  kein Request auf den MCP-Pfad.

### Documentation

- **Beide READMEs nennen die Connector-URL `https://<host>/mcp`** und erklären,
  warum ein SSE-Deployment dort einen 404 liefert.

- **`I14Y_MCP_ALLOWED_HOSTS` ist jetzt dokumentiert**, samt der beiden
  Fehlbedienungen, die im Betrieb gegensätzlich aussehen. Der Wert wird literal
  mit dem `Host`-Header verglichen: Mit Schema oder Port geschrieben trifft er
  nichts, und jede Anfrage scheitert mit HTTP 421 — also **nur Hostnamen,
  kommagetrennt, ohne Schema und ohne Port**. Weggelassen fällt er bei einem
  Nicht-Loopback-Bind nicht auf etwas Sicheres zurück, sondern schaltet die
  Host-Prüfung ganz ab (`dns_rebinding_protection_off` im Log). Beides war im
  Code begründet und in keinem README erwähnt.

## [0.4.0] — 2026-09-19

Zwei Gründe, warum dieses Release nötig ist, und beide betreffen Leute, die das
veröffentlichte Paket einsetzen.

**Der HTTP- und SSE-Transport war seit der 2.x-Migration tot — auch noch,
nachdem er als repariert galt.** Die 1.x-API führte `host`, `port` und
`transport_security` auf `mcp.settings`; in 2.x gibt es keines der drei, und
pydantic wirft auf eine Zuweisung an ein nicht deklariertes Feld sofort. Drei
solche Zeilen standen im Code. Eine (`transport_security`, in `_run_http`) wurde
behoben und mit einem Test versehen — die anderen zwei (`host`, `port`, in
`main`) blieben stehen, und damit starb jeder HTTP-Start weiterhin, nur zwei
Zeilen später:

```
ValueError: "Settings" object has no field "host"
```

Aufgefallen ist es erst beim **gebauten Rad in einer frischen venv**, nicht am
Quellbaum: `i14y-mcp` mit `I14Y_MCP_TRANSPORT=streamable-http` beendete sich
sofort, ohne je einen Port zu öffnen. Am Commit, der `0.3.2` setzte
(`107e920`), standen alle drei Zeilen — das veröffentlichte `0.3.2` hat also
keinen HTTP-Transport, nur stdio. Der Grund, warum 180 Tests das nicht sahen:
sie setzen alle *unterhalb* von `main()` an, und dort standen die Zeilen.
`tests/test_entrypoint.py` ruft den Einstiegspunkt jetzt selbst auf.

Die Lehre ist nicht «zwei Zeilen übersehen», sondern: eine Reparatur, die eine
von drei gleichartigen Zeilen entfernt, sieht im Diff vollständig aus. Und ein
Test, der die reparierte Ebene prüft statt die, die der Betrieb startet, belegt
die Reparatur nicht.

**Die Spec-Revision `2026-07-28` wird jetzt nicht nur bedient, sondern auch
beantwortet.** Die moderne Ära lief in `0.3.2` bereits vollständig — und
transportierte dabei eine leere Serverversion und `instructions: null`.

### Changed (breaking)

- **BRECHEND: Browser-Origins sind jetzt fail-closed.** `allow_origins` war
  der Literalwert `["*"]`, ohne jede Möglichkeit, ihn einzuengen —
  jede Website im Internet konnte diesen Server aus dem Browser eines
  Besuchers aufrufen. Gemessen vorher:
  `Origin: https://boesartig.example` bekam `200` mit
  `Access-Control-Allow-Origin: *`.

  Die Origins kommen jetzt aus `I14Y_MCP_CORS_ORIGINS` (kommagetrennt) und
  sind **standardmässig leer** — kein Browser-Client wird zugelassen. Wer
  Browser-Clients will, nennt die Origins; niemand erbt eine Freizügigkeit, die
  er nicht gewählt hat.

  `*` ist weiterhin erreichbar, aber nicht mehr stillschweigend: es muss
  ausdrücklich gesetzt werden und schreibt eine Warnung ins Log. Eine
  Verengung des Standards ist nicht dasselbe wie das Entfernen der Option.

  **Wer den bisherigen Zustand behalten will, setzt `I14Y_MCP_CORS_ORIGINS=*`.**
  stdio- und andere Nicht-Browser-Clients sind unberührt — CORS betrifft nur
  Browser.

### Added

- **Der Server sagt auf Spec `2026-07-28` jetzt, wer er ist.** Die moderne Ära
  lief hier schon vollständig — `server/discover`, Envelope pro Anfrage,
  Frischehinweise auf `tools/list`. Was sie transportierte, war gemessen dies:

  ```json
  {"name": "i14y-mcp", "version": ""}
  ```

  und `"instructions": null`. Das SDK stempelt `serverInfo` unter *jede*
  moderne Antwort, nicht nur unter die Erkennung; die leere Version stand also
  auf jedem einzelnen Response. `_version.__version__` war die ganze Zeit
  richtig und wurde `MCPServer` nur nie übergeben. 162 Tests blieben dabei
  grün, weil keiner hinsah.

  Gesetzt sind jetzt `version` (aus den Paket-Metadaten, dieselbe Quelle wie
  der `User-Agent`), `title`, `description`, `website_url` und `instructions`.
  `description` und `website_url` stehen wortgleich in `server.json`, dem
  Registry-Manifest — den zwei Stellen, an denen ein Client diesen Server
  beschrieben sieht; ein Test legt sie nebeneinander, statt darauf zu bauen,
  dass beide gepflegt werden.

- **`instructions` auf `server/discover`.** Auf `2026-07-28` ist das die
  einzige Stelle, an der ein Server als Ganzes erklärt wird — Tool-Beschreibungen
  erklären je ein Werkzeug. Der Text nennt die Aufrufreihenfolge und die zwei
  Eigenheiten der Quelle, an denen Aufrufer auflaufen: dass der Suchindex oben
  nur Datasets führt (Konzepte und Data Services gehen über `list_concepts`
  bzw. `list_data_services`) und dass jeder Datensatz mehrsprachig ist. Beides
  stand bisher nur in einer Tool-Beschreibung, die man schon gefunden haben
  musste.

- **Anzeigenamen für alle 13 Werkzeuge** (`tools[].title`). Ohne sie zeigt ein
  Client `search_codelist_entries`. Die Signatur-Sperre
  `tool-definitions.lock.json` ist unberührt: sie deckt Argumentnamen und
  Pflichtfelder ab, nicht die Anzeige.

- **`tests/test_spec_2026_07_28.py`** — zwölf Zusicherungen an der Antwort, nie
  an der Konfiguration. Der stdio-Fall fährt einen echten Unterprozess:
  `Client(mcp)` verbindet in-process und umgeht die JSON-RPC-Rahmung ganz
  (`_connect_inproc` im SDK), kann über den Transport, den `uvx i14y-mcp`
  startet, also nichts aussagen — und stdio ist die Vorgabe.

  Zwei Lücken hat erst die Gegenprobe gezeigt, beide in der ersten Fassung
  dieser Datei: `title=SERVER_TITLE` liess sich entfernen, ohne dass ein Test
  fiel, und `assert f"i14y-mcp/{version}" in USER_AGENT` war mit `version == ""`
  erfüllt — also genau im Ausgangsbefund grün. Beide sind geschlossen, die
  zweite durch einen Vergleich auf Gleichheit statt auf Teilstring.

- **Frischehinweise auf `tools/list` und `server/discover`** (SEP-2549, Spec
  `2026-07-28`): `ttlMs` 300000, `cacheScope` `public`. Das SDK setzt beides von
  sich aus auf «sofort veraltet, nie geteilt» — wer nichts übergibt, verhält
  sich also nicht neutral, sondern lässt jeden Client bei jeder Verbindung neu
  auflisten, für eine Liste, die beim Import feststeht und für jeden Aufrufer
  dieselbe ist. `prompts/list` und `resources/list` bleiben ungesetzt: dieser
  Server registriert weder das eine noch das andere.

- **Protokoll-Gate: beide Spec-Aeren gepinnt und geprueft**
  (`tests/test_protocol_version.py`). `mcp` 2.x bedient zwei Aeren ueber
  denselben Server — den `initialize`-Handshake, der bei `2025-11-25`
  deckelt, und den Pro-Request-Envelope, der `2026-07-28` erreicht.
  `LATEST_PROTOCOL_VERSION` ist ein Alias auf die **moderne** Aera; wer nur
  dagegen pinnt, laesst genau die Aera frei wandern, die heutige Clients
  aushandeln. Beide sind jetzt einzeln gepinnt, ein Dependabot-Bump von
  `mcp` kann keine davon still verschieben.

  Nachgemessen statt aus Konstantennamen geschlossen: ein echter `initialize`
  durch den zusammengebauten ASGI-Stack. Ein Client, der ueber den Handshake
  nach `2026-07-28` fragt, bekommt `2025-11-25` zurueck.

  Beide READMEs beschreiben die Aeren; ein Test haelt jede Sprache einzeln
  dagegen — im Portfolio sind EN und DE desselben Repos schon dreimal
  auseinandergelaufen, weil nur eine Fassung nachgezogen wurde.

- **Recorded response fixtures, one per external endpoint, each dated.**
  `tests/fixtures/` now holds real I14Y responses for all eleven endpoints the
  server calls, taken by `scripts/record_fixtures.py`, with source, date,
  selection rule and SHA-256 per file in `tests/fixtures/PROVENANCE.md`.
  `tests/test_recorded_fixtures.py` replays them through the actual tools.
  Counter-checked by neutralising each new assurance one at a time: reverting
  either mapper fails exactly its own tests, stripping the recording date fails
  the provenance check, adding a fixture without a provenance entry fails the
  completeness check, deleting a recording fails the coverage guard, and
  renaming `title` to `titel` in a recording fails exactly the dataset test —
  the field-rename scenario that unit tests missed in production.

### Changed

- **Frischehinweise für alle fünf cachebaren Methoden**, nicht mehr nur für
  `tools/list` und `server/discover`. Im Code stand, `prompts/list` und
  `resources/list` blieben bewusst ungesetzt, weil dieser Server weder Prompts
  noch Ressourcen registriert und ein Hinweis «eine Fläche beschriebe, die es
  nicht gibt». Nachgemessen trägt die Begründung nicht: `MCPServer` verdrahtet
  `on_list_prompts`, `on_list_resources` und `on_list_resource_templates`
  bedingungslos. Alle drei antworten auf der modernen Ära mit HTTP 200 und
  einer leeren Liste — und taten das mit `ttlMs: 0, cacheScope: private`, also
  dreimal dasselbe Nichts bei jeder Verbindung.

  Der neue Test leitet die Liste aus `CACHEABLE_METHODS` des SDK ab statt aus
  unserem eigenen Dict: `CACHE_HINTS` gegen sich selbst zu prüfen kann nie
  zeigen, dass ein Eintrag fehlt. Eine künftig neu bediente cachebare Methode
  fällt damit auf, statt still mit `ttlMs: 0` zu antworten.

- **Die Pruefsummen im Fixture-Nachweis waren Zierde.** `PROVENANCE.md` fuehrt
  je Datei einen SHA-256 — um genau einen Fall zu fangen: eine Aufzeichnung,
  die nach dem Lauf von Hand nachgebessert wurde. Eine korrigierte Antwort ist
  wieder eine erfundene, und von aussen ist ihr das nicht anzusehen.
  Nachgerechnet hat sie kein Test. `test_die_pruefsumme_im_nachweis_stimmt`
  tut es jetzt, ueber die Bytes auf der Platte statt ueber den Loader — genau
  die hat der Recorder gehasht.

- **Die Fixture-Ablage folgt jetzt der Portfolio-Konvention.** Die erste
  Fassung legte Herkunft und Aufnahmedatum in einen `_recording`-Block je
  JSON-Datei. 21 andere Server des Portfolios — darunter `meteoswiss-mcp` und
  `swiss-statistics-mcp` — halten dieselben Angaben stattdessen in
  `tests/fixtures/PROVENANCE.md`, zusammen mit Auswahlregel und SHA-256 je
  Datei, und laden ueber ein `tests/fixture_data.py`. Diese Abweichung war beim
  Anlegen unbekannt und ist damit behoben: die Fixtures liegen als rohe
  Antwortkoerper, `tests/conftest.py` weicht `tests/fixture_data.py`, und die
  IDs der Detail-Pfade leiten die Tests aus der Aufzeichnung selbst ab statt
  aus einer zweiten, still veraltenden Stelle. Neu aufgezeichnet am 2026-08-14.
  Dabei kam eine Zusicherung dazu, die vorher fehlte: eine Fixture ohne Eintrag
  in `PROVENANCE.md` faellt jetzt auf.

- **Counter-check rule in `CLAUDE.md` sharpened.** Neutralising an assurance
  and getting only a symptom back — runtime, log noise, empty fields — means
  the assurance is still missing, not that it held. Both defects found in this
  cycle read that way first: the mapper mismatch surfaced as null titles, and
  removing the backoff seam failed nothing at all, it just made the suite 29x
  slower.

- **The offline tests no longer disarm `asyncio.sleep` process-wide.** All three
  test modules collapsed the retry backoff with
  `monkeypatch.setattr(client.asyncio, "sleep", ...)`, which reads as a local
  override but replaces `sleep` on the shared module object — for httpx, respx,
  pytest-asyncio and every other importer. `client.py` now exposes the seam as
  a module-level alias `_sleep`, and the tests patch that. Two new tests hold
  the line: one asserts the patch does not reach the `asyncio` module and that
  real sleeping still works (real clock, not a fake one), the other records the
  delays the retry requests and checks them against the 2/4/8 ladder with its
  jitter bounds.
- **CI lints `scripts/` too.** Both ruff gates ran on `src/ tests/` only, so
  `scripts/record_fixtures.py` was unchecked. Verified by planting a violation
  in `scripts/`: the old paths stayed green, the new ones caught it.
  `CONTRIBUTING.md`, `CONTRIBUTING.de.md` and `CLAUDE.md` quote the gates
  verbatim and were updated in step.

- **`CONTRIBUTING.md` documented only one of the two lint gates.** The
  development section listed `ruff check src tests` and never mentioned
  `ruff format --check src/ tests/`, so following the instructions ran half the
  lint check and left the other half to fail in CI. Both files now list all
  three CI gates verbatim, note that lint and formatting are independent
  checks, and point at the ruff pin in `pyproject.toml`. `CONTRIBUTING.de.md`
  updated in step.

### Fixed

- **README.md nannte zwei Protokoll-Stände gleichzeitig.** Ein Abschnitt
  «MCP protocol version» behauptete `mcp >= 1.28.1` und eine Aushandlung «at
  initialize time», während der Abschnitt zwei Zeilen darunter die beiden
  tatsächlichen Ären führte und `pyproject.toml` seit dem 2.x-Umstieg
  `mcp>=2.0.0,<3` pinnt. Der veraltete Abschnitt ist entfernt, nicht korrigiert:
  er war eine zweite Fassung derselben Auskunft und wäre wieder auseinandergelaufen.
  `README.de.md` hatte ihn nie.

- **Two docstrings described the SDK's transport-security default wrongly.**
  `build_transport_security` and `tests/test_transport_security.py` both claimed
  the SDK "leaves DNS-rebinding protection OFF while `transport_security` is
  unset", quoting the SDK's own "backwards compatibility" note as if it settled
  the matter. It does not — that note describes
  `TransportSecurityMiddleware(None)`, constructed directly. `sse_app` and
  `streamable_http_app` never hand the middleware a bare `None`: with
  `transport_security` unset and a loopback `host` — and `host` **defaults** to
  `127.0.0.1` — they synthesise a loopback-only list themselves
  (`mcp/server/mcpserver/server.py`).

  Measured through the assembled stack: a bare `mcp.streamable_http_app()`
  answers `421 Invalid Host header` under `Host: testserver` and `200` under
  `Host: 127.0.0.1:8000`. An unwired server is therefore not unprotected, it is
  protected for loopback only — which is worse to diagnose, because it looks
  fine in local testing and rejects every real hostname and every configured
  origin in production. The test file's second claim, "this server never set it,
  so there was no Host check at all", was wrong for the same reason.

  No behaviour changes: this server passes `transport_security` and `host`, and
  the code was already correct. What was wrong was the account of *why*.
  `test_the_sdk_default_is_loopback_only` now measures both layers instead of
  restating them, so the correction cannot rot the way the claim it replaces
  did.

- **Der HTTP-Transport startete auch nach der `transport_security`-Reparatur
  nicht.** `main()` setzte weiterhin `mcp.settings.host` und
  `mcp.settings.port` — dieselbe Fehlerklasse, dieselbe Ausnahme, zwei Zeilen
  hinter der behobenen Stelle. Beide Werte reicht `_run_http` ohnehin an
  `build_http_app` und `uvicorn.run` weiter; die Zuweisungen waren also nicht
  nur tödlich, sondern auch wirkungslos. Sie sind entfernt.

  `tests/test_entrypoint.py` ruft `main()` jetzt selbst auf, mit gestubbtem
  `uvicorn.run`, für alle drei Schreibweisen der Transport-Variablen und für
  stdio. Die Gegenprobe: mit den zwei Zeilen zurück fallen genau vier Tests,
  vorher fiel keiner. Dazu eine Zusicherung, dass `Settings` die drei Felder
  nicht führt — damit eine künftige Zuweisung nicht wieder damit begründet
  wird, das Feld gebe es ja.

- **Jeder HTTP-Transport starb beim Start.** `_run_http` setzte
  `mcp.settings.transport_security = security` — die Form vor 2.x. In `mcp` 2.x
  gibt es das Feld nicht, pydantic wirft `ValueError: "Settings" object has no
  field "transport_security"`, und zwar bevor uvicorn überhaupt erreicht wurde.
  Die Transport-Sicherheit ist jetzt ein Schlüsselwort-Argument von
  `build_http_app`, wie im SDK vorgesehen. Ohne sie kam ein fremder `Host`
  durch die Prüfung (400 statt 421) — der Test hält genau diesen Unterschied
  fest, statt bloss zu belegen, dass die Funktion das Argument entgegennimmt.

- **`allow_headers` stand auf `["*", "Mcp-Session-Id"]`,** und die Wildcard
  gewann: Starlette schaltet damit auf `allow_all_headers` und spiegelt im
  Preflight zurück, was der Browser ankündigt. Die Liste nennt jetzt
  `Content-Type`, die drei Routing-Header der Spec `2026-07-28`,
  `Mcp-Session-Id` und `Last-Event-ID`. Letzterer setzt einen abgerissenen
  SSE-Strom fort und war unter der Wildcard nie geprüft — eine Wildcard kann
  nicht falsch werden und sagt deshalb nichts darüber, ob die Header, die das
  Protokoll braucht, freigegeben sind.

  `allow_origins` bleibt unverändert bei `["*"]`. Das ist eine eigene
  Entscheidung mit eigenen Folgen für bestehende Clients und gehört nicht in
  diesen Commit.

- **`list_concepts`, `get_concept` and `list_public_services` returned a null
  title for every record.** `/concepts` and `/publicservices` label their
  records `name`; datasets and data services use `title`. Both mappers read
  only `title`, so three tools produced titleless output in production while
  the whole suite stayed green — the handwritten fixtures invented a `title`
  key, so they agreed with the mapper instead of with the source. Found by
  replaying recorded responses, not by reading the code.

- **Die README nannte einen SDK-Bereich, den `pyproject.toml` nicht
  deklariert.** Der Abschnitt sprach von `mcp >= 1.28.1`, deklariert ist
  `mcp>=2.0.0,<3` — eine Major-Version daneben, und genau die, die die zweite
  Protokoll-Aera mitbringt.

- **The retry had six defects, all inherited from the shared template.** This
  server copied its retry from `reference/retry_backoff.py` in
  [mcp-data-source-probe-skill](https://github.com/malkreide/mcp-data-source-probe-skill),
  and the template shipped these until 2026-08-07. A sweep across eleven
  servers found that none read `Retry-After` and none jittered — one template,
  eleven copies, not eleven independent omissions.
  1. **No jitter.** The ladder was deterministic, so every client that hit the
     same outage retried in lockstep and the load returned as a wave exactly
     when the source recovered — the retry storm extending the outage it was
     meant to bridge. Now spread into `[0.5x, 1.5x]`.
  2. **`Retry-After` was never read.** A 429 or 503 answers the very question
     the backoff curve guesses at. Both RFC 9110 §10.2.3 forms are now read
     (delta-seconds and HTTP-date); an unparseable header yields `None` and
     falls back to the curve — it must never crash on the error path. The
     jitter on top is one-sided `[1.0x, 1.25x]`: the source said *when*, so
     later is polite and earlier ignores the value just read.
  3. **No cap on a single wait**, and the cap now binds *after* the jitter.
     `min(cap, base) * jitter` and `min(cap, base * jitter)` both contain a cap
     and a jitter; only the second is bounded — 20s times 1.5 is 30s.
  4. **The budget counted attempts, not seconds.** Four attempts against an
     upstream that takes 30s to time out is two minutes inside one tool call,
     and an attempt count never says so. Now 25s for the whole call, anchored
     on the MCP SDK's `MCP_DEFAULT_TIMEOUT = 30.0`.
  5. **Nothing held that budget.** It is now an `asyncio.wait_for` wall-clock
     deadline rather than an httpx timeout: httpx bounds each *operation*, and
     its read timeout restarts with every chunk, so a slowly trickling response
     outlived the budget without any single read expiring. `asyncio.timeout`
     would read better here, but it needs 3.11 and `requires-python` is
     `>=3.10`; the paired `except asyncio.TimeoutError` is 3.10-safe for the
     same reason, since the builtin only became an alias for it in 3.11.
  6. **The wrapper hid the failure mode.** `UpstreamError` stays — OBS-002
     keeps raw upstream detail away from the model, and it is a type a caller
     can branch on. What changed is what the message carries. It interpolated
     `{last_error}` alone, and `httpx.ConnectTimeout`, `ReadTimeout` and
     `ConnectError` all have an **empty** `str()` — precisely the set an outage
     produces. The sentence read `Last error: .` and named neither the failure
     mode nor the host. It now names the exception type, the host, and which of
     the two limits ran out. Anyone who wraps has to name the type.

  Six tests cover the new behaviour: `Retry-After` in both forms plus the
  refusal cases, the jitter spread, that the cap binds after jittering, the
  one-sided `Retry-After` jitter, and that an empty `str()` still yields a
  message naming type and host. The existing context test asserted only
  `"unreachable after"` — it passed `"timed out"` as the mock's message, which
  is why it could not catch the empty-string case: informative in the test,
  blank in production.

## [0.3.2] - 2026-08-02

### Fixed

- **The User-Agent named no version.** Outbound requests carried

  ```
  i14y-mcp (+https://github.com/malkreide/i14y-mcp)
  ```

  Nothing about it was wrong — it claimed no false number — but the operator of
  the data source could not tell which release was calling, which is half the
  reason to send a custom User-Agent at all. It now reads
  `i14y-mcp/<version> (+…)`, interpolated from the package metadata.

  This was the last such case in the portfolio. A fleet-wide probe reported it
  as `unverified`: a User-Agent was present but no value could be compared
  against the installed version. That is explicitly not a pass — "I could not
  resolve it" and "there is nothing wrong" are different claims.

- **`__version__` was a literal beside the one in `pyproject.toml`.** Two copies
  of a number the build decides. The same arrangement in `hn-tech-signal-mcp`
  led to `__version__` reporting `0.2.1` while the package shipped as `0.2.4`,
  and in `swiss-procurement-mcp` to a User-Agent announcing `0.4.0` from a
  package that was `0.18.3`.

  The version now comes from `importlib.metadata` in a module of its own,
  `_version.py`. A separate module rather than `__init__`, so that `client` can
  read the version without importing the package root: the root imports
  `server`, which imports `client`, and taking the version from a
  partially-initialised root would hold only until somebody reorders two lines.
  `bag-health-mcp` carries a latent circular import from exactly that shape.

  The fallback for an uninstalled source tree is `0.0.0+source` — a PEP 440
  local segment that cannot be read as a release.

- **Nothing asserted anything about the User-Agent before.** `tests/test_user_agent.py`
  now checks that it carries the installed version, that `__version__` equals it,
  that a version is named at all, and that no version literal returns under
  `src/`. Verified in the other direction too: with the bare token restored, two
  of the five tests fail.

## [0.3.1] - 2026-08-02

### Fixed

- **`structlog` carried no upper bound, and the index already serves a major past
  the floor.** The declared range was `structlog>=24.1`; PyPI has been serving
  `26.1.0`. The artefact does not change — the resolver's answer to the next
  fresh install does, and that is exactly how `swiss-energy-mcp` 0.3.3 became
  uninstallable when `mcp` 2.0.0 removed the module it imported.

  Now `structlog>=24.1,<27`. The bound is measured rather than guessed: this package
  installs and imports against `structlog 26.1.0` today, so the cap admits what
  demonstrably works and stops only the next, unknown major.

A dependency range only reaches users through a new release, hence the
version bump. No code changed.

## [0.3.0] — 2026-08-02

This release exists so that a repair reaches the people running the server:
**the published `0.2.1` cannot be installed any more.** It declares `mcp` with
no upper bound, and `mcp` 2.0.0 removed `mcp.server.fastmcp` — so a fresh
`pip install i14y-mcp` resolves to 2.0.0 and the console script dies on
startup with `ModuleNotFoundError`. Measured against the real artefact in an
empty venv, cold and warm interpreter alike.

The repository has carried the fix since the 2.x migration was merged; it was
simply never released, and `main` kept the same version number as the broken
artefact — so nothing contradicted it.

### Changed (breaking)

- **Migrated to the `mcp` Python SDK 2.x.** The server API moved from
  `mcp.server.fastmcp` to `mcp.server.mcpserver` with no compatibility shim,
  and the dependency is now `mcp>=2.0.0,<3`. The tool surface is unchanged —
  what breaks is embedding this server's Python API and the dependency floor.
  Anyone who must stay on `mcp` 1.x should stay on 0.2.x, and pin an upper
  bound themselves, because the published 0.2.1 has none.

### Fixed

- The dependency on `mcp` carries an upper bound at all. The previous
  unbounded range is what let a new major reach an unchanged artefact: the
  package did not change, the resolver's answer did.

## [0.2.1] — 2026-07-25

Patch release to complete the MCP Registry publish (0.2.0 shipped to PyPI but its
registry entry failed validation).

### Fixed
- Shortened the `server.json` description to ≤100 characters so the MCP Registry
  publish passes its metadata validation (the v0.2.0 registry publish had failed
  on this; PyPI publish succeeded).
- Added the `mcp-name: io.github.malkreide/i14y-mcp` ownership marker to
  `README.md` (the PyPI long-description) so the MCP Registry can validate that
  the PyPI package and the GitHub namespace share an owner. PyPI READMEs are
  immutable per version, so this required a new release to reach PyPI.

### Changed
- `publish.yml` now also accepts `workflow_dispatch`, so the MCP Registry publish
  can be re-run manually (PyPI upload is a no-op via `skip-existing`).

## [0.2.0] — 2026-07-24

First production-ready release. Aligns the repository with the Swiss Public Data
MCP portfolio, runs a full MCP best-practice audit, and remediates all findings.

**Audit verification:** production-ready ✅ — run-id
`2026-07-24T091742-Z-i14y-mcp`, catalog hash `091f446b2796…`, results 36 pass ·
0 fail · 5 non-blocking partials · 3 todo. Details under
[`audits/`](audits/2026-07-24T091742-Z-i14y-mcp/audit-report.md).

### Added
- Portfolio-standard repository scaffolding to align with the other Swiss Public
  Data MCP servers: `Dockerfile`, `compose.yaml`, `claude_desktop_config.json`,
  `.dockerignore`, `.gitignore`, and a `server.json` manifest for the MCP Registry.
- GitHub Actions workflows: `ci.yml` (matrix 3.10–3.13), `live.yml` (scheduled
  live API suite), `publish.yml` (PyPI + MCP Registry via OIDC Trusted Publishing),
  plus `.github/dependabot.yml`.
- Contributor and security documentation: `CONTRIBUTING.md` / `CONTRIBUTING.de.md`,
  `SECURITY.md` / `SECURITY.de.md`, and `PUBLISHING.md`.
- MCP best-practice audit results under `audits/` (44 checks, 19 findings).
- `docs/roadmap.md` documenting the Read-only-First phase architecture (OPS-003).
- `HEALTHCHECK` in the Docker image so orchestrators can detect an unhealthy
  container (SCALE-004).
- Structured JSON logging on stderr via `structlog`, with per-request severity
  levels (OBS-003).
- `Context` injection across all tools for client-visible progress/logging, with
  per-endpoint progress in `api_status` (SDK-003).
- `search_catalog` now returns a `match_type` and an actionable `hint` on an empty
  result instead of a bare empty list (ARCH-003).
- `docs/network-egress.md` documenting the code- and network-layer egress
  controls (SEC-021).
- `tool-definitions.lock.json`, a committed hash snapshot of the tool set and
  each tool's argument surface (names + required), verified by a test as a
  rug-pull guard that is stable across SDK patch upgrades (SEC-022).
- README sections on MCP primitives (tools-only rationale, ARCH-008) and the MCP
  protocol version / update policy (ARCH-012).
- Container FD `ulimits` and a memory reservation in `compose.yaml` (SCALE-006).
- All tool annotations now also set `idempotentHint: true` and
  `openWorldHint: true` (every tool is a side-effect-free GET against an external
  API), alongside the existing `readOnlyHint`/`destructiveHint` (ARCH-009).
- Second audit run under `audits/` confirming production-readiness (36 pass, 5
  residual non-blocking partials, 0 fail).
- Tests for the shared client, error masking, CORS session-header exposure, empty
  search hints, boundary input rejection, egress control and tool-lock integrity.

### Changed
- **HTTP transports now default to `HOST=127.0.0.1` (loopback)** instead of
  `0.0.0.0`; binding to all interfaces is an explicit opt-in and warns on stderr
  outside a container (SEC-016). The Docker image sets `HOST=0.0.0.0` on purpose;
  remote/PaaS deployments must set it explicitly.
- A single pooled `httpx.AsyncClient` is now created once in a FastMCP lifespan and
  reused across tool calls instead of being rebuilt per call (SDK-001).
- Tool arguments now carry strict schema constraints (`ge`/`le`, `min_length`,
  whitelist `pattern` on IDs), so malformed input is rejected at the boundary
  instead of silently clamped (SEC-018).
- The anchor demo query is now answered in two tool calls; `get_dataset` is
  documented as the aggregated detail tool (ARCH-007).

### Fixed
- SSE / streamable-http now sets CORS to expose the `Mcp-Session-Id` header, so
  browser MCP clients keep their session (SDK-004).
- Upstream failures surface actionable execution errors (pointing at
  `api_status` / `search_catalog`), covered by execution- and protocol-error
  tests (OBS-001).

### Security
- Upstream 4xx error bodies are no longer embedded verbatim in client-facing
  errors; a categorised message (HTTP status + path) is surfaced instead (OBS-002).
- Code-layer egress allow-list (`ALLOWED_HOSTS` frozenset) with
  `follow_redirects=False`, refusing any off-host redirect (SEC-021).

## [0.1.0] — 2026-07-21

### Added
- Initial release. 13 read-only tools over the I14Y interoperability platform:
  `search_catalog`, `list_datasets`, `get_dataset`, `get_dataset_distributions`,
  `list_data_services`, `get_data_service`, `list_public_services`,
  `list_concepts`, `get_concept`, `search_codelist_entries`, `list_publishers`,
  `list_catalogs`, `api_status`.
- Dual transport: stdio and streamable-http/SSE via `I14Y_MCP_TRANSPORT`.
- Retry with exponential backoff (2s/4s/8s); 4xx other than 429 fail fast.
- Pydantic v2 response envelope carrying `source` and `provenance`.
- Bilingual documentation (EN/DE) and full probe report in `docs/probe-i14y.md`.

### Known findings
Discovered during the live probe on 2026-07-21. Recorded here so the next
server in the portfolio does not have to rediscover them.

- **The search parameter is `query`, not `q`.** Unknown query parameters are
  silently discarded and the endpoint returns the entire index — a 15 MB
  response with HTTP 200. The API never says no; it says everything.
- **`page` and `pageSize` are ignored on `/api/search`.** The complete result
  set is always returned. Capping must happen client-side.
- **The `types` filter on search only works for `Dataset`.** `Concept`,
  `DataService`, `PublicService` and `MappingTable` are accepted without error
  but yield zero results, although those entities exist.
- **The search index covers about 51 % of the register** (1013 of ~2003
  datasets). Search is the entry point, `list_datasets` the completeness
  guarantee.
- **Multilingual nesting is inconsistent.** Themes wrap their language object
  under `name`, keywords under `label`, titles sit directly as
  `{de, fr, it, en}`. A naive extractor leaks a dict into a string field.
  Caught by a live test, not by unit tests.
- **`endpointUrls` may contain entries without a URI**, carrying only a label
  such as «OpenAPI Spezifikation». These are surfaced, not dropped.
- **`/api/concepts/{id}/codelist-entries` returns 405.** Only the `/search`
  subpath exists, and it requires `language` (HTTP 400 otherwise).
- **Read endpoints need no authentication**, despite the OpenAPI document
  declaring a Bearer scheme. Write endpoints do.

[Unreleased]: https://github.com/malkreide/i14y-mcp/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/malkreide/i14y-mcp/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/malkreide/i14y-mcp/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/malkreide/i14y-mcp/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/malkreide/i14y-mcp/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/malkreide/i14y-mcp/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/malkreide/i14y-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/malkreide/i14y-mcp/releases/tag/v0.1.0
