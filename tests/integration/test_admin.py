"""
Integration tests for the eyerate admin page (provider-selection UI)
and Bug B regression (search/lookup endpoints).

Includes Task 4 regression tests: provider failures must surface as HTTP 502
(not silent empty list / 404), and genuine zero-results must stay 200 empty list.
"""
import pytest
from unittest.mock import patch, AsyncMock
from matika.database import init_db


def _login(client, email, password):
    client.post("/login", data={"email": email, "password": password}, follow_redirects=False)


def test_eyerate_admin_shows_provider_selection(client, test_admin, db):
    """Admin page must render the provider-selection form, not the stub."""
    init_db(db)
    _login(client, "admin@example.com", "adminpassword")
    resp = client.get("/eyerate/admin")
    assert resp.status_code == 200
    assert "coming soon" not in resp.text.lower()
    # Should show all three providers
    assert "yahoo" in resp.text.lower()
    assert "finnhub" in resp.text.lower()
    assert "alphavantage" in resp.text.lower() or "alpha vantage" in resp.text.lower()
    # Should have a form
    assert 'method="post"' in resp.text.lower() or "method='post'" in resp.text.lower()


def test_eyerate_admin_defaults_to_yahoo(client, test_admin, db):
    """Default provider is Yahoo Finance when no setting is configured."""
    init_db(db)
    _login(client, "admin@example.com", "adminpassword")
    resp = client.get("/eyerate/admin")
    assert resp.status_code == 200
    # Yahoo radio button must be present
    assert 'value="yahoo"' in resp.text
    # At least one radio should be checked (default is yahoo)
    assert "checked" in resp.text


def test_eyerate_admin_save_endpoint(client, test_admin, db):
    """Admin can save the provider setting via POST."""
    init_db(db)
    _login(client, "admin@example.com", "adminpassword")
    # POST to change to finnhub
    resp = client.post("/eyerate/admin", data={
        "endpoint": "finnhub",
        "api_key": "test-api-key-123",
    }, follow_redirects=False)
    # Should redirect
    assert resp.status_code == 303
    # Now GET and verify setting is reflected in the page
    resp2 = client.get("/eyerate/admin")
    assert resp2.status_code == 200
    # finnhub radio should now be checked
    assert "finnhub" in resp2.text.lower()
    assert 'value="finnhub" checked' in resp2.text or (
        'value="finnhub"' in resp2.text and "checked" in resp2.text
    )


def test_securities_search_returns_results(client, test_admin, db):
    """Search endpoint returns data — not empty — when the provider works."""
    init_db(db)
    _login(client, "admin@example.com", "adminpassword")

    mock_results = [{"symbol": "VOO", "name": "Vanguard S&P 500 ETF", "type": "ETF", "exchange": "PCX"}]
    with patch("eyerate.plugin.get_financial_security_endpoint") as mock_ep_factory:
        mock_ep = AsyncMock()
        mock_ep.search.return_value = mock_results
        mock_ep_factory.return_value = mock_ep

        resp = client.get("/eyerate/securities/search?q=VOO")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert data[0]["symbol"] == "VOO"


def test_securities_lookup_returns_data(client, test_admin, db):
    """Lookup endpoint returns security details — not 404 — when the provider works."""
    init_db(db)
    _login(client, "admin@example.com", "adminpassword")

    mock_detail = {
        "symbol": "VOO",
        "name": "Vanguard S&P 500 ETF",
        "financial_security_type": "ETF",
        "asset_class": "Large Cap Stock",
        "current_price": "450.00",
    }
    with patch("eyerate.plugin.get_financial_security_endpoint") as mock_ep_factory:
        mock_ep = AsyncMock()
        mock_ep.lookup.return_value = mock_detail
        mock_ep_factory.return_value = mock_ep

        resp = client.get("/eyerate/securities/lookup?symbol=VOO")

    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "VOO"
    assert data["name"] == "Vanguard S&P 500 ETF"


