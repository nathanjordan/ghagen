# 12 — A real comment-geometry module in the TypeScript Emitter

**Status:** proposed | **Ports:** typescript (led) / python (mirror) | **Effort:** high-M | **Depends on:** 20 (merges first — same file, disjoint hunks); merges before 13 (six shared files)

Effort raised from M: the proposal now also fixes a cross-port EOL divergence found during review
(finding 3 below), which adds a branch to `comments.ts` in both container cases, two byte-exact
parity tests per port, and an inversion of an existing green Python test.

All line numbers are against `main` at `e7a972c`. **20 merges first** and deletes
`yaml-writer.ts:202-205` plus doc-comment lines `:180,:185-187`, so every `yaml-writer.ts` citation
below shifts up by as much as 7 lines on the merged tree. Nothing in 20's hunks is in mine.

## Files involved

### Modified

| Path                                                       | Lines | Role in this proposal                                                                                                                                                                                                             |
| ---------------------------------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/typescript/src/emitter/yaml-writer.ts`           | 480   | Delete `formatYamlComment` and `fixInlineCommentSpacing` (`:389-405`) and the call at `:450`; the header (`:430-433`) is pre-rendered; `commentString` (`:447`) becomes the identity                                              |
| `packages/typescript/src/emitter/comments.ts`              | 104   | The eight node-comment writes (`:29,37,40,43,74,80,96,99`) route through the geometry module; `attachModelComment`'s EOL path (`:86-103`) gains the key redirect `attachFieldComment` already has at `:34-38`                     |
| `packages/typescript/src/emitter/comments.test.ts`         | 128   | Asserts raw payloads on node slots (`:32,45,74,91,112`); payloads become rendered. New cases for the EOL-on-collection redirect                                                                                                   |
| `packages/typescript/src/emitter/yaml-writer.test.ts`      | 244   | `\s+` gutter assertions (`:125,141`) tighten to exact bytes; corruption round-trip tests added                                                                                                                                    |
| `packages/typescript/src/integration/snapshots.test.ts`    | 293   | `comments.yml` assertion (`:36-61`) — fixture bytes change at `:3`                                                                                                                                                                |
| `packages/python/src/ghagen/emitter/comments.py`           | 95    | `attach`'s EOL path (`:53,67,69`) stops depending on ruamel's neighbour heuristic; multi-line payloads redirect to the block path                                                                                                 |
| `packages/python/src/ghagen/emitter/yaml_writer.py`        | 132   | `_MAP_VALUE_INDENT` / `_SEQ_ITEM_INDENT` (`:25-26`) and `_apply_pre_comment_columns` (`:63-97`) move out; `dump_yaml` (`:122-123`) calls one geometry entry point; the module docstring (`:1-6`) drops "comment-column alignment" |
| `packages/python/tests/test_emitter/test_comments.py`      | 231   | `:231` asserts the **buggy** one-column output and is **inverted**; multi-line EOL test added; `:129,153` keep passing unchanged                                                                                                  |
| `packages/python/tests/test_emitter/test_yaml_writer.py`   | 205   | **Docstring only** (`:1-10`): it claims the comment-column pass is exercised here; after the move that is false. No test moves — see Test impact                                                                                  |
| `packages/python/tests/test_integration/test_snapshots.py` | 451   | `test_comments` (`:113-151`) — fixture bytes change at `:3`                                                                                                                                                                       |
| `fixtures/expected/comments.yml`                           | 24    | `:3` gains one column (`on:  # trigger configuration`); shared byte oracle for both ports                                                                                                                                         |
| `docs/src/content/docs/guides/comments.mdx`                | 320   | Four emitted-YAML lines are wrong today (`:77,153,234,244`) and the "Known limitations" note (`:318-320`) describes behaviour spec 0003 already fixed                                                                             |
| `docs/specs/0003-comment-attachment-module.md`             | 497   | `:288-289` ruled `fixInlineCommentSpacing` out of scope; amend with a pointer here (see last section)                                                                                                                             |
| `packages/typescript/CONTEXT.md`                           | 119   | **Emitter** entry only (`:34-38`) — the round's region map assigns 12 and 13 that region, 12 first                                                                                                                                |
| `packages/python/CONTEXT.md`                               | 114   | **Emitter** entry only (`:34-38`), the peer edit                                                                                                                                                                                  |

### New

| Path                                                          | Role in this proposal                                                                |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `packages/typescript/src/emitter/comment-geometry.ts`         | The module: one constant, two render functions, the backend hook (~15 lines of body) |
| `packages/typescript/src/emitter/comment-geometry.test.ts`    | Unit tests for the render functions and the constant                                 |
| `packages/python/src/ghagen/emitter/comment_geometry.py`      | The Python peer: the same constant and rule, ruamel-shaped implementation            |
| `packages/python/tests/test_emitter/test_comment_geometry.py` | First direct tests for the two node-tree passes                                      |

Not touched: `packages/typescript/src/emitter/header.ts`, `packages/python/src/ghagen/emitter/header.py`
(proposal 13), `packages/typescript/src/models/_base.ts` (proposal 24's `walk`, `:245`),
`docs/proposals/INDEX.md`. No TypeDoc entry point changes — the entry points are exactly the nine
`_docs-api-*.ts` files (`docs/astro.config.mjs:126-182`) and the new module is Emitter-internal,
exported from neither `src/index.ts` nor any barrel.

## Problem

Where an inline `#` sits relative to the value it annotates is one fact. In TypeScript that fact is
computed by a regular expression run over the **finished document text**, after the point where the
Emitter still knew which `#` was a comment and which was user data.

```ts
// packages/typescript/src/emitter/yaml-writer.ts:397-405
/**
 * Widen the gap before inline `#` comments from 1 space to 2 to match
 * ruamel.yaml's convention. The lookbehind condition (non-whitespace,
 * non-colon) leaves block comments (indented `#`) and key-only comments
 * (`key: #`) alone.
 */
