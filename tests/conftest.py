import os
import sys
import importlib.util
import pytest

# Add matika/src and matika/tests to sys.path
MATIKA_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "matika", "src"))
if MATIKA_SRC not in sys.path:
    sys.path.insert(0, MATIKA_SRC)

MATIKA_TESTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "matika", "tests"))
if MATIKA_TESTS not in sys.path:
    sys.path.insert(0, MATIKA_TESTS)

# Load matika's conftest explicitly and register it as a module
MATIKA_CONGTEST_PATH = os.path.join(MATIKA_TESTS, "conftest.py")
spec = importlib.util.spec_from_file_location("matika_conftest", MATIKA_CONGTEST_PATH)
matika_conftest = importlib.util.module_from_spec(spec)
sys.modules["matika_conftest"] = matika_conftest
spec.loader.exec_module(matika_conftest)

# Re-export fixtures
globals().update({name: getattr(matika_conftest, name) for name in dir(matika_conftest) if not name.startswith("__")})

@pytest.fixture(scope="session", autouse=True)
def setup_plugins():
    import json
    import shutil
    from matika.core.paths import get_matika_version

    EYERATE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    plugins_dir = os.path.join(EYERATE_ROOT, "plugins")
    if os.path.exists(plugins_dir):
        shutil.rmtree(plugins_dir)
    os.makedirs(plugins_dir, exist_ok=True)

    target_dir = os.path.join(plugins_dir, "eyerate")
    os.makedirs(target_dir, exist_ok=True)
    shutil.copytree(os.path.join(EYERATE_ROOT, "src"), os.path.join(target_dir, "src"), dirs_exist_ok=True)
    shutil.copy(os.path.join(EYERATE_ROOT, "eyerate_menu.json"), os.path.join(target_dir, "eyerate_menu.json"))

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
    
    MatikaBase.metadata.drop_all(bind=engine)
    EyeRateBase.metadata.drop_all(bind=engine)
    
    MatikaBase.metadata.create_all(bind=engine)
    EyeRateBase.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    from matika.database import init_db
    init_db(db)
    db.close()
    
    yield
    
    MatikaBase.metadata.drop_all(bind=engine)
    EyeRateBase.metadata.drop_all(bind=engine)
    if os.path.exists("./data/test_matika.db"):
        os.remove("./data/test_matika.db")
