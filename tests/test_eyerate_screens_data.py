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


def test_securities_template_has_action_form_id():
    """admin_securities.html renders the real #action-form submission form.

    This is a genuine, load-bearing structural element of the securities
    maintenance screen (the POST form carrying the maintenance fields),
    rendered unconditionally — not a hidden/empty decoy hook.
    """
    content = SECURITIES_TEMPLATE.read_text(encoding="utf-8")
    assert 'id="action-form"' in content, (
        "admin_securities.html: missing id='action-form' marker element"
    )


def test_securities_template_has_lookup_modal_id():
    """admin_securities.html renders the real #lookup-modal element.

    The Financial Security Lookup modal is securities-specific and genuinely
    load-bearing — it is driven by dialogs/lookup-dialog.js
    (document.getElementById('lookup-modal')) — rendered unconditionally, not a
    hidden/empty decoy hook.
    """
    content = SECURITIES_TEMPLATE.read_text(encoding="utf-8")
    assert 'id="lookup-modal"' in content, (
        "admin_securities.html: missing id='lookup-modal' marker element"
    )


# ---------------------------------------------------------------------------
# Interactive step coverage (b2 / b3)
#
# b2 enriches eyerate:securities_list to drive the read-only lookup flow.
# b3 adds eyerate:securities_lookup_error, a SEPARATE screen (unique id, same
# route) that configures keyless finnhub and asserts the in-dialog error. Because
# configuring keyless finnhub MUTATES server-side provider config, the b3 flow
# ARRANGES that mutation at the start AND RESETS the provider back to the default
# (yahoo) via the admin form at the end of its OWN step list. Known-initial-state
# in, known-initial-state out: the screen poisons nothing regardless of run order,
# so there is no "must run last" ordering crutch.
#
# Selectors used by the steps are grounded in real DOM hooks:
#   - #lookup-search-input / #btn-lookup-search / #btn-ok-lookup / #lookup-modal
#     / #action-form           → admin_securities.html (eyerate template)
#   - .lookup-result-row / .lookup-error
#                              → dialogs/lookup-dialog.js (eyerate-owned JS)
#   - name="endpoint" / value="finnhub" / value="yahoo" / name="api_key"
#     / type="submit"          → eyerate_admin.html (eyerate template)
#   - #field-symbol / .btn-lookup → rendered by matika's maintenance base
#     template from eyerate's metadata: the 'symbol' field declares has_lookup
#     (asserted against the metadata file below).
#   - #btn-new                 → matika maintenance base template (framework-owned
#     action button that reveals .btn-lookup by entering create mode).
# ---------------------------------------------------------------------------

LOOKUP_SCREEN_ID = "eyerate:securities_list"
LOOKUP_ERROR_SCREEN_ID = "eyerate:securities_lookup_error"
LOOKUP_DIALOG_JS = (
    _REPO_ROOT / "src" / "eyerate" / "static" / "js" / "dialogs" / "lookup-dialog.js"
)
METADATA_FILE = (
    _REPO_ROOT / "src" / "eyerate" / "metadata" / "securities_maint_activity_metadata.json"
)


def _get_screen(screen_id):
    for entry in load_screens_json()["screens"]:
        if entry.get("screen_id") == screen_id:
            return entry
    raise AssertionError(f"Screen {screen_id!r} not found in eyerate_screens.json")


def _step_pairs(entry):
    return [(s.get("verb"), s.get("target")) for s in entry.get("steps", [])]


def test_every_screen_step_has_a_target():
    """Every interaction step (all allowed verbs) must declare a non-empty target."""
    data = load_screens_json()
    for entry in data["screens"]:
        if entry.get("type") != "screen":
            continue
        sid = entry.get("screen_id", "<no id>")
        for step in entry.get("steps", []):
            assert step.get("target"), (
                f"Screen '{sid}' has a {step.get('verb')!r} step with no 'target'"
            )


