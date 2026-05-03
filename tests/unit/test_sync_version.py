"""
Tests for scripts/sync_version.py.

Runs entirely against fixture trees under tmp_path — never touches the real
working tree or the sibling matika clone. REPO_ROOT and MATIKA_REPO_ROOT are
patched at the module level so all path lookups inside sync_version resolve
to fixture directories.
"""

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import sync_version  # noqa: E402 — must come after sys.path manipulation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_tree(
    tmp_path: Path,
    eyerate_version: str,
    matika_version: str = "0.0.4",
    applug_version: str = "OLD",
    applug_matika_version: str = "OLD",
) -> tuple[Path, Path]:
    """Return (eyerate_root, matika_root) fixture dirs under tmp_path."""
    eyerate_root = tmp_path / "eyerate"
    matika_root = tmp_path / "matika"
    eyerate_root.mkdir()
    matika_root.mkdir()

    (eyerate_root / "VERSION").write_text(eyerate_version + "\n")
    (matika_root / "VERSION").write_text(matika_version + "\n")

    applug_data = {
        "id": "eyerate",
        "version": applug_version,
        "matika_version": applug_matika_version,
        "name": "EyeRate",
    }
    (eyerate_root / "applug.json").write_text(json.dumps(applug_data, indent=4) + "\n")

    return eyerate_root, matika_root


@contextmanager
def patched(eyerate_root: Path, matika_root: Path):
    with patch.object(sync_version, "REPO_ROOT", eyerate_root):
        with patch.object(sync_version, "MATIKA_REPO_ROOT", matika_root):
            yield


def run_sync(eyerate_root: Path, matika_root: Path, check_only: bool = False) -> list[str]:
    with patched(eyerate_root, matika_root):
        return sync_version.sync(check_only=check_only)


def run_drift_check(eyerate_root: Path, matika_root: Path, ev: str, mv: str) -> None:
    with patched(eyerate_root, matika_root):
        sync_version.drift_check(ev, mv)


def applug_versions(eyerate_root: Path) -> tuple[str, str]:
    data = json.loads((eyerate_root / "applug.json").read_text())
    return data.get("version", ""), data.get("matika_version", "")


# ---------------------------------------------------------------------------
# Core propagation
# ---------------------------------------------------------------------------

def test_dev_version_stripped_before_propagation(tmp_path):
    root, mroot = make_tree(tmp_path, "0.0.4_dev", "0.0.4")
    run_sync(root, mroot)
    v, mv = applug_versions(root)
    assert v == "0.0.4"
    assert mv == "0.0.4"


def test_matika_dev_version_stripped(tmp_path):
    root, mroot = make_tree(tmp_path, "0.0.4_dev", "0.0.4_dev")
    run_sync(root, mroot)
    _, mv = applug_versions(root)
    assert mv == "0.0.4"


def test_dev_suffix_never_written_to_applug(tmp_path):
    root, mroot = make_tree(tmp_path, "1.2.3_dev", "1.2.3_dev")
    run_sync(root, mroot)
    content = (root / "applug.json").read_text()
    assert "_dev" not in content


def test_sync_is_idempotent(tmp_path):
    root, mroot = make_tree(tmp_path, "0.0.4_dev")
    run_sync(root, mroot)
    before = (root / "applug.json").read_text()
    run_sync(root, mroot)
    assert (root / "applug.json").read_text() == before


def test_sync_returns_empty_when_already_current(tmp_path):
    root, mroot = make_tree(tmp_path, "0.0.4_dev")
    run_sync(root, mroot)
    written = run_sync(root, mroot)
    assert written == []


def test_sync_skips_missing_applug_json(tmp_path):
    root, mroot = make_tree(tmp_path, "0.0.4_dev")
    (root / "applug.json").unlink()
    run_sync(root, mroot)  # must not raise


# ---------------------------------------------------------------------------
# Drift check (standalone)
# ---------------------------------------------------------------------------

def test_drift_check_passes_when_all_targets_match(tmp_path):
    root, mroot = make_tree(tmp_path, "0.0.4_dev")
    run_sync(root, mroot)
    (root / "VERSION").write_text("0.0.4\n")
    run_drift_check(root, mroot, "0.0.4", "0.0.4")


def test_drift_check_fails_when_version_has_dev(tmp_path):
    root, mroot = make_tree(tmp_path, "0.0.4_dev")
    run_sync(root, mroot)
    with pytest.raises(SystemExit):
        run_drift_check(root, mroot, "0.0.4", "0.0.4")


