"""Tests for ghagen.emitter.header (template + variables)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ghagen.emitter.header import (
    DEFAULT_HEADER,
    HEADER_VARIABLES,
    build_header_variables,
    format_header,
)

# --- format_header ---------------------------------------------------------


def test_format_header_literal_text_wraps_lines_in_hashes() -> None:
    result = format_header("hello\nworld", {})
    assert result == "# hello\n# world\n"


def test_format_header_substitutes_source_file() -> None:
    variables = {
        "source_file": "workflows.py",
        "source_line": "7",
        "tool": "ghagen",
        "version": "9.9.9",
    }
    result = format_header("Generated from {source_file}.", variables)
    assert result == "# Generated from workflows.py.\n"


def test_format_header_substitutes_all_variables() -> None:
    variables = {
        "source_file": "a.py",
        "source_line": "42",
        "tool": "ghagen",
        "version": "1.2.3",
    }
    result = format_header(
        "tool={tool} v={version} src={source_file}:{source_line}",
        variables,
    )
    assert result == "# tool=ghagen v=1.2.3 src=a.py:42\n"


def test_format_header_unknown_variable_raises() -> None:
    variables = {
        "source_file": "a.py",
        "source_line": "1",
        "tool": "ghagen",
        "version": "0.0.0",
    }
    with pytest.raises(ValueError) as excinfo:
        format_header("bad {nope}", variables)

    msg = str(excinfo.value)
    assert "{nope}" in msg
    # Every valid variable name should appear in the error message so the
    # user knows what they can use.
    for name in HEADER_VARIABLES:
        assert f"{{{name}}}" in msg
    # The brace-escaping hint should be present.
    assert "{{" in msg and "}}" in msg


def test_format_header_escaped_braces_survive() -> None:
    """Literal { and } are emitted when doubled in the template."""
    result = format_header("a {{literal}} b", {})
    assert result == "# a {literal} b\n"


def test_format_header_blank_line_renders_bare_hash() -> None:
    result = format_header("line1\n\nline3", {})
    assert result == "# line1\n#\n# line3\n"


def test_format_header_ends_with_newline() -> None:
    assert format_header("x", {}).endswith("\n")


def test_default_header_is_a_template() -> None:
    """DEFAULT_HEADER references {source_file} so default output is useful."""
    assert "{source_file}" in DEFAULT_HEADER


# --- build_header_variables ------------------------------------------------


def test_build_variables_none_source_location() -> None:
    variables = build_header_variables(None)
    assert variables["source_file"] == "<unknown>"
    assert variables["source_line"] == "0"
    assert variables["tool"] == "ghagen"
    assert variables["version"]  # whatever the installed version is


def test_build_variables_relative_to_app_root(tmp_path: Path) -> None:
    """{source_file} is resolved relative to the .github/ghagen.toml root."""
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "ghagen.toml").write_text("")

    src = tmp_path / "ci" / "workflows.py"
    src.parent.mkdir()
    src.write_text("# stub")

    variables = build_header_variables((str(src), 12))
    assert variables["source_file"] == "ci/workflows.py"
    assert variables["source_line"] == "12"


def test_build_variables_fallback_when_no_app_root(tmp_path: Path) -> None:
    """Without a marker file, {source_file} falls back to the absolute path."""
    src = tmp_path / "orphan.py"
    src.write_text("# stub")

    variables = build_header_variables((str(src), 1))
    # If the host tmp_path isn't inside a ghagen checkout, this will be the
    # absolute path. If it *is* inside one, we at least assert that the
    # recorded path is a suffix of the result (covers both cases safely).
    assert variables["source_file"].endswith("orphan.py")


def test_build_variables_tool_is_ghagen() -> None:
    variables = build_header_variables(None)
    assert variables["tool"] == "ghagen"


# --- HEADER_VARIABLES contract ---------------------------------------------


def test_header_variables_contract() -> None:
    """The public contract lists exactly the four supported variables."""
    assert set(HEADER_VARIABLES.keys()) == {
        "source_file",
        "source_line",
        "tool",
        "version",
    }
    # Every entry has a non-empty description.
    for name, desc in HEADER_VARIABLES.items():
        assert desc, f"HEADER_VARIABLES[{name!r}] must have a description"
