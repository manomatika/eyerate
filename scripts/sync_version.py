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
  If neither is available the script exits with a clear error.

Run from the repo root:
  python scripts/sync_version.py
"""

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


def read_matika_version() -> str:
    """Return clean matika version (sibling clone preferred, MATIKA_VERSION env fallback)."""
    matika_version_file = MATIKA_REPO_ROOT / "VERSION"
    if matika_version_file.exists():
        raw = matika_version_file.read_text().strip()
        return raw.removesuffix("_dev")

    env_val = os.environ.get("MATIKA_VERSION", "").strip().lstrip("v")
    if env_val:
        return env_val.removesuffix("_dev")

    print(
        "ERROR: cannot determine matika_version.\n"
        f"  Tried: {matika_version_file} (not found)\n"
        "  Tried: MATIKA_VERSION env var (not set)\n"
        f"  Fix: ensure matika is cloned at {MATIKA_REPO_ROOT}, "
        "or set MATIKA_VERSION=<version>",
        file=sys.stderr,
    )
    sys.exit(1)


def _sync_applug_json(path: Path, version: str, matika_version: str) -> bool:
    """Write version and matika_version into applug.json. Returns True if file changed."""
    data = json.loads(path.read_text())
    if data.get("version") == version and data.get("matika_version") == matika_version:
        return False
    data["version"] = version
    data["matika_version"] = matika_version
    path.write_text(json.dumps(data, indent=4) + "\n")
    return True


def sync() -> list[str]:
    """Propagate VERSION (and matika VERSION) to all targets. Returns list of paths written."""
    raw, clean = read_version()
    matika_version = read_matika_version()
    print(
        f"sync_version: eyerate {raw!r} → {clean!r},  "
        f"matika_version → {matika_version!r}"
    )

    written: list[str] = []

    applug = REPO_ROOT / "applug.json"
    if applug.exists():
        changed = _sync_applug_json(applug, clean, matika_version)
        rel = str(applug.relative_to(REPO_ROOT))
        print(f"  {'UPDATED' if changed else 'OK     '}  {rel}")
        if changed:
            written.append(rel)
    else:
        print("  SKIP    applug.json (not found)")

    return written


def drift_check(expected_version: str, expected_matika_version: str) -> None:
    """
    Verify applug.json holds exactly expected_version and expected_matika_version.
    Exit 1 on any mismatch. Also fails if eyerate VERSION still carries _dev.
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
    sync()
