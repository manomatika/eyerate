# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

EyeRate is a **Matika AppLug** (plugin) — the reference implementation of the Matika plugin system. It adds financial security tracking (stocks, bonds, ETFs, mutual funds) to a Matika host application. It is not a standalone app; it runs inside Matika.

## AppLug Trust & Testing Posture

eyerate is the **reference applug** — trusted, org-authored. The model below is the ecosystem-wide posture applied from eyerate's perspective; the authority of record is `docs/ManoMatikaUseCases.md` in `manomatika/manomatika`.

### Trust model (install-trust)

- Installing an applug — via recipe at build time, or via future runtime applug loading — **is** the trust decision. matika treats every applug identically; there is no first-party/third-party distinction in mechanism.
- Safeguards hinder bad behavior to the extent practical, with no claim a determined bad actor is stopped: an applug is in-process Python and cannot be prevented from reaching host primitives directly.
- Dangerous host operations (network, filesystem, process, secrets) are expected to go **through matika APIs** — a reduced, documented, auditable safe-by-default surface. This is convention plus review, **not** a hard guarantee; never describe it as one.
- ManoMatika-org applugs are trusted by provenance and live in a non-public org applug repo. The SDK only ever bundles the reference applug — **eyerate**, which is trusted by provenance (org-authored), consistent with install-trust.

### Test execution is build automation, not a security boundary

- The framework discovers each applug's tests through a known interface and runs them all automatically at build time, identically for every applug. There is no trust dimension, no sandbox, and no isolation around test execution.
- WASM/Wasmtime/WASI isolation of applug code or tests is **out** — rejected on complexity, the security-critical runtime dependency it would introduce, and its inability to run the real product stack (compiled C/Rust extensions, sockets).

### Three-layer testing model

Keep these three layers distinct; never collapse them.

- **L1 — own suite.** eyerate unit/integration-tests its own functions in its own suite (file layout under *Testing* in Architecture).
- **L2 — generic structural harness.** Domain-blind "every declared screen routes, renders, and shows its markers." Applug-agnostic; matika owns the contract and ahimsa's gate runs it. eyerate declares its screens in `src/eyerate/eyerate_screens.json`.
- **L3 — applug-authored functional tests.** eyerate authors functional tests; the product gate (ahimsa) invokes them generically through a contract. Who authors (the applug) is separate from who invokes (the generic gate); there is no isolation requirement. eyerate is the canonical reference implementation of this contract. Adoption is in flight via `manomatika/eyerate#63` (open, not yet merged to `main`).

## Working Style & Discipline

This section captures the standing working rules across the manomatika ecosystem. **CLAUDE.md is authoritative for how a fresh Claude Code instance should operate in this repo; keep it current as practices evolve.** The terminal milestone of every release is `Documentation & Release Readiness`, which includes auditing and updating every CLAUDE.md against what actually shipped.

### Documentation integrity

CLAUDE.md must never knowingly contain stale information. Whenever CLAUDE.md is edited or regenerated, every factual claim about this repo (workflow/job status, ownership boundaries, file locations, build/release state) must be verified against the actual current repo state before being written. Stale claims are defects. When a claim cannot be verified, omit it rather than guess.

### Collaboration model

- **Human in the loop for every change.** The user holds architecture, code review, and merge decisions. Don't merge PRs; don't push without explicit instruction; don't open PRs without the user's go-ahead.
- **One question or command batch at a time.** When asking a question or proposing actions, stop and wait for the user's answer or for the user to read previous output before continuing. Don't paste a new prompt or run new commands on top of unreviewed output.
- **Investigate-and-report before editing when scope is unclear.** Read the relevant code/docs first, surface what you find, and let the user direct the fix. Never assume; never silently expand scope.
- **Push back on overthinking and scope creep.** Best-practice patterns, never papered-over hacks. Fix issues correctly now — except items the user has explicitly deferred (e.g. follow-on issues filed against a later milestone).
- **Flag best-practice violations before implementing.** If a request would land an anti-pattern (security bypass, hack-around, etc.), surface the concern and let the user decide before writing code.

