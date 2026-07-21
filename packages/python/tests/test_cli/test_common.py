"""Tests for ``ghagen.cli._common``'s config/entrypoint discovery.

Covers ``_find_config`` and ``_entrypoint_from_ghagen_yml`` directly
(unit level), complementing the CLI-level regression tests in
``test_main.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from ghagen.cli._common import CONFIG_SEARCH_PATHS, _find_config


def test_root_ghagen_yml_resolved_from_root(tmp_path: Path, monkeypatch: object):
    """Regression guard: entrypoint resolves when cwd == root (existing behavior)."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    (tmp_path / "workflows").mkdir()
    (tmp_path / "workflows" / "ci.py").write_text("# stub")
    (tmp_path / ".ghagen.yml").write_text("entrypoint: workflows/ci.py\n")

    result = _find_config(None)
    assert result == (tmp_path / "workflows" / "ci.py").resolve()


def test_root_ghagen_yml_resolved_from_subdirectory(
    tmp_path: Path, monkeypatch: object
):
    """The fix: entrypoint resolves from a subdirectory with no config of its own."""
    (tmp_path / "workflows").mkdir()
    (tmp_path / "workflows" / "ci.py").write_text("# stub")
    (tmp_path / ".ghagen.yml").write_text("entrypoint: workflows/ci.py\n")

    subdir = tmp_path / "subdir"
    subdir.mkdir()
    monkeypatch.chdir(subdir)  # type: ignore[attr-defined]

    result = _find_config(None)
    assert result == (tmp_path / "workflows" / "ci.py").resolve()


def test_search_path_candidate_found_from_subdirectory(
    tmp_path: Path, monkeypatch: object
):
    """CONFIG_SEARCH_PATHS candidates are probed against the discovered root."""
    (tmp_path / ".ghagen.yml").write_text("")
    candidate = tmp_path / CONFIG_SEARCH_PATHS[-1]
    candidate.write_text("# stub")

    subdir = tmp_path / "subdir"
    subdir.mkdir()
    monkeypatch.chdir(subdir)  # type: ignore[attr-defined]

    result = _find_config(None)
    assert result == candidate


def test_no_ghagen_yml_anywhere_probes_cwd_only(tmp_path: Path, monkeypatch: object):
    """No .ghagen.yml anywhere: CONFIG_SEARCH_PATHS is probed against cwd."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    # A candidate file placed at tmp_path (an ancestor of cwd, but not cwd
    # itself) must NOT be picked up -- there is no ancestor walk in this
    # fallback branch.
    (tmp_path / CONFIG_SEARCH_PATHS[-1]).write_text("# stub")
    monkeypatch.chdir(subdir)  # type: ignore[attr-defined]

    with pytest.raises(typer.Exit):
        _find_config(None)


def test_no_ghagen_yml_anywhere_finds_candidate_in_cwd(
    tmp_path: Path, monkeypatch: object
):
    """Unchanged fallback: CONFIG_SEARCH_PATHS resolves against cwd with no marker."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    candidate = tmp_path / CONFIG_SEARCH_PATHS[-1]
    candidate.write_text("# stub")

    result = _find_config(None)
    assert result.resolve() == candidate.resolve()


def test_explicit_config_flag_bypasses_discovery(tmp_path: Path, monkeypatch: object):
    """--config bypasses root discovery entirely, regardless of cwd."""
    (tmp_path / ".ghagen.yml").write_text("entrypoint: does_not_exist.py\n")
    flag_target = tmp_path / "flag.py"
    flag_target.write_text("# stub")

    subdir = tmp_path / "subdir"
    subdir.mkdir()
    monkeypatch.chdir(subdir)  # type: ignore[attr-defined]

    result = _find_config(str(flag_target))
    assert result == flag_target
