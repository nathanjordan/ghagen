"""Auto-dedent utility for multiline script strings."""

from __future__ import annotations

#: Module-level flag controlling whether ``Step.run`` values are
#: automatically dedented at construction time.  Defaults to ``True``.
#: Set to ``False`` (or via ``[options] auto_dedent = false`` in
#: ``ghagen.toml``) to disable.
#:
#: NOTE: This is module-level mutable state.  It is not thread-safe —
#: concurrent ``App`` instances with different configs will race.
#: Fine for ghagen's single-threaded CLI usage.
auto_dedent: bool = True


def dedent_script(s: str) -> str:
    """Dedent a script string for use in YAML ``run:`` blocks.

    Combines the best of :func:`inspect.cleandoc` and
    :func:`textwrap.dedent`:

    * Handles both ``\"\"\"content ...\"\"\"`` and ``\"\"\"\\n    content\\n\"\"\"``
      styles (like ``cleandoc``).
    * Preserves literal tabs (unlike ``cleandoc`` which calls
      ``expandtabs``).
    * Strips leading and trailing blank lines.
    * Preserves relative indentation within the script.

    Algorithm:

    1. Split into lines.
    2. Strip leading whitespace from the **first line only** so that the
       ``\"\"\"content`` style doesn't poison the common-indent calculation.
    3. Compute the minimum indentation across all non-blank lines
       (excluding the first, which was already stripped).
    4. Remove that common indent from every line.
    5. Strip leading and trailing blank lines.
    """
    if not s:
        return s

    lines = s.splitlines(True)

    # Strip leading whitespace from the first line independently.
    # This mirrors inspect.cleandoc's handling: when the opening triple
    # quote is on the same line as content, that line's indent is
    # irrelevant to the common indent of the rest.
    if lines:
        lines[0] = lines[0].lstrip(" \t")

    # Compute minimum indent of remaining non-blank lines.
    indent: int | None = None
    for line in lines[1:]:
        stripped = line.lstrip(" \t")
        if not stripped or stripped == "\n":
            continue
        line_indent = len(line) - len(stripped)
        if indent is None or line_indent < indent:
            indent = line_indent

    # Remove common indent from all lines (except the first, already stripped).
    if indent and indent > 0:
        for i in range(1, len(lines)):
            # Only strip if the line has enough leading whitespace.
            # Blank lines may have less — leave them alone.
            if len(lines[i]) > indent and lines[i][:indent].strip(" \t") == "":
                lines[i] = lines[i][indent:]

    result = "".join(lines)

    # Strip leading and trailing blank/whitespace-only lines.
    # We operate on lines to avoid stripping meaningful content.
    result_lines = result.splitlines(True)

    # Strip leading blank lines.
    while result_lines and not result_lines[0].strip():
        result_lines.pop(0)

    # Strip trailing blank/whitespace-only lines (e.g. from the closing
    # triple-quote's indentation).  Track whether we actually removed
    # anything so we know whether a trailing \n was an artifact.
    stripped_trailing = False
    while result_lines and not result_lines[-1].strip():
        result_lines.pop()
        stripped_trailing = True

    if not result_lines:
        return ""

    # When we removed trailing blank lines, the final content line's
    # trailing \n is an artifact of the triple-quote format, not
    # intentional user content.  Strip it so ``"""\n    echo\n"""``
    # produces ``"echo"`` rather than ``"echo\n"``.
    # When no trailing lines were stripped, the user wrote the trailing
    # \n deliberately (e.g. ``"echo hello\n"``), so preserve it.
    if stripped_trailing and result_lines[-1].endswith("\n"):
        result_lines[-1] = result_lines[-1][:-1]

    return "".join(result_lines)
