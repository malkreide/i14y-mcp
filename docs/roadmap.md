# Roadmap & project phase

`i14y-mcp` follows the portfolio's **Read-only First** phase architecture: a
server earns write and multi-agent capabilities only after the previous phase is
proven and audited. This keeps the security surface small while the server is
young.

## Current phase: **Phase 1 — Read-only**

All 13 tools are annotated `readOnlyHint: true`, `destructiveHint: false` and
issue only HTTP `GET` requests against the public I14Y API. There is no
authentication, no write/send/filesystem capability, and no personal data. This
is the intended long-term posture for a metadata-catalogue server — Phase 2 is
only entered if a concrete use case requires it.

| Phase | Scope | Status |
|---|---|---|
| **1 — Read-only** | Discovery/read tools over the public catalogue; stdio + SSE transport; no auth | ✅ current |
| **2 — Write** | Any write/submit capability (not currently planned) | ⛔ not started |
| **3 — Multi-agent** | Aggregation behind a shared MCP gateway | ⛔ not started |

## Phase-transition prerequisites

Moving to **Phase 2 (write)** would require, before any write tool is merged:

- an authentication model with bound, TTL'd, server-side-invalidated session IDs;
- human-in-the-loop confirmation for destructive operations (HITL checks);
- input validation hardened to strict Pydantic argument schemas (SEC-018);
- a fresh security audit (see [`../audits/`](../audits/)) with no open `critical`/`high` findings.

Moving to **Phase 3 (multi-agent / gateway)** would additionally require:

- tool-name namespacing and tool-definition hash pinning (SEC-022);
- the gateway's tool allow-listing and tool-poisoning detection enabled
  (SEC-014/SEC-015).

## Backlog

The open items from the latest audit run live under
[`../audits/`](../audits/) as per-finding documents with remediation steps and
effort estimates. They are tracked there rather than duplicated here.
