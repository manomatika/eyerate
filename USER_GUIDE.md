**EyeRate** | Version: **v0.0.2** | Copyright (c) 2026 Patrick James Tallman


































# EyeRate User Guide

This guide provides instructions on how to use the EyeRate financial tracking features within the Matika framework.

## 1. Accessing EyeRate
Once EyeRate is installed into Matika, it adds new capabilities to your dashboard:
- **Securities Maintenance:** Found under the **Activities** menu.
- **Provider Settings:** Found under **User Settings** (if you have permission).

## 2. Managing Securities
The Securities page allows you to track specific financial instruments.

### Adding a Security
1. Click the **"New Security"** button.
2. Enter the **Ticker Symbol** (e.g., VOO, AAPL).
3. Provide a descriptive name.
4. Select the **Security Type** (Stock, ETF, etc.) and **Asset Class**.
5. Click **Save**.

### Bulk Discovery
Instead of manual entry, use the **Search/Lookup** field:
1. Type a symbol and click **Lookup**.
2. EyeRate will fetch metadata (Name, Current Price, Yield) from the configured data provider.
3. Review and save the results.

## 3. Data Providers
EyeRate supports multiple market data sources. You can switch between them in the settings panel.

- **Yahoo Standard:** No API key required. Uses scraping logic to fetch daily quotes and yields.
- **Finnhub / Alpha Vantage:** Requires an API key from the respective provider. Offers more robust data for high-frequency tracking.

## 4. Troubleshooting
- **No Data Found:** Verify that the ticker symbol is correct and that your internet connection is active.
- **Permission Denied:** Ensure your Matika user has been assigned a role with "FULL" access to the `/admin/securities` path.
- **Yields Not Updating:** Some providers may lag in reporting yields for specific ETFs or Mutual Funds. Switching providers may resolve this.

## 5. Developer Support
EyeRate is open-source. For technical issues or feature requests, please visit the GitHub repository.
