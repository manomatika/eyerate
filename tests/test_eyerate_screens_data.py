"""
Tests for src/eyerate/eyerate_screens.json — the screen inventory for the eyerate AppLug.

Validates:
  - The file parses as valid JSON with schema_version "1.0"
  - All user-facing GET/HTML routes (/eyerate/securities, /eyerate/admin) are
    classified as "screen" entries with required markers and steps
  - All not_a_screen entries have a reason field
  - All screen entries have markers and at least one step with an allowed verb
  - ScreenLoaderService can load the file without errors
"""
import json
import shutil
from pathlib import Path

import pytest

# Resolve the screens file relative to this test file's location so the test
# runs correctly whether invoked from the eyerate worktree root or elsewhere.
_REPO_ROOT = Path(__file__).parent.parent
SCREENS_FILE = _REPO_ROOT / "src" / "eyerate" / "eyerate_screens.json"

EXPECTED_SCREEN_ROUTES = {"/eyerate/securities", "/eyerate/admin"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_screens_json():
    with open(SCREENS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Schema and structure
# ---------------------------------------------------------------------------

def test_screens_file_exists():
    """eyerate_screens.json exists in src/eyerate/."""
    assert SCREENS_FILE.exists(), f"Missing file: {SCREENS_FILE}"


def test_screens_schema_version():
    """eyerate_screens.json has schema_version '1.0'."""
    data = load_screens_json()
    assert data.get("schema_version") == "1.0", (
        f"Expected schema_version '1.0', got {data.get('schema_version')!r}"
    )


def test_screens_has_screens_list():
    """eyerate_screens.json has a top-level 'screens' list."""
    data = load_screens_json()
    assert isinstance(data.get("screens"), list), "'screens' must be a list"
    assert len(data["screens"]) > 0, "'screens' list must not be empty"


# ---------------------------------------------------------------------------
# Type: screen — markers, steps, routes
# ---------------------------------------------------------------------------

def test_expected_routes_classified_as_screens():
    """
    /eyerate/securities and /eyerate/admin must each appear as a type='screen' entry.
    """
    data = load_screens_json()
    screen_routes = {
        entry["route"]
        for entry in data["screens"]
        if entry.get("type") == "screen"
    }
    for route in EXPECTED_SCREEN_ROUTES:
        assert route in screen_routes, (
            f"Expected route {route!r} to be classified as type='screen', "
            f"but only found screen routes: {sorted(screen_routes)}"
        )


def test_all_screen_entries_have_markers():
    """Every type='screen' entry must have a non-empty 'markers' list."""
    data = load_screens_json()
    for entry in data["screens"]:
        if entry.get("type") != "screen":
            continue
        sid = entry.get("screen_id", "<no id>")
        assert "markers" in entry, f"Screen '{sid}' is missing 'markers'"
        assert isinstance(entry["markers"], list), f"Screen '{sid}' markers must be a list"
        assert len(entry["markers"]) > 0, f"Screen '{sid}' markers must not be empty"


def test_all_screen_entries_have_steps():
    """Every type='screen' entry must have a non-empty 'steps' list."""
    from matika.core.screen_loader import ALLOWED_VERBS

    data = load_screens_json()
    for entry in data["screens"]:
        if entry.get("type") != "screen":
            continue
        sid = entry.get("screen_id", "<no id>")
        assert "steps" in entry, f"Screen '{sid}' is missing 'steps'"
        assert isinstance(entry["steps"], list), f"Screen '{sid}' steps must be a list"
        assert len(entry["steps"]) > 0, f"Screen '{sid}' steps must not be empty"
        for step in entry["steps"]:
            verb = step.get("verb")
            assert verb in ALLOWED_VERBS, (
                f"Screen '{sid}' has step with unknown verb {verb!r}. "
                f"Allowed: {sorted(ALLOWED_VERBS)}"
            )


def test_screen_entries_have_navigate_step():
    """Every type='screen' entry must include at least one navigate step."""
    data = load_screens_json()
    for entry in data["screens"]:
        if entry.get("type") != "screen":
            continue
        sid = entry.get("screen_id", "<no id>")
        verbs = [step.get("verb") for step in entry.get("steps", [])]
        assert "navigate" in verbs, (
            f"Screen '{sid}' must have at least one navigate step; found: {verbs}"
        )


# ---------------------------------------------------------------------------
# Type: not_a_screen — reason field
# ---------------------------------------------------------------------------

def test_all_not_a_screen_entries_have_reason():
    """Every type='not_a_screen' entry must have a non-empty 'reason' string."""
    data = load_screens_json()
    for entry in data["screens"]:
        if entry.get("type") != "not_a_screen":
            continue
        sid = entry.get("screen_id", "<no id>")
        assert "reason" in entry, f"not_a_screen entry '{sid}' is missing 'reason'"
        assert isinstance(entry["reason"], str), (
            f"not_a_screen entry '{sid}' reason must be a string"
        )
        assert entry["reason"].strip(), (
            f"not_a_screen entry '{sid}' reason must not be empty"
        )


# ---------------------------------------------------------------------------
# screen_id uniqueness
# ---------------------------------------------------------------------------

def test_screen_ids_are_unique():
    """All screen_id values must be unique within the file."""
    data = load_screens_json()
    ids = [entry.get("screen_id") for entry in data["screens"] if entry.get("screen_id")]
    assert len(ids) == len(set(ids)), (
        f"Duplicate screen_ids found: {[x for x in ids if ids.count(x) > 1]}"
    )


def test_screen_ids_use_eyerate_prefix():
    """All screen_id values must use the 'eyerate:' namespace prefix."""
    data = load_screens_json()
    for entry in data["screens"]:
        sid = entry.get("screen_id", "")
        assert sid.startswith("eyerate:"), (
            f"screen_id {sid!r} must start with 'eyerate:'"
        )


# ---------------------------------------------------------------------------
# ScreenLoaderService integration
# ---------------------------------------------------------------------------

def test_eyerate_screens_loads_via_service(tmp_path):
    """
    ScreenLoaderService must load eyerate_screens.json without errors and
    return an 'eyerate' key in the result.
    """
    from matika.core.screen_loader import ScreenLoaderService

    # Copy eyerate_screens.json into a plugin-layout temp directory.
    plugin_dir = tmp_path / "plugins" / "eyerate"
    plugin_dir.mkdir(parents=True)
    shutil.copy(str(SCREENS_FILE), str(plugin_dir / "eyerate_screens.json"))

    loader = ScreenLoaderService(
        core_screens_dir=str(tmp_path / "nonexistent_core"),
        plugins_dir=str(tmp_path / "plugins"),
    )
    result = loader.load_screens()
    assert "eyerate" in result, (
        f"Expected 'eyerate' key in ScreenLoaderService result; got: {list(result.keys())}"
    )

    # The loaded entries must include our two screens.
    screen_routes = {
        entry["route"]
        for entry in result["eyerate"]
        if entry.get("type") == "screen"
    }
    for route in EXPECTED_SCREEN_ROUTES:
        assert route in screen_routes, (
            f"ScreenLoaderService result missing expected screen route {route!r}; "
            f"found screen routes: {sorted(screen_routes)}"
        )


def test_eyerate_screens_service_no_duplicate_ids(tmp_path):
    """
    ScreenLoaderService must not raise RuntimeError for duplicate screen_ids
    within the eyerate plugin alone.
    """
    from matika.core.screen_loader import ScreenLoaderService

    plugin_dir = tmp_path / "plugins" / "eyerate"
    plugin_dir.mkdir(parents=True)
    shutil.copy(str(SCREENS_FILE), str(plugin_dir / "eyerate_screens.json"))

    loader = ScreenLoaderService(
        core_screens_dir=str(tmp_path / "nonexistent_core"),
        plugins_dir=str(tmp_path / "plugins"),
    )
    # Must not raise
    result = loader.load_screens()
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# DOM test hooks — verify markers exist as real attributes in templates
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = _REPO_ROOT / "src" / "eyerate" / "templates"
ADMIN_TEMPLATE = _TEMPLATES_DIR / "eyerate_admin.html"
SECURITIES_TEMPLATE = _TEMPLATES_DIR / "admin_securities.html"


def test_eyerate_admin_form_has_id_hook():
    content = ADMIN_TEMPLATE.read_text(encoding="utf-8")
    assert 'id="eyerate-admin-form"' in content, (
        "eyerate_admin.html: form is missing id='eyerate-admin-form'"
    )


def test_eyerate_admin_fieldset_has_class_hook():
    content = ADMIN_TEMPLATE.read_text(encoding="utf-8")
    assert 'class="admin-provider-section"' in content, (
        "eyerate_admin.html: fieldset is missing class='admin-provider-section'"
    )


def test_securities_template_has_securities_list_id():
    content = SECURITIES_TEMPLATE.read_text(encoding="utf-8")
    assert 'id="securities-list"' in content, (
        "admin_securities.html: missing id='securities-list' marker element"
    )


def test_securities_template_has_securities_table_class():
    content = SECURITIES_TEMPLATE.read_text(encoding="utf-8")
    assert 'class="securities-table"' in content, (
        "admin_securities.html: missing class='securities-table' marker element"
    )
