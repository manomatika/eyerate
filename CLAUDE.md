**EyeRate** | Version: **v0.0.4** | Copyright (c) 2026 Patrick James Tallman

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

EyeRate is a **Matika AppLug** (plugin) — the reference implementation of the Matika plugin system. It adds financial security tracking (stocks, bonds, ETFs, mutual funds) to a Matika host application. It is not a standalone app; it runs inside Matika.

## Commands

**Run all tests** (requires `../matika` sibling directory):
```bash
export PYTHONPATH=src:../matika/src
python -m pytest tests/
```

**Run a single test:**
```bash
export PYTHONPATH=src:../matika/src
python -m pytest tests/test_securities.py::test_securities_crud
```

**Development workflow scripts:**
```bash
python scripts/start_milestone.py   # Create GitHub milestone + branch + issues from milestone_tasks.yaml
python scripts/release.py vX.Y.Z             # commit VERSION + applug.json; push/tag/PR manually after review
python scripts/sync_version.py      # Sync VERSION file → applug.json
```

## Architecture

### Manifest Files

- `applug.json` — Plugin ID (`eyerate`), `name` (`"EyeRate"`), `display_name` (`"EyeRate"`), `version`, entry point, permissions, and the settings UI schema (drives the data provider selector in Matika's settings page). Permissions: Admin=FULL, User=FULL for `/eyerate/securities`.
- `eyerate_menus.json` — Consolidated menu manifest. Contains two optional top-level sections:
  - `application` — Application-type menu (e.g. EyeRate top-level nav entry).
  - `roles` — Array of role menus. Each entry has `role`, `id`, `label_key`, and `items`.
    - **Admin role items**: flat `Link` objects (no `Menu` wrapper); appear aggregated in the Admin dropdown.
    - **User role items**: wrapped in a `Menu` object to produce a named dropdown.

### Menu Loading Pipeline

`MenuLoaderService.load_applug_menus()` reads all `*_menus.json` files from loaded plugins. Role hubs are built by merging the `roles` sections from these files with Matika's core `Role`-type menus.

- **Admin dropdown**: aggregates System items and all applug Admin-role items. When two or more sources contribute items, a `SectionHeader` separates each source. A single-source dropdown never shows a section header.
- **Other role hubs**: built from `Menu`-wrapped items in the matching role's `roles` entry.
- `_build_role_menus` has been removed; role hub construction now derives entirely from `*_menus.json` roles sections plus core menus.
- The `fresh_login` session flag ensures users land on the Default hub immediately after login.

### Plugin Wiring (`plugin.py`)

`EyeRatePlugin` extends `BaseAppLug`. The `on_load()` method runs at Matika startup and:
1. Runs SQLAlchemy `create_all` to migrate the `securities` table (plugin-managed; not in Matika's Alembic migrations).
2. Registers the FastAPI router at the `/admin` prefix.
3. Mounts `/static/eyerate` if a `static/` directory exists.
4. Appends the plugin's `templates/` directory to Jinja2's search path.

### Security Requirements

All EyeRate POST routes must include:
```python
_auth: User = Depends(check_page_permission)
_csrf = Depends(validate_csrf)
```
GET routes that call external APIs (search, lookup) must include `Depends(login_required)`. Bulk JSON-body routes (bulk_create, bulk_delete) use `check_page_permission` only (JSON requests are not CSRF-vulnerable).

### Data Providers (`endpoints.py`)

The active endpoint is resolved at runtime from the Matika system setting `financial_security_data_endpoint`. All providers implement `BaseFinancialSecurityEndpoint` with `search()` and `lookup()` methods:

- **YahooScraperEndpoint** (default) — uses `curl_cffi` for search, `yfinance` for lookup
- **FinnhubEndpoint** — requires `financial_security_data_api_key` system setting
- **AlphaVantageEndpoint** — requires `financial_security_data_api_key` system setting

### Routes (`routes.py`)

FastAPI router registered at `/eyerate/securities`. All routes use `get_db`, `check_page_permission`, and `validate_csrf` (form routes) from Matika's security layer.

### Test Setup (`tests/conftest.py`)

Tests require `../matika` as a sibling directory. The conftest:
1. Adds `../matika/src` and `../matika/tests` to `sys.path`.
2. Dynamically loads and re-exports all fixtures from Matika's own `conftest.py`.
3. Creates a temporary `plugins/eyerate/` directory by copying `src/` and the manifest files, simulating how Matika discovers and loads the plugin.
4. Overrides `setup_database` to create both Matika and EyeRate schemas together.

Tests are organized by what they exercise: `tests/` holds integration tests that require the full stack; subdirectories (`tests/scripts/`, etc.) hold pure unit tests that no-op the parent autouse fixtures. See `tests/README.md` for the full convention.

### Locale

`src/eyerate/locales/en.json` — Contributes `menu_eyerate: "EyeRate"` and all field labels. Merged into Matika's global `t` dict at runtime.

## Release Pipeline

- `VERSION` is the single source of truth for version metadata. Never hand-edit version literals in any other file (`applug.json`, etc.) — the release tooling propagates from `VERSION`.
- During development, `VERSION` carries a `_dev` suffix (e.g. `0.0.4_dev`). Propagated files always carry the stripped version (e.g. `0.0.4`) — `_dev` is a marker on `VERSION` only.
- `scripts/release.py <version>` is the release entry point: verifies `VERSION` currently reads `<target>_dev`, strips `_dev`, runs `sync_version.py`, runs the drift pre-flight check, commits. Does **not** push, tag, or create a GitHub release — those steps are manual, after human review.
- `scripts/sync_version.py` propagates `VERSION` into `applug.json`: `"version"` from this repo's `VERSION`; `"matika_version"` from matika's `VERSION` (resolved via sibling clone at `../matika` or `MATIKA_VERSION` env var). When adding a new file with a version literal, add it to the script's allowlist.
- If matika's `VERSION` is unavailable (sibling clone absent and env var unset), `sync_version.py` exits 2 with a clear error. This is a hard error, not a warning — eyerate cannot be drift-checked or released without matika's version.
- `scripts/sync_version.py --check` runs in read-only drift detection mode. Exits 0 (clean), 1 (drift), 2 (configuration error). Human drift output uses double quotes around values (e.g. `DRIFT  applug.json: expected version "0.0.4", found "0.0.3"`). `--check --json` produces structured output: `{"version": "...", "drift": [{"path": "...", "field": "version"|"matika_version", "expected": "...", "found": "..."}]}`. Each drifted field in `applug.json` appears as a separate drift entry. An empty `drift` array (`[]`) means clean.

## Test Layout

- `tests/` — integration tests requiring the full matika+eyerate application stack. The `conftest.py` here uses autouse session fixtures.
- `tests/scripts/` — tests for the `scripts/` directory (release tooling, drift detection). Pure unit tests with no application-stack dependencies; local `conftest.py` no-ops the parent autouse fixtures.
- New tests go in the directory that matches what they exercise. Tests that don't need the application stack do not belong in `tests/`.

## Standing Rules

- Never run `git merge` or `rm -rf`.
- Do not stage or commit files unless explicitly instructed. The developer handles all git staging and commits manually unless full git permissions have been explicitly granted.
- Never commit `MATIKA_ENV=development` or any `.env` file containing it.
- All tests must pass with 0 skipped and 0 failed — no exceptions.
- Standard Python `.gitignore` (GitHub's official Python template) is in place: covers `__pycache__/`, build/dist, `*.egg-info/`, `.pytest_cache/`, `.coverage`, `htmlcov/`, venv variants, `.tox/`, and OS/IDE noise. Never commit compiled artifacts.
