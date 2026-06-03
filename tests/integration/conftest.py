"""
Conftest for the integration tier — tests that exercise the full
matika+eyerate stack. Loads matika's conftest, re-exports its fixtures,
and provides session-scoped autouse fixtures that bring up the plugin
tree and database schema.

This conftest may import and exec matika's stack code. Tier-isolation
is enforced by directory layout: scripts-tier tests in `tests/scripts/`
do not load this conftest at all, so the matika exec and the resulting
sqlalchemy import never fire for that tier. See `CLAUDE.md` "Test
Layout" for the tier contract.
"""
import os
import sys
import importlib.util
import pytest


# Resolve matika's tests directory. sys.path itself is set by the
# parent tests/conftest.py — this conftest only needs the absolute path
# to load matika's conftest via importlib.
MATIKA_TESTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "matika", "tests"))
MATIKA_CONFTEST_PATH = os.path.join(MATIKA_TESTS, "conftest.py")

# Load matika's conftest as the module name "matika_conftest" so its
# names are stable across re-exports and sub-imports.
spec = importlib.util.spec_from_file_location("matika_conftest", MATIKA_CONFTEST_PATH)
matika_conftest = importlib.util.module_from_spec(spec)
sys.modules["matika_conftest"] = matika_conftest
spec.loader.exec_module(matika_conftest)

# Re-export matika's fixtures into this conftest's globals so pytest's
# fixture resolver finds them when integration-tier tests request them.
globals().update({name: getattr(matika_conftest, name) for name in dir(matika_conftest) if not name.startswith("__")})


@pytest.fixture(scope="session", autouse=True)
def setup_plugins():
    import json
    import shutil
    from matika.core.paths import get_matika_version

    EYERATE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    plugins_dir = os.path.join(EYERATE_ROOT, "plugins")
    if os.path.exists(plugins_dir):
        shutil.rmtree(plugins_dir)
    os.makedirs(plugins_dir, exist_ok=True)

    target_dir = os.path.join(plugins_dir, "eyerate")
    os.makedirs(target_dir, exist_ok=True)
    shutil.copytree(os.path.join(EYERATE_ROOT, "src"), os.path.join(target_dir, "src"), dirs_exist_ok=True)
    shutil.copy(os.path.join(EYERATE_ROOT, "eyerate_menus.json"), os.path.join(target_dir, "eyerate_menus.json"))

    # Copy applug.json then patch matika_version to match the running Matika
    # version. Without this, tests would fail whenever Matika's VERSION is ahead
    # of the matika_version declared in applug.json (which is normal during dev).
    manifest_src = os.path.join(EYERATE_ROOT, "applug.json")
    manifest_dest = os.path.join(target_dir, "applug.json")
    with open(manifest_src) as f:
        manifest = json.load(f)
    manifest["matika_version"] = get_matika_version()
    with open(manifest_dest, "w") as f:
        json.dump(manifest, f, indent=4)

    yield plugins_dir
    if os.path.exists(plugins_dir):
        shutil.rmtree(plugins_dir)


@pytest.fixture(scope="session", autouse=True)
def setup_database(setup_plugins):
    # Override setup_database to include EyeRate models
    from matika.models import Base as MatikaBase
    from eyerate.models import Base as EyeRateBase
    from matika_conftest import engine, TestingSessionLocal

    # matika's conftest builds the test DATABASE_URL as an absolute SQLite
    # path under ./data/ but does not create the directory. In a clean
    # checkout (fresh clone, git worktree, or CI runner) that directory
    # does not exist yet, so the first connection fails with
    # "unable to open database file". Ensure it exists before any engine
    # connect. The engine is lazy — SQLAlchemy opens the file on first
    # connect, which happens just below in drop_all — so creating the dir
    # here is in time. data/ is runtime-only and untracked, so the
    # integration tier is the right place to guarantee it.
    os.makedirs("data", exist_ok=True)

    MatikaBase.metadata.drop_all(bind=engine)
    EyeRateBase.metadata.drop_all(bind=engine)

    MatikaBase.metadata.create_all(bind=engine)
    EyeRateBase.metadata.create_all(bind=engine)

    from alembic.config import Config
    from alembic import command as alembic_command
    alembic_ini = os.path.join(os.path.dirname(__file__), "..", "..", "..", "matika", "alembic.ini")
    alembic_cfg = Config(alembic_ini)
    alembic_command.stamp(alembic_cfg, "head")

    db = TestingSessionLocal()
    from matika.database import init_db
    init_db(db)
    db.close()

    yield

    MatikaBase.metadata.drop_all(bind=engine)
    EyeRateBase.metadata.drop_all(bind=engine)
    if os.path.exists("./data/test_matika.db"):
        os.remove("./data/test_matika.db")
