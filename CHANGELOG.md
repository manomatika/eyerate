**EyeRate** | Version: **v0.0.4** | Copyright (c) 2026 Patrick James Tallman

# Changelog

All notable changes to EyeRate are documented here.

---

## [Unreleased / 0.0.4-dev]

### Added
- *(nothing yet)*

---

## [0.0.2] — 2026-04-27

### Compatibility Contract

First version under Matika's formal compatibility contract.

#### Added
- `matika_version` field in `applug.json` declaring compatibility with
  Matika 0.0.2 exactly. Replaces the informal `matika_version_min` field.
- `tests/conftest.py` patches `matika_version` in the copied applug.json
  at test-setup time, keeping tests green across Matika development versions
  without changing the declared compatibility target in applug.json.

#### Changed
- Removed informal `matika_version_min` field (superseded by `matika_version`).
