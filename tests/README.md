# eyerate tests

Tests are organized by what they exercise.

- `tests/` — integration tests that require the full matika+eyerate application stack. The `conftest.py` here uses autouse session fixtures to bring up the stack.
- `tests/scripts/` — tests for the `scripts/` directory (release tooling, sync_version, drift detection). Pure unit tests with no application-stack dependencies. The local `conftest.py` no-ops the parent autouse fixtures.

When adding a new test, choose the directory based on what the test actually needs. If a test could run with no application stack at all, it belongs under a subdirectory matching what it tests (`tests/scripts/`, future `tests/utils/`, etc.). If it needs the stack, it goes at the top level.
