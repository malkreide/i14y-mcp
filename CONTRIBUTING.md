# Contributing

[🇩🇪 Deutsche Version](CONTRIBUTING.de.md)

Thanks for your interest in `i14y-mcp`. This is a read-only MCP server over the
public I14Y API; contributions should keep it that way.

## Ground rules

- **Read-only.** Every tool stays annotated `readOnlyHint: true`,
  `destructiveHint: false`. No write, send, or filesystem capability. Write
  endpoints exist in the upstream API but are deliberately not exposed.
- **One egress host.** Requests go only to the fixed base URL
  `https://api.i14y.admin.ch/api`, enforced by the `ALLOWED_HOSTS` allow-list in
  `src/i14y_mcp/client.py` (see [`docs/network-egress.md`](docs/network-egress.md));
  no user-supplied URLs, so there is no SSRF surface.
- **No secrets.** The read endpoints are unauthenticated; do not add credential
  handling.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

PYTHONPATH=src pytest tests/ -m "not live"   # offline, respx-mocked
PYTHONPATH=src pytest tests/ -m live         # hits the real API
ruff check src/ tests/ scripts/               # lint gate
ruff format --check src/ tests/ scripts/      # formatting gate
```

The offline suite replays real responses from `tests/fixtures/`, one per
external endpoint. Source, recording date, selection rule and SHA-256 are listed
per file in `tests/fixtures/PROVENANCE.md`. Re-record them against the live API
with:

```bash
python scripts/record_fixtures.py
```

Do not hand-write a success payload: a stub agrees with whatever you assumed,
which is how a renamed upstream field once stayed green through the whole
suite. Error paths (404, timeouts, masked 4xx) stay handwritten — they cannot
be recorded on demand.

These are the three gates CI runs, verbatim. Lint and formatting are separate
checks: `ruff check` says nothing about formatting, so a green linter next to a
red `ruff format --check` is an ordinary state, not a contradiction. Use the
ruff version pinned in `pyproject.toml` — `pip install -e ".[dev]"` installs it.
A different version reports differences nobody introduced.

## Pull requests

- Add tests for user-facing changes; keep both ruff gates and the offline suite
  green.
- Add a `CHANGELOG.md` entry under `[Unreleased]`.
- Update both `README.md` and `README.de.md` for any documentation change.
- For release/publishing, see [`PUBLISHING.md`](PUBLISHING.md).

## Reporting security issues

See [`SECURITY.md`](SECURITY.md) — please use private reporting, not public issues.

## The live suite: when it runs, and who sees a red result

**Cadence:** every Monday at 05:17 UTC, plus on demand via *Actions → Live API tests → Run
workflow*. See [`.github/workflows/live.yml`](.github/workflows/live.yml).

**Who sees it:** A red run opens an issue labelled `upstream` and the stable title “Live-Tests gegen i14y.admin.ch rot (<Datum>)”. A second red run recognises the open issue by its title prefix and appends to that same thread rather than opening a second one. Once the suite is green again, the issue closes itself.

**Three answers, not two.** `scripts/classify_live_run.py` reads the JUnit XML rather than
the exit code and separates `clear` (ran, green), `finding` (ran, something
fell) and `unknown` (did not run — install failed, nothing collected,
everything skipped). An `unknown` never closes an issue: closing would claim a
comparison that never happened.

**A red live run does not necessarily mean *our* bug.** It means the contract
with the source has changed, or the source is down. Both belong seen; only the
first belongs fixed. Please read the run before disabling the job — that is how
this check dies, and it is the only one in the repository that can contradict a
wrong assumption about i14y.admin.ch. Every other test asserts against a fixture, and
the fixture was written from the same assumption as the code.