def test_fill_and_assert_value_steps_declare_a_value():
    """fill and assert_value steps must declare a 'value' field."""
    data = load_screens_json()
    for entry in data["screens"]:
        if entry.get("type") != "screen":
            continue
        sid = entry.get("screen_id", "<no id>")
        for step in entry.get("steps", []):
            if step.get("verb") in ("fill", "assert_value"):
                assert "value" in step, (
                    f"Screen '{sid}' has a {step['verb']!r} step on "
                    f"{step.get('target')!r} with no 'value'"
                )


def test_securities_list_drives_interactive_lookup_flow():
    """b2: securities_list drives the real read-only lookup flow end to end."""
    pairs = _step_pairs(_get_screen(LOOKUP_SCREEN_ID))
    for expected in [
        ("navigate", "/eyerate/securities"),
        ("click", "#btn-new"),
        ("click", ".btn-lookup"),
        ("wait_for", "#lookup-modal"),
        ("fill", "#lookup-search-input"),
        ("click", "#btn-lookup-search"),
        ("wait_for", ".lookup-result-row"),
        ("assert_present", ".lookup-result-row"),
        ("click", ".lookup-result-row"),
        ("click", "#btn-ok-lookup"),
        ("assert_value", "#field-symbol"),
    ]:
        assert expected in pairs, f"securities_list missing step {expected}"


def test_securities_list_fills_and_asserts_voo():
    """b2: the search field is filled with VOO and the symbol field is asserted VOO."""
    entry = _get_screen(LOOKUP_SCREEN_ID)
    fills = {s["target"]: s.get("value") for s in entry["steps"] if s["verb"] == "fill"}
    assert fills.get("#lookup-search-input") == "VOO"
    asserts = {
        s["target"]: s.get("value") for s in entry["steps"] if s["verb"] == "assert_value"
    }
    assert asserts.get("#field-symbol") == "VOO"


def test_lookup_error_screen_exists_and_is_well_formed():
    """b3: the keyless-finnhub error screen exists with required markers + navigate."""
    entry = _get_screen(LOOKUP_ERROR_SCREEN_ID)
    assert entry.get("type") == "screen"
    assert entry.get("route") == "/eyerate/securities"
    assert entry.get("markers"), "lookup_error screen must declare markers"
    verbs = [s.get("verb") for s in entry.get("steps", [])]
    assert "navigate" in verbs, "lookup_error screen must have a navigate step"


def test_lookup_error_screen_drives_keyless_finnhub_error_flow():
    """b3: ARRANGE keyless finnhub via the admin form, ASSERT the visible
    in-dialog error row and the absence of result rows, then RESET the provider
    back to the default (yahoo) via the admin form — all within the screen's own
    step list, in order."""
    pairs = _step_pairs(_get_screen(LOOKUP_ERROR_SCREEN_ID))
    for expected in [
        # ARRANGE: select keyless finnhub.
        ("navigate", "/eyerate/admin"),
        ("click", 'input[name="endpoint"][value="finnhub"]'),
        ("fill", 'input[name="api_key"]'),
        ("click", '#eyerate-admin-form button[type="submit"]'),
        # ACT + ASSERT: drive the lookup and observe the error.
        ("navigate", "/eyerate/securities"),
        ("click", "#btn-new"),
        ("click", ".btn-lookup"),
        ("fill", "#lookup-search-input"),
        ("click", "#btn-lookup-search"),
        ("assert_present", ".lookup-error"),
        ("assert_absent", ".lookup-result-row"),
        # RESET: restore the default (yahoo) provider.
        ("navigate", "/eyerate/admin"),
        ("click", 'input[name="endpoint"][value="yahoo"]'),
        ("click", '#eyerate-admin-form button[type="submit"]'),
    ]:
        assert expected in pairs, f"lookup_error screen missing step {expected}"


