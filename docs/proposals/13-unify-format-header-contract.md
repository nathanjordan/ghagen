# 13 — Unify the `format_header` contract and put headers under the shared byte oracle

**Status:** proposed | **Ports:** both (typescript changes, python is the reference) | **Effort:** L | **Depends on:** **12** (a real comment-geometry module in the TS Emitter) — an **ordering** edge, not a cycle. 12 deletes `fixInlineCommentSpacing` and `formatYamlComment` from `yaml-writer.ts` and exports `renderBlockComment` from the new `comment-geometry.ts`; 13's `toYaml` and `header.ts` are written against that tree, and the two proposals share **seven** files. **12 goes first**

## Files involved

Line counts, and every emitted-byte measurement in this document, taken at `main` `e7a972c`. Every
`packages/typescript/src/emitter/yaml-writer.ts`
line number below is a **pre-20, pre-12** coordinate: 20 prunes `:180`, `:185-187` and `:202-205`,
so anything cited below `:205` shifts by up to 7 lines before 13 is written, and 12 then rewrites
`:389-451` outright.

### Modified

| Path                                                       | Lines | Role in this proposal                                                                                                                                                                                    |
| ---------------------------------------------------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/typescript/src/emitter/header.ts`                | 134   | `formatHeader` returns the `#`-prefixed block (or `null`); the false "identical headers" comment at `:4-5` is corrected; gains `splitHeaderLines` + `wrapAsComment`                                      |
| `packages/typescript/src/emitter/yaml-writer.ts`           | 480   | `toYaml` stops routing the header through `doc.commentBefore` (`:430-433`) and concatenates it instead. **Shared with 12** (same function body)                                                          |
| `packages/python/src/ghagen/emitter/header.py`             | 176   | `format_header`'s docstring becomes the normative contract for both ports; `_wrap_as_comment` (`:129-132`) states its line-break set instead of inheriting it from `str.splitlines()`                    |
| `packages/python/src/ghagen/emitter/yaml_writer.py`        | 132   | `dump_yaml`'s `header` parameter (`:126-129`): two dead guards deleted, invariant stated. **Shared with 12** (adjacent lines in the same function: 12 edits `:122-123`, 13 edits `:125-130`)             |
| `packages/typescript/src/emitter/header.test.ts`           | 65    | every expectation flips to the wrapped shape; new shape cases (`""`, trailing break, CR/CRLF)                                                                                                            |
| `packages/typescript/src/emitter/yaml-writer.test.ts`      | 244   | the five header tests at `:34-64` are all `toContain` — blind past the first line; they become whole-output equality. **Shared with 12** (12's hunks are `:125,141` plus new round-trip tests; disjoint) |
| `packages/python/tests/test_emitter/test_header.py`        | 140   | add the shapes Python does not currently pin (`""`, trailing break, CR/CRLF, and the non-LF Unicode breaks)                                                                                              |
| `packages/python/tests/test_emitter/test_yaml_writer.py`   | 205   | `test_dump_yaml_with_header` (`:91-95`) follows the tightened `dump_yaml` interface. **Shared with 12**                                                                                                  |
| `packages/python/tests/test_integration/test_snapshots.py` | 451   | six new header golden cases                                                                                                                                                                              |
| `packages/typescript/src/integration/snapshots.test.ts`    | 293   | the six peer cases. **Shared with 12** (12 changes the `comments.yml` case at `:36-61`)                                                                                                                  |
| `packages/python/tests/test_integration/test_header.py`    | 191   | `startswith` / `in` assertions become whole-output equality (see Test impact)                                                                                                                            |
| `docs/src/content/docs/guides/comments.mdx`                | 320   | document the emitted shape: no blank line after the header, `""` renders a bare `#`, one trailing break dropped. **Shared with 12** (12 edits `:77,153,234,244,318-320`; 13 edits `:268,314`)            |
| `docs/issues/02-fixture-coverage-gaps.md`                  | 8     | amend — headers were a fifth, unrecorded fixture gap                                                                                                                                                     |
| `packages/python/CONTEXT.md`                               | 114   | Emitter entry (`:34-38`) + a new **Header** glossary entry after **CommentNode** (`:49-51`); applied in the implementation phase, wording in the last section                                            |
| `packages/typescript/CONTEXT.md`                           | 119   | Emitter entry (`:34-38`) + a new **Header** glossary entry after **CommentNode** (`:51-53`); same                                                                                                        |

### New

| Path                                       | Role in this proposal                                                  |
| ------------------------------------------ | ---------------------------------------------------------------------- |
| `fixtures/expected/header_string.yml`      | single-line string header                                              |
| `fixtures/expected/header_multiline.yml`   | multi-line header with an interior blank line **and** a trailing break |
| `fixtures/expected/header_crlf.yml`        | CRLF **and** bare CR in the header text                                |
| `fixtures/expected/header_empty.yml`       | `header=""`                                                            |
| `fixtures/expected/header_closure.yml`     | closure return value, containing a literal `#`                         |
| `fixtures/expected/header_doc_comment.yml` | header **plus** a root Document comment                                |

`header=None` needs no new fixture: all ten existing goldens already assert it.

Not touched, deliberately: `packages/python/src/ghagen/emitter/document.py` (`emit` at `:48-49`
already threads `format_header`'s return straight into `dump_yaml`), `packages/typescript/src/app.ts`,
`packages/python/src/ghagen/app.py` (input shapes are unchanged),
`packages/typescript/src/emitter/comment-geometry.ts` (13 **imports** 12's `renderBlockComment`; it
adds nothing to that module), `packages/typescript/src/integration/test-utils.ts` and
`packages/python/tests/test_integration/conftest.py` (see _Risks_: the DEFAULT-branch fixture and its
two masking helpers are dropped), and the ten existing goldens.

## Problem

`format_header` / `formatHeader` are peer modules in the two ports' Emitters. They accept the same
four input shapes and are documented as behaving identically —
`packages/typescript/src/emitter/header.ts:4-5` says so in as many words:

```ts
 * Mirrors `packages/python/src/ghagen/emitter/header.py` so the two
 * implementations emit identical headers given identical inputs.
```

That claim is false. Measured by emitting **one identical single-job workflow** through both ports,
there is **one interface divergence** (§1) and **five emitted-byte divergences** (§2–§6) arising
from **four mechanisms**:

| Mechanism                                                           | Divergences | Owner                                         |
| ------------------------------------------------------------------- | ----------- | --------------------------------------------- |
| the `yaml` library's unconditional blank line after `commentBefore` | 2, 6        | **13**                                        |
| `""` is falsy, so the header is dropped entirely                    | 3           | **13**                                        |
| two different line-splitting rules                                  | 4           | **13**                                        |
| `fixInlineCommentSpacing` rewrites the header text                  | 5           | **12** (already claimed at `12` §Test impact) |

12 closes divergence 5 by deleting the pass. 13 closes the other four. None of the five is caught,
because the repo's byte oracle — the shared `fixtures/expected/` goldens asserted by both suites —
passes `header=None` in **every** case and therefore contains zero header bytes (§7).

### 1. The two peers return different things (live, interface)

Python wraps; TypeScript does not.

```python
# packages/python/src/ghagen/emitter/header.py:129-132
def _wrap_as_comment(text: str) -> str:
    """Wrap *text* with ``# `` line prefixes, terminated by a newline."""
    lines = text.splitlines() or [""]
    return "\n".join(f"# {line}" if line else "#" for line in lines) + "\n"
```

```ts
// packages/typescript/src/emitter/header.ts:110-111 (docstring), 120-122
 * Returns the comment text without `#` prefixes — the yaml library handles
 * comment formatting automatically.
...
  if (typeof header === "string") {
    return header;
  }
```

So the `#` prefix, the line-splitting rule, and the trailing newline are **inside** the Python module
and **outside** the TypeScript one. In TS they are re-decided by the backend: `formatYamlComment`
(`yaml-writer.ts:389-395`) does the `#` prefixing and the `yaml` library decides placement. Two
callers, two different renderings of "the header." This is not itself a byte divergence — it is the
reason the next five exist.

### 2. TS inserts a blank line after every header; Python never does (live)

`toYaml` hands the header to the document node (`yaml-writer.ts:430-433`):

```ts
const headerStr = formatHeader(options?.header, target.sourceLocation);
if (headerStr !== null) {
  doc.commentBefore = headerStr;
}
```

`yaml@2.8.3` unconditionally separates a document `commentBefore` from the body
(`packages/typescript/node_modules/yaml/dist/stringify/stringifyDocument.js:23-27`):

```js
if (doc.commentBefore) {
  if (lines.length !== 1) lines.unshift(""); // ← the blank line, library-owned
  const cs = commentString(doc.commentBefore);
  lines.unshift(stringifyComment.indentComment(cs, ""));
}
```

`lines` is empty at that point (ghagen emits no directives and no `---`), so `lines.length !== 1`
always holds and the blank line is always inserted. Python's `dump_yaml` writes the header straight
to the stream and then dumps (`packages/python/src/ghagen/emitter/yaml_writer.py:125-130`):

```python
    stream = StringIO()
    if header:
        stream.write(header)
        if not header.endswith("\n"):
            stream.write("\n")
    yaml.dump(data, stream)
```

Measured on the same workflow, first bytes:

| Input                                      | Python                            | TypeScript                            |
| ------------------------------------------ | --------------------------------- | ------------------------------------- |
| `header="Hand written"`                    | `# Hand written\nname: CI\n`      | `# Hand written\n\nname: CI\n`        |
| `header=lambda v: f"built by {v['tool']}"` | `# built by ghagen\nname: CI\n`   | `# built by ghagen\n\nname: CI\n`     |
| `header="line1\n\nline3"`                  | `# line1\n#\n# line3\nname: CI\n` | `# line1\n#\n# line3\n\nname: CI\n`   |
| `header=None`                              | `name: CI\n`                      | `name: CI\n` (the only agreeing case) |

The Python shape is the one the repo itself ships: all four of `.github/workflows/*.yml` open
`# This file is generated by ghagen from .github/ghagen_workflows.py.` /
`# Do not edit manually.` / `name: …` with no blank line. **12 does not change this** — it
pre-renders the payload but still assigns it to `doc.commentBefore` (`12` §Migration plan), so the library still
inserts the separator. Divergence 2 is 13's alone.

### 3. `header=""` diverges — and the symptom changes when 12 lands (live)

On `main`: `formatHeader("")` returns `""` (`header.ts:120-122`), `"" !== null` so
`doc.commentBefore = ""` (`yaml-writer.ts:431-433`), and `if (doc.commentBefore)` at
`stringifyDocument.js:23` is falsy — the header is dropped outright. Python's `_wrap_as_comment("")`
takes the `or [""]` branch at `header.py:131` and returns `"#\n"`.

|             | Python          | TypeScript (`main`) | TypeScript (post-12) |
| ----------- | --------------- | ------------------- | -------------------- |
| `header=""` | `#\nname: CI\n` | `name: CI\n`        | `#\n\nname: CI\n`    |

Post-12 the header is pre-rendered, and `renderBlockComment("") === "#"` is truthy, so it survives —
the divergence stops being "the header vanishes" and becomes "the header is followed by a blank
line," i.e. it collapses into divergence 2. **The golden must therefore be generated against the
post-12 tree, not against `main`**, and the `""` shape is currently covered by no test or fixture in
either port.

Either way, `""` means "no header" in one port and "an empty comment line" in the other. This is the
same class of bug the port already treats as serious: `None`/`null` vs the DEFAULT sentinel exists
precisely so "no header" is unambiguous, and `""` re-introduces a third, undeclared meaning that the
two ports resolve differently.

### 4. Line splitting differs: trailing breaks, CR, CRLF and the non-LF Unicode breaks (live)

Python uses `str.splitlines()`, which drops exactly one trailing break and treats `\r\n`, a bare
`\r`, and seven further characters as breaks. TS's `formatYamlComment` splits on `"\n"` only
(`yaml-writer.ts:392`); 12's `renderBlockComment` lifts that body verbatim (`12` §Migration plan), so this
divergence survives 12 unchanged. Measured, both ports, same workflow:

| Header text        | Python `format_header`  | TS (`main` and post-12)                              |
| ------------------ | ----------------------- | ---------------------------------------------------- |
| `"x\n"`            | `# x\n`                 | `# x\n#\n` — a spurious bare `#`                     |
| `"x\n\n"`          | `# x\n#\n`              | `# x\n#\n#\n`                                        |
| `"a\r\nb"`         | `# a\n# b\n`            | `# a\r\n# b\n` — a **literal CR inside the comment** |
| `"a\rb\rc"`        | `# a\n# b\n# c\n`       | `# a\rb\rc\n` — two literal CRs, one line            |
| `"a\vb"`           | `# a\n# b\n`            | `# a\vb\n` — a literal VT inside the comment         |
| `""`               | `#\n`                   | _(see §3)_                                           |
| `"\nx"`            | `#\n# x\n`              | `#\n# x\n`                                           |
| `"line1\n\nline3"` | `# line1\n#\n# line3\n` | `# line1\n#\n# line3\n`                              |

The control-character rows are not cosmetic. **ruamel refuses to read the documents TypeScript
writes for them** — measured against `ruamel.yaml` 0.19.1 on `# a<C>b\nname: CI\n`:

| `<C>`                                   | ruamel                                                                                                                   | `yaml@2.8.3` |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------ |
| `\v` (0x0B), `\f` (0x0C), `\x1c`–`\x1e` | `ReaderError: unacceptable character #x000b: special characters are not allowed`                                         | parses       |
| `\x85` (NEL), U+2028, U+2029            | `ScannerError: mapping values are not allowed here` (ruamel treats it as a line break on read, so `b` starts a new line) | parses       |

So the trailing-`\n` and CR cases are byte divergences, and the rest are byte divergences that also
make the TypeScript port emit YAML the Python port cannot parse. A trailing `\n` is not exotic
either — the docs' own closure example (`comments.mdx:285-290`) builds its header by concatenating
an f-string that ends in `\n` with a second line, and a user who stops after the first line gets an
extra `#` in TypeScript only.

### 5. TS's inline-comment-spacing pass rewrites the user's header text (live — **12 owns this**)

`fixInlineCommentSpacing` (`yaml-writer.ts:403-405`) runs over the **whole** rendered document,
header included:

```ts
function fixInlineCommentSpacing(yaml: string): string {
  return yaml.replace(/([^\s:]) (# )/g, "$1  $2");
}
```

| Input                               | Python                       | TypeScript (`main`)           |
| ----------------------------------- | ---------------------------- | ----------------------------- |
| `header="see foo.py # for details"` | `# see foo.py # for details` | `# see foo.py  # for details` |

`comments.mdx:268` promises string headers are emitted "verbatim." In TS on `main` they are not.
**This divergence is 12's, not 13's**: 12 deletes the pass outright (`12` §Migration plan) and already claims the
regression test (`12` §Test impact, TypeScript-side). 13 does not re-claim it. It is listed here only
because it is one of the five, and because `header_closure.yml` carries a `#` payload as a
standing **cross-port** byte guard — a guard 12's TS-only unit test does not provide, and which is
free once the fixture exists.

### 6. Header + root Document comment (live)

The same library-owned blank line lands between the header and the Document's own top-level comment:

| Input                                                 | Python                                           | TypeScript                                         |
| ----------------------------------------------------- | ------------------------------------------------ | -------------------------------------------------- |
| `header="Hand written"`, `comment="root doc comment"` | `# Hand written\n# root doc comment\nname: CI\n` | `# Hand written\n\n# root doc comment\nname: CI\n` |

Same mechanism as divergence 2, and it closes for the same reason: once the header never reaches
`doc.commentBefore`, the Document's own comment is the only `commentBefore` there is, and it renders
flush against the body exactly as Python's does. 12 does not touch it — 12 changes the Document
comment's _payload_ rendering, not the separator.

### 7. The byte oracle covers zero header bytes (live)

Every shared-fixture assertion in both suites passes `header=None`:

- `packages/python/tests/test_integration/test_snapshots.py` — all ten: `:66, 110, 151, 183, 217,
316, 358, 385, 411, 451`.
- `packages/typescript/src/integration/snapshots.test.ts` — the same ten: `:33, 61, 91, 115, 137,
156, 221, 253, 272, 291`.
- `packages/typescript/src/integration/schema-validation.test.ts:17,21` — also `header: null`.
- The non-fixture Python integration suites too: `test_full_workflow.py` (9 call sites),
  `test_action.py:59,95,125`.

`fixtures/expected/` holds 13 files — the ten shared `.yml` goldens plus three upgrade artefacts
(`upgrade_report.json`, `upgrade_pr_body.md`, `upgrade_issue_body.md`) — and **not one of the ten
begins with a `#`**. The cross-port byte comparison, the repo's primary parity proof, has never seen
a header.

**Why the dedicated header tests do not catch it.** All three exist and all three pass:

- `packages/python/tests/test_emitter/test_header.py` (140 lines) asserts `format_header`'s **return
  value** by equality: `== "# hello\n# world\n"` (`:34`), `== "# line1\n#\n# line3\n"` (`:72`),
  `.endswith("\n")` (`:28,58,78`). It never calls `dump_yaml`. It pins Python's contract precisely
  and says nothing about placement.
- `packages/typescript/src/emitter/header.test.ts` (65 lines) asserts `formatHeader`'s **return
  value** by equality too — `toBe("Custom header text")` (`:15`), `toBe("Built with {tool} v{version}")`
  (`:20`). It pins the _other_ contract, and passes for the same reason. Two green suites asserting
  incompatible interfaces is the shape of the whole problem.
- `packages/python/tests/test_integration/test_header.py` (191 lines) is the only end-to-end header
  test in either port, and every assertion is a prefix or a substring:
  `content.startswith("# This file is generated by ghagen from ci/workflows.py.\n")` (`:66`),
  `"# Do not edit manually." in content` (`:67`), `startswith("# AUTO: from wf.py via ghagen\n")`
  (`:101`), `startswith("# literal {nope} stays literal\n")` (`:132`), `startswith(...)` (`:186,189`).
  A blank line inserted _after_ the matched prefix is invisible to all of them.
- `packages/typescript/src/emitter/yaml-writer.test.ts:34-64` is the nearest TypeScript equivalent —
  five header tests, and **all five are `toContain`** (`:37,38,44,50,57,63`). `toContain` is blind to
  a blank line, to a spurious trailing `#`, and to a literal CR anywhere after the matched substring.
- The `render()`-level threading tests in both ports are prefix assertions by construction:
  `assert text.startswith("# hand written")` (`packages/python/tests/test_synth.py:124`),
  `expect(text.startsWith("# hand written")).toBe(true)` (`packages/typescript/src/synth.test.ts:96`),
  and `startswith("#")` / `startsWith("#")` for the DEFAULT case (`test_synth.py:115`,
  `synth.test.ts:104`).
- `packages/python/tests/test_emitter/test_yaml_writer.py:91-95` calls `dump_yaml(cm, header="# My header\n")`
  — a hand-wrapped string, so it exercises `dump_yaml` but bypasses `format_header` entirely, and it
  too asserts with `startswith`.

Net: not one assertion in either suite compares whole emitted bytes for a document that has a
header. Every header assertion is either a unit test of the return value (which locks the ports into
_different_ contracts) or a prefix/substring check (which is blind to everything after the match).

## Current interface

**Python — `format_header(header, source_location) -> str | None`** (`header.py:135-176`):

- Input: `HeaderInput = str | None | Callable[[HeaderVariables], str] | _DefaultSentinel` (`:75`).
- `DEFAULT` sentinel → render `DEFAULT_HEADER` with `format_map(variables)` (`:170-172`).
- `None` → return `None`, meaning "skip the header" (`:162-163`).
- `str` → verbatim, no substitution (`:165-166`).
- callable → invoke with `HeaderVariables`, use the result (`:174-176`).
- **Return:** every non-`None` path goes through `_wrap_as_comment` (`:129-132`), so the return is a
  `#`-prefixed block, blank source lines rendered as a bare `#`, always terminated by exactly one
  `\n`. `""` returns `"#\n"` — never the empty string.
- **Owner of the `#`:** the header module. **Owner of the trailing newline:** the header module.
  **Owner of the line-break set:** `str.splitlines()`, unstated and undocumented.
- Caller (`document.py:48-49`) passes it straight to `dump_yaml`, which writes it and dumps.

**Python — `dump_yaml(data, header) -> str`** (`yaml_writer.py:100-132`): the `header` parameter is
typed `str | None` and documented "already formatted with `#`" (`:108`) — an invariant the signature
does not carry and the body does not enforce. Given the real upstream contract, both guards at
`:126-129` are dead: `format_header` never returns `""` (so `if header:` is `if header is not None:`)
and never returns a non-newline-terminated string (so the `endswith` fallback never fires). They are
live only for direct callers such as `test_yaml_writer.py:93`, which hand-wraps.

**TypeScript — `formatHeader(header, sourceLocation) -> string | null`** (`header.ts:113-134`):

- Input: `string | null | ((vars: HeaderVariables) => string) | undefined` (`:114`) — the same four
  shapes, mapped to language-idiomatic carriers (`undefined` = default, `null` = skip). This half is
  correct parity and is **not** what this proposal changes.
- **Return:** raw text with no `#`, no line normalization, no trailing newline (`:110-111`). `""`
  returns `""`, which is indistinguishable from "an empty header" downstream.
- **Owner of the `#`:** `formatYamlComment` (`yaml-writer.ts:389-395`), passed as `commentString` to
  `doc.toString` (`:447`); after 12, `renderBlockComment` in `comment-geometry.ts`. **Owner of the
  trailing newline and the blank separator line:** the `yaml` library
  (`stringifyDocument.js:23-27`). **Owner of the post-hoc rewrite:** `fixInlineCommentSpacing`
  (`:403-405`), deleted by 12.

A maintainer of the header module in one port cannot reason about emitted bytes at all in the other:
in TS the answer is spread across the header module, the writer, and a third-party stringifier the
repo does not own.

## Proposed interface

**One contract, Python's.** `format_header` / `formatHeader` returns _the exact bytes that go at the
top of the file_, or `null`/`None` for "no header." The writer concatenates; it decides nothing.

```ts
/**
 * Resolve a header value into the exact bytes that precede the YAML body.
 *
 * Returns a `#`-prefixed comment block terminated by exactly one "\n": every
 * line gains a "# " prefix, a blank line renders as a bare "#", one trailing
 * line break in the input is dropped, and CRLF, CR, LF, VT, FF, FS, GS, RS,
 * NEL, LINE SEPARATOR and PARAGRAPH SEPARATOR are all line breaks. Returns
 * `null`, and only `null`, to mean "emit no header". `""` is a header: it
 * renders as "#\n".
 *
 * Peer of `format_header` in packages/python/src/ghagen/emitter/header.py; the
 * two return byte-identical blocks for byte-identical inputs, and
 * fixtures/expected/header_*.yml is the assertion of that.
 */
export function formatHeader(
  header: string | null | ((vars: HeaderVariables) => string) | undefined,
  sourceLocation?: SourceLocation | null,
): string | null;
```

The wrapping rule moves into `header.ts`, reusing 12's exported `renderBlockComment`
(`comment-geometry.ts`, `12` §(b) A comment-geometry module in each port) for the per-line `#`, so the header and TypeScript's in-document
block comments cannot drift on prefixing.

**That last property holds in TypeScript only, and the proposal does not claim otherwise.** On the
Python side the `#` prefix has two owners and 12 leaves both in place: ruamel's
`yaml_set_comment_before_after_key` prefixes in-document block comments (`comments.py:51,58`), and
`_wrap_as_comment` prefixes the header. 12 declares **no** `render_block_comment` Python peer
(`12` §Python peer). So the port split after 12+13 is uneven — TypeScript: one block-comment renderer shared
by header and nodes; Python: two, with the header's stated in `header.py`. That asymmetry is the same
one `docs/specs/0003-comment-attachment-module.md:291-298` already documents for the
`comments.ts`/`comments.py` pair ("the two modules play the identical role while differing in
internals"); parity here is at the _emitted bytes_, which the goldens assert directly.

### The line-break rule, stated in both ports

```ts
/**
 * Split header text into lines, dropping one trailing break.
 *
 * The break set is Python `str.splitlines()`'s, written out rather than
 * inherited, so both ports implement the same *stated* rule. It is not an
 * arbitrary choice: ruamel rejects VT/FF/FS/GS/RS outright inside a comment
 * ("unacceptable character") and rescans NEL/U+2028/U+2029 as line breaks, so
 * any of them surviving into the emitted comment produces a document the
 * Python port cannot read back.
 */
const HEADER_BREAK = /\r\n|[\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029]/;

function splitHeaderLines(text: string): string[] {
  const lines = text.split(HEADER_BREAK);
  if (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();
  return lines.length === 0 ? [""] : lines;
}

function wrapAsComment(text: string): string {
  return renderBlockComment(splitHeaderLines(text).join("\n")) + "\n";
}
```

Python's `_wrap_as_comment` gains the identical rule, replacing the bare `splitlines()`:

```python
#: Python ``str.splitlines()``'s break set, written out so the contract this
#: module publishes is the contract it implements. See format_header.__doc__.
_HEADER_BREAK = re.compile("\r\n|[\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029]")


def _split_header_lines(text: str) -> list[str]:
    lines = _HEADER_BREAK.split(text)
    if lines and lines[-1] == "":
        lines.pop()
    return lines or [""]
```

**Verified: `_split_header_lines` is byte-equivalent to `text.splitlines() or [""]` on 23 shapes,
0 mismatches** — including all nine non-LF breaks, both CR forms, `""`, `"\r\n"`, `"a\n\rb"`, and
the trailing-break cases. Python's emitted bytes are therefore **unchanged** by this proposal; only
the source of the rule moves, from an undocumented stdlib behaviour to a declared constant. The
TypeScript prototype above produces the identical block for all 23.

### The writer

`toYaml` loses its `doc.commentBefore` branch entirely. Written against the **post-12** tree, where
`fixInlineCommentSpacing` and `formatYamlComment` no longer exist and `commentString` is the
identity (`12` §(b) A comment-geometry module in each port):

```ts
const yaml = doc.toString({ lineWidth: 0, indentSeq: false, singleQuote: true, commentString });
const headerStr = formatHeader(options?.header, target.sourceLocation);
return headerStr === null ? yaml : headerStr + yaml;
```

The reason the header must not travel through the document node is `stringifyDocument.js:23-27`
alone: it unconditionally separates a `commentBefore` from the body and silently drops a falsy one.
Those two behaviours are divergences 2/6 and 3, and neither is configurable. Concatenation is the
only way to own the bytes.

Python's side changes only in precision: `format_header`'s docstring (`header.py:139-161`) becomes
the normative statement of the contract above — including the `""` → `"#\n"` rule, the
one-trailing-break rule and the break set, which are today emergent properties of `splitlines()`
rather than declared ones — and `dump_yaml` states the invariant and drops its two dead branches:

```python
    stream = StringIO()
    if header is not None:
        # A fully wrapped comment block, "#"-prefixed and "\n"-terminated (the
        # contract of ghagen.emitter.header.format_header). dump_yaml does not
        # wrap, pad, or re-indent it.
        stream.write(header)
    yaml.dump(data, stream)
```

**Verified.** The TypeScript prototype, run against every shape below, is byte-identical to Python's
`format_header`:

| Input                | Both ports, after the change |
| -------------------- | ---------------------------- |
| `""`                 | `#\n`                        |
| `"x\n"`              | `# x\n`                      |
| `"x\n\n"`            | `# x\n#\n`                   |
| `"\nx"`              | `#\n# x\n`                   |
| `"# already hashed"` | `# # already hashed\n`       |
| `"line1\n\nline3"`   | `# line1\n#\n# line3\n`      |
| `"   "`              | `#    \n`                    |
| `"a\r\nb"`           | `# a\n# b\n`                 |
| `"a\rb\rc"`          | `# a\n# b\n# c\n`            |
| `"a\vb"`             | `# a\n# b\n`                 |
| `"\r\n"`             | `#\n`                        |

Divergences 2, 3, 4 and 6 all close: the blank line is gone because the library never sees the
header, `""` survives because `null` is the only skip signal, trailing breaks and CR/CRLF follow one
shared splitting rule, and the root Document comment sits directly under the header as in Python.
Divergence 5 is already closed by 12.

### Putting headers under the byte oracle

Six shared goldens, each asserted byte-identical from both ports against the same file, over one
small shared workflow (`name: CI`, one push trigger, one job, one `uses:` step — 10 body lines).

| Fixture                  | Header input                                  | What it pins                                                                     | Divergence                             |
| ------------------------ | --------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------- |
| `header_string.yml`      | `"Hand written"`                              | no blank line after the header                                                   | 2                                      |
| `header_multiline.yml`   | `"line1\n\nline3\n"`                          | bare `#` for a blank line; one trailing break dropped                            | 4                                      |
| `header_crlf.yml`        | `"a\r\nb\rc"`                                 | CRLF **and** bare CR are breaks; no CR reaches the output                        | 4                                      |
| `header_empty.yml`       | `""`                                          | `""` is a header, not a skip                                                     | 3                                      |
| `header_closure.yml`     | `(v) => "built by " + v.tool + " # verbatim"` | the closure branch wraps identically to the string branch; `#` survives verbatim | 2 (+ standing guard for 12's fix of 5) |
| `header_doc_comment.yml` | `"Hand written"` + root `comment`             | header abuts the Document comment                                                | 6                                      |

**How they are read.** `fixtures/expected/` already contains two kinds of golden: ten emitter YAML
snapshots managed through `pytest-snapshot` (`test_snapshots.py:6,39,44` on the Python side,
`loadFixture` on the TypeScript side), and three artefacts read by hand in **both** ports —
`upgrade_report.json`, `upgrade_pr_body.md`, `upgrade_issue_body.md`
(`test_cli/test_deps.py:763,905,910`; `cli/deps.test.ts:104,158,162`). The six header goldens join
the second group, because they are an _oracle_ — the artefact that proves the divergence is closed —
rather than a regenerable snapshot of current behaviour:

- TypeScript: `expect(toYaml(w, { header: … })).toBe(loadFixture("header_string.yml"))`, using the
  existing helper at `src/integration/test-utils.ts:10-12` — the same call shape as
  `cli/deps.test.ts:11,104`.
- Python: `(SNAPSHOT_DIR / "header_string.yml").read_text()`, where `test_snapshots.py:39` already
  computes `SNAPSHOT_DIR`. The same shape as `test_cli/test_deps.py:9,23`.

This needs **no** `FIXTURES_DIR` work. The two ports' constants are genuinely asymmetric —
`packages/typescript/src/paths.ts:41` resolves `fixtures/expected` while
`scripts/ghagen_schema/paths.py:35` resolves `fixtures` and Python re-appends `"expected"` at
`test_snapshots.py:39` and `test_cli/test_deps.py:23` — but 13 consumes both exactly as its
neighbours already do and adds no new resolution. Whether that asymmetry is worth fixing is tracked
elsewhere; 13 is not a dependent of the answer.

**Generated from Python, which is the reference side and is byte-unchanged by both 12 and 13.**
The six golden bodies, measured:

```
header_string.yml       # Hand written\nname: CI\n…
header_multiline.yml    # line1\n#\n# line3\nname: CI\n…
header_crlf.yml         # a\n# b\n# c\nname: CI\n…
header_empty.yml        #\nname: CI\n…
header_closure.yml      # built by ghagen # verbatim\nname: CI\n…
header_doc_comment.yml  # Hand written\n# root doc comment\nname: CI\n…
```

Every one contains only ASCII, no CR, and exactly one trailing newline. `header_closure.yml` is
version-independent by construction: `v.tool` is the constant `"ghagen"`, and no golden references
`{version}` or `{source_file}`, so none of them embeds a package path, an install layout, or a
resolved source file. That matters beyond determinism — under a symlinked
`node_modules/@ghagen/ghagen`, `callsites()` returns a `file:` URL and the prefix comparison at
`packages/typescript/src/_package_paths.ts:34` does not match, which perturbs which frame becomes
the `sourceLocation`. No golden here is exposed to that, because none of them renders a source path.

## What sits behind the seam

`format_header` becomes a **deep** module: a four-shape input and a `str | None` output, with the
whole of "what the top of a generated file looks like" behind it — variable resolution, template
substitution, the line-break set, `#` prefixing, blank-line rendering, and newline termination. Its
callers (`document.py:48-49`, `yaml-writer.ts` `toYaml`) shrink to `write(header)` / `header + yaml`.

Today the TS peer is **shallow**: its interface (`string | null`, "the yaml library handles comment
formatting") is nearly as complex as its body, because the interesting decisions are all downstream
of it, in a module ghagen does not own. That shallowness is the mechanism of divergences 2, 3 and 6 —
`stringifyDocument.js` gets to decide ghagen's output format, and it decides differently from ruamel.

**Leverage:** one caller, one line, no knowledge of comment syntax. **Locality:** a change to the
header's on-disk shape — a different prefix, a trailing blank line, wrapping long lines — is one edit
in one function per port, with a golden diff proving both ports moved together. Today the same change
is an edit in the header module, an edit in the writer, and a hope about the `yaml` library.

**Deletion test on `wrapAsComment`/`splitHeaderLines`:** delete them and TS must re-derive the `#`
prefix and the line rule at the writer — which is precisely where it lives today and precisely why
the ports diverge. The complexity reappears at the caller, so the function earns its keep.

**Deletion test on `_HEADER_BREAK` (Python):** delete it and `splitlines()` returns as the silent
source of truth — the docstring `format_header` publishes would once again be a claim no code makes,
which is exactly the defect at `header.ts:4-5`. It is not a pass-through: it is the one place the
rule is _stated_, and the TypeScript peer is derived from it.

**Deletion test on the six new goldens:** delete them and every one of divergences 2, 3, 4 and 6
becomes re-introducible with a green suite, because the surviving header tests are unit-level
(locking each port's _own_ contract) or prefix/substring-level (blind past the match). They are the
only assertion in the repo that the two ports' headers agree byte-for-byte.

## Migration plan

Pre-1.0; clean break. **Land after 12**, on a tree where `fixInlineCommentSpacing` and
`formatYamlComment` are gone, `commentString` is the identity, and `renderBlockComment` is exported
from `comment-geometry.ts`.

1. **TS header module.** Add `HEADER_BREAK`, `splitHeaderLines` and `wrapAsComment` to `header.ts`,
   importing `renderBlockComment` from `./comment-geometry.js`; wrap every non-`null` return of
   `formatHeader`. Replace the `:4-5` comment with the contract, and the `:110-111` "the yaml library
   handles comment formatting" docstring with the block above.
2. **TS writer.** Delete the `doc.commentBefore` assignment (`yaml-writer.ts:430-433`, as 12 left
   it) and concatenate the header after `doc.toString`. The invariant to preserve through any 12
   rebase is narrow: _header text never reaches the document node._
3. **TS unit tests.** `header.test.ts` expectations flip to wrapped blocks; add `""`, `"x\n"`,
   `"a\r\nb"`, `"a\rb\rc"` and one non-LF break. `yaml-writer.test.ts:34-64`'s five `toContain`
   header assertions become whole-output equality.
4. **Python.** Add `_HEADER_BREAK` / `_split_header_lines`; point `_wrap_as_comment` at it; restate
   `format_header`'s docstring as the normative contract; add the missing shape tests; tighten
   `dump_yaml`'s header write and update `test_dump_yaml_with_header`.
5. **Goldens.** Add the six files and the twelve test cases (six per port), generated from the Python
   port and hand-read in both, per the idiom above.
6. **Python integration.** `test_integration/test_header.py`'s four `startswith`/`in` assertions
   become whole-output equality.
7. **Docs.** `comments.mdx:268,314`: state that the body follows the header with no blank line, that
   an empty-string header renders a bare `#`, and that one trailing break in the header string is
   dropped.
8. Full suite both ports, plus `uv run ghagen check-synced` — the repo's own workflows are generated
   by the Python port (`.github/ghagen_workflows.py`) and are unaffected by construction, which is
   the regression check that this change touches only the TS side's emitted bytes.

## Test impact

### The goldens, and exactly which bytes they pin

The six `fixtures/expected/header_*.yml` files are the load-bearing artefact of this proposal — the
only thing in the repo that will prove the per-port header divergence (H11) is closed. All six share
one body (`name: CI` / one push trigger / one job / one `uses:` step) so that every byte difference
between them is header. Line by line, each golden pins:

| Golden line(s)               | What it pins                                                                                                                                                            |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `header_string.yml:1-2`      | `# Hand written` immediately followed by `name: CI` — **no blank line** (divergence 2)                                                                                  |
| `header_multiline.yml:1-3`   | `# line1` / bare `#` for the blank source line / `# line3`, and **no fourth `#`** from the trailing break (divergence 4)                                                |
| `header_crlf.yml:1-3`        | three `#` lines from `"a\r\nb\rc"` — CRLF and bare CR both break, and **the file contains no 0x0D byte anywhere** (divergence 4)                                        |
| `header_empty.yml:1`         | a lone `#`, and line 2 is `name: CI` — `""` is a header, and it does not get a separator (divergences 3 + 2)                                                            |
| `header_closure.yml:1`       | `# built by ghagen # verbatim` — closure branch wraps like the string branch, and the interior `#` keeps **one** space (divergence 2; standing guard for 12's fix of 5) |
| `header_doc_comment.yml:1-2` | `# Hand written` then `# root doc comment` on the next line, then `name: CI` (divergence 6)                                                                             |
| all six, trailing            | exactly one trailing newline, no other trailing whitespace                                                                                                              |

**Red-before is asymmetric, and the count is six, not twelve.** 13 generates the golden bytes from
the Python port, so the six Python cases are **green by construction** the moment they are written —
they are regression guards, not failing tests. The six TypeScript cases are the red-before set.
Measured on `main`, TypeScript's leading bytes for each golden's input, against the golden's:

| Golden                   | Golden (Python)                        | TS on `main`                             | TS post-12, pre-13                 |
| ------------------------ | -------------------------------------- | ---------------------------------------- | ---------------------------------- |
| `header_string.yml`      | `# Hand written\n`                     | `# Hand written\n\n`                     | unchanged                          |
| `header_multiline.yml`   | `# line1\n#\n# line3\n`                | `# line1\n#\n# line3\n#\n\n`             | unchanged                          |
| `header_crlf.yml`        | `# a\n# b\n# c\n`                      | `# a\r\n# b\rc\n\n`                      | unchanged                          |
| `header_empty.yml`       | `#\n`                                  | _(nothing — header dropped)_             | `#\n\n`                            |
| `header_closure.yml`     | `# built by ghagen # verbatim\n`       | `# built by ghagen  # verbatim\n\n`      | `# built by ghagen # verbatim\n\n` |
| `header_doc_comment.yml` | `# Hand written\n# root doc comment\n` | `# Hand written\n\n# root doc comment\n` | unchanged                          |

All six are red on `main` and all six are still red after 12 — 12 narrows two of them and closes
none. That is the check that 13 is not redundant with its own dependency.

### Everything else

- **New (unit, both ports):** `""`, trailing-break, CR, CRLF and one non-LF break (`"a\vb"`). Python
  currently pins none of them despite `splitlines()` defining behaviour for all of them; TypeScript
  gets the behaviour for the first time.
- **Rewritten:** every expectation in `packages/typescript/src/emitter/header.test.ts` — `:15`,
  `:20`, `:29`, `:37-38` — now expects `#`-prefixed, newline-terminated blocks. `:24`
  (`formatHeader(null)` is `null`) is unchanged and becomes the sole skip signal.
- **Rewritten:** `packages/typescript/src/emitter/yaml-writer.test.ts:34-64` — the five header tests
  move from `toContain` to whole-output equality. Their outputs are three lines and deterministic
  (`simpleModel({ name: "ci" })`), so equality costs nothing and removes the last substring header
  assertion in the TypeScript port.
- **Rewritten:** `packages/python/tests/test_integration/test_header.py` `:66-69`, `:101-103`,
  `:132-134`, `:186-191` move from `startswith`/`in` to whole-output equality against the emitted
  file. Each of those outputs is deterministic — `App(root=".")` under `monkeypatch.chdir(tmp_path)`,
  a `.ghagen.yml` marker written by the test, and no `{version}` in the default template. Those four
  assertions are the ones that _should_ have caught a blank line and did not; a prefix assertion on a
  header is a hole by construction.
- **Unchanged and vindicated:** `packages/python/tests/test_emitter/test_header.py` survives almost
  intact. It already asserts the winning contract by equality — which is the strongest single
  argument for picking Python's side.
- **Unchanged:** all ten existing goldens (`header=None` output is identical before and after) and
  the `render()`-level threading tests in both ports (`test_synth.py:109,115,124`;
  `synth.test.ts:88,96,104` — all still true of the new bytes).
- **Baseline movement:** roughly +11 pytest and +11 vitest from the new cases, against the current
  562 / 515.

**The TypeScript parity gap, named and answered.** TypeScript has no peer of
`packages/python/tests/test_integration/test_header.py` — no end-to-end "synth a project, read the
file, check the header" suite — and `AGENTS.md:43` mandates feature parity between the ports. 13
does **not** build one, and that is a deliberate call rather than an omission: the six shared goldens
assert the emitted header bytes from _both_ ports against the _same_ files, which is strictly
stronger than a per-port end-to-end test, and item 3 above closes the substring-assertion gap inside
`yaml-writer.test.ts`. What a TypeScript peer would add over the goldens is coverage of the
`{source_file}` resolution path through `synth()` — already covered per-port by
`synth.test.ts:88,96,104` and `header.test.ts:32-39`. If a reviewer wants the suite anyway it is
additive and can land separately; nothing in 13 depends on it.

## Risks & alternatives

- **Alternative: adopt TypeScript's contract instead** (`formatHeader` returns raw text; Python
  stops wrapping and `dump_yaml` prefixes). Rejected on three counts. It makes the header module
  shallower in _both_ ports rather than one; it hands the emitted shape to `yaml`'s stringifier,
  which has no option to suppress the blank line (`stringifyDocument.js:24-25` is unconditional), so
  Python would have to grow a blank line to match a shape nobody wants; and it invalidates the one
  header test suite that is already precise (`test_emitter/test_header.py`). Python's contract also
  matches every generated file already checked into `.github/workflows/`.
- **Alternative: state the break set as CRLF/CR/LF only, and change Python to match.** This was the
  reviewer's preferred fix for the docstring defect, and it is rejected on measured evidence.
  Narrowing Python's break set is a _behaviour regression_: `header="a\vb"` currently emits
  `# a\n# b\n` from Python and would start emitting `# a\vb\n`, which `ruamel.yaml` 0.19.1 refuses to
  read back (`ReaderError: unacceptable character #x000b`) — so the Python port would begin writing
  files it cannot itself parse, for a shape it handles correctly today. `\f` and `\x85` are reachable
  from any pasted or file-sourced header string. Writing the full break set out explicitly achieves
  the reviewer's actual goal — both ports implement the _stated_ rule and `splitlines()` stops being
  the silent source of truth — without the regression, and additionally fixes the same class of bug
  in TypeScript, which emits the raw control character today.
- **Alternative: keep `doc.commentBefore` and strip the blank line afterwards** with a regex on the
  rendered string. Rejected — it re-introduces the post-hoc string rewrite 12 exists to delete, it
  cannot fix divergence 3 (`""` is dropped inside the library, before any output exists to rewrite),
  and it would put header text back inside the reach of exactly the kind of pass 12 removed.
- **`header_default.yml` is dropped, deliberately.** An earlier draft added a seventh golden for the
  DEFAULT branch plus a `maskSourceFile()` / `mask_source_file()` helper pair in
  `test-utils.ts` / `conftest.py`, because `{source_file}` names a `.py` file in one port and a `.ts`
  file in the other and can never be byte-shared. Dropped: it was the only invented mechanism in the
  proposal, it was the only golden whose bytes depended on install layout (see the
  `_package_paths.ts:34` note above), and DEFAULT-branch placement is already covered per-port by
  `test_synth.py:115` / `synth.test.ts:104` and by `test_integration/test_header.py:66` after item 6
  tightens it to whole-output equality. Two `Files involved` rows go with it.
- **Risk: a user-visible byte change for TypeScript users who emit a header.** Real, intended, and
  the point. Every TS-generated file with a header loses one blank line; a header with a trailing
  newline loses a spurious `#`; files with `header: null` (including all ten goldens) are unchanged.
  Pre-1.0, and the new bytes are the ones the docs already advertise. Worth a release note.
- **Risk: 12 lands first and reshapes `toYaml` beyond recognition.** Accepted — a sequencing cost,
  not a design conflict. What 13 needs from 12 is narrow and already declared: `renderBlockComment`
  exported from `comment-geometry.ts` (`12` §(b) A comment-geometry module in each port), and no pass that rewrites emitted text. If 12 were
  dropped, 13's only extra cost is a four-line `#`-prefixer duplicated in `header.ts` — the ordering
  edge is justified by the seven shared files, not by any cycle.

**Scope boundaries vs siblings.**

- **12 (TS comment-geometry module)** — ordering dependency, and **seven** shared files, not one:
  `yaml-writer.ts` (12 rewrites `:389-451`; 13 edits `:430-433` inside it), `yaml_writer.py`
  (adjacent lines in `dump_yaml`: 12 at `:122-123`, 13 at `:125-130`), `yaml-writer.test.ts` (12 at
  `:125,141` + new tests, 13 at `:34-64` — disjoint hunks), `test_yaml_writer.py`, `test_snapshots.py`,
  `snapshots.test.ts` and `comments.mdx`. The dependency is **acyclic**: `comment-geometry.ts`
  imports nothing from `header.ts` (`12` §Scope boundaries vs siblings), while `yaml-writer.ts:11` imports `header.ts`, so
  `header.ts → comment-geometry.ts` inverts nothing. 13 does not restructure the in-document comment
  path and does not move `attachModelComment` / `attachFieldComment`; it removes one branch, adds one
  concatenation, and _consumes_ `renderBlockComment`. Divergence 5 is 12's outright; divergence 6 is
  13's, though it sits next to 12's Document-comment territory.
- **10 (delete `order` from `ModelSpec`)** — two edges. (a) File adjacency: 10 also edits
  `yaml-writer.ts`, but in `orderedEntries` (`:189-215`) and the spec literals, not `toYaml`
  (`:424-451`); and both edit `test_yaml_writer.py` in different functions. (b) **Semantic:** 13
  takes the shared golden set from **ten to sixteen**, so every "the ten shared golden fixtures"
  count in 10's Problem, _What sits behind the seam_, _Test impact_ and _Risks_ sections
  (`10` §Problem) reads sixteen once 13 lands. 10 is being told the same; the two documents
  must agree. Separately, 12 changes `fixtures/expected/comments.yml:3`, so 10's zero-byte-delta
  acceptance criterion must be read against the tree at 10's land time, not against today's fixtures.
- **11 (shared spec-surface conformance table)** — a different oracle: 11 asserts that both ports
  declare the same _spec surface_; 13 asserts that both ports emit the same _bytes_ for a header. No
  file overlap. If 11's table grows a "same constants" section, `DEFAULT_HEADER` is a natural entry
  and 13 does not claim it.
- **15 (lockfile encoding)** — **no overlap.** Both proposals add a designated byte oracle to
  `fixtures/expected/` and both use the hand-read idiom, but 15's `lockfile_golden.yml` and 13's six
  `header_*.yml` are disjoint files read by disjoint suites (`test_lockfile.py` / `lockfile.test.ts`
  vs `test_snapshots.py` / `snapshots.test.ts`), and the two proposals share no source file. 13
  follows 15's reviser in _how_ to read a golden; that is a convention, not a dependency.
- **Whoever implements `docs/issues/02`** — same two snapshot test files
  (`test_snapshots.py`, `snapshots.test.ts`) and the same fixture directory. See below.
- **09, 14, 16–24** — no overlap.

**Relationship to `docs/issues/02` (fixture coverage gaps).** 13 closes **none** of the four gaps
that issue records (`defaults:` block, empty `workflow_dispatch` present-null, dynamic extras
interleave, SHA-pinned `uses:`) — those are all body-shape gaps and this proposal adds no body
coverage. It does establish that the issue's inventory was incomplete: headers are a fifth gap of
the same kind, and a larger one, since the missing coverage spanned a live five-way byte divergence
rather than an untested-but-agreeing path. The issue should be amended to record it. Scheduling
note: issue 02's remedy ("add one workflow fixture covering all four") and 13's six goldens touch the
same two test files and the same directory; doing them in one pass over `fixtures/expected/` avoids a
second round of conflicts.

## ADR / CONTEXT.md impact

- **No ADR contradicted.** ADR-0001 (as amended) puts _all_ emission logic in the Emitter; both
  `format_header` and `dump_yaml`/`toYaml` are already Emitter-internal, and this proposal moves an
  emission decision _out_ of a third-party stringifier and _into_ the Emitter module that is
  supposed to own it. ADR-0001's amendment of 2026-07-28 names `emit`/`emit_file`/`to_data` and
  `toYaml`/`toYamlFile`/`toData` as the Emitter's public surface; `format_header` stays behind it and
  its signature is unchanged from the outside.
- **`docs/specs/0003-comment-attachment-module.md:288-289` is not contradicted, and 13 says so in
  the code it touches.** That line ruled `fixInlineCommentSpacing` in scope to _stay_ — "it is
  string-level output normalization on the final dump, not node attachment." 12 reopens that call;
  13 does not. 13 keeps whatever the pass has become and moves header text out of its reach, which is
  compatible with the spec's ruling under either outcome. One sentence to that effect belongs
  wherever 13 edits `toYaml`.
- **No new ADR needed.** "Header wrapping is the header module's job" is an interface repair inside
  an existing decision, not a new system-wide one. If the reviewer disagrees, the sentence to record
  is: _the Emitter never delegates emitted-byte decisions to a backend library; the backend renders
  the body, ghagen renders everything else._
- **`packages/python/CONTEXT.md:34-38` / `packages/typescript/CONTEXT.md:34-38`, the Emitter
  entry** — **shared with 12; apply 12's sentence first, then this one, or merge the two.** 12 adds
  that comment _geometry_ is a named module with a stated constant and that no Emitter pass rewrites
  emitted text. 13 extends the same entry with: _and owns the emitted header bytes end to end — the
  backend never sees them._
- **`packages/python/CONTEXT.md` / `packages/typescript/CONTEXT.md` — a new glossary entry,
  inserted immediately after **CommentNode** (`python:49-51`, `typescript:51-53`)**, phrased
  identically in both. Applied in the implementation phase; this document does not edit the files:

  > **Header**: the auto-generated comment block at the top of every emitted file. `format_header` /
  > `formatHeader` resolves the four input shapes (default, `None`/`null`, string, closure) to the
  > exact bytes that precede the YAML body — `#`-prefixed, one trailing newline, blank lines as a
  > bare `#`, one trailing line break in the input dropped — or to `None`/`null` for "no header".
  > The writer concatenates; it never re-wraps, pads, or re-indents. Byte parity is asserted by
  > `fixtures/expected/header_*.yml`.
  > _Avoid_: banner, preamble, file comment.

- **`docs/src/content/docs/guides/comments.mdx:268,314`** — `:314` ("every line gets a leading `# `,
  blank lines render as a bare `#`") is correct and becomes true of both ports; add that the body
  follows the header with no blank line, that an empty-string header renders a single `#`, and that
  one trailing line break in the header string is dropped. `:268`'s "emitted verbatim" claim becomes
  true of TypeScript once 12 lands and stays true under 13.
- **`docs/issues/02-fixture-coverage-gaps.md`** — amend to record headers as a fifth gap, per the
  paragraph above.
