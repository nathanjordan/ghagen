"""Tests for ghagen._dedent.dedent_script."""

from ghagen._dedent import dedent_script


def test_triple_quoted_leading_blank_line():
    s = """
        echo hello
        echo world
    """
    assert dedent_script(s) == "echo hello\necho world"


def test_triple_quoted_content_on_first_line():
    s = """echo hello
        echo world"""
    assert dedent_script(s) == "echo hello\necho world"


def test_preserves_relative_indentation():
    s = """
        if [ -f config ]; then
            source config
        fi
    """
    assert dedent_script(s) == "if [ -f config ]; then\n    source config\nfi"


def test_single_line_noop():
    assert dedent_script("echo hello") == "echo hello"


def test_newline_concatenated_noop():
    # Strings built with \n-concatenation have no common indent.
    s = "echo hello\necho world"
    assert dedent_script(s) == "echo hello\necho world"


def test_empty_string():
    assert dedent_script("") == ""


def test_preserves_tabs():
    """Tabs must not be expanded — critical for <<- heredocs."""
    s = """
        cat <<-EOF
        \tindented with tab
        EOF
    """
    assert dedent_script(s) == "cat <<-EOF\n\tindented with tab\nEOF"


def test_mixed_indent_levels():
    s = """
        level0
          level1
            level2
    """
    assert dedent_script(s) == "level0\n  level1\n    level2"


def test_blank_lines_in_middle_preserved():
    s = """
        echo start

        echo end
    """
    assert dedent_script(s) == "echo start\n\necho end"


def test_strips_leading_trailing_blank_lines_only():
    """Internal blank lines are preserved, outer ones stripped."""
    s = "\n\n    echo hello\n\n    echo world\n\n"
    assert dedent_script(s) == "echo hello\n\necho world"


def test_only_whitespace_lines():
    s = "\n  \n\n"
    assert dedent_script(s) == ""


def test_no_common_indent():
    s = "line1\nline2\nline3"
    assert dedent_script(s) == "line1\nline2\nline3"


def test_single_indented_line():
    s = """
        single line
    """
    assert dedent_script(s) == "single line"


def test_preserves_intentional_trailing_newline():
    """Trailing \\n in \\n-concatenated strings is preserved."""
    s = "echo hello\necho world\n"
    assert dedent_script(s) == "echo hello\necho world\n"


def test_strips_trailing_newline_from_triple_quote():
    """Triple-quoted strings lose the artifact trailing \\n."""
    s = """
        echo hello
        echo world
    """
    result = dedent_script(s)
    assert result == "echo hello\necho world"
    assert not result.endswith("\n")
