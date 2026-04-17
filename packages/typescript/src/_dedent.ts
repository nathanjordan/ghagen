/**
 * Auto-dedent utility for multiline script strings.
 *
 * Ported from `packages/python/src/ghagen/_dedent.py`. Combines the best
 * of Python's `inspect.cleandoc` and `textwrap.dedent`:
 *
 *   - Handles both `"""content ..."""` and `"""\n    content\n"""` styles.
 *   - Preserves literal tabs (does not call `expandtabs`).
 *   - Strips leading and trailing blank lines.
 *   - Preserves relative indentation within the script.
 *
 * NOTE: `autoDedent` is module-level mutable state. It is not safe for
 * concurrent App instances with different configs. Fine for ghagen's
 * single-threaded CLI usage.
 */

/**
 * Module-level flag controlling whether `step({ run: ... })` values are
 * auto-dedented at construction time. Defaults to true. Set via
 * `setAutoDedent(false)` or `[options] auto_dedent = false` in
 * `.github/ghagen.toml`.
 */
let autoDedentFlag = true;

/** Read the current auto-dedent flag. */
export function getAutoDedent(): boolean {
  return autoDedentFlag;
}

/** Set the module-level auto-dedent flag. */
export function setAutoDedent(value: boolean): void {
  autoDedentFlag = value;
}

/**
 * Split a string into lines, preserving line terminators (mirroring
 * Python's `str.splitlines(keepends=True)`).
 */
function splitLinesKeepEnds(s: string): string[] {
  if (!s) return [];
  const lines: string[] = [];
  let i = 0;
  while (i < s.length) {
    let j = i;
    while (j < s.length && s[j] !== "\n" && s[j] !== "\r") j++;
    if (j < s.length) {
      // Include the terminator (\n, \r, or \r\n).
      if (s[j] === "\r" && s[j + 1] === "\n") j += 2;
      else j += 1;
    }
    lines.push(s.slice(i, j));
    i = j;
  }
  return lines;
}

/** Strip leading spaces and tabs from a string (Python `str.lstrip(" \t")`). */
function lstripSpaceTab(s: string): string {
  let i = 0;
  while (i < s.length && (s[i] === " " || s[i] === "\t")) i++;
  return s.slice(i);
}

/**
 * Dedent a script string for use in YAML `run:` blocks.
 *
 * Algorithm:
 *   1. Split into lines (with terminators preserved).
 *   2. Strip leading whitespace from the first line only.
 *   3. Compute the minimum indentation across non-blank lines (excluding
 *      the first, which was already stripped).
 *   4. Remove that common indent from every line.
 *   5. Strip leading and trailing blank lines.
 */
export function dedentScript(s: string): string {
  if (!s) return s;

  const lines = splitLinesKeepEnds(s);

  // Strip leading whitespace from the first line independently.
  if (lines.length > 0) {
    lines[0] = lstripSpaceTab(lines[0]!);
  }

  // Compute minimum indent of remaining non-blank lines.
  let indent: number | null = null;
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i]!;
    const stripped = lstripSpaceTab(line);
    if (!stripped || stripped === "\n") continue;
    const lineIndent = line.length - stripped.length;
    if (indent === null || lineIndent < indent) {
      indent = lineIndent;
    }
  }

  // Remove common indent from all lines (except the first, already stripped).
  if (indent !== null && indent > 0) {
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i]!;
      // Only strip if the line has enough leading whitespace.
      if (
        line.length > indent &&
        lstripSpaceTab(line.slice(0, indent)) === ""
      ) {
        lines[i] = line.slice(indent);
      }
    }
  }

  let result = lines.join("");

  // Strip leading and trailing blank/whitespace-only lines.
  let resultLines = splitLinesKeepEnds(result);

  // Strip leading blank lines.
  while (resultLines.length > 0 && resultLines[0]!.trim() === "") {
    resultLines.shift();
  }

  // Strip trailing blank/whitespace-only lines. Track whether we removed
  // any so we know whether a trailing \n was an artifact.
  let strippedTrailing = false;
  while (
    resultLines.length > 0 &&
    resultLines[resultLines.length - 1]!.trim() === ""
  ) {
    resultLines.pop();
    strippedTrailing = true;
  }

  if (resultLines.length === 0) return "";

  // When trailing blank lines were stripped, the final content line's
  // trailing \n is an artifact of the triple-quote/template literal
  // format — strip it. When no trailing lines were stripped, preserve
  // the user's deliberate trailing \n.
  const last = resultLines[resultLines.length - 1]!;
  if (strippedTrailing && last.endsWith("\n")) {
    resultLines[resultLines.length - 1] = last.slice(0, -1);
  }

  result = resultLines.join("");
  return result;
}
