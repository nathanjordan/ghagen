"""Tests for ``ghagen.cli._common``'s config/entrypoint discovery.

Covers ``_find_config`` — the CLI render layer over
:func:`ghagen.config.load_project_config` — at the unit level, complementing
the value-level tests in ``test_config.py`` and the CLI-level regression tests
in ``test_main.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import typer

from ghagen.cli._common import _find_config, _load_app
from ghagen.config import CONFIG_SEARCH_PATHS


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


def test_load_app_scopes_its_sys_path_insertion(tmp_path: Path):
    """``_load_app`` leaves ``sys.path`` exactly as it found it.

    The helper is imported *inside* ``create_app()``, not at config import
    time, so a ``finally:`` mistakenly closed after ``exec_module`` — before
    ``resolve_app`` invokes the factory — fails this test with an
    ``ImportError``. That is ADR-0004's Python tracking window, defended here
    at the CLI loader as well as in ``pin.sources``.
    """
    helper = tmp_path / "cli_scoped_helper.py"
    helper.write_text('CHECKOUT = "actions/checkout@v4"\n')

    config = tmp_path / "cli_scoped_cfg.py"
    config.write_text(
        "from ghagen.app import App\n"
        "def create_app():\n"
        "    import cli_scoped_helper  # imported only when the factory runs\n"
        "    _ = cli_scoped_helper.CHECKOUT\n"
        "    return App(lockfile=None)\n"
    )

    parent = str(tmp_path.resolve())
    before = list(sys.path)
    assert parent not in before

    try:
        app = _load_app(config)
        assert app is not None
    finally:
        sys.modules.pop("cli_scoped_helper", None)

    assert sys.path == before


def test_load_app_leaves_a_caller_owned_sys_path_entry_alone(tmp_path: Path):
    """Idempotency: only an entry this call inserted is removed."""
    config = tmp_path / "cli_owned_cfg.py"
    config.write_text("from ghagen.app import App\napp = App(lockfile=None)\n")

    parent = str(tmp_path.resolve())
    sys.path.insert(0, parent)
    try:
        _load_app(config)
        assert parent in sys.path
    finally:
        sys.path.remove(parent)
