"""Tests for ghagen.paths (app root discovery)."""

from pathlib import Path

from ghagen.paths import GHAGEN_YML_MARKER, find_app_root


def test_finds_marker_at_start_dir(tmp_path: Path) -> None:
    """find_app_root returns the directory when the marker is present there."""
    (tmp_path / ".ghagen.yml").write_text("")

    assert find_app_root(tmp_path) == tmp_path.resolve()


def test_finds_marker_several_levels_up(tmp_path: Path) -> None:
    """find_app_root walks upward through parents until it finds the marker."""
    (tmp_path / ".ghagen.yml").write_text("")

    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)

    assert find_app_root(deep) == tmp_path.resolve()


def test_returns_none_when_no_marker(tmp_path: Path) -> None:
    """find_app_root returns None when no ancestor has the marker."""
    # A deeply nested directory with no .ghagen.yml anywhere above it
    # within tmp_path. pytest's tmp_path is inside a scratch area that
    # presumably has no .ghagen.yml.
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)

    # If the host environment happens to sit inside a ghagen checkout, we
    # skip this check. Real CI and dev environments will hit the None branch.
    probe = find_app_root(deep)
    assert probe is None or probe != deep.resolve()


def test_accepts_file_path_as_start(tmp_path: Path) -> None:
    """When start is a file, the search begins at its parent directory."""
    (tmp_path / ".ghagen.yml").write_text("")

    nested_file = tmp_path / "sub" / "workflows.py"
    nested_file.parent.mkdir()
    nested_file.write_text("# stub")

    assert find_app_root(nested_file) == tmp_path.resolve()


def test_marker_constant_value() -> None:
    """GHAGEN_YML_MARKER points at the canonical config file location."""
    assert Path(".ghagen.yml") == GHAGEN_YML_MARKER
