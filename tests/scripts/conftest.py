"""
Local conftest for unit tests that need no database or plugin setup.
Overrides the session-scoped autouse fixtures from tests/conftest.py so
those fixtures do not fire for tests in this directory.
"""
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_plugins():
    pass


@pytest.fixture(scope="session", autouse=True)
def setup_database(setup_plugins):
    pass
