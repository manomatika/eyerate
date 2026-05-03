"""
sync_version.py — propagates canonical version data from VERSION files into all
version-bearing files in the eyerate working tree.

Propagation targets (allowlist):
  applug.json  — "version"        (from eyerate's own VERSION file)
  applug.json  — "matika_version" (from matika's VERSION file)

Both VERSION files may carry a _dev suffix (e.g. "0.0.4_dev"). That suffix is
stripped before propagation so all targets always hold a clean X.Y.Z string.
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
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

# Sibling matika clone — standard layout: ~/dev/projects/{matika,eyerate}
MATIKA_REPO_ROOT = REPO_ROOT.parent / "matika"

# Every file this script touches. drift_check() verifies exactly these fields.
SYNC_TARGETS: list[tuple[str, str]] = [
    ("applug.json", 'applug.json "version" + "matika_version"'),
]


def read_version() -> tuple[str, str]:
    """Return (raw, clean) for eyerate's VERSION. clean has _dev stripped."""
    version_file = REPO_ROOT / "VERSION"
    if not version_file.exists():
        print("ERROR: VERSION file not found", file=sys.stderr)
        sys.exit(1)
    raw = version_file.read_text().strip()
    clean = raw.removesuffix("_dev")
    return raw, clean


def _try_read_matika_version() -> str | None:
    """Return clean matika version, or None if unavailable (no exit)."""
    matika_version_file = MATIKA_REPO_ROOT / "VERSION"
    if matika_version_file.exists():
        return matika_version_file.read_text().strip().removesuffix("_dev")
    env_val = os.environ.get("MATIKA_VERSION", "").strip().lstrip("v")
    if env_val:
        return env_val.removesuffix("_dev")
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
    In check mode VERSION may carry _dev; the stripped value is what targets
    are compared against (same as propagation — no special failure for _dev).
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
    Verify applug.json holds exactly expected_version and expected_matika_version.
    Exit 1 on any mismatch. Also fails if eyerate VERSION still carries _dev.

    Note: release.py uses sync(check_only=True) as its drift gate instead of
    calling this directly. This function is retained for standalone use.
    """
    version_file = REPO_ROOT / "VERSION"
    raw = version_file.read_text().strip()
    if "_dev" in raw:
        print(
            f"DRIFT: VERSION is {raw!r} — _dev must be removed before drift check",
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
                f"  applug.json: version={found_version!r}  (expected {expected_version!r})"
            )
        if found_matika != expected_matika_version:
            errors.append(
                f"  applug.json: matika_version={found_matika!r}  "
                f"(expected {expected_matika_version!r})"
            )

    if errors:
        print("DRIFT CHECK FAILED:", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)

    print(
        f"drift check: applug.json version={expected_version!r}, "
        f"matika_version={expected_matika_version!r}  ✓"
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
