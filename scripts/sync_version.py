"""
sync_version.py — propagates canonical version data from VERSION files into all
version-bearing files in the eyerate working tree.

Propagation targets (allowlist):
  applug.json  — "version"        (from eyerate's own VERSION file)
  applug.json  — "matika_version" (from matika's VERSION file)

Version CORE vs PRE-RELEASE SUFFIX
----------------------------------
A version is CORE (X.Y.Z) plus an optional SemVer-valid PRE-RELEASE SUFFIX
(-dev, -rc.N). The suffix lives only on human/audit surfaces — the VERSION
file string, git tags, GitHub release titles/bodies, the audit log.

Anything that COMPARES versions, NAMES an artifact, or EMBEDS a version into a
manifest/installer field must strip to BARE CORE first: everything before the
first "-" (see strip_to_core). applug.json "version" and "matika_version" are
manifest pins consumed by ahimsa's resolver cross-check, so they ALWAYS hold
bare core — never a pre-release suffix. matika_version is the matika FRAMEWORK
compatibility pin; the name is intentional and is not renamed.

Supported pre-release ladder: X.Y.Z-dev < X.Y.Z-rc.N < X.Y.Z (final).
VERSION files themselves are never modified by this script.

matika_version source (checked in priority order):
  1. <sibling clone>/matika/VERSION   (~/dev/projects/matika/VERSION by convention)
  2. MATIKA_VERSION environment variable
  If neither is available the script exits with code 2 (configuration error)
  in both propagation and --check mode.

Usage:
  python scripts/sync_version.py                # propagate (write files)
  python scripts/sync_version.py --check        # read-only drift check, human output
  python scripts/sync_version.py --check --json # read-only drift check, JSON output
"""

import argparse
import json
import os
import re as _re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

# Sibling matika clone — standard layout: ~/dev/projects/{matika,eyerate}
MATIKA_REPO_ROOT = REPO_ROOT.parent / "matika"

# Every file this script touches. drift_check() verifies exactly these fields.
SYNC_TARGETS: list[tuple[str, str]] = [
    ("applug.json", 'applug.json "version" + "matika_version"'),
]


# ===========================================================================
# CANONICAL SEMVER PARSER
#
# _parse_semver is the SINGLE strict SemVer 2.0.0 parser for this script.
# strip_to_core() and is_prerelease() both build on it so there is exactly ONE
# parser. sync_version.py cannot import the installed matika package, so this
# parser is an IDENTICAL, verbatim copy of matika.core.paths._parse_semver
# (same parse rules, same error-message shape). Any change to matika's parser
# MUST be mirrored here. matika's own scripts/sync_version.py mirrors the same
# block for its build/release tooling.
# ===========================================================================

# MAJOR.MINOR.PATCH: each a non-negative integer with NO leading zeros.
_SEMVER_CORE = r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
# A pre-release identifier: numeric (no leading zeros) OR alphanumeric-with-hyphen.
_SEMVER_PRE_IDENT = r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
# Dot-separated pre-release identifiers, after the first '-'.
_SEMVER_PRERELEASE = rf"(?:{_SEMVER_PRE_IDENT}(?:\.{_SEMVER_PRE_IDENT})*)"
# Build metadata: dot-separated alphanumeric-with-hyphen identifiers, after '+'.
_SEMVER_BUILD = r"(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)"

_SEMVER_RE = _re.compile(
    rf"^(?P<core>{_SEMVER_CORE})"
    rf"(?:-(?P<prerelease>{_SEMVER_PRERELEASE}))?"
    rf"(?:\+(?P<build>{_SEMVER_BUILD}))?$"
)


def _parse_semver(raw):
    """Strictly parse a SemVer 2.0.0 string of the form
    ``[v]MAJOR.MINOR.PATCH[-prerelease][+build]``.

    A single optional leading 'v' is tolerated and stripped. MAJOR/MINOR/PATCH
    are non-negative integers with no leading zeros (so '01.2.3' is invalid),
    exactly three of them. Pre-release identifiers are dot-separated; numeric
    identifiers carry no leading zeros; identifiers are alphanumerics and hyphens
    (so a pre-release identifier MAY contain hyphens, e.g. 'alpha-1'). Build
    metadata after '+' is NOT part of the core and is NOT a pre-release signal.
    An empty pre-release ('1.2.3-') or empty build is invalid.

    Returns ``(core, prerelease, build)`` where prerelease/build are the
    substrings after '-'/'+' or None when absent. Raises ValueError naming the
    offending value and the expected shape on any invalid input.
    """
    if not isinstance(raw, str):
        raise ValueError(
            f"invalid version {raw!r}: expected a string of the form "
            f"[v]MAJOR.MINOR.PATCH[-prerelease][+build]"
        )
    candidate = raw.strip()
    if candidate.startswith("v"):
        candidate = candidate[1:]
    m = _SEMVER_RE.match(candidate)
    if not m:
        raise ValueError(
            f"invalid version {raw!r}: expected SemVer of the form "
            f"[v]MAJOR.MINOR.PATCH[-prerelease][+build] "
            f"(three dot-separated non-negative integers without leading zeros, "
            f"optional pre-release and build metadata)"
        )
    return m.group("core"), m.group("prerelease"), m.group("build")


