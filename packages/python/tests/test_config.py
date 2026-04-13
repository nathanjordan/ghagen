"""Tests for ghagen.config (project-level options)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ghagen.config import load_options


@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project directory with .github/."""
    (tmp_path / ".github").mkdir()
    return tmp_path


def test_defaults_when_no_config(tmp_project: Path):
    opts = load_options(tmp_project)
    assert opts.auto_dedent is True


def test_ghagen_toml_auto_dedent_false(tmp_project: Path):
    (tmp_project / ".github" / "ghagen.toml").write_text(
        "[options]\nauto_dedent = false\n"
    )
    opts = load_options(tmp_project)
    assert opts.auto_dedent is False


def test_ghagen_toml_auto_dedent_true(tmp_project: Path):
    (tmp_project / ".github" / "ghagen.toml").write_text(
        "[options]\nauto_dedent = true\n"
    )
    opts = load_options(tmp_project)
    assert opts.auto_dedent is True


def test_ghagen_toml_no_options_section(tmp_project: Path):
    (tmp_project / ".github" / "ghagen.toml").write_text("[lint]\n")
    opts = load_options(tmp_project)
    assert opts.auto_dedent is True


def test_pyproject_toml_options(tmp_project: Path):
    (tmp_project / "pyproject.toml").write_text(
        "[tool.ghagen.options]\nauto_dedent = false\n"
    )
    opts = load_options(tmp_project)
    assert opts.auto_dedent is False


def test_ghagen_toml_takes_precedence(tmp_project: Path):
    (tmp_project / ".github" / "ghagen.toml").write_text(
        "[options]\nauto_dedent = false\n"
    )
    (tmp_project / "pyproject.toml").write_text(
        "[tool.ghagen.options]\nauto_dedent = true\n"
    )
    opts = load_options(tmp_project)
    assert opts.auto_dedent is False


def test_invalid_auto_dedent_type(tmp_project: Path):
    (tmp_project / ".github" / "ghagen.toml").write_text(
        '[options]\nauto_dedent = "yes"\n'
    )
    with pytest.raises(ValueError, match="must be a boolean"):
        load_options(tmp_project)


def test_invalid_options_not_table(tmp_project: Path):
    (tmp_project / ".github" / "ghagen.toml").write_text("options = 42\n")
    with pytest.raises(ValueError, match="must be a table"):
        load_options(tmp_project)
