**EyeRate** | Version: **v0.0.2** | Copyright (c) 2026 Patrick James Tallman


































# EyeRate - Financial Security Plugin for Matika

EyeRate is a reference implementation of a Matika **AppLug** (plugin). it provides specialized functionality for tracking financial securities, fetching real-time market data, and calculating yields.

## Features

- **Security Maintenance:** CRUD operations for stocks, bonds, ETFs, and mutual funds.
- **Dynamic Data Sourcing:** Pluggable endpoint system supporting Yahoo Finance (scraper), Finnhub, and Alpha Vantage.
- **Bulk Operations:** Automated discovery and creation of securities via ticker symbols.
- **Permission Integration:** Pre-configured roles and permissions that hook into the Matika core RBAC.
- **Custom UI:** Specialized templates for financial data visualization.

## Installation into Matika

EyeRate is designed to be installed into a Matika host.

1. **Clone into Matika Plugins:**
   Navigate to your Matika installation and clone EyeRate into the `plugins/` directory:
   ```bash
   cd matika/plugins
   git clone https://github.com/pjtallman/eyerate.git eyerate
   ```

2. **Dependencies:**
   Ensure your Matika environment has the required dependencies:
   ```bash
   pip install yfinance curl_cffi beautifulsoup4
   ```

3. **Restart Matika:**
   Restart the Matika server. EyeRate will be automatically discovered and integrated.

## Plugin Structure

EyeRate demonstrates the standard Matika plugin layout:
- `applug.json`: Defines the plugin ID, entry point (`eyerate.plugin.EyeRatePlugin`), and required permissions.
- `eyerate_menu.json`: Adds the "Securities" maintenance page to Matika's "Activities" menu.
- `src/eyerate/`: Python package containing routers, models, and logic.
- `src/eyerate/templates/`: Jinja2 templates that are merged into the Matika template pool.

## Development

To run tests for EyeRate standalone (using the Matika test environment):
```bash
export PYTHONPATH=src:../matika/src
python -m pytest tests/
```

## Documentation
- [User Guide](USER_GUIDE.md)

## License
Copyright (c) 2026 Patrick James Tallman. All Rights Reserved.