def strip_to_core(version: str) -> str:
    """Return the bare MAJOR.MINOR.PATCH core of a SemVer string.

    The single shared "strip to core" helper, built on the canonical
    _parse_semver. A pre-release suffix (-dev, -rc.N) and build metadata (+...)
    are dropped; a bare core is returned unchanged. This is the canonical
    identity used for ALL comparison, artifact naming, and manifest/installer
    embedding (applug.json "version" + "matika_version").

    Examples:
      "0.0.4-dev"        -> "0.0.4"
      "0.0.4-rc.1"       -> "0.0.4"
      "v0.0.4-rc.1"      -> "0.0.4"
      "0.0.4+build.5"    -> "0.0.4"
      "1.2.3-alpha-1"    -> "1.2.3"
      "0.0.4"            -> "0.0.4"

    Raises ValueError (naming the offending value) on any non-SemVer input.
    """
    core, _prerelease, _build = _parse_semver(version)
    return core


def is_prerelease(version: str) -> bool:
    """True iff a SemVer string carries a pre-release component.

    Build metadata alone (e.g. ``0.0.4+build``) is NOT a pre-release. Raises
    ValueError (naming the offending value) on any non-SemVer input.
    """
    _core, prerelease, _build = _parse_semver(version)
    return prerelease is not None


