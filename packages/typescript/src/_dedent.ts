/** Auto-dedent utility for multiline script strings. */

/**
 * Split *s* into lines, keeping the trailing `\n` on each (mirrors Python's
 * `str.splitlines(keepends=True)` for the `\n` case). An empty string yields
 * an empty array.
 */
function splitLinesKeepends(s: string): string[] {
  if (s === "") {
    return [];
  }
  return s.split(/(?<=\n)/);
}

/**
 * Dedent a script string for use in YAML `run:` blocks.
 *
 * This is a direct port of the Python `ghagen._dedent.dedent_script` so both
 * language implementations produce byte-identical `run:` output. It combines
 * the best of `inspect.cleandoc` and `textwrap.dedent`:
 *
 * - Handles both `` `content ...` `` and `` `\n    content\n` `` styles.
 * - Preserves literal tabs (critical for `<<-` heredocs).
 * - Strips leading and trailing blank lines.
 * - Preserves relative indentation within the script.
 * - Preserves an *intentional* trailing newline (e.g. a `\n`-concatenated
 *   `"echo hi\n"`), while dropping the artifact trailing newline of a
 *   template-literal that closes on its own indented line.
 *
 * Algorithm:
 *
 * 1. Split into lines.
 * 2. Strip leading whitespace from the **first line only** so that the
 *    `` `content `` style doesn't poison the common-indent calculation.
 * 3. Compute the minimum indentation across all non-blank lines (excluding
 *    the first, which was already stripped).
 * 4. Remove that common indent from every line.
 * 5. Strip leading and trailing blank lines.
 */
export function dedentScript(s: string): string {
  if (!s) {
    return s;
  }

  const lines = splitLinesKeepends(s);

  // Strip leading whitespace from the first line independently. When the
  // opening delimiter is on the same line as content, that line's indent is
  // irrelevant to the common indent of the rest.
  if (lines.length > 0) {
    lines[0] = lines[0].replace(/^[ \t]+/, "");
  }

  // Compute minimum indent of remaining non-blank lines.
  let indent: number | null = null;
  for (let i = 1; i < lines.length; i++) {
    const stripped = lines[i].replace(/^[ \t]+/, "");
    if (stripped === "" || stripped === "\n") {
      continue;
    }
    const lineIndent = lines[i].length - stripped.length;
    if (indent === null || lineIndent < indent) {
      indent = lineIndent;
    }
  }

  // Remove common indent from all lines (except the first, already stripped).
  if (indent && indent > 0) {
    for (let i = 1; i < lines.length; i++) {
      // Only strip if the line has enough leading whitespace. Blank lines may
      // have less — leave them alone.
      if (lines[i].length > indent && lines[i].slice(0, indent).replace(/[ \t]/g, "") === "") {
        lines[i] = lines[i].slice(indent);
      }
    }
  }

  // Strip leading and trailing blank/whitespace-only lines. Operate on lines
  // to avoid stripping meaningful content.
  const resultLines = splitLinesKeepends(lines.join(""));

  while (resultLines.length > 0 && resultLines[0].trim() === "") {
    resultLines.shift();
  }

  // Track whether we removed a trailing blank line so we know whether a
  // trailing `\n` was an artifact.
  let strippedTrailing = false;
  while (resultLines.length > 0 && resultLines[resultLines.length - 1].trim() === "") {
    resultLines.pop();
    strippedTrailing = true;
  }

  if (resultLines.length === 0) {
    return "";
  }

  // When we removed trailing blank lines, the final content line's trailing
  // `\n` is an artifact of the delimiter format, not intentional user content.
  // Strip it so `` `\n    echo\n` `` produces `"echo"` rather than `"echo\n"`.
  // When no trailing lines were stripped, the user wrote the trailing `\n`
  // deliberately (e.g. `"echo hello\n"`), so preserve it.
  const last = resultLines.length - 1;
  if (strippedTrailing && resultLines[last].endsWith("\n")) {
    resultLines[last] = resultLines[last].slice(0, -1);
  }

  return resultLines.join("");
}
