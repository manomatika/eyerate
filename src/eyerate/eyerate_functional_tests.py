"""Eyerate Layer-3 functional tests — invoked generically by the product gate.

These tests exercise eyerate behaviors against the frozen, booted product.
The existing Layer-1 integration tests (tests/integration/) are unchanged.
Layer-3 is the gate-invocable declaration of the same behaviors.

Function signatures follow the applug-functional-test contract:
  def test_xxx(base_url: str, session) -> None

`session` is a requests.Session pre-authenticated as the QA admin user.

Order-independence contract: every test ARRANGES the server-side provider
precondition it needs at the start AND RESETS the provider back to the default
(yahoo) afterwards via a guaranteed-run ``try/finally`` teardown — so reset
happens even if the body assertion fails. Known-initial-state in,
known-initial-state out. No test depends on running before or after another, and
no external setup/teardown hooks are required.
"""
from __future__ import annotations

import re

DEFAULT_ENDPOINT = "yahoo"


def _set_provider(base_url: str, session, endpoint: str, api_key: str = "") -> None:
    """Set the server-side financial-data provider via the admin form.

    Fetches a fresh CSRF token from GET /eyerate/admin, then POSTs the provider
    selection. Eyerate-internal helper used to both ARRANGE preconditions and
    RESET to a known state.
    """
    resp = session.get(f"{base_url}/eyerate/admin")
    assert resp.status_code == 200, (
        f"Expected 200 from GET /eyerate/admin, got {resp.status_code}"
    )
    match = re.search(r'name="csrf_token"\s+value="([^"]*)"', resp.text)
    assert match, "Could not find csrf_token in admin form HTML"
    csrf_token = match.group(1)

    resp = session.post(
        f"{base_url}/eyerate/admin",
        data={"endpoint": endpoint, "api_key": api_key, "csrf_token": csrf_token},
        allow_redirects=True,
    )
    assert resp.status_code == 200, (
        f"Admin save for endpoint={endpoint!r} did not succeed (got {resp.status_code})"
    )


def _reset_provider_to_default(base_url: str, session) -> None:
    """Reset the server-side provider back to the default (yahoo), no API key."""
    _set_provider(base_url, session, DEFAULT_ENDPOINT, api_key="")


def test_lookup_voo(base_url: str, session) -> None:
    """VOO symbol lookup returns HTTP 200 with VOO in the result symbol field.

    Self-arranges the default (yahoo) provider so it is robust to any leaked
    state, and resets to yahoo in a guaranteed-run ``finally`` — order-independent.
    """
    _set_provider(base_url, session, DEFAULT_ENDPOINT, api_key="")
    try:
        resp = session.get(f"{base_url}/eyerate/securities/lookup", params={"symbol": "VOO"})
        assert resp.status_code == 200, (
            f"Expected 200 from /eyerate/securities/lookup?symbol=VOO, got {resp.status_code}"
        )
        data = resp.json()
        symbol = (data.get("symbol") or data.get("ticker") or "").upper()
        assert "VOO" in symbol, (
            f"Expected 'VOO' in lookup result symbol; got: {data}"
        )
    finally:
        _reset_provider_to_default(base_url, session)


def test_search_voo(base_url: str, session) -> None:
    """VOO symbol search returns HTTP 200 with VOO present in the result list.

    Exercises GET /eyerate/securities/search?q=VOO. The endpoint returns
    ``provider.search(q)`` as JSON: a list of ``{symbol, name, type, exchange}``
    result dicts (see endpoints.py). The default yahoo provider needs no API key.

    Self-arranges the default (yahoo) provider so it is robust to any leaked
    state, and resets to yahoo in a guaranteed-run ``finally`` — order-independent.
    """
    _set_provider(base_url, session, DEFAULT_ENDPOINT, api_key="")
    try:
        resp = session.get(f"{base_url}/eyerate/securities/search", params={"q": "VOO"})
        assert resp.status_code == 200, (
            f"Expected 200 from /eyerate/securities/search?q=VOO, got {resp.status_code}"
        )
        data = resp.json()
        assert isinstance(data, list), (
            f"Expected a JSON list from /eyerate/securities/search; got {type(data).__name__}: {data!r}"
        )
        symbols = {(item.get("symbol") or "").upper() for item in data if isinstance(item, dict)}
        assert "VOO" in symbols, (
            f"Expected 'VOO' among search result symbols; got: {data}"
        )
    finally:
        _reset_provider_to_default(base_url, session)


def test_keyless_finnhub_502(base_url: str, session) -> None:
    """Finnhub with no API key → HTTP 502 from the securities lookup endpoint.

    Self-arranges the keyless-finnhub provider, asserts the 502, and resets to
    the default (yahoo) provider in a guaranteed-run ``finally`` — so the keyless
    mutation never leaks regardless of order or assertion outcome.
    """
    _set_provider(base_url, session, "finnhub", api_key="")
    try:
        resp = session.get(f"{base_url}/eyerate/securities/lookup", params={"symbol": "VOO"})
        assert resp.status_code == 502, (
            f"Expected 502 from /eyerate/securities/lookup with keyless Finnhub, "
            f"got {resp.status_code}"
        )
        detail = resp.text.lower()
        assert "finnhub" in detail or "lookup failed" in detail, (
            f"Expected Finnhub error detail in 502 body; got: {resp.text[:300]}"
        )
    finally:
        _reset_provider_to_default(base_url, session)
