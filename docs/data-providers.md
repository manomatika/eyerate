# Data Providers

> Back-reference: this file holds the full data-provider and provider-error-contract detail
> that was previously inline in `CLAUDE.md` (`## Architecture` → `### Data Providers`).

## Active Provider Resolution

The active provider is resolved per-request in `plugin.py` `get_financial_security_endpoint(db)` from two Matika system settings: `financial_security_data_endpoint` (`yahoo` default / `finnhub` / `alphavantage`) and `financial_security_data_api_key` (fed to Finnhub/Alpha Vantage). All providers implement `BaseFinancialSecurityEndpoint` with async `search()`, `lookup()`, and `get_name()`:

- **YahooScraperEndpoint** (default) — `curl_cffi` for search, `yfinance` for lookup; `get_name()` → `"Matika Standard (Yahoo Scraper)"`
- **FinnhubEndpoint** — requires `financial_security_data_api_key`
- **AlphaVantageEndpoint** — requires `financial_security_data_api_key`

## Provider Error Contract (load-bearing — no silent empties)

A `ProviderError` exception distinguishes a genuine zero-result from a failed call:

- An empty list / `None` means "the provider succeeded and found nothing."
- A **`ProviderError`** means the call itself failed (rate-limit, non-200, missing API key, transport error). Every provider wraps its failure modes (`except Exception as e: raise ProviderError(...)`) so failures never leak out as a silent empty result.
- `routes.py` translates `ProviderError` into **HTTP 502** with a `detail` body (`f"lookup failed: {e}"`) on both `search` and `lookup`; a genuine `None` from `lookup` maps to **HTTP 404**. The error is surfaced LOUDLY in the UI, never swallowed. This contract (and the admin UI below) is verified against the frozen artifact by ahimsa's tier-a/tier-b checks (forced keyless `finnhub` → visible HTTP 502, not an empty list).

## Admin Provider-Selection UI

Beyond the declarative `settings_ui` schema in `applug.json`, eyerate serves a rendered admin page at `/eyerate/admin` (`routes.py` `eyerate_admin` GET + `eyerate_admin_save` POST, CSRF-protected via `validate_csrf`), template `templates/eyerate_admin.html` — three provider radios (`yahoo`/`finnhub`/`alphavantage`) plus an API-key input, persisted to `SystemSetting` rows.
