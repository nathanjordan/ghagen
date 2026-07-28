"""Tests for ghagen.config (project-level options and typed discovery)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ghagen.config import load_options, load_project_config


def test_defaults_when_no_config(tmp_path: Path):
    opts = load_options(tmp_path)
    assert opts.auto_dedent is True


def test_auto_dedent_false(tmp_path: Path):
    (tmp_path / ".ghagen.yml").write_text("options:\n  auto_dedent: false\n")
    opts = load_options(tmp_path)
    assert opts.auto_dedent is False


def test_auto_dedent_true(tmp_path: Path):
    (tmp_path / ".ghagen.yml").write_text("options:\n  auto_dedent: true\n")
    opts = load_options(tmp_path)
    assert opts.auto_dedent is True


def test_no_options_section(tmp_path: Path):
    (tmp_path / ".ghagen.yml").write_text("lint:\n  disable: []\n")
    opts = load_options(tmp_path)
    assert opts.auto_dedent is True


def test_invalid_auto_dedent_type(tmp_path: Path):
    (tmp_path / ".ghagen.yml").write_text('options:\n  auto_dedent: "yes"\n')
    with pytest.raises(ValueError, match="must be a boolean"):
        load_options(tmp_path)


def test_invalid_options_not_table(tmp_path: Path):
    (tmp_path / ".ghagen.yml").write_text("options: 42\n")
    with pytest.raises(ValueError, match="must be a table"):
        load_options(tmp_path)


def test_load_options_ignores_bad_entrypoint(tmp_path: Path):
    """A malformed ``entrypoint:`` must never break the options path."""
    (tmp_path / ".ghagen.yml").write_text(
        "entrypoint: 42\noptions:\n  auto_dedent: false\n"
    )
    assert load_options(tmp_path).auto_dedent is False


class TestLoadProjectConfig:
    """The single parse: one call yields options + entrypoint + errors."""

    def test_single_parse_success(self, tmp_path: Path):
        (tmp_path / "workflows").mkdir()
        (tmp_path / "workflows" / "ci.py").write_text("# stub")
        (tmp_path / ".ghagen.yml").write_text(
            "entrypoint: workflows/ci.py\noptions:\n  auto_dedent: false\n"
        )

        config = load_project_config(tmp_path)
        assert config.root == tmp_path.resolve()
        assert config.entrypoint == "workflows/ci.py"
        assert config.config_path == (tmp_path / "workflows" / "ci.py").resolve()
        assert config.options.auto_dedent is False
        assert config.errors == ()

    def test_no_marker_anchors_search_at_cwd(self, tmp_path: Path):
        (tmp_path / "ghagen_config.py").write_text("# stub")
        config = load_project_config(tmp_path)
        assert config.root is None
        assert config.config_path == tmp_path / "ghagen_config.py"
        assert config.options.auto_dedent is True
        assert config.errors == ()

    def test_kind_parse_on_malformed_yaml(self, tmp_path: Path):
        (tmp_path / ".ghagen.yml").write_text("key: [unterminated\n")
        config = load_project_config(tmp_path)
        assert [e.kind for e in config.errors] == ["parse"]

    def test_kind_not_a_mapping(self, tmp_path: Path):
        (tmp_path / ".ghagen.yml").write_text("- a\n- b\n")
        config = load_project_config(tmp_path)
        assert [e.kind for e in config.errors] == ["not-a-mapping"]

    def test_kind_bad_entrypoint_type(self, tmp_path: Path):
        (tmp_path / ".ghagen.yml").write_text("entrypoint: 42\n")
        config = load_project_config(tmp_path)
        assert [e.kind for e in config.errors] == ["bad-entrypoint-type"]
        assert config.config_path is None

    def test_kind_entrypoint_missing(self, tmp_path: Path):
        (tmp_path / ".ghagen.yml").write_text("entrypoint: nope.py\n")
        config = load_project_config(tmp_path)
        assert [e.kind for e in config.errors] == ["entrypoint-missing"]

    def test_kind_bad_option_type(self, tmp_path: Path):
        (tmp_path / ".ghagen.yml").write_text('options:\n  auto_dedent: "yes"\n')
        config = load_project_config(tmp_path)
        assert [e.kind for e in config.errors] == ["bad-option-type"]

    def test_cli_flag_short_circuits(self, tmp_path: Path):
        (tmp_path / ".ghagen.yml").write_text("entrypoint: does_not_exist.py\n")
        flag = tmp_path / "flag.py"
        flag.write_text("# stub")
        config = load_project_config(tmp_path, cli_config_flag=str(flag))
        assert config.config_path == flag
        assert config.errors == ()
