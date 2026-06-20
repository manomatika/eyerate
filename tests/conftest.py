"""
Shared minimal setup for the eyerate test tree. Tier-specific conftest
files live one directory down — see `tests/integration/conftest.py`.
The scripts tier (`tests/scripts/`) has no conftest of its own and
inherits only from this file.

This file MUST NOT import or load anything that pulls in matika's
runtime stack (sqlalchemy, FastAPI app, etc.). Doing so would break the
contract that `pytest tests/scripts/` runs in any Python environment
without venv setup. See CLAUDE.md "Test Layout" for the tier contract.
"""
import os
import sys


# Make matika importable for any tier that needs it. Adding to sys.path
# is a path-only operation — it does NOT trigger any imports here.
MATIKA_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "matika", "src"))
if MATIKA_SRC not in sys.path:
    sys.path.insert(0, MATIKA_SRC)

MATIKA_TESTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "matika", "tests"))
if MATIKA_TESTS not in sys.path:
    sys.path.insert(0, MATIKA_TESTS)

# Make eyerate itself importable (integration tests import from eyerate.*).
EYERATE_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if EYERATE_SRC not in sys.path:
    sys.path.insert(0, EYERATE_SRC)
