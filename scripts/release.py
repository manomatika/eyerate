"""
release.py — prepare an eyerate release commit (final OR pre-release).

Version CORE vs PRE-RELEASE SUFFIX:
  The target may be a final core (X.Y.Z) or a pre-release on the ladder
  X.Y.Z-dev < X.Y.Z-rc.N < X.Y.Z. The suffix is a human/audit marker: it is
  written verbatim into the VERSION file, but applug.json always receives the
  bare CORE (everything before the first "-") because those fields are manifest
  pins consumed by ahimsa's resolver cross-check.

What it does:
  1. Verifies eyerate VERSION currently matches the target's CORE
     (suffix on either side is ignored for this match — you set VERSION to a
     dev/rc marker during development and release.py finalizes the string).
  2. Writes the target version string (with any suffix) to eyerate VERSION.
  3. Calls sync_version.sync() to propagate the bare-core eyerate version and
     matika_version (sibling matika clone / MATIKA_VERSION env var) into
     applug.json.
  4. Runs the drift gate — applug.json must exactly match both bare cores.
  5. Commits VERSION + applug.json.
  6. Prints next-step reminders.

What it does NOT do:
  Push, tag, create a PR, merge, or create a GitHub release.
  Do those steps manually after reviewing the commit.

Usage:
  python scripts/release.py v0.0.4          # final
  python scripts/release.py 0.0.4
  python scripts/release.py 0.0.4-rc.1      # release candidate
  python scripts/release.py v0.0.4-dev      # dev pre-release
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sync_version import (  # noqa: E402
    REPO_ROOT,
    read_matika_version,
    read_version,
    version_core,
    sync,
)


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    if result.returncode != 0:
        print(f"ERROR: {' '.join(cmd)}\n{result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/release.py <version>  (e.g. v0.0.4 or 0.0.4)")
        sys.exit(1)

    # Validate the requested version through the canonical SemVer parser
    # (version_core raises ValueError naming the bad value on invalid input).
    # A single leading "v" is tolerated by the parser; strip it from the stored
    # target string so VERSION/tags hold the bare form.
    raw_target = sys.argv[1]
    try:
        target_core = version_core(raw_target)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    target = raw_target[1:] if raw_target.startswith("v") else raw_target

    # 1. Verify current VERSION shares the target's CORE. The pre-release suffix
    #    on either side is a human/audit marker and is ignored for this match.
    raw, raw_core = read_version()
    if raw_core != target_core:
        print(f"ERROR: VERSION core is {raw_core!r}, expected {target_core!r} (VERSION={raw!r})")
        print(f"Set VERSION to the {target_core} line (e.g. {target_core}-dev) before release.py.")
        sys.exit(1)

    # Read matika version now (before we write anything — fail fast if unavailable)
    matika_version = read_matika_version()

    print(f"Releasing eyerate {target}  (core={target_core!r}, matika_version={matika_version!r})")

    # 2. Write the target string (carries any pre-release suffix) to VERSION
    version_file = REPO_ROOT / "VERSION"
    version_file.write_text(target + "\n")
    print(f"  WROTE   VERSION ← {target!r}")

    # 3. Propagate
    sync()

    # 4. Drift check — same computation as propagation, read-only
    drifted = sync(check_only=True)
    if drifted:
        print("Drift check failed — aborting release.", file=sys.stderr)
        sys.exit(1)

    # 5. Commit
    stage_paths = ["VERSION", "applug.json"]
    existing = [p for p in stage_paths if (REPO_ROOT / p).exists()]
    _run(["git", "add"] + existing)
    _run(["git", "commit", "-m", f"chore: release {target}"])

    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    print(f"\nRelease commit created on {branch!r}.")
    print("Next steps (manual, after review):")
    print(f"  git push origin {branch}")
    print(f"  gh pr create --title 'Release v{target}' ...")
    print(f"  git tag v{target} && git push origin v{target}")
    print("  (a v*-* tag is published as a GitHub pre-release; v*.*.* as a full release)")
    print()
    print("Don't forget to update CHANGELOG.md and any version references in docs/.")


if __name__ == "__main__":
    main()
