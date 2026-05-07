# eyerate tests

Three buckets, separated by directory. The tier each test belongs to is
determined by what it actually exercises, NOT by convention alone — the
tier separation is enforced by directory layout so that the parent
conftest cannot accidentally pull stack code into the scripts tier.

## Layout

- `tests/conftest.py` — minimal shared setup. Adds matika's `src/` and
  `tests/` to `sys.path`. **Must not** import or load anything that
  pulls in matika's runtime stack (sqlalchemy, FastAPI app, etc.).

- `tests/integration/` — stack-coupled tests. Owns the matika-conftest
  exec, fixture re-export, and session-scoped autouse fixtures
  (`setup_plugins`, `setup_database`). Runs only with a venv that has
  matika's full dependency tree.

- `tests/scripts/` — stack-independent unit tests for the `scripts/`
  directory and other infrastructure. **No conftest of its own** —
  inherits only from the minimal parent. Must run from a fresh shell
  with no venv, no sqlalchemy, no eyerate or matika runtime imports
  reachable.

## Choosing the right bucket

When adding a test:

- Does it import anything from `eyerate.*` or `matika.*` runtime
  modules? Or use a fixture from matika's conftest? → `tests/integration/`.
- Does it test pure-Python infrastructure (release tooling, drift
  detection, file layout) without importing the stack? →
  `tests/scripts/`. Use `pytest.importorskip` for optional deps that
  let the test gracefully degrade in minimal environments.

Do not relax the scripts-tier contract. If a test feels like it
"almost" belongs in scripts but needs one or two stack imports, it
belongs in integration.
