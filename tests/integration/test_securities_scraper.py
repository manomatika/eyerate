import pytest
from unittest.mock import patch, MagicMock
from eyerate.endpoints import YahooScraperEndpoint, FinnhubEndpoint, AlphaVantageEndpoint, ProviderError
from eyerate.error.error_codes import (
    EYERATE_PROV_001,
    EYERATE_PROV_002,
    EYERATE_PROV_003,
    EYERATE_PROV_004,
)
from eyerate.models import FinancialSecurityType as SecurityType, AssetClass

@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_yahoo_endpoint_search(mock_session):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "quotes": [
            {"symbol": "VOO", "shortname": "Vanguard S&P 500 ETF", "quoteType": "ETF", "exchange": "NYE"}
        ]
    }
    mock_session.return_value.__aenter__.return_value.get.return_value = mock_response

    endpoint = YahooScraperEndpoint()
    results = await endpoint.search("VOO")

    assert len(results) == 1
    assert results[0]["symbol"] == "VOO"
    assert results[0]["name"] == "Vanguard S&P 500 ETF"
    assert results[0]["type"] == "ETF"

@pytest.mark.asyncio
@patch("eyerate.endpoints.yf.Ticker")
async def test_yahoo_endpoint_lookup(mock_ticker):
    mock_ticker.return_value.info = {
        "symbol": "VOO",
        "longName": "Vanguard S&P 500 ETF",
        "quoteType": "ETF",
        "regularMarketPrice": 450.12,
        "regularMarketPreviousClose": 448.00,
        "regularMarketOpen": 449.00,
        "navPrice": 450.10,
        "fiftyTwoWeekRange": "380.00 - 460.00",
        "averageDailyVolume3Month": 3000000,
        "yield": 0.015
    }

    endpoint = YahooScraperEndpoint()
    data = await endpoint.lookup("VOO")

    assert data is not None
    assert data["symbol"] == "VOO"
    assert data["name"] == "Vanguard S&P 500 ETF"
    assert data["financial_security_type"] == SecurityType.ETF.value
    assert data["current_price"] == "450.12"
    assert data["yield_30_day"] == "0.015"


# ---------------------------------------------------------------------------
# ProviderError propagation — these would have caught Bug B's silent nature
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_yahoo_search_raises_provider_error_on_http_500(mock_session):
    """Non-200 status must raise ProviderError, not silently return []."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_session.return_value.__aenter__.return_value.get.return_value = mock_response

    endpoint = YahooScraperEndpoint()
    with pytest.raises(ProviderError, match="HTTP 500") as excinfo:
        await endpoint.search("VOO")
    assert excinfo.value.code == EYERATE_PROV_003


@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_yahoo_search_raises_provider_error_on_rate_limit(mock_session):
    """HTTP 429 must raise ProviderError, not silently return []."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_session.return_value.__aenter__.return_value.get.return_value = mock_response

    endpoint = YahooScraperEndpoint()
    with pytest.raises(ProviderError, match="rate limited") as excinfo:
        await endpoint.search("VOO")
    assert excinfo.value.code == EYERATE_PROV_002


