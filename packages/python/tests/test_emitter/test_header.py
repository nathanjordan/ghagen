"""Tests for ghagen.emitter.header (template + variables)."""

from __future__ import annotations

from pathlib import Path

from ghagen.emitter.header import (
    DEFAULT,
    DEFAULT_HEADER,
    HEADER_VARIABLES,
    HeaderVariables,
    build_header_variables,
    format_header,
)

# --- format_header ---------------------------------------------------------


def test_format_header_default_renders_internal_template() -> None:
    """Passing the DEFAULT sentinel substitutes {source_file} from variables."""
    result = format_header(DEFAULT, ("workflows.py", 7))
    # Sourced from a synthetic non-app-rooted path; expect the abs path
    # to end with workflows.py.
    assert result is not None
    assert "workflows.py" in result
    assert ":7" not in result  # source_line not in default template
    assert "Do not edit manually." in result
    assert result.endswith("\n")


def test_format_header_string_is_emitted_verbatim() -> None:
    """User-provided strings are NOT format_map'd."""
    result = format_header("hello\nworld", None)
    assert result == "# hello\n# world\n"


def test_format_header_string_preserves_literal_braces() -> None:
    """Literal { and } in user strings survive — no substitution happens."""
    result = format_header("a {literal} {tool} b", None)
    assert result == "# a {literal} {tool} b\n"


def test_format_header_none_returns_none() -> None:
    """``header=None`` skips emission entirely."""
    assert format_header(None, ("x.py", 1)) is None


def test_format_header_callable_receives_variables() -> None:
    captured: list[HeaderVariables] = []

    def build(vars_: HeaderVariables) -> str:
        captured.append(vars_)
        return f"built by {vars_['tool']} v{vars_['version']}"

    result = format_header(build, ("workflows.py", 7))
    assert result is not None
    assert result.startswith("# built by ghagen v")
    assert result.endswith("\n")
    assert len(captured) == 1
    # The closure receives every variable in HEADER_VARIABLES.
    assert set(captured[0].keys()) == set(HEADER_VARIABLES.keys())


def test_format_header_callable_result_wrapped_with_hash() -> None:
    """Closure return values pass through the same # prefixing as strings."""
    result = format_header(lambda _v: "line1\nline2", None)
    assert result == "# line1\n# line2\n"


def test_format_header_blank_line_renders_bare_hash() -> None:
    result = format_header("line1\n\nline3", None)
    assert result == "# line1\n#\n# line3\n"


def test_format_header_ends_with_newline() -> None:
    result = format_header("x", None)
    assert result is not None
    assert result.endswith("\n")


# --- format_header shape contract ------------------------------------------
#
# The peer of ``formatHeader() shape contract`` in
# ``packages/typescript/src/emitter/header.test.ts``. ``None`` is the *only*
# skip signal; every other input yields a ``#``-prefixed block ending in
# exactly one ``\n``.


def test_format_header_empty_string_renders_bare_hash() -> None:
    """``header=""`` is a header — a lone ``#`` — not a skip."""
    assert format_header("", None) == "#\n"


def test_format_header_drops_one_trailing_break() -> None:
    assert format_header("x\n", None) == "# x\n"
    assert format_header("x\n\n", None) == "# x\n#\n"
    assert format_header("\r\n", None) == "#\n"


def test_format_header_crlf_is_one_break() -> None:
    result = format_header("a\r\nb", None)
    assert result == "# a\n# b\n"
    assert "\r" not in result


def test_format_header_bare_cr_is_a_break() -> None:
    result = format_header("a\rb\rc", None)
    assert result == "# a\n# b\n# c\n"
    assert "\r" not in result


def test_format_header_non_lf_unicode_breaks() -> None:
    """VT/FF/FS/GS/RS/NEL/U+2028/U+2029 all break the line.

    Not cosmetic: ruamel rejects VT/FF/FS/GS/RS inside a comment outright
    ("unacceptable character") and rescans NEL/U+2028/U+2029 as line breaks,
    so a surviving control character makes an unreadable document.
    """
    for char in "\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029":
        assert format_header(f"a{char}b", None) == "# a\n# b\n", repr(char)


def test_format_header_leading_break_is_not_collapsed() -> None:
    assert format_header("\nx", None) == "#\n# x\n"


def test_format_header_already_hashed_line_is_prefixed_again() -> None:
    assert format_header("# already hashed", None) == "# # already hashed\n"


def test_format_header_preserves_interior_whitespace() -> None:
    assert format_header("   ", None) == "#    \n"


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
    """{source_file} is resolved relative to the .ghagen.yml root."""
    (tmp_path / ".ghagen.yml").write_text("")

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
