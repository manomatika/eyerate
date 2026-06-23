# Release Pipeline

> Back-reference: this file holds the full release-pipeline detail
> that was previously inline in `CLAUDE.md` (`## Release Pipeline`).

## Version Source of Truth

`VERSION` is the single source of truth for version metadata. Never hand-edit version literals in any other file (`applug.json`, etc.) — the release tooling propagates from `VERSION`.

A version is a **CORE** (`X.Y.Z`) plus an optional SemVer-valid **pre-release suffix** on the ladder `X.Y.Z-dev < X.Y.Z-rc.N < X.Y.Z` (final). The suffix is a human/audit marker only — it lives on the `VERSION` file string, git tags, GitHub release titles/bodies, and the audit log. Anything that **compares** versions, **names** an artifact, or **embeds** a version into a manifest/installer field strips to **bare core** first (everything before the first `-`, via the shared `version_core` helper). Propagated manifest fields (`applug.json`) always hold bare core (e.g. `0.0.4`), never a suffix.

## Release Scripts

- `scripts/release.py <version>` is the release entry point. It accepts a final core (`0.0.4`) or a pre-release target (`0.0.4-rc.1`, `0.0.4-dev`): it verifies `VERSION`'s **core** matches the target's core, writes the target string (suffix and all) into `VERSION`, runs `sync_version.py` (which writes **bare core** into `applug.json`), runs the drift pre-flight check, and commits. Does **not** push, tag, or create a GitHub release — those steps are manual, after human review.
- `scripts/sync_version.py` propagates `VERSION` into `applug.json`: `"version"` from this repo's `VERSION`; `"matika_version"` from matika's `VERSION` (resolved via sibling clone at `../matika` or `MATIKA_VERSION` env var). When adding a new file with a version literal, add it to the script's allowlist.

## SemVer Parser

The canonical SemVer 2.0.0 parser — `_parse_semver`, with `version_core` and `is_prerelease` built on it — is the version source of truth. The authoritative copy lives in matika `src/matika/core/paths.py`; because `sync_version.py` cannot import the installed matika package, it carries a **verbatim, identical mirror** of that block. Any change to matika's parser MUST be mirrored here (matika's own `scripts/sync_version.py` mirrors the same block). The parser is **fail-loud**: any non-SemVer input — and any missing/unreadable/malformed `VERSION` — raises a `ValueError` naming the offending value and exits non-zero. There is no `"unknown"` sentinel and no silent garbage propagation.

If matika's `VERSION` is unavailable (sibling clone absent and env var unset), `sync_version.py` exits 2 with a clear error. This is a hard error, not a warning — eyerate cannot be drift-checked or released without matika's version.

## Drift Detection

`scripts/sync_version.py --check` runs in read-only drift detection mode. Exits 0 (clean), 1 (drift), 2 (configuration error). Human drift output uses double quotes around values (e.g. `DRIFT  applug.json: expected version "0.0.4", found "0.0.3"`). `--check --json` produces structured output: `{"version": "...", "drift": [{"path": "...", "field": "version"|"matika_version", "expected": "...", "found": "..."}]}`. Each drifted field in `applug.json` appears as a separate drift entry. An empty `drift` array (`[]`) means clean.

## GitHub Release Notes (notes-only)

eyerate has a tag-triggered release job (`.github/workflows/release.yml`, triggers on `v*.*.*` / `v*.*.*-*`, `contents: write`) that creates a GitHub Release whose body is read from `docs/release-notes/<tag>.md`, with a minimal auto-generated fallback body if no per-tag file exists (Q3 fallback). A tag carrying a pre-release suffix (`v*-*`, e.g. `v0.0.4-dev` / `v0.0.4-rc.1`) is published with `--prerelease`; a bare-core tag (`v*.*.*` with no suffix) is published as a full release. eyerate ships **no installer artifacts of its own** — the DMG/EXE are built by the ahimsa engine, and the single hosted installer lives on the **manomatika/manomatika** product release; eyerate's notes link to it. Author `docs/release-notes/<tag>.md` in the same PR that finalizes the version.

The ecosystem-wide release log (`RELEASES.md`, generated from `release-log.yaml`) lives in **manomatika/manomatika**. eyerate's tag entries are records in that file (keyed `repo: eyerate`). eyerate has no `RELEASES.md` of its own.

Every tag — pre-release (`-dev`, `-rc.N`) and final alike — updates the per-tag documentation triad in lockstep: this repo's `CLAUDE.md` and `CHANGELOG.md` (in-repo), plus the ecosystem `RELEASES.md` record in **manomatika/manomatika**. Land all three in the same PR that finalizes the version.