### Git, branches, references, and worktrees

- **The user does all git review and merges in the browser.** Don't merge PRs, push to main, or tag releases unless explicitly instructed.
- **Don't stage or commit unless explicitly granted.** The user handles `git add` / `git commit` manually by default. When granted, follow the conventional-commit pattern (`docs:`, `fix:`, `feat:`, `refactor:`, etc.) and include `Closes manomatika/<repo>#N` (fully qualified) where applicable.
- **Cross-repo issue/PR references must always be fully qualified.** Write `manomatika/matika#N`, `manomatika/eyerate#N`, `manomatika/ahimsa#N` — never a bare `#N` for an issue that lives in a different repo. Bare refs are only safe when the PR and the issue are in the same repo. Cross-repo `Closes` references only cross-link — they do NOT auto-close; close manually after merge.
- **cc does not run `git merge` locally.** Integration of branches is done by the user via PR merge in the browser. For any local branch updates cc performs, use `git rebase` or `git cherry-pick`. cc may run `rm -rf` ONLY within a repo working directory under `~/dev/projects/` (a clone `~/dev/projects/<repo>/` or a worktree `~/dev/projects/<repo>-<branch>/`) or under `~/dev/projects/cc_output/` — never anywhere else on the filesystem, and never with an unanchored or variable-expanded path that could resolve outside them. Targeted `git rm` for tracked files remains the norm; `rm -rf` is the constrained exception (rule 23).
- **`VERSION` is the single source of truth** for version metadata in this repo. Never hand-edit version literals in other files; release tooling propagates from `VERSION`.
- **The user uses git worktrees** for parallel work (e.g. `~/dev/projects/matika-45/` alongside `~/dev/projects/matika/` on a separate branch). At any moment, the user may be operating in any of several working directories for the same repo. Always check the current branch (`git branch --show-current`) and confirm it matches what you expect before assuming.
- **Multi-instance/parallel discipline.** When operating as one of multiple parallel cc instances, stay strictly within the assigned worktree, branch, and scope of files described in the task. Do not modify files outside the assigned scope, even if issues are noticed elsewhere — surface those issues to the user as separate items to triage rather than fixing in-flight. Cross-cutting changes that touch another agent's work area must be coordinated by the user, not initiated unilaterally.

### Code and test discipline

- **Regression tests are required for every fix.** A bug fix that doesn't include a test that would have caught the bug isn't done.
- **All tests must RUN IN FULL and pass — 100% clean.** Every affected repo's COMPLETE suite must RUN with nothing excluded, deselected, skipped, or marked integration-only, and pass: 0 failed / 0 skipped / 0 xfail / 0 deselected / 0 warnings. No test may be excluded or filtered and no warning suppressed without the product owner's explicit, per-case approval recorded as a documented rule variation.
- **Full-suite, every change, everywhere — 100% clean (standing rule 21).** ANY code change, in ANY repo, requires the COMPLETE unit-test suite of every affected repo (and any repo whose behavior could be impacted) to RUN IN FULL — nothing excluded, deselected, skipped, or marked integration-only — and pass 100%: 0 failed / 0 skipped / 0 xfail / 0 deselected / 0 warnings. Eliminate every warning at its ROOT (fix the code or bump the dependency); never blanket-suppress with a `filterwarnings` / `-W ignore` / `-m 'not …'` filter. Use each repo's correct test environment (the uv-managed `.venv`) so a green run is never an env artifact. A change is not done until every suite is 100% clean.
- **Escaped-bug regression mandate (standing rule 22).** Any bug that reaches CI, an rc, or install/runtime testing without being caught by the suite MUST, as part of its fix, gain a regression test that would have caught it — added at the layer where it escaped (unit/integration for logic gaps; a feature/E2E check against the FROZEN, pinned artifact for product-behavior gaps). The fix is not done until that test exists, fails without the fix, and passes with it.
- **Never weaken or disable security / correctness checks** (CSRF, permission, auth, validation) as a workaround. If a check is producing a wrong answer, fix the call site to satisfy it correctly — never bypass.

