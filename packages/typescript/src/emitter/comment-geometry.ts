/**
 * Comment geometry: how far a `#` sits from the thing it annotates, and what
 * happens when it cannot sit there at all.
 *
 * This module renders comment *text* — it never sees, and cannot see, the
 * emitted document. That is the whole point: a `#` inside a `run:` script and
 * a `#` that starts a comment are indistinguishable once the tree is
 * serialized, so the geometry decision is taken here, at attach time, where
 * scalar content is out of reach by construction.
 *
 * Invariant: a `yaml` node's `commentBefore` / `comment` slot may only ever
 * hold a value returned by this module. The writers are the comment slots in
 * `emitter/comments.ts` plus the header line in `emitter/yaml-writer.ts`.
 * Because {@link commentString} is the identity, an unrendered payload reaches
 * the output verbatim — a loud failure (invalid YAML), not a silent drift.
 *
 * This is the TypeScript peer of `emitter/comment_geometry.py`.
 */

/**
 * Columns between the end of a line's content and the `#` of its EOL comment.
 *
 * Two, matching ruamel.yaml's convention and therefore the Python port.
 */
export const EOL_GUTTER = 2;

/**
 * Render a block comment: `#`-prefix each line; a blank line becomes a bare `#`.
 *
 * Block-comment *columns* are not this module's business in TypeScript — the
 * `yaml` backend indents a `commentBefore` to its node automatically. (The
 * Python peer must own them; ruamel does not.)
 */
export function renderBlockComment(text: string): string {
  return text
    .split("\n")
    .map((line) => (line ? `# ${line}` : "#"))
    .join("\n");
}

/**
 * Render an end-of-line comment, gutter included, or `null` when the payload
 * cannot sit at end-of-line.
 *
 * `stringifyComment.lineComment` (yaml@2.8.3,
 * `dist/stringify/stringifyComment.js:16-20`) has three branches and only the
 * third contributes a column. `emitter/comments.ts` makes the third the only
 * reachable one: an EOL comment is never attached to a collection *value* (it
 * goes on the pair's key), and a payload containing a newline returns `null`
 * here so the caller places it as a block comment instead. The backend
 * therefore contributes exactly one column and this function contributes
 * `EOL_GUTTER - 1`.
 *
 * A payload that already carries its own `#` is passed through un-prefixed,
 * matching ruamel's `yaml_add_eol_comment` contract and so the Python peer.
 */
export function renderEolComment(text: string): string | null {
  if (text.includes("\n")) {
    return null;
  }
  const body = text.startsWith("#") ? text : `# ${text}`;
  return " ".repeat(EOL_GUTTER - 1) + body;
}

/**
 * The `commentString` hook for `Document.toString` — the identity.
 *
 * Everything reaching a comment slot is already rendered by this module, so
 * the backend has nothing left to add.
 */
export const commentString = (rendered: string): string => rendered;
