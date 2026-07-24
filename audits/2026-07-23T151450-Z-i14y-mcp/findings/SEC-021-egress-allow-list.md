## Finding: SEC-021 — Egress-Allow-List: Code-Layer und Network-Layer

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `i14y-mcp` |
| **Check-Reference** | `SEC-021` |
| **PDF-Reference** | Anhang B5 + B12 |
| **Audit-Datum** | 2026-07-23 |
| **Auditor** | Claude Code (mcp-audit skill) |
| **Check-Status** | partial |

### Observed Behavior

Die feste Single-Host-`base_url` (`client.py:15`) wirkt de facto als Code-Layer-Egress auf genau ein Ziel, und SECURITY.md dokumentiert «Fixed HTTPS base URL only». Es fehlen jedoch eine explizite Allow-List (`frozenset` + `assert_host_allowed`), eine Network-Layer-Egress-Kontrolle (keine NetworkPolicy/Security-Group) und `docs/network-egress.md`; `follow_redirects=True` ist nicht host-beschränkt.

### Expected Behavior

Egress soll auf zwei Ebenen kontrolliert sein: Code-Layer (Host-Allow-List, geprüfte Redirects) und Network-Layer (NetworkPolicy/Egress-Firewall), plus Doku.

### Evidence

- src/i14y_mcp/client.py:15,57-58 — BASE_URL is hardcoded to a single host and set as httpx base_url; effectively a single-destination egress constraint at the code layer (no other host is reachable via user input)
- SECURITY.md:22 — documents 'Fixed HTTPS base URL to api.i14y.admin.ch only'
- server.py tools pass only relative paths, so egress targets are constrained to one host by construction

### Risk Description

Ein offener Redirect der Upstream-API könnte den Client (theoretisch) auf einen fremden Host lenken; ohne Network-Layer-Kontrolle gibt es keine zweite Verteidigungslinie.

### Remediation

1. Host-Allow-List als `frozenset({"api.i14y.admin.ch"})` einführen und Redirect-Ziele dagegen prüfen (oder `follow_redirects=False`).
2. `docs/network-egress.md` mit dem erlaubten Host dokumentieren.
3. Für Cloud-Deployments eine Egress-NetworkPolicy/Security-Group empfehlen.

### Effort Estimate

**S** (< 1 Tag, lokaler Fix)

### Verification After Fix

- Re-Audit dieses Checks (`SEC-021`) gegen den Katalog
- Neuer/angepasster Test, der das Anti-Pattern abprüft (wo automatisierbar)