@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_yahoo_search_200_empty_quotes_returns_empty_list(mock_session):
    """200 response with no quotes must return [] (genuine empty), not raise."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"quotes": []}
    mock_session.return_value.__aenter__.return_value.get.return_value = mock_response

    endpoint = YahooScraperEndpoint()
    # Use a query that won't trigger the ticker-fallback logic (contains a space)
    results = await endpoint.search("no match here")
    assert results == []


@pytest.mark.asyncio
@patch("eyerate.endpoints.yf.Ticker")
async def test_yahoo_lookup_raises_provider_error_on_exception(mock_ticker):
    """Exception in yfinance (e.g. ImportError in frozen app) must raise ProviderError."""
    mock_ticker.side_effect = ImportError("No module named 'yfinance'")

    endpoint = YahooScraperEndpoint()
    with pytest.raises(ProviderError, match="Yahoo lookup error") as excinfo:
        await endpoint.lookup("VOO")
    assert excinfo.value.code == EYERATE_PROV_004


@pytest.mark.asyncio
async def test_finnhub_search_raises_provider_error_on_missing_key():
    """Missing API key must raise ProviderError, not silently return []."""
    endpoint = FinnhubEndpoint(api_key="")
    with pytest.raises(ProviderError, match="API key") as excinfo:
        await endpoint.search("VOO")
    assert excinfo.value.code == EYERATE_PROV_001


@pytest.mark.asyncio
async def test_alphavantage_search_raises_provider_error_on_missing_key():
    """Missing API key must raise ProviderError, not silently return []."""
    endpoint = AlphaVantageEndpoint(api_key="")
    with pytest.raises(ProviderError, match="API key") as excinfo:
        await endpoint.search("VOO")
    assert excinfo.value.code == EYERATE_PROV_001


@pytest.mark.asyncio
async def test_finnhub_lookup_raises_provider_error_on_missing_key():
    """Missing API key must raise ProviderError, not silently return None."""
    endpoint = FinnhubEndpoint(api_key="")
    with pytest.raises(ProviderError, match="API key") as excinfo:
        await endpoint.lookup("VOO")
    assert excinfo.value.code == EYERATE_PROV_001


@pytest.mark.asyncio
async def test_alphavantage_lookup_raises_provider_error_on_missing_key():
    """Missing API key must raise ProviderError, not silently return None."""
    endpoint = AlphaVantageEndpoint(api_key="")
    with pytest.raises(ProviderError, match="API key") as excinfo:
        await endpoint.lookup("VOO")
    assert excinfo.value.code == EYERATE_PROV_001


# ---------------------------------------------------------------------------
# R4 (manomatika/eyerate#77): ProviderError.code coverage for every remaining
# raise site not already exercised above. Each asserts the exact
# EYERATE-PROV-NNN code threaded through that specific failure path.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_yahoo_search_raises_provider_error_on_unexpected_exception(mock_session):
    """A non-HTTP exception during search (e.g. connection reset) must carry PROV-004."""
    mock_session.return_value.__aenter__.side_effect = RuntimeError("connection reset")

    endpoint = YahooScraperEndpoint()
    with pytest.raises(ProviderError, match="Yahoo search error") as excinfo:
        await endpoint.search("VOO")
    assert excinfo.value.code == EYERATE_PROV_004


@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_finnhub_search_raises_provider_error_on_rate_limit(mock_session):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_session.return_value.__aenter__.return_value.get.return_value = mock_response

    endpoint = FinnhubEndpoint(api_key="key")
    with pytest.raises(ProviderError, match="rate limited") as excinfo:
        await endpoint.search("VOO")
    assert excinfo.value.code == EYERATE_PROV_002


@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_finnhub_search_raises_provider_error_on_http_error(mock_session):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_session.return_value.__aenter__.return_value.get.return_value = mock_response

    endpoint = FinnhubEndpoint(api_key="key")
    with pytest.raises(ProviderError, match="HTTP 500") as excinfo:
        await endpoint.search("VOO")
    assert excinfo.value.code == EYERATE_PROV_003


@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_finnhub_search_raises_provider_error_on_unexpected_exception(mock_session):
    mock_session.return_value.__aenter__.side_effect = RuntimeError("connection reset")

    endpoint = FinnhubEndpoint(api_key="key")
    with pytest.raises(ProviderError, match="Finnhub search error") as excinfo:
        await endpoint.search("VOO")
    assert excinfo.value.code == EYERATE_PROV_004


@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_finnhub_lookup_raises_provider_error_on_rate_limit(mock_session):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_session.return_value.__aenter__.return_value.get.return_value = mock_response

    endpoint = FinnhubEndpoint(api_key="key")
    with pytest.raises(ProviderError, match="rate limited") as excinfo:
        await endpoint.lookup("VOO")
    assert excinfo.value.code == EYERATE_PROV_002


@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_finnhub_lookup_raises_provider_error_on_quote_http_error(mock_session):
    q_resp = MagicMock(); q_resp.status_code = 500
    p_resp = MagicMock(); p_resp.status_code = 200
    mock_session.return_value.__aenter__.return_value.get.side_effect = [q_resp, p_resp]

    endpoint = FinnhubEndpoint(api_key="key")
    with pytest.raises(ProviderError, match="Finnhub quote HTTP 500") as excinfo:
        await endpoint.lookup("VOO")
    assert excinfo.value.code == EYERATE_PROV_003


@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_finnhub_lookup_raises_provider_error_on_profile_http_error(mock_session):
    q_resp = MagicMock(); q_resp.status_code = 200
    p_resp = MagicMock(); p_resp.status_code = 500
    mock_session.return_value.__aenter__.return_value.get.side_effect = [q_resp, p_resp]

    endpoint = FinnhubEndpoint(api_key="key")
    with pytest.raises(ProviderError, match="Finnhub profile HTTP 500") as excinfo:
        await endpoint.lookup("VOO")
    assert excinfo.value.code == EYERATE_PROV_003


@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_finnhub_lookup_raises_provider_error_on_unexpected_exception(mock_session):
    mock_session.return_value.__aenter__.side_effect = RuntimeError("connection reset")

    endpoint = FinnhubEndpoint(api_key="key")
    with pytest.raises(ProviderError, match="Finnhub lookup error") as excinfo:
        await endpoint.lookup("VOO")
    assert excinfo.value.code == EYERATE_PROV_004


@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_alphavantage_search_raises_provider_error_on_http_error(mock_session):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_session.return_value.__aenter__.return_value.get.return_value = mock_response

    endpoint = AlphaVantageEndpoint(api_key="key")
    with pytest.raises(ProviderError, match="HTTP 500") as excinfo:
        await endpoint.search("VOO")
    assert excinfo.value.code == EYERATE_PROV_003


@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_alphavantage_search_raises_provider_error_on_rate_limit(mock_session):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"Note": "Thank you for using Alpha Vantage! ..."}
    mock_session.return_value.__aenter__.return_value.get.return_value = mock_response

    endpoint = AlphaVantageEndpoint(api_key="key")
    with pytest.raises(ProviderError, match="rate limited") as excinfo:
        await endpoint.search("VOO")
    assert excinfo.value.code == EYERATE_PROV_002


@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_alphavantage_search_raises_provider_error_on_unexpected_exception(mock_session):
    mock_session.return_value.__aenter__.side_effect = RuntimeError("connection reset")

    endpoint = AlphaVantageEndpoint(api_key="key")
    with pytest.raises(ProviderError, match="Alpha Vantage search error") as excinfo:
        await endpoint.search("VOO")
    assert excinfo.value.code == EYERATE_PROV_004


@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_alphavantage_lookup_raises_provider_error_on_http_error(mock_session):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_session.return_value.__aenter__.return_value.get.return_value = mock_response

    endpoint = AlphaVantageEndpoint(api_key="key")
    with pytest.raises(ProviderError, match="HTTP 500") as excinfo:
        await endpoint.lookup("VOO")
    assert excinfo.value.code == EYERATE_PROV_003


@pytest.mark.asyncio
@patch("eyerate.endpoints.AsyncSession")
async def test_alphavantage_lookup_raises_provider_error_on_unexpected_exception(mock_session):
    mock_session.return_value.__aenter__.side_effect = RuntimeError("connection reset")

    endpoint = AlphaVantageEndpoint(api_key="key")
    with pytest.raises(ProviderError, match="Alpha Vantage lookup error") as excinfo:
        await endpoint.lookup("VOO")
    assert excinfo.value.code == EYERATE_PROV_004


def test_provider_error_requires_a_well_formed_code():
    """Constructing ProviderError with a code that isn't <COMPONENT>-<FAC>-<NNN>
    must fail loud (rule 18) — this is what makes ProviderError.code trustworthy
    as a machine carrier rather than an arbitrary string."""
    with pytest.raises(ValueError, match="well-formed"):
        ProviderError("not-a-real-code", "boom")