### Repository ecosystem

- **manomatika** is the GitHub org. The shipped PRODUCT is **ManoMatika** — a pinned *triple* of component versions (matika + eyerate + ahimsa), blessed by a single product release. The repos:
  - **manomatika/manomatika** — PRODUCT AUTHORITY. Owns the recipes, the audit log (`release-log.yaml` + `RELEASES.md`), the product release + single hosted installer binary, cross-component umbrella docs, the per-version manifest/BOM (pins each component by tag AND resolved SHA), and the QA gate.
  - **manomatika/matika** — the framework (plugin-agnostic FastAPI host). Component; notes-only releases.
  - **manomatika/eyerate** — the reference AppLug (financial security tracking). Component; notes-only releases. **This repo.**
  - **manomatika/ahimsa** — the recipe ENGINE: build / validation / release *mechanism* + recipe *schema*. Owns no recipes, no audit-log content, and hosts no product releases of its own.
- Local clones live at `~/dev/projects/<repo>/` (sibling directories). Additional worktrees for the same repo live at `~/dev/projects/<repo>-<branch>/`.

### Milestones, Project, and dates

- **Milestone naming is shared and match-when-present** across repos. When a milestone exists in more than one repo, its title is byte-for-byte identical so the org Project rolls it up into a single cross-repo group. Milestone names never contain version numbers or dates.
- **Canonical milestone titles in the current release cycle:**
  - `Deployment & Install`
  - `Cleanup & Tooling` (matika + eyerate + ahimsa)
  - `Registry` (ahimsa only)
  - `Signing & Distribution` (ahimsa only)
  - `QA & System Test` (ahimsa only)
  - `Planning` (matika + eyerate + ahimsa)
  - `Playwright` (matika only)
  - `Documentation & Release Readiness` — the terminal release gate (all four)
