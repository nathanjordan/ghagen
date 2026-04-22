"""Tests for ghagen.config (project-level options)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ghagen.config import load_options


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
