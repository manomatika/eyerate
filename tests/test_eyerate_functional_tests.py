"""Tests for eyerate Layer-3 functional test declarations and implementations."""
import inspect
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_REPO_ROOT = Path(__file__).parent.parent
FUNCTIONAL_TESTS_JSON = _REPO_ROOT / "src" / "eyerate" / "eyerate_functional_tests.json"
FUNCTIONAL_TESTS_PY = _REPO_ROOT / "src" / "eyerate" / "eyerate_functional_tests.py"


def _load_json():
    with open(FUNCTIONAL_TESTS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("eyerate_functional_tests", str(FUNCTIONAL_TESTS_PY))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_json_resp(status, data):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = data
    m.text = json.dumps(data)
    return m


def _make_text_resp(status, text):
    m = MagicMock()
    m.status_code = status
    m.text = text
    m.json.side_effect = ValueError("not JSON")
    return m


# --- JSON manifest structure ---

def test_json_exists():
    assert FUNCTIONAL_TESTS_JSON.exists()

def test_schema_version():
    assert _load_json()["schema_version"] == "1.0"

def test_has_functional_tests():
    data = _load_json()
    assert isinstance(data["functional_tests"], list)
    assert len(data["functional_tests"]) >= 2

def test_lookup_voo_declared():
    ids = {t["test_id"] for t in _load_json()["functional_tests"]}
    assert "eyerate:lookup_voo" in ids

def test_search_voo_declared():
    ids = {t["test_id"] for t in _load_json()["functional_tests"]}
    assert "eyerate:search_voo" in ids

def test_keyless_finnhub_declared():
    ids = {t["test_id"] for t in _load_json()["functional_tests"]}
    assert "eyerate:keyless_finnhub_502" in ids

def test_functional_tests_declare_no_order_dependency():
    """Order-independence contract: the manifest declares no run-order field.

    Each functional test self-arranges its precondition and self-resets to the
    default provider via guaranteed-run teardown, so declaration order in the
    JSON carries no semantics. This replaces the old 'search must precede
    keyless_finnhub' ordering crutch.
    """
    for entry in _load_json()["functional_tests"]:
        for ordering_key in ("order", "run_after", "run_before", "depends_on"):
            assert ordering_key not in entry, (
                f"{entry['test_id']} declares ordering key {ordering_key!r}; "
                f"functional tests must be order-independent"
            )

def test_all_required_fields_present():
    for entry in _load_json()["functional_tests"]:
        for f in ("test_id", "description", "module", "function"):
            assert f in entry, f"Missing {f!r} in {entry.get('test_id','?')}"

def test_all_test_ids_use_eyerate_namespace():
    for entry in _load_json()["functional_tests"]:
        assert entry["test_id"].startswith("eyerate:")

def test_all_tests_reference_correct_module():
    for entry in _load_json()["functional_tests"]:
        assert entry["module"] == "eyerate_functional_tests"

# --- Python module ---

def test_module_importable():
    assert _get_module() is not None

def test_lookup_voo_callable():
    mod = _get_module()
    assert callable(getattr(mod, "test_lookup_voo", None))

def test_search_voo_callable():
    mod = _get_module()
    assert callable(getattr(mod, "test_search_voo", None))

def test_keyless_finnhub_callable():
    mod = _get_module()
    assert callable(getattr(mod, "test_keyless_finnhub_502", None))

def test_no_undeclared_test_functions():
    """Every test_* function in the module is declared in the JSON manifest."""
    declared = {t["function"] for t in _load_json()["functional_tests"]}
    mod = _get_module()
    all_test_fns = {
        n for n, fn in inspect.getmembers(mod, inspect.isfunction)
        if n.startswith("test_")
    }
    undeclared = all_test_fns - declared
    assert not undeclared, f"Undeclared test_* in module: {undeclared}"

# --- Unit tests for function implementations (mock session) ---
#
# Each functional test now follows ARRANGE (set provider via admin form) →
# ASSERT (body) → RESET (provider back to yahoo, in a guaranteed-run finally).
# The mock GET side_effect lists therefore interleave admin-form fetches (for the
# CSRF token in both arrange and reset) with the endpoint call under test:
#   lookup/search:  [arrange admin html, endpoint resp, reset admin html]
#   keyless_finnhub:[arrange admin html, lookup resp,   reset admin html]
# session.post is the admin save, called once on arrange and once on reset.

_ADMIN_HTML = '<input type="hidden" name="csrf_token" value="tok">'


def _post_endpoints(session):
    """The 'endpoint' value of every admin-save POST, in call order."""
    return [
        (call.kwargs.get("data") or {}).get("endpoint")
        for call in session.post.call_args_list
    ]


def _assert_reset_to_yahoo(session):
    """The final admin-save POST must reset the provider to the default (yahoo)."""
    endpoints = _post_endpoints(session)
    assert endpoints, "expected at least one admin-save POST (reset)"
    assert endpoints[-1] == "yahoo", (
        f"expected the final reset POST to set endpoint=yahoo; got {endpoints}"
    )


def test_lookup_voo_passes_on_200_with_voo():
    mod = _get_module()
    session = MagicMock()
    session.get.side_effect = [
        _make_text_resp(200, _ADMIN_HTML),  # arrange CSRF
        _make_json_resp(200, {"symbol": "VOO", "name": "Vanguard"}),  # lookup
        _make_text_resp(200, _ADMIN_HTML),  # reset CSRF
    ]
    session.post.return_value = _make_text_resp(200, "ok")
    mod.test_lookup_voo(base_url="http://localhost:8000", session=session)
    _assert_reset_to_yahoo(session)

def test_lookup_voo_fails_on_non_200():
    mod = _get_module()
    session = MagicMock()
    session.get.side_effect = [
        _make_text_resp(200, _ADMIN_HTML),  # arrange CSRF
        _make_json_resp(500, {}),           # lookup → assertion fails
        _make_text_resp(200, _ADMIN_HTML),  # reset CSRF (guaranteed-run)
    ]
    session.post.return_value = _make_text_resp(200, "ok")
    with pytest.raises(AssertionError, match="200"):
        mod.test_lookup_voo(base_url="http://localhost:8000", session=session)
    # Guaranteed-run teardown: reset must fire even though the body assertion failed.
    _assert_reset_to_yahoo(session)

def test_lookup_voo_fails_if_voo_absent():
    mod = _get_module()
    session = MagicMock()
    session.get.side_effect = [
        _make_text_resp(200, _ADMIN_HTML),
        _make_json_resp(200, {"symbol": "AAPL"}),
        _make_text_resp(200, _ADMIN_HTML),
    ]
    session.post.return_value = _make_text_resp(200, "ok")
    with pytest.raises(AssertionError):
        mod.test_lookup_voo(base_url="http://localhost:8000", session=session)
    _assert_reset_to_yahoo(session)

def test_search_voo_passes_on_200_with_voo():
    mod = _get_module()
    session = MagicMock()
    session.get.side_effect = [
        _make_text_resp(200, _ADMIN_HTML),
        _make_json_resp(
            200,
            [
                {"symbol": "VOO", "name": "Vanguard S&P 500 ETF", "type": "ETF", "exchange": "PCX"},
                {"symbol": "VOOG", "name": "Vanguard S&P 500 Growth ETF", "type": "ETF", "exchange": "PCX"},
            ],
        ),
        _make_text_resp(200, _ADMIN_HTML),
    ]
    session.post.return_value = _make_text_resp(200, "ok")
    mod.test_search_voo(base_url="http://localhost:8000", session=session)
    _assert_reset_to_yahoo(session)

def test_search_voo_fails_on_non_200():
    mod = _get_module()
    session = MagicMock()
    session.get.side_effect = [
        _make_text_resp(200, _ADMIN_HTML),
        _make_json_resp(502, {"detail": "lookup failed"}),
        _make_text_resp(200, _ADMIN_HTML),
    ]
    session.post.return_value = _make_text_resp(200, "ok")
    with pytest.raises(AssertionError, match="200"):
        mod.test_search_voo(base_url="http://localhost:8000", session=session)
    _assert_reset_to_yahoo(session)

def test_search_voo_fails_if_voo_absent():
    mod = _get_module()
    session = MagicMock()
    session.get.side_effect = [
        _make_text_resp(200, _ADMIN_HTML),
        _make_json_resp(200, [{"symbol": "AAPL", "name": "Apple Inc."}]),
        _make_text_resp(200, _ADMIN_HTML),
    ]
    session.post.return_value = _make_text_resp(200, "ok")
    with pytest.raises(AssertionError):
        mod.test_search_voo(base_url="http://localhost:8000", session=session)
    _assert_reset_to_yahoo(session)

def test_search_voo_fails_if_not_a_list():
    mod = _get_module()
    session = MagicMock()
    session.get.side_effect = [
        _make_text_resp(200, _ADMIN_HTML),
        _make_json_resp(200, {"symbol": "VOO"}),
        _make_text_resp(200, _ADMIN_HTML),
    ]
    session.post.return_value = _make_text_resp(200, "ok")
    with pytest.raises(AssertionError, match="list"):
        mod.test_search_voo(base_url="http://localhost:8000", session=session)
    _assert_reset_to_yahoo(session)

def test_keyless_finnhub_passes_on_502():
    mod = _get_module()
    session = MagicMock()
    session.get.side_effect = [
        _make_text_resp(200, _ADMIN_HTML),  # arrange CSRF (set finnhub)
        _make_text_resp(502, '{"detail": "lookup failed: Finnhub search HTTP 401"}'),  # lookup
        _make_text_resp(200, _ADMIN_HTML),  # reset CSRF
    ]
    session.post.return_value = _make_text_resp(200, "ok")
    mod.test_keyless_finnhub_502(base_url="http://localhost:8000", session=session)
    # Arrange POSTs finnhub, reset POSTs yahoo.
    assert _post_endpoints(session) == ["finnhub", "yahoo"]

def test_keyless_finnhub_fails_on_200_lookup():
    mod = _get_module()
    session = MagicMock()
    session.get.side_effect = [
        _make_text_resp(200, _ADMIN_HTML),  # arrange CSRF (set finnhub)
        _make_json_resp(200, {"symbol": "VOO"}),  # lookup → assertion fails
        _make_text_resp(200, _ADMIN_HTML),  # reset CSRF (guaranteed-run)
    ]
    session.post.return_value = _make_text_resp(200, "ok")
    with pytest.raises(AssertionError, match="502"):
        mod.test_keyless_finnhub_502(base_url="http://localhost:8000", session=session)
    # Guaranteed-run teardown: the keyless mutation is reset to yahoo even though
    # the body assertion failed.
    _assert_reset_to_yahoo(session)
