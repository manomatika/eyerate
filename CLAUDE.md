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
python -m pytest tests/integration/test_securities.py::test_securities_crud
```

**Development workflow scripts:**
```bash
python scripts/start_milestone.py   # Create GitHub milestone + branch + issues from milestone_tasks.yaml
python scripts/release.py vX.Y.Z             # commit VERSION + applug.json; push/tag/PR manually after review
python scripts/sync_version.py      # Sync VERSION file → applug.json
```

**TypeScript compilation:**
```bash
npm install     # one-time: installs typescript devDependency
npm run build   # compile src/eyerate/ts/**/*.ts → src/eyerate/static/js/
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

### TypeScript Layout Convention

TypeScript source lives under `src/eyerate/ts/` with mandatory subdirectories:

| Directory | Purpose |
|---|---|
| `ts/admin/` | Admin-page-specific scripts (e.g. `admin-securities.ts`) |
| `ts/dialogs/` | Reusable dialog/modal components (e.g. `lookup-dialog.ts`) |
| `ts/shared/` | Types, utilities, and ambient declarations shared across features |

**Naming rules:**
- TypeScript source filenames: `kebab-case.ts`
- Python files: `snake_case.py` (unchanged)
- HTML templates: `snake_case.html` (unchanged — Jinja2 template names are Python-realm)

**Compilation:** `tsconfig.json` mirrors the `ts/` subdirectory structure into `src/eyerate/static/js/`:
- `ts/admin/admin-securities.ts` → `static/js/admin/admin-securities.js`
- `ts/dialogs/lookup-dialog.ts` → `static/js/dialogs/lookup-dialog.js`

**Committed output:** Compiled JS is committed to git. The repo is self-contained; no build step is required to run in dev or CI. Run `npm run build` after editing any `.ts` file and commit both the source and the compiled output together.

**Matika-side imports:** Cross-framework imports use the npm bare specifier `@manomatika/matika-frontend`, e.g.:

```typescript
import { MaintenanceActivityManager, ActivityMetadata } from '@manomatika/matika-frontend';
```

At runtime, matika's `base.html` ships an `<script type="importmap">` that resolves this specifier to `/static/js/index.js` (served from matika's static directory). The npm package on GitHub Packages is consumed at build time for TypeScript type checking; the runtime resolution happens entirely through the import map. The earlier `ts/shared/matika-externals.d.ts` shim and the `paths` entry in `tsconfig.json` (TODO(A.3) markers) were removed when A.3 landed — that directory and entry no longer exist. `npm run build` is still required after editing any `.ts` file; compiled JS is committed alongside source per repo convention.

### Plugin Wiring (`plugin.py`)

`EyeRatePlugin` extends `BaseAppLug`. The `on_load()` method runs at Matika startup and:
1. Runs SQLAlchemy `create_all` to migrate the `securities` table (plugin-managed; not in Matika's Alembic migrations).
2. Registers the FastAPI router at the `/admin` prefix.
3. Mounts `/eyerate/static` pointing at `src/eyerate/static/` — serves compiled JS under `/eyerate/static/js/admin/` and `/eyerate/static/js/dialogs/`. Note: the path is `/eyerate/static` (not `/static/eyerate`) to avoid a Starlette route-ordering conflict with matika's broad `/static` catch-all mount.
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

### Test Setup

Tests require `../matika` as a sibling directory. Conftest is split across two files to enforce tier isolation:

- `tests/conftest.py` — minimal shared setup. Adds `../matika/src` and `../matika/tests` to `sys.path`. Imports nothing from `eyerate.*` or `matika.*`. Loads cleanly in any Python environment.
- `tests/integration/conftest.py` — stack setup. Loads matika's `conftest.py` via `importlib`, re-exports its fixtures, and provides session-scoped autouse fixtures (`setup_plugins`, `setup_database`) that copy `src/` into a temporary `plugins/eyerate/` directory and create both Matika and EyeRate schemas.

The integration conftest is loaded only when pytest collects tests under `tests/integration/`. Scripts-tier tests under `tests/scripts/` never trigger the matika exec or any sqlalchemy import.

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

Three buckets, separated by directory. Tier isolation is enforced by directory layout — the parent conftest cannot accidentally pull stack code into the scripts tier.

- `tests/conftest.py` — minimal shared setup only. Adds `../matika/src` and `../matika/tests` to `sys.path`. **Never load stack-coupled code here. Never `exec_module` matika's conftest here.** Doing so breaks the contract that `pytest tests/scripts/` runs in any Python environment without venv setup.
- `tests/integration/` — stack-coupled tests requiring the full matika+eyerate application stack. Owns the matika conftest re-export and any DB / plugin / FastAPI setup. Has its own `conftest.py`.
- `tests/scripts/` — stack-independent unit tests for the `scripts/` directory and other infrastructure (release tooling, drift detection, static-asset layout). Runs without venv, without sqlalchemy, without any `eyerate.*` or `matika.*` runtime imports. **Has no `conftest.py` of its own** — inherits only from the minimal parent. Tests that need optional deps (e.g. fastapi for the static-asset regression test) use `pytest.importorskip` to gracefully degrade in minimal environments.

The tier separation is enforced by directory structure. Do not collapse back to a single conftest. When adding a test, choose the bucket by what it actually imports: any `eyerate.*` / `matika.*` runtime import → `tests/integration/`. No such import → `tests/scripts/`.

## Standing Rules

- Never run `git merge` or `rm -rf`.
- Do not stage or commit files unless explicitly instructed. The developer handles all git staging and commits manually unless full git permissions have been explicitly granted.
- Never commit `MATIKA_ENV=development` or any `.env` file containing it.
- All tests must pass with 0 skipped and 0 failed — no exceptions.
- Standard Python `.gitignore` (GitHub's official Python template) is in place: covers `__pycache__/`, build/dist, `*.egg-info/`, `.pytest_cache/`, `.coverage`, `htmlcov/`, venv variants, `.tox/`, and OS/IDE noise. Never commit compiled artifacts.
