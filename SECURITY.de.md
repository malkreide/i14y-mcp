# Sicherheitsrichtlinie & Posture

[🇬🇧 English Version](SECURITY.md)

`i14y-mcp` ist ein **Read-only-**, **No-Auth-**, **Public-Open-Data-**MCP-Server.
Dieses Dokument fasst die Sicherheits-Posture zusammen und beschreibt, wie
Schwachstellen gemeldet werden.

## Schwachstelle melden

Bitte ein privates Security Advisory im GitHub-Repository eröffnen oder die in
`README.md` genannte Maintainerin kontaktieren. Für ausnutzbare Schwachstellen
keine öffentlichen Issues erstellen.

## Posture-Zusammenfassung

Alle 13 Tools stellen ausschliesslich Lese-Anfragen an die öffentliche I14Y-API
(`api.i14y.admin.ch`); es gibt keine Schreib-, Sende- oder
Dateisystem-Fähigkeiten, und es werden keine Personendaten verarbeitet — der
Server stellt ausschliesslich Katalog-Metadaten bereit.

| Bereich | Kontrolle |
|---|---|
| Egress | Fixe HTTPS-Basis-URL nur zu `api.i14y.admin.ch`; keine nutzergesteuerten URLs, daher keine SSRF-Angriffsfläche |
| TLS | httpx-Zertifikatsprüfung standardmässig aktiv und im Code nie deaktiviert |
| Auth / Secrets | Unauthentifizierte öffentliche Lese-API — es werden keine API-Keys, Tokens oder Secrets gespeichert oder weitergereicht. Schreib-Endpunkte der Quell-API benötigen einen Bearer-Token und werden bewusst nicht exponiert |
| Input | Pydantic-v2-Validierung an allen Tool-Grenzen; Query-Parameter werden URL-kodiert und numerische Bereiche geklammert |
| Tools | Alle mit `readOnlyHint: true`, `destructiveHint: false` annotiert; keine dynamische oder Remote-Tool-Registrierung |
| Fehler | Upstream-RFC-7807-Fehlerbodies werden als strukturierte Daten offengelegt, nie stillschweigend verschluckt; `api_status` liefert immer einen auswertbaren Zustand |
| Stdout | Reserviert für den JSON-RPC-Stream; der Server gibt kein Fremd-Logging auf stdout aus |
| Binding | `stdio` als Default (keine Netzwerk-Angriffsfläche). SSE / streamable-http bindet an `HOST` (Default `0.0.0.0`), gedacht für Container-Deployment hinter einem Reverse-Proxy / Gateway |

## Akzeptierte Risiken (Kontrollen auf Portfolio-Ebene)

Die folgenden Punkte werden auf der MCP-Gateway-/Host-Ebene behandelt, nicht in
diesem einzelnen Server. Das Restrisiko ist hier gering, weil der Server
read-only und unauthentifiziert ist und nur einen vertrauenswürdigen
Open-Data-Anbieter erreicht.

- **Session-Krypto-Bindung** — nicht anwendbar: Es gibt keine Nutzeridentität zum
  Binden, da der Server öffentliche Daten ohne Authentifizierung bereitstellt.
- **Server-übergreifende Tool-Poisoning-Erkennung** — Aufgabe des Gateways/Hosts.
  Die Tool-Definitionen dieses Servers sind versioniert, in-repo verfasst und per
  PR reviewt; es gibt keine dynamische oder Remote-Tool-Registrierung.
- **Netzwerk-Binding für gehostete Deployments** — der SSE-/streamable-http-
  Transport bindet an `HOST` (Default `0.0.0.0`), damit der publizierte Port aus
  dem Container erreichbar ist. Dann mit einem Reverse-Proxy / Gateway betreiben,
  das TLS und Zugriffskontrolle erzwingt; der Default-Transport (`stdio`) hat gar
  keine Netzwerk-Angriffsfläche.

## Re-Evaluations-Trigger

Diese Akzeptanzen sind neu zu bewerten, sobald der Server je:

- **Schreib**-Fähigkeit erhält oder **PII** verarbeitet, oder
- ein **Authentifizierungs**-Modell erhält (dann gebundene, TTL-behaftete,
  serverseitig invalidierbare Session-IDs implementieren und vor dem Merge
  re-auditieren), oder
- Tools **dynamisch** / aus Remote-Quellen registriert, oder
- hinter einem gemeinsamen MCP-Gateway aggregiert wird (dann Tool-Allow-Listing
  und Tool-Poisoning-Erkennung des Gateways aktivieren).
