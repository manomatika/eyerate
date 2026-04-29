**EyeRate** | Version: **0.0.3** | Copyright (c) 2026 Patrick James Tallman

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
python scripts/release.py --version v0.0.2  # PR, merge, tag, GitHub release, close milestone
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

### Locale

`src/eyerate/locales/en.json` — Contributes `menu_eyerate: "EyeRate"` and all field labels. Merged into Matika's global `t` dict at runtime.

## Standing Rules

- Never run `git merge` or `rm -rf`.
- Do not stage or commit files unless explicitly instructed. The developer handles all git staging and commits manually unless full git permissions have been explicitly granted.
- Never commit `MATIKA_ENV=development` or any `.env` file containing it.
- All tests must pass with 0 skipped and 0 failed — no exceptions.