- **Org-level Project: [ManoMatika Roadmap](https://github.com/orgs/manomatika/projects/1)** is the cross-repo backlog view. Its description records which component versions compose each manomatika release (e.g. ManoMatika v0.0.1 = matika v0.0.4 + eyerate v0.0.4 + ahimsa v0.0.1).
- **Milestone due dates are the single source of truth for dates.** The roadmap renders timelines from milestone Markers; do NOT create per-item date fields on the Project for scheduling (Pattern A — milestone-driven).

### Communication and output

- **Put prompts and commands in code blocks** so the user can one-tap copy them.
- The user is on **macOS** and uses **Ghostty** and **tmux** for terminal work (shell defaults to zsh). The user also runs a **Dell Latitude** (64 GB RAM, no high-performance GPU) for local models via **Ollama**, currently favoring **qwen**. All configs are managed with **chezmoi**; any change to any config must follow chezmoi best practice and standards. chezmoi usage is captured in a separate handoff file, `chezmoi-dotfiles-handoff.md`. The user edits in **neovim**, and may also use **VSC**.
- The user is **expert in software architecture and engineering, novice in git/GitHub specifics.** When git or `gh` commands appear in plans or output, explain plainly what they do, what they touch, and what the user will see.

## Commands

**Run all tests** (requires `../matika` sibling directory):
```bash
export SECRET_KEY="test-only-secret-key-never-use-in-production"
export PYTHONPATH=src:../matika/src
python -m pytest tests/
```

Note: `uv run pytest` is not the canonical invocation here — eyerate requires `../matika/src` on `PYTHONPATH` because matika is a sibling directory, not an installed package. Set `PYTHONPATH` explicitly as shown above.

**Run a single test:**
```bash
export SECRET_KEY="test-only-secret-key-never-use-in-production"
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

- `applug.json` — Plugin `id` (`eyerate`), `name` (`"EyeRate"`), `description`, `version`, `matika_version`, entry point, permissions, and the `settings_ui` schema. There is **no** `display_name` key (the UI label falls back to `name`). The `settings_ui` schema drives the data-provider selector on Matika's settings page (section `data_providers`): a `financial_security_data_endpoint` select (`yahoo`/`finnhub`/`alphavantage`, default `yahoo`) and a `financial_security_data_api_key` textbox shown only when the endpoint is `finnhub` or `alphavantage`. Permissions: Admin=FULL, User=FULL for `/eyerate/securities`.
- `eyerate_menus.json` — Consolidated menu manifest. Contains two optional top-level sections: `application` (application-type menu) and `roles` (array of role menus, each with `role`, `id`, `label_key`, and `items`). Admin role items are flat `Link` objects; User role items are wrapped in a `Menu` object. Full detail: see `docs/menu-loading.md`.
- `eyerate_screens.json` — Screen inventory for Playwright-based testing. Uses the matika screen schema v1.0 (`schema_version: "1.0"`, `screens` array). Covers `eyerate:securities_list` (`/eyerate/securities`), `eyerate:admin` (`/eyerate/admin`), and `not_a_screen` entries for POST-only handlers. Consumed by `ScreenLoaderService` in matika.

### Plugin Wiring (`plugin.py`)

`EyeRatePlugin` extends `BaseAppLug`. The `on_load()` method runs at Matika startup: runs SQLAlchemy `create_all` to migrate the `securities` table (plugin-managed; not in Matika's Alembic migrations); registers the FastAPI router at the `/admin` prefix; mounts `/eyerate/static` pointing at `src/eyerate/static/` (note: `/eyerate/static` not `/static/eyerate` to avoid a Starlette route-ordering conflict); and appends the plugin's `templates/` directory to Jinja2's search path.

### Security Requirements

All EyeRate POST routes must include:
```python
_auth: User = Depends(check_page_permission)
_csrf = Depends(validate_csrf)
```
GET routes that call external APIs (search, lookup) must include `Depends(login_required)`. Bulk JSON-body routes (bulk_create, bulk_delete) use `check_page_permission` only (JSON requests are not CSRF-vulnerable).

### Data Providers

The active provider is resolved per-request from two Matika system settings: `financial_security_data_endpoint` (`yahoo` default / `finnhub` / `alphavantage`) and `financial_security_data_api_key`. **Provider error contract (load-bearing):** a `ProviderError` exception distinguishes a genuine zero-result from a failed call; `routes.py` translates `ProviderError` into **HTTP 502** with a `detail` body — never a silent empty result. Full detail: see `docs/data-providers.md`.

### Routes (`routes.py`)

FastAPI router registered at `/eyerate/securities`. All routes use `get_db`, `check_page_permission`, and `validate_csrf` (form routes) from Matika's security layer.

### TypeScript

Source lives under `src/eyerate/ts/` (subdirs: `admin/`, `dialogs/`, `shared/`). Compiled JS is committed to git. Run `npm run build` after editing any `.ts` file and commit both source and compiled output together. Full detail: see `docs/typescript.md`.

### Testing

Tests require `../matika` as a sibling directory. This is eyerate's **L1** suite (see *AppLug Trust & Testing Posture*); its file layout has three tiers — `tests/conftest.py` (minimal shared), `tests/integration/` (stack-coupled), `tests/scripts/` (stack-independent) — which are distinct from the L1/L2/L3 testing-model layers. Full setup, layout, and CI gate detail: see `docs/testing.md`.

### Locale

Locale i18n detail: see `docs/locale.md`.

### Release Pipeline

`VERSION` is the single source of truth. `scripts/release.py` and `scripts/sync_version.py` propagate it into `applug.json`. Full pipeline, versioning contract, drift detection, and GitHub Release notes detail: see `docs/release-pipeline.md`.

## Standing Rules

General working discipline (tests, git, security checks, cross-repo refs, etc.) lives in the *Working Style & Discipline* section at the top of this file. The bullets below are eyerate-specific.

- Never commit any `.env` file.
- Standard Python `.gitignore` (GitHub's official Python template) is in place: covers `__pycache__/`, build/dist, `*.egg-info/`, `.pytest_cache/`, `.coverage`, `htmlcov/`, venv variants, `.tox/`, and OS/IDE noise. Never commit compiled artifacts.