def test_lookup_error_screen_resets_provider_to_default_at_end():
    """b3 order-independence contract: the keyless-finnhub error screen MUTATES
    server-side provider config, so it self-resets the provider to the default
    (yahoo) as the FINAL action of its own step list. Known-initial-state in,
    known-initial-state out — the screen poisons nothing regardless of run order,
    replacing the old 'must run last' ordering crutch."""
    pairs = _step_pairs(_get_screen(LOOKUP_ERROR_SCREEN_ID))
    assert pairs[-3:] == [
        ("navigate", "/eyerate/admin"),
        ("click", 'input[name="endpoint"][value="yahoo"]'),
        ("click", '#eyerate-admin-form button[type="submit"]'),
    ], (
        "lookup_error screen must END by resetting the provider to yahoo via the "
        f"admin form; last steps were: {pairs[-3:]}"
    )


# --- DOM hooks for the NEW selectors introduced by b2/b3 ---

def test_securities_template_has_lookup_search_input_hook():
    content = SECURITIES_TEMPLATE.read_text(encoding="utf-8")
    assert 'id="lookup-search-input"' in content, (
        "admin_securities.html: missing id='lookup-search-input' (b2/b3 search field)"
    )


def test_securities_template_has_lookup_search_button_hook():
    content = SECURITIES_TEMPLATE.read_text(encoding="utf-8")
    assert 'id="btn-lookup-search"' in content, (
        "admin_securities.html: missing id='btn-lookup-search' (b2/b3 search trigger)"
    )


def test_securities_template_has_lookup_ok_button_hook():
    content = SECURITIES_TEMPLATE.read_text(encoding="utf-8")
    assert 'id="btn-ok-lookup"' in content, (
        "admin_securities.html: missing id='btn-ok-lookup' (b2 row-select confirm)"
    )


def test_lookup_dialog_js_renders_result_row_class():
    content = LOOKUP_DIALOG_JS.read_text(encoding="utf-8")
    assert "lookup-result-row" in content, (
        "lookup-dialog.js: result rows must carry class='lookup-result-row' (b2/b3)"
    )


def test_lookup_dialog_js_renders_error_row_class():
    """The b3 error assertion targets .lookup-error; the lookup dialog must render
    that class on its error row so the screen step and the DOM cannot drift."""
    content = LOOKUP_DIALOG_JS.read_text(encoding="utf-8")
    assert 'class="lookup-error"' in content, (
        "lookup-dialog.js: error row must carry class='lookup-error' (b3)"
    )


def test_admin_template_has_finnhub_endpoint_radio_hook():
    content = ADMIN_TEMPLATE.read_text(encoding="utf-8")
    assert 'name="endpoint"' in content and 'value="finnhub"' in content, (
        "eyerate_admin.html: missing finnhub endpoint radio (b3 provider select)"
    )


def test_admin_template_has_yahoo_endpoint_radio_hook():
    content = ADMIN_TEMPLATE.read_text(encoding="utf-8")
    assert 'name="endpoint"' in content and 'value="yahoo"' in content, (
        "eyerate_admin.html: missing yahoo endpoint radio (b3 reset-to-default select)"
    )


def test_admin_template_has_api_key_input_hook():
    content = ADMIN_TEMPLATE.read_text(encoding="utf-8")
    assert 'name="api_key"' in content, (
        "eyerate_admin.html: missing name='api_key' input (b3 keyless config)"
    )


def test_admin_template_has_submit_button_hook():
    content = ADMIN_TEMPLATE.read_text(encoding="utf-8")
    assert 'type="submit"' in content, (
        "eyerate_admin.html: missing submit button (b3 admin save)"
    )


def test_symbol_field_declares_has_lookup_in_metadata():
    """#field-symbol and .btn-lookup are rendered by matika's maintenance base
    template from eyerate's metadata: the 'symbol' field declares has_lookup,
    which produces id='field-symbol' plus the .btn-lookup button. This grounds
    the two framework-rendered selectors used by b2/b3 against eyerate-owned data."""
    meta = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    fields = meta["maintenance_panel"]["fields"]
    symbol = next((f for f in fields if f.get("name") == "symbol"), None)
    assert symbol is not None, "metadata: no 'symbol' field in maintenance_panel"
    assert symbol.get("has_lookup") is True, (
        "metadata: 'symbol' field must declare has_lookup (renders #field-symbol + .btn-lookup)"
    )