def test_drift_check_fails_on_version_mismatch(tmp_path):
    root, mroot = make_tree(tmp_path, "0.0.4_dev")
    run_sync(root, mroot)
    (root / "VERSION").write_text("0.0.4\n")
    data = json.loads((root / "applug.json").read_text())
    data["version"] = "0.0.1"
    (root / "applug.json").write_text(json.dumps(data, indent=4) + "\n")
    with pytest.raises(SystemExit):
        run_drift_check(root, mroot, "0.0.4", "0.0.4")


def test_drift_check_fails_on_matika_version_mismatch(tmp_path):
    root, mroot = make_tree(tmp_path, "0.0.4_dev")
    run_sync(root, mroot)
    (root / "VERSION").write_text("0.0.4\n")
    data = json.loads((root / "applug.json").read_text())
    data["matika_version"] = "9.9.9"
    (root / "applug.json").write_text(json.dumps(data, indent=4) + "\n")
    with pytest.raises(SystemExit):
        run_drift_check(root, mroot, "0.0.4", "0.0.4")


# ---------------------------------------------------------------------------
# --check mode
# ---------------------------------------------------------------------------

def test_check_mode_returns_empty_when_clean(tmp_path):
    root, mroot = make_tree(tmp_path, "0.0.4_dev")
    run_sync(root, mroot)
    drifted = run_sync(root, mroot, check_only=True)
    assert drifted == []


def test_check_mode_reports_version_drift(tmp_path):
    root, mroot = make_tree(tmp_path, "0.0.4_dev")
    run_sync(root, mroot)
    data = json.loads((root / "applug.json").read_text())
    data["version"] = "0.0.1"
    (root / "applug.json").write_text(json.dumps(data, indent=4) + "\n")
    drifted = run_sync(root, mroot, check_only=True)
    assert drifted == ["applug.json"]


def test_check_mode_reports_matika_version_drift(tmp_path):
    root, mroot = make_tree(tmp_path, "0.0.4_dev")
    run_sync(root, mroot)
    data = json.loads((root / "applug.json").read_text())
    data["matika_version"] = "9.9.9"
    (root / "applug.json").write_text(json.dumps(data, indent=4) + "\n")
    drifted = run_sync(root, mroot, check_only=True)
    assert drifted == ["applug.json"]


def test_check_mode_does_not_modify_files(tmp_path):
    root, mroot = make_tree(tmp_path, "0.0.4_dev")
    # Files at OLD — check mode must not fix them
    before = (root / "applug.json").read_text()
    run_sync(root, mroot, check_only=True)
    assert (root / "applug.json").read_text() == before


def test_check_mode_accepts_dev_version(tmp_path):
    """--check must not fail just because VERSION carries _dev."""
    root, mroot = make_tree(tmp_path, "0.0.4_dev")
    run_sync(root, mroot)
    drifted = run_sync(root, mroot, check_only=True)
    assert drifted == []


def test_check_mode_warns_and_skips_when_matika_absent(tmp_path, capsys):
    """If matika VERSION is unreachable, warn and skip matika_version check."""
    root, mroot = make_tree(tmp_path, "0.0.4_dev")
    run_sync(root, mroot)
    # Remove matika VERSION to simulate absent sibling
    (mroot / "VERSION").unlink()
    drifted = run_sync(root, mroot, check_only=True)
    out = capsys.readouterr().out
    assert "WARN" in out
    assert drifted == []  # version field is clean; matika_version skipped


def test_check_mode_still_reports_version_drift_when_matika_absent(tmp_path):
    """Even with no matika VERSION, version-field drift is still reported."""
    root, mroot = make_tree(tmp_path, "0.0.4_dev")
    run_sync(root, mroot)
    (mroot / "VERSION").unlink()
    data = json.loads((root / "applug.json").read_text())
    data["version"] = "0.0.1"
    (root / "applug.json").write_text(json.dumps(data, indent=4) + "\n")
    drifted = run_sync(root, mroot, check_only=True)
    assert drifted == ["applug.json"]


def test_release_drift_gate_uses_check_mode(tmp_path):
    """release.py calls sync(check_only=True) as its drift gate.
    Verify the gate returns no drift immediately after propagation."""
    root, mroot = make_tree(tmp_path, "0.0.4_dev")
    with patched(root, mroot):
        sync_version.sync()                          # propagation (as release does)
        drifted = sync_version.sync(check_only=True) # drift gate (as release does)
    assert drifted == [], f"Drift gate should pass after clean propagation, got: {drifted}"