function fixInlineCommentSpacing(yaml: string): string {
  return yaml.replace(/([^\s:]) (# )/g, "$1  $2");
}
```

```ts
// packages/typescript/src/emitter/yaml-writer.ts:443-450
const yaml = doc.toString({
  lineWidth: 0,
  indentSeq: false,
  singleQuote: true,
  commentString: formatYamlComment,
});

return fixInlineCommentSpacing(yaml);
```

Four consequences follow, all live, all reproduced against `main` at `e7a972c`.

### 1. User-data corruption — **live**

A `run:` script containing a trailing shell comment does not survive emission. Emitting a workflow
whose step has `run: "npm ci # install deps\nnpm test\n"` and re-parsing with `YAML.parse`:

```
in : "npm ci # install deps\nnpm test\n"
out: "npm ci  # install deps\nnpm test\n"
```

A byte is injected into the user's shell script. The document is still valid YAML and still parses;
it just no longer round-trips to the model. The same happens to a single-line `run`, to an `env`
value, and to any other string scalar:

```yaml
run: |
  echo hi  # not a yaml comment   # ← user wrote one space
  make build
run: 'echo a  # b'                # ← user wrote "echo a # b"
env:
  COLOR: 'red  # crimson'         # ← user wrote "red # crimson"
```

**Exactly which shapes are affected.** The regex needs a non-whitespace, non-colon character, then
exactly one space, then `#` then a space. Measured, one workflow per row, comparing the input string
to `YAML.parse(toYaml(...)).jobs.j.steps[0].run`:

| Input `run`                                         | Result                                                                       |
| --------------------------------------------------- | ---------------------------------------------------------------------------- |
| `echo hi # note`                                    | **corrupt** → `echo hi  # note`                                              |
| `npm ci # install deps\nnpm test\n` (block literal) | **corrupt**                                                                  |
| `echo 'a # b'`                                      | **corrupt** → `echo 'a  # b'`                                                |
| `curl https://x/y#frag # note`                      | **corrupt** (the fragment `#frag` is untouched; the trailing comment is not) |
| `echo hi #note` (no space after `#`)                | safe                                                                         |
| `echo hi  # note` (already two spaces)              | safe                                                                         |
| `echo hi: # note` (colon before)                    | safe                                                                         |
| `# note\necho hi` (`#` at line start)               | safe                                                                         |
| `#!/usr/bin/env bash\necho hi`                      | safe                                                                         |
| `echo hi\t# note` (tab before)                      | safe                                                                         |
| `sed -i 's/# a/# b/' f`                             | safe                                                                         |

So the rule is precise and narrow — `X # ` where `X` is neither whitespace nor `:` — and it is
exactly the shape a trailing comment on a shell command takes. It is reachable through
`step({ run: … })`, the most ordinary call in the library.

The same regex also rewrites **comment payloads** and **custom headers**, because by the time it runs
those are text too. All three documented header forms corrupt, not just the string one:

```
withComment("CI", "see issue # 42 for details")   →  "# see issue  # 42 for details"
toYaml(w, { header: "build # 7 of pipeline" })    →  "# build  # 7 of pipeline"
toYaml(w, { header: (v) => `build # 7 by ${v.tool}` })  →  "# build  # 7 by ghagen"
```

The repo's own six generated files (`.github/workflows/*.yml`, `check-synth/action.yml`,
`check-deps/action.yml`) are **not** comment-free: they carry 37 inline pin comments of the shape
`uses: <sha>  # v6` (20 in `ci.yml`, 8 in `release.yml`, 4 in `docs.yml`, 3 in `schema-drift.yml`,
1 in each action). None is _corrupted_, because they are Python-generated and every one is already
at two columns — but "comment-free" was the wrong reason to believe `check-synced` is safe, and it
would let an implementer skip the check that actually matters (see migration step 8).

`check-synced` cannot detect the corruption either: write and check both go through the same
emitter, so the injected byte is stable across runs.

**The Python port does not have this defect.** The identical model emitted by `Workflow.to_yaml`
round-trips all four corrupt rows byte-exactly:

```yaml
run: |
  echo hi # not a yaml comment
  make build
run: 'echo a # b'
COLOR: 'red # crimson'
```

`packages/python/src/ghagen/emitter/yaml_writer.py` never touches the emitted text. It owns two
named **node-tree** passes — `_apply_block_scalar_style` (`:29-60`) and
`_apply_pre_comment_columns` (`:63-97`) — invoked from `dump_yaml` (`:122-123`), with the ruamel
geometry constants named in one place (`:20-26`). (The survey cited `:22-25,33-104`; those ranges
are stale — the numbers above are the tree as it stands.)

### 2. The gutter is nobody's decision — in **either** port. **Live**, and it diverges.

The survey's framing — structured decision in Python, untyped regex in TypeScript — is right about
the mechanism but too generous to Python. Python's two passes cover **block-comment columns** and
block-scalar promotion. Neither concerns the **inline** gutter, and no ghagen code decides it. It
falls out of `CommentedMap._yaml_get_column` (`ruamel.yaml` 0.19.1, `comments.py:733-758`), reached
from `yaml_add_eol_comment` (`:375-399`), which `attach` calls at
`packages/python/src/ghagen/emitter/comments.py:53`:

```python
# ruamel.yaml/comments.py:386-394
if column is None:
    try:
        column = self._yaml_get_column(key)   # peeks at a NEIGHBOURING key's comment
    except AttributeError:
        column = 0
if comment[0] != '#':
    comment = '# ' + comment
if column is None:
    if comment[0] == '#':
        comment = ' ' + comment               # ← the second column, only on this path
        column = 0
```

`_yaml_get_column` picks a neighbouring key and delegates to `_yaml_get_columnX`, which reads
`self.ca.items[key][2].start_mark.column` (`comments.py:730-731`) — slot 2 is the neighbour's **EOL**
token. When the neighbour carries only a _block_ comment that slot is `None`, `None.start_mark`
raises `AttributeError`, `column` becomes `0`, and the `' ' + comment` line is never reached.
Verified by direct call:

```
ca.items['name'] = [None, [CommentToken('# the name\n', col: 0)], None, None]
_yaml_get_column('on') → AttributeError: 'NoneType' object has no attribute 'start_mark'
```

The observable consequence, same model, one bit different — measured through `dump_yaml`:

```python
# no comment on a neighbouring key          # a block comment on the neighbouring key
name: Lint                                  # Run linters before tests
runs-on: ubuntu-latest  # job note          name: Lint
                                            runs-on: ubuntu-latest # job note
```

Python's inline gutter is **two columns normally and one column when an adjacent key in the same map
happens to carry a comment.** TypeScript's is one column after a `key:` and two after a scalar,
because of a character class in a regex. These are different rules that agree on
`fixtures/expected/comments.yml` and disagree off it.

**The case is not untested — it is tested green, asserting the bug.**
`packages/python/tests/test_emitter/test_comments.py:231` reads:

```python
assert "runs-on: ubuntu-latest # job note" in result
```

That is the one-column output, pinned by a passing test. It must be **inverted**, not restated.

`fixtures/expected/comments.yml` is the shared byte oracle for both ports
(`packages/typescript/src/paths.ts:41` resolves `fixtures/expected`; Python reaches the same
directory as `SNAPSHOT_DIR` at `packages/python/tests/test_integration/test_snapshots.py:39`, which
appends `"expected"` to `scripts/ghagen_schema/paths.py:35`). It contains exactly two inline
comments:

```yaml
# fixtures/expected/comments.yml:1-3 …and :14
# The name shown in the GitHub UI
name: Commented Workflow
on: # trigger configuration
  #   ⋮
  - name: Ruff # fast Python linter
```

Line 3 is one column _because_ line 1 exists — remove the block comment on `name` and Python emits
two columns while TypeScript still emits one. The oracle pins the single input on which two
unrelated mechanisms coincide. Drop the `withComment` on `name` and the ports diverge in bytes,
today, with no test to catch it.

### 3. A model's own EOL comment lands somewhere different in each port — **live**

Undisclosed by the survey and by this proposal's first draft; found by review and reproduced here.
`job({ eolComment: … })` is ordinary documented surface, and every Job's canonical order ends in
`steps`, so this is the **common** case, not an edge:

```
python     (main):  "    steps:  # job note\n    - run: x\n"
typescript (main):  "    steps:\n    - run: x\n    # job note\n"
```

Same in the seq-item container, with `step({ with_: {a: "1"}, eolComment: "note" })`:

```
python     (main):  "    - with:  # note\n        a: '1'\n"
typescript (main):  "    - with:\n        a: '1'\n        # note\n"
```

The mechanism is `attachModelComment` (`packages/typescript/src/emitter/comments.ts:86-103`): it
writes the EOL comment to the target pair's **value**, and when that value is a `YAMLMap` /
`YAMLSeq` the comment is swallowed into the nested block. `attachFieldComment` already solves this
for the field case by redirecting to the pair's **key** (`comments.ts:34-38`, with the reason in the
doc comment at `:22-24`); `attachModelComment` never got the same treatment. Python has no such
split: `yaml_add_eol_comment(key=…)` always renders on the key's line.

This matters to the module below for a second reason. `stringifyComment.lineComment`
(`yaml@2.8.3`, `dist/stringify/stringifyComment.js:16-20`) has **three** branches and only the last
contributes a column:

```js
const lineComment = (str, indent, comment) =>
  str.endsWith("\n")
    ? indentComment(comment, indent) // 1. value is a block map/seq — no column
    : comment.includes("\n")
      ? "\n" + indentComment(comment, indent) // 2. multi-line payload — no column
      : (str.endsWith(" ") ? "" : " ") + comment; // 3. exactly one column
```

"The `yaml` backend contributes exactly one column" is only true of branch 3. Any design that
pre-renders the gutter into the payload and leaves branch 1 reachable ships a spurious column —
measured on a built prototype, `job({runsOn:'x', eolComment:'job note', steps:[…]})` emitting
`     # job note` (five spaces) where `main` emits four. Fixing finding 3 is therefore a
**prerequisite** for the module, not an optional extra.

### 4. Python emits **invalid YAML** for a multi-line EOL comment — **live**

`with_eol_comment(value, "line one\nline two")` is accepted by the model layer and produces a
document that will not parse:

```
'name: CI  # line one\nline two\non:\n  push: {}\njobs: {}\n'
```

```
PARSE ERROR: ScannerError while scanning a simple key
  in "<file>", line 2, column 1: could not find expected ':'
```

No model-layer validation rejects the newline. TypeScript handles the same input — branch 2 of
`lineComment` degrades the payload to an indented comment block _below_ the value:

```yaml
name:
  CI
  # line one
  # line two
```

Neither behaviour was chosen by ghagen. One is valid, one is not, and they differ.

### What the four findings have in common

"How far from the value does an inline comment sit, where does it sit when the value is a block, and
what happens when it cannot sit there at all" is a single fact about emission geometry. Today it is:
a regex over finished text (TS), a ruamel private heuristic nobody calls deliberately (Python), a
container rule implemented in one of two sibling functions (TS), and two different backend fallbacks
for the multi-line case. It has no home, no name, and almost no test — the two `\s+` assertions in
`packages/typescript/src/emitter/yaml-writer.test.ts:125,141` are the entire TypeScript gutter
coverage, and `\s+` matches one space and two equally.

## Current interface

To place a comment correctly today a maintainer must know:

- **TS**: that `attachFieldComment` / `attachModelComment`
  (`packages/typescript/src/emitter/comments.ts:26-47,66-104`) write raw text into eight node slots;
  that the two disagree about where an EOL comment goes when the target value is a collection
  (`:34-38` redirects to the key, `:91-101` does not); that `formatYamlComment`
  (`yaml-writer.ts:389-395`) later `#`-prefixes each line via the `commentString` hook (`:447`);
  that `lineComment` then contributes one column, or none, depending on which of its three branches
  fires; and that a regex at `:403-405` widens one space to two afterwards by inspecting the whole
  document — including every scalar in it.
- **Python**: that `attach` (`comments.py:21-69`) delegates the EOL column to ruamel, whose answer
  depends on the neighbouring keys; that block-comment columns are _not_ delegated but rewritten by
  `_apply_pre_comment_columns` (`yaml_writer.py:63-97`) using `_MAP_VALUE_INDENT` /
  `_SEQ_ITEM_INDENT` (`:25-26`); and that the two mechanisms are unrelated.

Nothing in either port states the gutter as a value. `docs/specs/0003-comment-attachment-module.md:288-289`
explicitly deferred it — "`fixInlineCommentSpacing` **stays** — it is string-level output
normalization on the final dump, not node attachment." That classification is what this proposal
reopens: the pass is not normalization, it is the geometry decision, taken in the one representation
where the distinction between a comment and a `#` in a script no longer exists.

## Proposed interface

### (a) Give `attachModelComment` the container rule `attachFieldComment` already has

In `comments.ts`, when the EOL target pair's value is a `YAMLMap` or `YAMLSeq`, attach to the pair's
**key** instead of its value — the same three lines as `:34-38`. This closes finding 3, makes
TypeScript byte-identical to Python for `job({eolComment})` and for a seq-item model whose first
value is a collection, and removes `lineComment` branch 1 from the reachable set. It is a
prerequisite for (b), not a separable nicety.

### (b) A comment-geometry module in each port

`comment-geometry.ts` / `comment_geometry.py`. The TypeScript interface in full:

```ts
// packages/typescript/src/emitter/comment-geometry.ts

/** Columns between the end of a line's content and the `#` of its EOL comment. */
export const EOL_GUTTER = 2;

/** Render a block comment: `#`-prefix each line; a blank line becomes a bare `#`. */
export function renderBlockComment(text: string): string;

/**
 * Render an end-of-line comment, gutter included, or `null` when the payload
 * cannot sit at end-of-line.
 *
 * `stringifyComment.lineComment` (yaml@2.8.3,
 * `dist/stringify/stringifyComment.js:16-20`) has three branches and only the
 * third contributes a column. `comments.ts` makes the third the only reachable
 * one: an EOL comment is never attached to a collection *value* (it goes on the
 * key), and a payload containing a newline returns `null` here so the caller
 * places it as a block comment. The backend therefore contributes exactly one
 * column and this function contributes `EOL_GUTTER - 1`.
 */
export function renderEolComment(text: string): string | null;

/** The `commentString` hook for `Document.toString` — the identity. */
export const commentString: (rendered: string) => string;
```

**What a caller must know.**

1. **Types**: the two render functions, the backend hook, and the constant — four names.
   `comments.ts` is the only caller in the node path; `yaml-writer.ts` additionally calls
   `renderBlockComment` on the header string and passes `commentString` to `doc.toString`.
2. **Invariant**: a `yaml` node's `commentBefore` / `comment` slot may only ever hold a value
   returned by this module. Enforceable by inspection — the eight writes in `comments.ts` plus the
   header line at `yaml-writer.ts:432` are the complete set of writers in the package (verified:
   `commentBefore` and `.comment =` appear nowhere else outside tests). Because `commentString` is
   the identity, an unrendered payload reaches the output verbatim, which is a loud failure (invalid
   YAML in the snapshot tests), not a silent one.
3. **Ordering guarantee**: rendering is per-attachment and independent of document order, of
   sibling keys, and of which other nodes carry comments. This is precisely the property Python
   lacks today (finding 2), and it is what makes the gutter testable as a unit.
4. **Error mode**: `renderEolComment` returns `null` for a multi-line payload. `comments.ts` then
   attaches it as a block comment on the same item, joined **after** any existing block comment for
   that item with the same `\n` concatenation `attachModelComment` already uses at `comments.ts:80`
   (which joins in the other order, model comment first). Stated once, identical in both ports; no
   backend fallback is relied on.
5. **What it never does**: it never sees, and cannot see, the emitted document. It takes comment
   text and returns comment text. Scalar content is out of reach by construction.

`fixInlineCommentSpacing` and `formatYamlComment` are **deleted** from `yaml-writer.ts`;
`formatYamlComment`'s body becomes `renderBlockComment`. `toYaml` ends:

```ts
return doc.toString({ lineWidth: 0, indentSeq: false, singleQuote: true, commentString });
```

No `String.replace`. Built end to end against `yaml@2.8.3` on a throwaway `dist/` copy and measured:
all eleven rows of the corruption table round-trip exactly, `ci_basic.yml` is byte-identical,
`comments.yml` changes by exactly one byte at `:3` and nowhere else, and both H15 shapes match
Python byte-for-byte. The pre-rendered payloads reproduce every shape the current pipeline
produces — block comments at nested indents, seq-item block comments above the dash, and the
two-column gutter:

```yaml
# The name shown in the GitHub UI
name: Commented Workflow
on: # trigger configuration
  push: {}
job:
  # multi
  # line block
  runs-on: ubuntu-latest
  steps:
    # a step
    - name: Ruff # fast Python linter
      run: "echo hi # not a comment"
```

The last line is the point: the `#` in the script is left alone because nothing ever looked at it.

### Python peer

Same name, same constant, same stated rule; a different implementation, because ruamel resolves
comment columns absolutely at dump time rather than relatively at attach time. That asymmetry is
already the documented shape of the `comments.ts` / `comments.py` pair
(`docs/specs/0003-comment-attachment-module.md:291-298`: "the two modules play the identical role
while differing in internals").

```python
# packages/python/src/ghagen/emitter/comment_geometry.py
EOL_GUTTER = 2           # columns between content and `#`
_MAP_VALUE_INDENT = 2    # moved from yaml_writer.py:25
_SEQ_ITEM_INDENT = 2     # moved from yaml_writer.py:26

def render_eol_comment(text: str) -> str | None: ...
def apply_comment_geometry(node: CommentedMap) -> None: ...   # the single entry point
```

Three public names — the constant, the EOL renderer, and the one pass entry point. The two indent
constants stay underscore-private, as they are today.

`apply_comment_geometry` runs the two node-tree passes: `_apply_pre_comment_columns` (moved
verbatim from `yaml_writer.py:63-97`) and a new `_apply_eol_comment_gutter`, which walks
`node.ca.items` — slot 2 for a `CommentedMap`, slot 0 for a `CommentedSeq`, verified by direct
inspection — and rewrites each EOL `CommentToken.value` to `render_eol_comment(text)` at column 0, so
ruamel's neighbour heuristic never decides anything. Prototyped in-process against the real
`dump_yaml`: it normalises the neighbour-dependent case from one column to two and leaves the
already-correct cases byte-identical, including the `- uses: <sha>  # v6` shape that all 37 in-tree
pin comments take.

There is no `render_block_comment` peer, and that asymmetry is deliberate but incomplete —
see "What sits behind the seam".

`comments.py` additionally gains the multi-line check at its three EOL sites (`:53,67,69`),
redirecting a newline-bearing `eol_comment` to the block path — which is what makes finding 4 go
away.

`dump_yaml` (`yaml_writer.py:122-123`) becomes:

```python
_apply_block_scalar_style(data)      # scalar style — stays here
apply_comment_geometry(data)         # all comment geometry — one call
```

`yaml_writer.py` drops to roughly 95 lines and stops being two unrelated concerns in one file.

## What sits behind the seam

This is a **representation change with locality as a side effect**, not a deep module and not a
relocation. Four exported names in TypeScript and three in Python sit in front of perhaps fifteen
lines of body — calling that "deep" would be overclaiming. What is real is the change of
representation: the gutter decision moves from _finished document text_, where a comment `#` and a
script `#` are indistinguishable, to _comment text at attach time_, where scalar content is out of
reach by construction. That is what makes finding 1 impossible rather than narrower.

Behind the names sit the backend-specific facts that are currently undiscoverable without reading
library source: `lineComment`'s three branches and which of them contributes a column; ruamel's
`_yaml_get_column` heuristic and its `AttributeError` path; the map-vs-seq `ca.items` slot indices;
the map/seq indent widths; and the multi-line degradation rule.

**Parity here is of role, not of structure, and the split is uneven.** TypeScript's module owns
block-comment _rendering_ (the `#` prefix) and the EOL gutter; it owns nothing about block-comment
_columns_, which the `yaml` backend indents automatically. Python's module owns block-comment
_columns_ and the EOL gutter; it owns nothing about the `#` prefix, which stays in ruamel's
`yaml_set_comment_before_after_key` for node comments and in `header.py::_wrap_as_comment`
(`packages/python/src/ghagen/emitter/header.py:129-132`) for the header — a second, independent
implementation of the same `#`-prefix-per-line rule that this proposal does **not** unify. Naming
that residual is more useful than claiming the module "owns every answer to where the `#` goes",
which is true of TypeScript only. Unifying Python's two `#`-prefix implementations is 13's call,
since 13 owns `header.py`.

The leverage: `comments.ts` / `comments.py` go back to being purely about _which node_ a comment
attaches to, and know nothing about columns. `yaml-writer.ts` goes back to being purely about node
construction and stops owning a text-rewriting pass over its own output.

The locality: "the inline gutter is two columns" appears once per port instead of zero times, and
a change to it is a one-line edit with a unit test attached, not a regex whose blast radius is
every scalar in every emitted document.

Deliberately **not** proposed: a pluggable geometry adapter. The two implementations live in
different packages and neither package will ever hold two; that would be a hypothetical seam of the
kind proposal 07 removed.

## Migration plan

Pre-1.0; clean break. TypeScript leads, Python mirrors in the same change so the shared fixture is
never red between steps. Rebases onto 20.

1. `comments.ts`: give `attachModelComment`'s EOL path (`:86-103`) the key redirect that
   `attachFieldComment` has at `:34-38`, in both the `atSeqItem` and map-value branches. Update the
   doc comment at `:56-61`, which currently promises "the EOL comment on the last value". This step
   alone changes emitted bytes and closes finding 3; land it with its own parity tests.
2. Add `comment-geometry.ts` with `EOL_GUTTER`, `renderBlockComment` (body lifted from
   `formatYamlComment`, `yaml-writer.ts:389-395`), `renderEolComment`, `commentString`.
3. Route the eight node-comment writes in `comments.ts` through the renderers; add the multi-line
   redirect at the two EOL sites (`:33-46`, `:86-103`).
4. `yaml-writer.ts`: render the header with `renderBlockComment` (`:430-433`), pass the identity
   `commentString` (`:447`), **delete** `formatYamlComment` and `fixInlineCommentSpacing`
   (`:389-405`) and the call at `:450`.
5. Add `comment_geometry.py`; move `_MAP_VALUE_INDENT` / `_SEQ_ITEM_INDENT` and
   `_apply_pre_comment_columns` into it; add `_apply_eol_comment_gutter` and
   `apply_comment_geometry`; point `dump_yaml` at the single entry; drop "comment-column alignment"
   from the `yaml_writer.py` module docstring (`:1-6`).
6. `comments.py`: add the multi-line redirect at `:53,67,69`.
7. Update `fixtures/expected/comments.yml:3` to `on:  # trigger configuration`. This is the only
   byte change to any fixture; both ports produce it after steps 1-6, verified by generating the
   fixture from each port independently and diffing them against each other (identical) and against
   the current fixture (one line). Every other fixture is comment-free — `comments.yml` is the only
   file in `fixtures/expected/` containing a `#` at all — and must stay byte-identical.
8. Update `docs/src/content/docs/guides/comments.mdx`. Four emitted-YAML lines are wrong today:
   `:77` shows `run: ruff check . # fast Python linter`, wrong in both the gutter _and_ the
   placement (the real output is `- name: Ruff  # fast Python linter`, as
   `fixtures/expected/comments.yml:14` shows); `:153` and `:234` show a one-column `on: #`; and
   `:244` (`- # fast Python linter` above `name: Ruff`) plus the "Known limitations" note at
   `:318-320` describe a seq-item EOL rendering that spec 0003 already fixed
   (`packages/python/tests/test_emitter/test_comments.py:153` asserts
   `- uses: actions/checkout@v4  # checkout step`). Correcting them is in scope because this
   proposal is what makes the documented geometry a stated rule.
9. Full suite both ports; `uv run ghagen check-synced`. The repo's own six generated files carry 37
   inline pin comments, all Python-generated, all of the seq-item `- uses: <sha>  # v6` shape and
   all already at two columns. The Python pass leaves that shape byte-identical (verified against
   `dump_yaml`), so `check-synced` stays green — but it must actually be run, and a byte diff on any
   of the six is a real regression, not noise.

## Test impact

The suite currently cannot fail on findings 1, 3 or 4, and _passes_ on finding 2's bug. After this
change each has a test that fails on `main`.

- **New (TS, `yaml-writer.test.ts`)**: round-trip guard. For each shape in the corruption table,
  emit a workflow whose step `run` is that string and assert
  `YAML.parse(toYaml(w)).jobs.j.steps[0].run` equals the input exactly. Fails on `main` for the four
  corrupt rows. Written as a round-trip rather than a substring match because the corrupted output
  is _valid YAML_, so only comparing against the input catches it.
- **New (TS)**: `withComment("CI", "see issue # 42")` emits `# see issue # 42`; and all three header
  forms — `header: "build # 7"`, `header: (v) => …` containing `#`, and the default — survive
  verbatim. All fail on `main`.
- **New (both) — finding 3, the H15 parity pair**: `job({runsOn, eolComment, steps})` must emit
  `steps:  # job note` above the steps list, and a seq-item model whose first value is a map must
  emit `- with:  # note`. Byte-exact, identical strings asserted in both ports. **TypeScript fails
  on `main`** in both cases (the comment lands below the block); Python passes and is the reference.
- **Tightened (TS, `yaml-writer.test.ts:125,141`)**: `/name: ci\s+# inline note/` →
  `` `name: ci${" ".repeat(EOL_GUTTER)}# inline note` ``. `\s+` is why the gutter was never pinned.
- **New (TS, `comment-geometry.test.ts`)**: `renderBlockComment` on empty and multi-line input;
  `renderEolComment` returns `null` for a newline payload; `renderEolComment("x") === " # x"`, i.e.
  `EOL_GUTTER - 1` spaces wide, with a comment naming the backend's contributed column and the
  branch of `lineComment` that supplies it.
- **New (both) — finding 2, the neighbour-independence pair**: (i) a workflow with an EOL comment on
  `on:` and **no** comment on any neighbouring key — assert `on:  # …` byte-exactly; Python already
  emits two columns and passes, **TypeScript fails on `main`** with one. (ii) the mirror case, the
  same workflow **with** a block comment on `name` — **Python fails on `main`** with one column.
  Together they pin the gutter as neighbour-independent in both ports.
- **Inverted (Python, `test_comments.py:231`)**: `assert "runs-on: ubuntu-latest # job note" in result`
  becomes `"runs-on: ubuntu-latest  # job note"`. This is an existing **green** test asserting the
  buggy one-column output; it is the second half of the mirror pair above and must flip, not be
  restated.
- **New (both)**: `with_eol_comment(v, "a\nb")` / `withEolComment(v, "a\nb")` emits parseable YAML
  with the payload as a block comment above the item. Python fails on `main` with a `ScannerError`
  (finding 4); TypeScript's placement changes from indented-below to above.
- **Rewritten (TS, `comments.test.ts:32,45,74,91,112`)**: these read raw text out of node slots
  (`expect((pair.key as Scalar).commentBefore).toBe("The name")`). They become
  `toBe(renderBlockComment("The name"))` — still asserting attachment, now through the module that
  owns the payload format. Two new cases cover the EOL-on-collection redirect from step 1.
- **New (Python, `test_comment_geometry.py`)**: the first _direct_ tests of
  `_apply_pre_comment_columns` and `_apply_eol_comment_gutter`. **No test moves.** The earlier claim
  that `test_yaml_writer.py`'s pre-comment-column tests follow the function to a new home was wrong:
  `test_yaml_writer.py` never imports or names `_apply_pre_comment_columns` (its emitter imports are
  `_apply_block_scalar_style` and `dump_yaml`, `:23-26`), and the pass's only coverage today is
  indirect, through `dump_yaml`, at `test_comments.py:196,199,218`. Those three assertions stay
  where they are and keep passing; the only change to `test_yaml_writer.py` is its module docstring
  (`:1-10`), which claims the comment-column pass is exercised there.
- **Unchanged (`test_comments.py:129,153`)**: `"- main  # primary branch"` and
  `"- uses: actions/checkout@v4  # checkout step"` keep passing byte-for-byte, verified against the
  prototyped pass. They stay literal — a byte oracle should read as bytes; `EOL_GUTTER`'s value is
  pinned once per port in the geometry unit tests.

Baseline is pytest 562 / vitest 515; expect roughly +12 pytest and +16 vitest, plus one inverted
pytest assertion.

## Risks & alternatives

- **Alternative: keep the regex, tighten it.** Rejected. There is no lookbehind that distinguishes a
  comment `#` from a script `#`, because the information that made them different was discarded when
  the tree was serialized. Any tightening trades one class of false positive for another; the
  `curl https://x/y#frag # note` row shows the regex already half-guessing.
- **Alternative: delete `fixInlineCommentSpacing` outright and accept a one-column gutter.**
  Rejected, and worth stating because it is the cheap option. With the pass removed and nothing in
  its place, `lineComment` branch 3 yields `name: Ruff # fast Python linter`. Python's default is
  two columns. Deleting the pass makes every inline comment in every document diverge between the
  ports, trading a narrow data bug for a broad parity break.
- **Alternative: make Python match TypeScript instead.** Rejected. TypeScript's rule is
  _"two columns, except one after a colon"_ — an artefact of a character class, not a convention
  anyone chose. Python's neighbour-free default (two) is also ruamel's, so standardising on two
  changes one fixture byte instead of many.
- **Risk: `header: ""` changes TypeScript's emitted bytes, and no fixture covers it.** Real, and it
  moves toward parity. On `main`, `doc.commentBefore = ""` is falsy so the `yaml` backend emits no
  header at all; pre-rendering makes it `renderBlockComment("") === "#"`, which is truthy, so
  TypeScript starts emitting a bare `#` — which is what Python already does
  (`_wrap_as_comment("")` → `"#\n"`). No test or fixture exercises `header: ""` today
  (`grep 'header: ""'` over `packages/typescript/src` returns nothing). **13 owns this shape** and
  adds `fixtures/expected/header_empty.yml` for it; 13 must pin it against the post-12 tree, not
  against `main`. Flagged rather than fixed here because header shapes are 13's, not this
  proposal's.
- **Risk: the Python fix reads a ruamel-private structure (`node.ca.items`, `CommentToken.value`).**
  Accepted. `_apply_pre_comment_columns` already does exactly this (`yaml_writer.py:79-84`), and
  after this change there is one module doing it instead of two, with the coupling named in its
  docstring alongside the pinned ruamel version (0.19.1).
- **Risk: the identity `commentString` makes an unrendered payload emit raw text.** Accepted, and
  preferred to the alternative. The failure is immediate and total (invalid YAML in the snapshot
  tests) rather than a one-byte drift nobody notices; and the writer set is nine lines in two files,
  all listed above.
- **Deletion test — the module.** Delete `comment-geometry.ts` and three facts — `EOL_GUTTER`, which
  `lineComment` branch is reachable and what it contributes, and the multi-line degradation rule —
  reappear at the five EOL writes and three block writes in `comments.ts` plus the header line in
  `yaml-writer.ts`. Delete `comment_geometry.py` and the two node-tree passes plus three
  indent/gutter constants scatter back into `yaml_writer.py` and `comments.py`. Complexity reappears
  across N callers — it earns its keep. It is not a pass-through: the current code has no module
  here at all, and that is the defect.
- **Deletion test — `fixInlineCommentSpacing`.** Delete it _with_ the module in place and nothing
  reappears; the gutter is already decided upstream. Delete it _without_ the module and the
  `comments.yml` fixture regresses. That asymmetry is the whole proposal: the pass is doing real
  work in the wrong representation.

### Scope boundaries vs siblings

- **20 (delete caller-less pin/spec surface) — merges FIRST, disjoint hunks in a shared file.**
  20 deletes the `extrasPlacement` / `withinOrder` branch at `yaml-writer.ts:202-205` (**not**
  `:201`, which binds `orderKeys` and is consumed at `:207`) and trims the doc comment at `:180`
  and `:185-187`. All of that is inside `orderedEntries` (`:189-215`); mine is
  `formatYamlComment` / `fixInlineCommentSpacing` / `toYaml` (`:389-451`) plus the header line at
  `:430-433`. This proposal is written against the **pruned** tree: it builds on top of 20's
  `:202-205` and `:180,:185-187` deletions and nothing else of 20's, and its `yaml-writer.ts` line
  numbers shift up by as much as 7 once 20 lands. `extrasPlacement` is 20's, uncontested.
- **13 (unify the `format_header` contract) — merges AFTER, six shared files plus both CONTEXT.md.**
  The shared set is larger than either document first recorded: `yaml-writer.ts`, `yaml_writer.py`
  (adjacent lines inside `dump_yaml`), `packages/python/tests/test_emitter/test_yaml_writer.py`,
  `packages/python/tests/test_integration/test_snapshots.py`,
  `packages/typescript/src/integration/snapshots.test.ts`, and
  `docs/src/content/docs/guides/comments.mdx` — plus `packages/{typescript,python}/CONTEXT.md`
  (region `:34-38`, see the last section). Fixtures do **not** collide: this proposal adds none and
  edits only `comments.yml`; 13 adds six new `header_*.yml`.
  **12 goes first for three reasons.** 13's proposed `toYaml` still calls `fixInlineCommentSpacing`,
  which this proposal deletes. 13's `header_closure.yml` fixture contains a literal `#` and has
  stable bytes only once that regex is gone (`header: (v) => "build # 7"` → `# build  # 7` today).
  And 12 changes the `header: ""` shape 13 pins (see Risks). The edge is acyclic:
  `comment-geometry.ts` is a leaf that imports nothing from `header.ts`, so it does not invert
  `yaml-writer.ts:11`.
  **What 12 hands 13, explicitly:** the exported `renderBlockComment` is the `#`-prefix-per-line
  rule 13 needs when `formatHeader` starts returning a pre-wrapped block — it is the TypeScript peer
  of Python's `header.py::_wrap_as_comment` (`:129-132`), and 13 should import it rather than write
  a third copy. Header _content_ rules — templates, variables, `formatHeader`'s four shapes — stay
  entirely 13's; this proposal touches only how the resulting string reaches the node, one line at
  `yaml-writer.ts:432`. `emitter/header.ts` and `emitter/header.py` are not in my table.
- **24 (narrow `walk()`) — narrower than either document assumed; no serialization needed.**
  The only shared file is `yaml-writer.ts`, and 24 lists it under _Not touched, deliberately_
  (`24` §Not touched, deliberately) and states in its `12 — 24` entry under _Risks & alternatives_ that it **does not
  edit** it (`24` §Risks & alternatives, measured by `tsc --noEmit` over a copy with only `_base.ts` patched): the
  narrowing removes parameters, so the `clone.walk((node) => {…})` call site (`yaml-writer.ts:46`,
  inside `dedentSteps`, `:44-52`) compiles unchanged. This proposal does not touch `dedentSteps`,
  `clone` (`:45`) or that call, and its `yaml-writer.ts` edits (`:389-405`, `:430-433`, `:447`,
  `:450`) are all outside `:44-52`. 24 also disclaims
  `packages/python/tests/test_emitter/test_yaml_writer.py` (`24` §Not touched, deliberately), which it does not touch and
  which this proposal shares with 10 (`10` §Modified — TypeScript source), not with 24. **Zero shared lines** — 24 reaches the
  same conclusion independently (`24` §Risks & alternatives). Residual contact: compile-compatibility at
  `yaml-writer.ts:46` and the file name. Hand-merge; do not serialize.
- **10 (delete `ModelSpec.order`) — semantic edge, no file overlap.** This proposal changes
  `fixtures/expected/comments.yml:3` by one byte. 10's zero-byte-delta acceptance criterion must
  therefore be read against the tree **at 10's land time**, not against today's fixtures: after 12,
  `comments.yml:3` reads `on:  # trigger configuration`. 10 has been told the same; the two
  documents agree that the fixture bytes move, once, here.
- **02's observation surface** (`toData` / `to_data`) is unaffected: it never renders comments to
  text, it returns `CommentNode` values (`yaml-writer.ts:269-273`). Comment _geometry_ is only
  observable through the YAML string — `toData`'s own doc comment says as much at
  `yaml-writer.ts:296-299` ("Unlike `toYaml`, this does not run the `yaml`-backend passes … assert
  those via the YAML string"), which is why the new tests assert bytes. ADR-0001's 2026-07-28
  amendment (`docs/adr/0001-*.md:41-47`) puts model assertions on `toData`; geometry is exactly the
  exception that doc comment carves out.

## ADR / CONTEXT.md impact

- **No ADR contradicted.** ADR-0001's 2026-07-21 amendment (`:24`) puts all serialization recursion
  in the Emitter; this moves a decision from the tail of `toYaml` into a named Emitter module and
  out of text. No ADR mentions comment columns.
- **`docs/specs/0003-comment-attachment-module.md:288-289` is amended.** It ruled
  `fixInlineCommentSpacing` "string-level output normalization on the final dump, not node
  attachment," and kept it. The spec's _boundary_ claim is correct and this proposal honours it —
  the gutter is not node attachment, so it goes in a third module rather than into `comments.ts`.
  What the evidence above defeats is the **classification**: the pass makes a geometry decision, and
  making it on finished text is what corrupts `run` scripts. Amend `:288-289` with a pointer here
  rather than editing the spec's history. Spec 0003's parity argument (`:297-298`, "parity is at the
  interface's _responsibility_") is reused unchanged for the TS/Python asymmetry in this module.
  **Open — Phase 3 decision:** whether `docs/specs/0003:288-289` is amended in place or annotated
  with a dated addendum. Either records the same correction; the choice is the user's, as with every
  reversal of a written decision.
- **`packages/typescript/CONTEXT.md:34-38` and `packages/python/CONTEXT.md:34-38` — the Emitter
  entry, and nothing else.** The round's region map assigns `:34-38` jointly to 12 and 13, 12 first,
  or merged into a single sentence at merge time. The entry lists "comments" among what the Emitter
  owns; add that comment _geometry_ — the inline gutter and the block-comment column — is a named
  module with a stated constant, and that no Emitter pass rewrites emitted text. **No new glossary
  term is claimed**: the earlier draft proposed a **comment geometry** entry, which would have taken
  a line outside `:34-38` and collided with the map. The definition folds into the Emitter sentence
  instead.
