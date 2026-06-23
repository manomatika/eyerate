# Test Setup and Layout

> Back-reference: this file holds the full test-setup and test-layout detail
> that was previously inline in `CLAUDE.md` (`### Test Setup` and `## Test Layout`).

## Test Setup

Tests require `../matika` as a sibling directory. Conftest is split across two files to enforce tier isolation:

- `tests/conftest.py` — minimal shared setup. Adds `../matika/src` and `../matika/tests` to `sys.path`. Imports nothing from `eyerate.*` or `matika.*`. Loads cleanly in any Python environment.
- `tests/integration/conftest.py` — stack setup. Loads matika's `conftest.py` via `importlib`, re-exports its fixtures, and provides session-scoped autouse fixtures (`setup_plugins`, `setup_database`) that copy `src/` into a temporary `plugins/eyerate/` directory and create both Matika and EyeRate schemas.

The integration conftest is loaded only when pytest collects tests under `tests/integration/`. Scripts-tier tests under `tests/scripts/` never trigger the matika exec or any sqlalchemy import.

## Test Layout

Three buckets, separated by directory. Tier isolation is enforced by directory layout — the parent conftest cannot accidentally pull stack code into the scripts tier.

- `tests/conftest.py` — minimal shared setup only. Adds `../matika/src` and `../matika/tests` to `sys.path`. **Never load stack-coupled code here. Never `exec_module` matika's conftest here.** Doing so breaks the contract that `pytest tests/scripts/` runs in any Python environment without venv setup.
- `tests/integration/` — stack-coupled tests requiring the full matika+eyerate application stack. Owns the matika conftest re-export and any DB / plugin / FastAPI setup. Has its own `conftest.py`.
- `tests/scripts/` — stack-independent unit tests for the `scripts/` directory and other infrastructure (release tooling, drift detection, static-asset layout). Runs without venv, without sqlalchemy, without any `eyerate.*` or `matika.*` runtime imports. **Has no `conftest.py` of its own** — inherits only from the minimal parent. Tests that need optional deps (e.g. fastapi for the static-asset regression test) use `pytest.importorskip` to gracefully degrade in minimal environments.

The tier separation is enforced by directory structure. Do not collapse back to a single conftest. When adding a test, choose the bucket by what it actually imports: any `eyerate.*` / `matika.*` runtime import → `tests/integration/`. No such import → `tests/scripts/`.

## Running the Suite

**Environment matters.** The full suite is green on main, but the `tests/integration/` tier `exec_module`s matika's `conftest.py` resolved via a **sibling-clone relative path** (`../../../matika/tests/conftest.py` from `tests/integration/`). It only resolves when eyerate's checkout/worktree sits beside the matika clone (`~/dev/projects/eyerate` next to `~/dev/projects/matika`) **and** `PYTHONPATH` includes `../matika/src`. Run with:

```bash
export SECRET_KEY="test-only-secret-key-never-use-in-production"
export PYTHONPATH=src:../matika/src
python -m pytest tests/        # full suite green
```

Running the integration tier from a worktree that is NOT a matika sibling (e.g. under `/tmp`) makes that exec path 404 → **all integration tests ERROR at collection** (not a real failure — a setup artifact). If you see "N errors" in the integration tier, check your CWD/sibling layout before assuming a regression.

## CI Gate

eyerate has two PR-triggered workflows: `check-compiled-assets.yml` (TS staleness check) and `test.yml` (Python pytest gate). `test.yml` triggers on push and PR to `main`; it checks out eyerate and matika as siblings, installs via `pip install uv` → `uv venv` → `uv pip install`, sets `PYTHONPATH=src:../matika/src`, and runs `python -m pytest tests/ -v`. A Python regression is caught by CI before merge.
