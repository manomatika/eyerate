**EyeRate** | Version: **v0.0.4** | Copyright (c) 2026 Patrick James Tallman

# Changelog

All notable changes to EyeRate are documented here.

---

## [0.0.4-rc.1] — 2026-06-17

First release candidate for v0.0.4, part of the **ManoMatika v0.0.1** product
cut. Published as a GitHub prerelease for QA validation. Version core `0.0.4`;
`-rc.1` is a pre-release marker only.

### Added
- Release pipeline mirroring matika: `scripts/sync_version.py` propagates
  `version` + `matika_version` (resolved from the `../matika` sibling or
  `MATIKA_VERSION`) into `applug.json`; `scripts/release.py`; read-only `--check`
  drift detection and `--json` output.
- Strict SemVer parser mirroring matika's canonical block (`version_core`,
  `is_prerelease`); fail-loud, with a hard error when matika's `VERSION` is
  unavailable.
- npm consumption of matika's frontend via the `@manomatika/matika-frontend` bare
  specifier (build-time type checking; runtime via matika's import map).
- TypeScript source reorganized into `ts/` subdirectories with kebab-case
  filenames; `tsconfig.json` + `package.json` build setup.
- Tag-triggered notes-only GitHub Release job (`release.yml`) sourcing its body
  from `docs/release-notes/<tag>.md`; pre-release tags flagged `--prerelease`.
- Husky pre-commit hook + CI staleness check for compiled TypeScript assets.

### Changed
- Test suite split into stack-independent `tests/scripts/` and stack-coupled
  `tests/integration/` tiers; integration suite self-sufficient in clean
  checkouts.
- Cleanup & Tooling: Node-20 bump; DEVELOPER_GUIDE schema; USER_GUIDE menu naming.
- Propagated `0.0.4` baseline into `applug.json`.
- `sync_version --check` human output uses double-quoted values (matches matika).
- Extended `.gitignore` to the standard Python template + OS/IDE noise.
- Refreshed CLAUDE.md and docs for the 3-repo ManoMatika product architecture and
  the version ladder.

### Fixed
- Static asset 404: mount EyeRate static at `/eyerate/static` (not
  `/static/eyerate`); added a regression test.
- Unified the financial security field name on `financial_security_type` end to
  end.
- Lowercase GitHub slug references (`manomatika/matika`, `manomatika/eyerate`).

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
