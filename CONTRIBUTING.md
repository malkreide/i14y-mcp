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
ruff check src/ tests/                       # lint gate
ruff format --check src/ tests/              # formatting gate
```

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
