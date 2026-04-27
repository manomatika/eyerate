**EyeRate** | Version: **0.0.1** | Copyright (c) 2026 Patrick James Tallman

# Changelog

All notable changes to EyeRate are documented here.

---

## [Unreleased / 0.0.2_dev]

### Added
- *(nothing yet)*

---

## [0.0.1] — 2026-04-27

### First Formal Release

#### Added
- `matika_version` field in `applug.json` declaring compatibility with
  Matika 0.0.2. Replaces the informal `matika_version_min` field.
  EyeRate 0.0.1 is built and tested against Matika 0.0.2 exactly.
- `VERSION` file established at 0.0.1 as the baseline for EyeRate's
  own version tracking, independent of Matika's version.
- `tests/conftest.py` updated to patch `matika_version` in the copied
  applug.json at test-setup time, so tests stay green across Matika
  development versions without changing the declared compatibility target.

#### Changed
- `applug.json` `version` field set to `0.0.1` (aligned with VERSION file).
- Removed informal `matika_version_min` field (superseded by `matika_version`).
