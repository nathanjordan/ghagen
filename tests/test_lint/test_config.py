"""Tests for lint config loading with precedence and multi-source warning."""

from __future__ import annotations

from pathlib import Path

import pytest

from ghagen.lint.config import LintConfig, load_config
from ghagen.lint.violation import Severity


def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def test_load_config_defaults_when_no_files(tmp_path: Path) -> None:
    """With no config files present, returns an empty LintConfig and no warnings."""
    config, warnings = load_config(tmp_path)
    assert config.disable == set()
    assert config.severity == {}
    assert warnings == []


def test_load_config_from_github_ghagen_toml(tmp_path: Path) -> None:
    _write(
        tmp_path / ".github" / "ghagen.toml",
        """
[lint]
disable = ["missing-timeout"]

[lint.severity]
unpinned-actions = "error"
""",
    )
    config, warnings = load_config(tmp_path)
    assert config.disable == {"missing-timeout"}
    assert config.severity == {"unpinned-actions": Severity.ERROR}
    assert warnings == []


def test_load_config_from_pyproject_toml(tmp_path: Path) -> None:
    _write(
        tmp_path / "pyproject.toml",
        """
[tool.ghagen.lint]
disable = ["missing-permissions"]

[tool.ghagen.lint.severity]
missing-timeout = "error"
""",
    )
    config, warnings = load_config(tmp_path)
    assert config.disable == {"missing-permissions"}
    assert config.severity == {"missing-timeout": Severity.ERROR}
    assert warnings == []


def test_ghagen_toml_wins_over_pyproject(tmp_path: Path) -> None:
    """When both exist, .github/ghagen.toml is used and pyproject is ignored,
    and a warning is emitted naming which source was chosen."""
    _write(
        tmp_path / ".github" / "ghagen.toml",
        """
[lint]
disable = ["a"]
""",
    )
    _write(
        tmp_path / "pyproject.toml",
        """
[tool.ghagen.lint]
disable = ["b"]
""",
    )
    config, warnings = load_config(tmp_path)
    assert config.disable == {"a"}  # ghagen.toml won
    assert len(warnings) == 1
    msg = warnings[0]
    assert ".github/ghagen.toml" in msg
    assert "pyproject.toml" in msg
    assert "used" in msg or "ignored" in msg


def test_cli_disable_overrides_config_file(tmp_path: Path) -> None:
    """CLI --disable flags are unioned into the final disable set."""
    _write(
        tmp_path / ".github" / "ghagen.toml",
        """
[lint]
disable = ["missing-timeout"]
""",
    )
    config, _ = load_config(tmp_path, cli_disable=["unpinned-actions"])
    assert config.disable == {"missing-timeout", "unpinned-actions"}


def test_cli_disable_with_no_config_files(tmp_path: Path) -> None:
    config, warnings = load_config(tmp_path, cli_disable=["a", "b"])
    assert config.disable == {"a", "b"}
    assert warnings == []


def test_pyproject_with_no_ghagen_section_is_ignored(tmp_path: Path) -> None:
    """A pyproject.toml without [tool.ghagen.lint] should not trigger anything."""
    _write(
        tmp_path / "pyproject.toml",
        """
[project]
name = "myproj"

[tool.ruff]
line-length = 88
""",
    )
    config, warnings = load_config(tmp_path)
    assert config.disable == set()
    assert warnings == []


def test_invalid_severity_value_raises(tmp_path: Path) -> None:
    _write(
        tmp_path / ".github" / "ghagen.toml",
        """
[lint.severity]
missing-timeout = "not-a-real-severity"
""",
    )
    with pytest.raises(ValueError, match="severity"):
        load_config(tmp_path)


def test_malformed_toml_raises(tmp_path: Path) -> None:
    _write(
        tmp_path / ".github" / "ghagen.toml",
        "this is [[[not valid toml",
    )
    with pytest.raises(ValueError, match="parse"):
        load_config(tmp_path)


def test_lint_config_is_a_plain_dataclass() -> None:
    """LintConfig can be constructed directly without going through the loader."""
    config = LintConfig(
        disable={"missing-timeout"},
        severity={"unpinned-actions": Severity.ERROR},
    )
    assert "missing-timeout" in config.disable
    assert config.severity["unpinned-actions"] == Severity.ERROR