# ---------------------------------------------------------------------------
# Task 4 regression tests: silent-empty anti-pattern eliminated
# These tests would have caught Bug B's silent failure nature.
# ---------------------------------------------------------------------------

def test_securities_search_provider_error_returns_502(client, test_admin, db):
    """Provider failure → search returns 502, NOT a silent empty list."""
    init_db(db)
    _login(client, "admin@example.com", "adminpassword")

    from eyerate.endpoints import ProviderError
    with patch("eyerate.plugin.get_financial_security_endpoint") as mock_ep_factory:
        mock_ep = AsyncMock()
        mock_ep.search.side_effect = ProviderError("Yahoo search HTTP 500")
        mock_ep_factory.return_value = mock_ep

        resp = client.get("/eyerate/securities/search?q=VOO")

    assert resp.status_code == 502
    body = resp.json()
    assert "lookup failed" in body["detail"]
    # Must NOT be a silent empty list — caller can distinguish failure from no results
    assert not isinstance(body, list)


def test_securities_search_genuine_empty_returns_200_empty_list(client, test_admin, db):
    """Genuine zero results → 200 with empty list (not an error)."""
    init_db(db)
    _login(client, "admin@example.com", "adminpassword")

    with patch("eyerate.plugin.get_financial_security_endpoint") as mock_ep_factory:
        mock_ep = AsyncMock()
        mock_ep.search.return_value = []
        mock_ep_factory.return_value = mock_ep

        resp = client.get("/eyerate/securities/search?q=ZZZNOMATCH")

    assert resp.status_code == 200
    assert resp.json() == []


def test_securities_search_error_and_empty_are_distinguishable(client, test_admin, db):
    """Provider error and genuine empty result are distinguishable at the HTTP level."""
    init_db(db)
    _login(client, "admin@example.com", "adminpassword")

    from eyerate.endpoints import ProviderError
    with patch("eyerate.plugin.get_financial_security_endpoint") as mock_ep_factory:
        mock_ep = AsyncMock()
        mock_ep.search.side_effect = ProviderError("dep import failed")
        mock_ep_factory.return_value = mock_ep
        error_resp = client.get("/eyerate/securities/search?q=VOO")

    with patch("eyerate.plugin.get_financial_security_endpoint") as mock_ep_factory:
        mock_ep = AsyncMock()
        mock_ep.search.return_value = []
        mock_ep_factory.return_value = mock_ep
        empty_resp = client.get("/eyerate/securities/search?q=ZZZNOMATCH")

    # Error must be 502; genuine empty must be 200 — the two states are never the same
    assert error_resp.status_code == 502
    assert empty_resp.status_code == 200
    assert error_resp.status_code != empty_resp.status_code


def test_securities_lookup_provider_error_returns_502_not_404(client, test_admin, db):
    """Provider failure on lookup → 502, NOT 404 (failure ≠ symbol not found)."""
    init_db(db)
    _login(client, "admin@example.com", "adminpassword")

    from eyerate.endpoints import ProviderError
    with patch("eyerate.plugin.get_financial_security_endpoint") as mock_ep_factory:
        mock_ep = AsyncMock()
        mock_ep.lookup.side_effect = ProviderError("yfinance not importable in frozen app")
        mock_ep_factory.return_value = mock_ep

        resp = client.get("/eyerate/securities/lookup?symbol=VOO")

    assert resp.status_code == 502
    body = resp.json()
    assert "lookup failed" in body["detail"]
    # 502 (provider failed) is distinct from 404 (symbol not found)
    assert resp.status_code != 404


def test_securities_lookup_not_found_returns_404(client, test_admin, db):
    """Genuine 'symbol not found' (provider returns None) → 404, not 502."""
    init_db(db)
    _login(client, "admin@example.com", "adminpassword")

    with patch("eyerate.plugin.get_financial_security_endpoint") as mock_ep_factory:
        mock_ep = AsyncMock()
        mock_ep.lookup.return_value = None
        mock_ep_factory.return_value = mock_ep

        resp = client.get("/eyerate/securities/lookup?symbol=FAKE")

    assert resp.status_code == 404
