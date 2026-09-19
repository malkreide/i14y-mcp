# Publishing to PyPI

`i14y-mcp` is published to [PyPI](https://pypi.org/project/i14y-mcp/) so it
can be installed with `uvx i14y-mcp` / `pip install i14y-mcp`.

Publishing uses **PyPI Trusted Publishing (OIDC)** — no long-lived API token is
stored anywhere. A published GitHub Release triggers
[`.github/workflows/publish.yml`](.github/workflows/publish.yml), which builds
the distribution, uploads it to PyPI, and publishes the server to the MCP
Registry on the repo's behalf.

---

## One-time setup

Do these steps once, before the first release.

### 1. Create a PyPI account

- Register at <https://pypi.org/account/register/> and enable 2FA.
- (Optional but recommended) also register at <https://test.pypi.org/> for a dry run.

### 2. Register the Trusted Publisher on PyPI

Because the project does not exist on PyPI yet, add it as a **pending publisher**:

1. Go to <https://pypi.org/manage/account/publishing/>.
2. Under **Add a new pending publisher**, fill in:
   - **PyPI Project Name:** `i14y-mcp`
   - **Owner:** `malkreide`
   - **Repository name:** `i14y-mcp`
   - **Workflow name:** `publish.yml`
   - **Environment name:** `pypi`
3. Save. On the first successful publish, PyPI converts this into the real project
   and a normal trusted publisher.

### 3. Create the `pypi` GitHub environment

The workflow runs in an environment named `pypi` (matching the trusted-publisher
config above):

1. GitHub → repo **Settings** → **Environments** → **New environment** → name it `pypi`.
2. (Optional) add a required reviewer or a tag protection rule so a human approves
   each publish.

No secrets are needed — OIDC handles authentication.

---

## Releasing a new version

Repeat these steps for every release.

### 1. Bump the version

Edit `pyproject.toml` and bump `version` following [SemVer](https://semver.org/):

```toml
version = "0.1.0"   # -> 0.1.1 (patch) / 0.2.0 (minor) / 1.0.0 (major)
```

Bump `server.json` in the **same commit** — both `version` and
`packages[0].version`. `scripts/check_version_sync.py` is a CI gate and fails
the build otherwise; measured on the 0.4.0 bump, pyproject alone reports:

```
DRIFT: pyproject.toml steht auf '0.4.0', diese Stellen weichen ab:
  server.json → version = '0.3.2'
  server.json → packages[0].version = '0.3.2'
```

`publish.yml` *does* overwrite `server.json` from the tag at release time — and
that is precisely why the committed value rots unnoticed and why the gate
exists. The published artefact never contradicts a stale number; a human
reading the repo does.

The READMEs carry no pinned version badge today. If you add one, the same gate
starts checking it, with nothing to configure.

### 2. Update the changelog

In `CHANGELOG.md`, move the `[Unreleased]` notes into a new dated version section:

```markdown
## [0.1.1] — 2026-07-23
```

### 3. Verify locally before tagging

Run the five CI gates, not a subset — a green linter next to a red format
gate is not a contradiction, it is two gates:

```bash
PYTHONPATH=src pytest tests/ -m "not live"
python scripts/check_ruff_pin.py
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python scripts/check_version_sync.py

# build and validate the artifacts
python -m build
twine check dist/*
```

Check `ruff --version` first: the pin is `ruff==0.16.3` in
`[project.optional-dependencies].dev`, and an older `ruff` earlier in `PATH`
beats it without the install saying anything.

`twine check` must report `PASSED` for both the `.whl` and the `.tar.gz`.

### 4. Commit, tag, and push

```bash
git add pyproject.toml CHANGELOG.md README.md README.de.md
git commit -m "chore: release v0.1.1"
git tag -a v0.1.1 -m "Release v0.1.1"
git push origin main --follow-tags
```

### 5. Create the GitHub Release

Creating a **published** GitHub Release for the tag is what triggers publishing:

- GitHub → **Releases** → **Draft a new release** → choose tag `v0.1.1` →
  **Publish release**, or with the CLI:

```bash
gh release create v0.1.1 --title "v0.1.1" --notes-file CHANGELOG.md --latest
```

### 6. Watch the workflow

- The **Publish to PyPI** workflow runs automatically: it builds, runs
  `twine check`, uploads via OIDC, then publishes to the MCP Registry.
- If you added a required reviewer to the `pypi` environment, approve the run.
- Confirm the new version at <https://pypi.org/project/i14y-mcp/>.

### 7. Smoke-test the published package

```bash
uvx i14y-mcp@latest    # confirm it starts
```

---

## Manual publish (fallback)

Only needed if the workflow is unavailable. Requires a PyPI API token
(<https://pypi.org/manage/account/token/>).

```bash
python -m build
twine check dist/*

# optional: dry run against TestPyPI first
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ --no-deps i14y-mcp

# real upload
twine upload dist/*
```

With `uv` this is simply:

```bash
uv build
uv publish            # uses UV_PUBLISH_TOKEN or prompts
```

---

## Checklist

- [ ] `version` bumped in `pyproject.toml` (SemVer)
- [ ] `server.json` bumped in the same commit (`version` + `packages[0].version`)
- [ ] `CHANGELOG.md` has a dated section for the release, and the link
      references at the bottom of the file name the new tag
- [ ] Version badge updated in both READMEs (if pinned — none today)
- [ ] All five CI gates pass locally, with the pinned `ruff 0.16.3`
- [ ] `python -m build` + `twine check dist/*` pass
- [ ] Tag `vX.Y.Z` pushed and GitHub Release published
- [ ] New version visible on PyPI and `uvx i14y-mcp` works
