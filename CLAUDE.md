**EyeRate** | Version: **v0.0.4** | Copyright (c) 2026 Patrick James Tallman

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working Style & Discipline

This section captures the standing working rules across the manomatika ecosystem. **CLAUDE.md is authoritative for how a fresh Claude Code instance should operate in this repo; keep it current as practices evolve.** The terminal milestone of every release is `Documentation & Release Readiness`, which includes auditing and updating every CLAUDE.md against what actually shipped.

### Collaboration model

- **Human in the loop for every change.** The user holds architecture, code review, and merge decisions. Don't merge PRs; don't push without explicit instruction; don't open PRs without the user's go-ahead.
- **One question or command batch at a time.** When asking a question or proposing actions, stop and wait for the user's answer or for the user to read previous output before continuing. Don't paste a new prompt or run new commands on top of unreviewed output.
- **Investigate-and-report before editing when scope is unclear.** Read the relevant code/docs first, surface what you find, and let the user direct the fix. Never assume; never silently expand scope.
- **Push back on overthinking and scope creep.** Best-practice patterns, never papered-over hacks. Fix issues correctly now — except items the user has explicitly deferred (e.g. follow-on issues filed against a later milestone).
- **Flag best-practice violations before implementing.** If a request would land an anti-pattern (security bypass, hack-around, etc.), surface the concern and let the user decide before writing code.

### Git, branches, references, and worktrees

- **The user does all git review and merges in the browser.** Don't merge PRs, push to main, or tag releases unless explicitly instructed.
- **Don't stage or commit unless explicitly granted.** The user handles `git add` / `git commit` manually by default. When granted, follow the conventional-commit pattern (`docs:`, `fix:`, `feat:`, `refactor:`, etc.) and include `Closes manomatika/<repo>#N` (fully qualified) where applicable.
- **Cross-repo issue/PR references must always be fully qualified.** Write `manomatika/matika#N`, `manomatika/eyerate#N`, `manomatika/ahimsa#N` — never a bare `#N` for an issue that lives in a different repo. Bare refs have caused real damage: a misqualified `Closes #11` / `Closes #12` in matika PR #35 closed unrelated issues in another repo's tracker. Bare refs are only safe when the PR and the issue are in the same repo.
- **cc does not run `git merge` locally; never run `rm -rf`.** Integration of branches is done by the user via PR merge in the browser. For any local branch updates cc performs, use `git rebase` or `git cherry-pick`. Use targeted `git rm` if files must be removed.
- **`VERSION` is the single source of truth** for version metadata in this repo. Never hand-edit version literals in other files; release tooling propagates from `VERSION`.
- **The user uses git worktrees** for parallel work (e.g. `~/dev/projects/matika-45/` alongside `~/dev/projects/matika/` on a separate branch). At any moment, the user may be operating in any of several working directories for the same repo. Always check the current branch (`git branch --show-current`) and confirm it matches what you expect before assuming.
- **Multi-instance/parallel discipline.** When operating as one of multiple parallel cc instances, stay strictly within the assigned worktree, branch, and scope of files described in the task. Do not modify files outside the assigned scope, even if issues are noticed elsewhere — surface those issues to the user as separate items to triage rather than fixing in-flight. Cross-cutting changes that touch another agent's work area must be coordinated by the user, not initiated unilaterally.

### Code and test discipline

- **Regression tests are required for every fix.** A bug fix that doesn't include a test that would have caught the bug isn't done.
- **All tests must pass — 0 failed, 0 skipped, 0 xfail.** No exceptions without explicit user approval. In multi-repo changes, every affected repo's full suite must pass before any PR is opened.
- **Never weaken or disable security / correctness checks** (CSRF, permission, auth, validation) as a workaround. If a check is producing a wrong answer, fix the call site to satisfy it correctly — never bypass.

### Repository ecosystem

- **manomatika** is the GitHub org. Three repos compose the ecosystem:
  - **manomatika/matika** — the framework (plugin-agnostic FastAPI host)
  - **manomatika/eyerate** — the reference AppLug (financial security tracking)
  - **manomatika/ahimsa** — release / build / recipe-validation tooling
- Local clones live at `~/dev/projects/<repo>/` (sibling directories). Additional worktrees for the same repo live at `~/dev/projects/<repo>-<branch>/`.

### Milestones, Project, and dates

- **Milestone naming is shared and match-when-present** across repos. When a milestone exists in more than one repo, its title is byte-for-byte identical so the org Project rolls it up into a single cross-repo group. Milestone names never contain version numbers or dates.
- **Canonical milestone titles in the current release cycle:**
  - `Deployment & Install`
  - `Cleanup & Tooling`
  - `Registry` (ahimsa only)
  - `Signing & Distribution` (ahimsa only)
  - `QA & System Test` (ahimsa only)
  - `v0.0.5 Planning` (eyerate + ahimsa)
  - `Documentation & Release Readiness` — the terminal release gate (all three)
- **Org-level Project: [ManoMatika Roadmap](https://github.com/orgs/manomatika/projects/1)** is the cross-repo backlog view. Its description records which component versions compose each manomatika release (e.g. ManoMatika v0.0.1 = matika v0.0.4 + eyerate v0.0.4 + ahimsa v0.0.1).
- **Milestone due dates are the single source of truth for dates.** The roadmap renders timelines from milestone Markers; do NOT create per-item date fields on the Project for scheduling (Pattern A — milestone-driven).

### Communication and output

- **Put prompts and commands in code blocks** so the user can one-tap copy them.
- The user is on **macOS / iTerm2** (tmux planned). Shell defaults to zsh.
- The user is **expert in software architecture and engineering, novice in git/GitHub specifics.** When git or `gh` commands appear in plans or output, explain plainly what they do, what they touch, and what the user will see.

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

General working discipline (tests, git, security checks, cross-repo refs, etc.) lives in the *Working Style & Discipline* section at the top of this file. The bullets below are eyerate-specific.

- Never commit `MATIKA_ENV=development` or any `.env` file containing it.
- Standard Python `.gitignore` (GitHub's official Python template) is in place: covers `__pycache__/`, build/dist, `*.egg-info/`, `.pytest_cache/`, `.coverage`, `htmlcov/`, venv variants, `.tox/`, and OS/IDE noise. Never commit compiled artifacts.
