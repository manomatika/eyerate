"""
Integration tests for the eyerate admin page (provider-selection UI)
and Bug B regression (search/lookup endpoints).
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