def read_version() -> tuple[str, str]:
    """Return (raw, clean) for eyerate's VERSION. clean is the bare core.

    RULE B: a missing/unreadable/malformed VERSION raises with full context —
    WHICH file, the bad value, and the expected shape. There is NO "unknown"
    sentinel and no silent garbage propagation: an invalid VERSION is a serious
    bug and must surface at its real source.
    """
    version_file = REPO_ROOT / "VERSION"
    try:
        raw = version_file.read_text().strip()
    except OSError as exc:
        print(
            f"ERROR: eyerate VERSION file missing or unreadable at "
            f"{version_file}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        clean = strip_to_core(raw)
    except ValueError as exc:
        print(
            f"ERROR: eyerate VERSION file {version_file} holds an invalid "
            f"version: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    return raw, clean


def _try_read_matika_version() -> str | None:
    """Return clean matika version, or None if no source is available (no exit).

    RULE B: a source that EXISTS but holds a malformed value raises with full
    context (WHICH source, the bad value, the expected shape) rather than being
    treated as "unavailable" — only a genuinely absent source returns None so
    the caller can emit its configuration-error guidance.
    """
    matika_version_file = MATIKA_REPO_ROOT / "VERSION"
    if matika_version_file.exists():
        raw = matika_version_file.read_text().strip()
        try:
            return strip_to_core(raw)
        except ValueError as exc:
            print(
                f"ERROR: matika VERSION file {matika_version_file} holds an "
                f"invalid version: {exc}",
                file=sys.stderr,
            )
            sys.exit(2)
    env_val = os.environ.get("MATIKA_VERSION", "").strip()
    if env_val:
        try:
            return strip_to_core(env_val)
        except ValueError as exc:
            print(
                f"ERROR: MATIKA_VERSION environment variable holds an invalid "
                f"version: {exc}",
                file=sys.stderr,
            )
            sys.exit(2)
    return None


def read_matika_version() -> str:
    """Return clean matika version. Exit 2 (configuration error) if unavailable."""
    result = _try_read_matika_version()
    if result is not None:
        return result
    print(
        "ERROR: cannot verify matika_version — matika's VERSION file not found\n"
        f"  Looked for: {MATIKA_REPO_ROOT / 'VERSION'}\n"
        "  MATIKA_VERSION env var: not set\n"
        f"  Either clone matika as a sibling directory or set MATIKA_VERSION=<version>",
        file=sys.stderr,
    )
    sys.exit(2)


# ---------------------------------------------------------------------------
# Core: propagate or check (single code path, branches only at write step)
# ---------------------------------------------------------------------------

def sync(check_only: bool = False, quiet: bool = False) -> list:
    """
    Propagate VERSION (and matika VERSION) to all targets (check_only=False),
    or compare without writing (check_only=True).

    Returns:
      Normal mode  — list[str]  of relative paths that were written.
      Check mode   — list[dict] of drift entries:
                     {"path", "field", "expected", "found"} per drifted field.
                     Empty list means clean.

    quiet=True suppresses all print output (use for JSON consumers).

    Exits 2 (configuration error) if matika's VERSION is unavailable in either
    mode — a check that silently skips matika_version is dangerously incomplete.
    In check mode VERSION may carry a pre-release suffix (-dev, -rc.N); the
    bare core is what targets are compared against (same as propagation — no
    special failure for a pre-release suffix).
    """
    raw, clean = read_version()
    matika_version: str = read_matika_version()  # exits 2 if unavailable

    if not quiet:
        action = "--check: checking against" if check_only else f"{raw!r} → propagating"
        print(f"sync_version {action} eyerate {clean!r},  matika_version → {matika_version!r}")

    affected: list = []

    applug = REPO_ROOT / "applug.json"
    if applug.exists():
        rel = str(applug.relative_to(REPO_ROOT))
        data = json.loads(applug.read_text())

        if check_only:
            any_drift = False

            found_version = data.get("version", "<not found>")
            if found_version != clean:
                if not quiet:
                    print(f'DRIFT  {rel}: expected version "{clean}", found "{found_version}"')
                affected.append(
                    {"path": rel, "field": "version", "expected": clean, "found": found_version}
                )
                any_drift = True

            found_matika = data.get("matika_version", "<not found>")
            if found_matika != matika_version:
                if not quiet:
                    print(
                        f'DRIFT  {rel}: expected matika_version "{matika_version}", '
                        f'found "{found_matika}"'
                    )
                affected.append(
                    {
                        "path": rel,
                        "field": "matika_version",
                        "expected": matika_version,
                        "found": found_matika,
                    }
                )
                any_drift = True

            if not any_drift and not quiet:
                print(f"  OK       {rel}")
        else:
            changed = (
                data.get("version") != clean
                or data.get("matika_version") != matika_version
            )
            if changed:
                data["version"] = clean
                data["matika_version"] = matika_version
                applug.write_text(json.dumps(data, indent=4) + "\n")
                if not quiet:
                    print(f"  UPDATED  {rel}")
                affected.append(rel)
            else:
                if not quiet:
                    print(f"  OK       {rel}")
    else:
        if not quiet:
            print("  SKIP    applug.json (not found)")

    return affected


def drift_check(expected_version: str, expected_matika_version: str) -> None:
    """
    Verify applug.json holds exactly expected_version and expected_matika_version
    (both bare core). Exit 1 on any mismatch. Also fails if eyerate VERSION still
    carries a pre-release suffix (-dev, -rc.N), which means a final release was
    not finalized before the drift check.

    Note: release.py uses sync(check_only=True) as its drift gate instead of
    calling this directly. This function is retained for standalone use.
    """
    version_file = REPO_ROOT / "VERSION"
    try:
        raw = version_file.read_text().strip()
    except OSError as exc:
        print(
            f"DRIFT: eyerate VERSION file missing or unreadable at "
            f"{version_file}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        prerelease = is_prerelease(raw)
    except ValueError as exc:
        print(
            f"DRIFT: eyerate VERSION file {version_file} holds an invalid "
            f"version: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    if prerelease:
        print(
            f"DRIFT: VERSION is {raw!r} — pre-release suffix must be removed "
            "before drift check",
            file=sys.stderr,
        )
        sys.exit(1)

    errors: list[str] = []

    applug = REPO_ROOT / "applug.json"
    if applug.exists():
        data = json.loads(applug.read_text())
        found_version = data.get("version", "<not found>")
        found_matika = data.get("matika_version", "<not found>")
        if found_version != expected_version:
            errors.append(
                f'  applug.json: version="{found_version}"  (expected "{expected_version}")'
            )
        if found_matika != expected_matika_version:
            errors.append(
                f'  applug.json: matika_version="{found_matika}"  '
                f'(expected "{expected_matika_version}")'
            )

    if errors:
        print("DRIFT CHECK FAILED:", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)

    print(
        f'drift check: applug.json version="{expected_version}", '
        f'matika_version="{expected_matika_version}"  ✓'
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sync VERSION to all version-bearing files."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Read-only drift check. Exit 0 if clean, 1 if any file drifted.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output (requires --check). Exit 0 if clean, 1 if drift.",
    )
    args = parser.parse_args()

    if args.json and not args.check:
        print("ERROR: --json requires --check", file=sys.stderr)
        sys.exit(2)

    drifted: list = sync(check_only=args.check, quiet=args.json)

    if args.check:
        if args.json:
            _, clean = read_version()
            print(json.dumps({"version": clean, "drift": drifted}))
        if drifted:
            sys.exit(1)
        elif not args.json:
            print("sync_version --check: no drift")
