"""Eyerate Layer-3 functional tests — invoked generically by the product gate.

These tests exercise eyerate behaviors against the frozen, booted product.
The existing Layer-1 integration tests (tests/integration/) are unchanged.
Layer-3 is the gate-invocable declaration of the same behaviors.

Function signatures follow the applug-functional-test contract:
  def test_xxx(base_url: str, session) -> None

`session` is a requests.Session pre-authenticated as the QA admin user.
"""
from __future__ import annotations

import re


def test_lookup_voo(base_url: str, session) -> None:
    """VOO symbol lookup returns HTTP 200 with VOO in the result symbol field."""
    resp = session.get(f"{base_url}/eyerate/securities/lookup", params={"symbol": "VOO"})
    assert resp.status_code == 200, (
        f"Expected 200 from /eyerate/securities/lookup?symbol=VOO, got {resp.status_code}"
    )
    data = resp.json()
    symbol = (data.get("symbol") or data.get("ticker") or "").upper()
    assert "VOO" in symbol, (
        f"Expected 'VOO' in lookup result symbol; got: {data}"
    )


def test_keyless_finnhub_502(base_url: str, session) -> None:
    """Finnhub with no API key → HTTP 502 from the securities lookup endpoint."""
    # 1. Fetch admin page to get CSRF token.
    resp = session.get(f"{base_url}/eyerate/admin")
    assert resp.status_code == 200, (
        f"Expected 200 from GET /eyerate/admin, got {resp.status_code}"
    )
    match = re.search(r'name="csrf_token"\s+value="([^"]*)"', resp.text)
    assert match, "Could not find csrf_token in admin form HTML"
    csrf_token = match.group(1)

    # 2. Configure Finnhub with no API key.
    resp = session.post(
        f"{base_url}/eyerate/admin",
        data={"endpoint": "finnhub", "api_key": "", "csrf_token": csrf_token},
        allow_redirects=True,
    )
    assert resp.status_code == 200, (
        f"Admin save did not redirect successfully (got {resp.status_code})"
    )

    # 3. Lookup should return HTTP 502 with Finnhub error detail.
    resp = session.get(f"{base_url}/eyerate/securities/lookup", params={"symbol": "VOO"})
    assert resp.status_code == 502, (
        f"Expected 502 from /eyerate/securities/lookup with keyless Finnhub, "
        f"got {resp.status_code}"
    )
    detail = resp.text.lower()
    assert "finnhub" in detail or "lookup failed" in detail, (
        f"Expected Finnhub error detail in 502 body; got: {resp.text[:300]}"
    )
