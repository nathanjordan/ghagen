"""Tests for lint config loading from .ghagen.yml."""

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


def test_load_config_from_ghagen_yml(tmp_path: Path) -> None:
    _write(
        tmp_path / ".ghagen.yml",
        "lint:\n  disable:\n    - missing-timeout\n\n  severity:\n    unpinned-actions: error\n",
    )
    config, warnings = load_config(tmp_path)
    assert config.disable == {"missing-timeout"}
    assert config.severity == {"unpinned-actions": Severity.ERROR}
    assert warnings == []


def test_cli_disable_overrides_config_file(tmp_path: Path) -> None:
    """CLI --disable flags are unioned into the final disable set."""
    _write(
        tmp_path / ".ghagen.yml",
        "lint:\n  disable:\n    - missing-timeout\n",
    )
    config, _ = load_config(tmp_path, cli_disable=["unpinned-actions"])
    assert config.disable == {"missing-timeout", "unpinned-actions"}


def test_cli_disable_with_no_config_files(tmp_path: Path) -> None:
    config, warnings = load_config(tmp_path, cli_disable=["a", "b"])
    assert config.disable == {"a", "b"}
    assert warnings == []


def test_invalid_severity_value_raises(tmp_path: Path) -> None:
    _write(
        tmp_path / ".ghagen.yml",
        "lint:\n  severity:\n    missing-timeout: not-a-real-severity\n",
    )
    with pytest.raises(ValueError, match="severity"):
        load_config(tmp_path)


def test_malformed_yaml_raises(tmp_path: Path) -> None:
    _write(
        tmp_path / ".ghagen.yml",
        ":\n  - :\n  bad: [\"",
    )
    with pytest.raises(ValueError, match="parse"):
        load_config(tmp_path)


def test_ghagen_yml_without_lint_section(tmp_path: Path) -> None:
    """A .ghagen.yml without a lint key should fall back to defaults."""
    _write(
        tmp_path / ".ghagen.yml",
        "options:\n  root: workflows/\n",
    )
    config, warnings = load_config(tmp_path)
    assert config.disable == set()
    assert config.severity == {}
    assert warnings == []


def test_lint_config_is_a_plain_dataclass() -> None:
    """LintConfig can be constructed directly without going through the loader."""
    config = LintConfig(
        disable={"missing-timeout"},
        severity={"unpinned-actions": Severity.ERROR},
    )
    assert "missing-timeout" in config.disable
    assert config.severity["unpinned-actions"] == Severity.ERROR
