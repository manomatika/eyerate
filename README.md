**EyeRate** | Version: **v0.0.4** | Copyright (c) 2026 Patrick James Tallman

# EyeRate — Financial Security AppLug for Matika

EyeRate is the **reference implementation** of a Matika [AppLug](https://github.com/manomatika/Matika) (plugin). It provides specialised functionality for tracking financial securities, fetching real-time market data, and calculating yields. It is not a standalone application — it runs inside a Matika host process.

## Features

- **Security Maintenance:** CRUD operations for stocks, bonds, ETFs, and mutual funds.
- **Dynamic Data Sourcing:** Pluggable endpoint system supporting Yahoo Finance (scraper), Finnhub, and Alpha Vantage.
- **Bulk Operations:** Automated discovery and creation of securities via ticker symbols.
- **Permission Integration:** Pre-configured roles and permissions that hook into the Matika core RBAC.
- **Custom UI:** Specialised templates for financial data visualisation, extending Matika's `MaintenanceActivityManager` frontend base class.

## Installation into Matika

EyeRate is designed to run inside a Matika host. There are three injection patterns, depending on context.

### Local development (sibling-repo + symlink — recommended)

Clone matika and eyerate as siblings, then have matika create a symlink into its `plugins/` directory.

```bash
# 1. Clone eyerate alongside matika
cd ~/dev/projects
git clone https://github.com/manomatika/EyeRate.git eyerate

# 2. Tell matika where the plugin lives (one-time per machine)
cd matika
cp plugins.dev.json.example plugins.dev.json
# Edit plugins.dev.json:  { "plugins": ["../eyerate"] }
python scripts/dev_setup.py     # creates plugins/eyerate → ../eyerate symlink
```

`scripts/dev_setup.py` is idempotent and validates each path contains `applug.json` and a `*_menus.json` (plural — the consolidated AppLug menu format) before creating the symlink.

For the full cold-start sequence (venv activation, env vars, server launch, browser test URL), see matika's [DEVELOPER_GUIDE.md](https://github.com/manomatika/Matika/blob/main/docs/DEVELOPER_GUIDE.md).

### Production deployment

Set `MATIKA_PLUGINS_DIR` in the server's environment to a directory outside the core repository that contains your licensed AppLugs (each as a subdirectory). Matika picks this up at startup. See matika's [DEPLOYMENT.md](https://github.com/manomatika/Matika/blob/main/docs/DEPLOYMENT.md) for the full operator guide.

### End-user installer (future)

A standalone `.dmg` / `.exe` built with PyInstaller bundles the framework and selected applugs. No Python environment required. See ahimsa for the build pipeline.

## Dependencies

EyeRate's Python dependencies (yfinance, curl_cffi, beautifulsoup4) are declared in `requirements.txt`. Install from the eyerate clone:

```bash
pip install -r requirements.txt
```

These are eyerate-specific and intentionally not in matika's `requirements.txt` (matika is plugin-agnostic and ships no domain-specific dependencies).

## Plugin Structure

EyeRate demonstrates the standard Matika plugin layout:
- `applug.json` — manifest: plugin id (`eyerate`), version, `matika_version`, entry point (`eyerate.plugin.EyeRatePlugin`), permissions.
- `eyerate_menus.json` — consolidated menu file (plural, schema v1.0): `application` section drives the EyeRate Application hub; `roles` sections drive per-role hubs.
- `src/eyerate/` — Python package containing routes, models, endpoints, and the plugin entry class.
- `src/eyerate/templates/` — Jinja2 templates merged into matika's template pool at startup.
- `src/eyerate/ts/` — TypeScript source; compiled to `src/eyerate/static/js/` (committed to git per repo convention; rerun `npm run build` after editing `.ts` files).

### Frontend consumption of matika

EyeRate's frontend imports matika's TypeScript base classes via the npm bare specifier:

```typescript
import { MaintenanceActivityManager, ActivityMetadata } from '@manomatika/matika-frontend';
```

At runtime, matika's `base.html` ships an `<script type="importmap">` that resolves `@manomatika/matika-frontend` to `/static/js/index.js` (served from matika's own static directory). No npm install of the package is required to run — the bare specifier resolves browser-side via the import map. The npm package (`@manomatika/matika-frontend` on GitHub Packages) is consumed at build time for TypeScript type checking.

## Development

Run tests against the matika test environment (requires `../matika` as a sibling directory):

```bash
export PYTHONPATH=src:../matika/src
python -m pytest tests/
```

See `CLAUDE.md` for the full test layout and tier-isolation convention.

## Documentation
- [User Guide](docs/USER_GUIDE.md)

## License
Copyright (c) 2026 Patrick James Tallman. All Rights Reserved.
