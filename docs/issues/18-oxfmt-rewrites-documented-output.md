# The docs formatter rewrites documented program output

**Status:** closed — remedy 1 implemented. The guides' emitted-output blocks are now produced by a
real `toYaml()` run at docs-build time and pinned to `fixtures/expected/docs_*.yml` from both ports;
all eight `{/* prettier-ignore */}` markers are retired

`oxfmt` reformats fenced ` ```yaml ` blocks inside `.mdx`. It collapses a two-column end-of-line
gutter to one column (`on:  #` → `on: #`) and re-indents sequence items. Those blocks are not
examples an author chose the shape of — they are **transcripts of what the emitter emits**, and the
emitter's gutter width is now a named constant (`EOL_GUTTER = 2`, `emitter/comment-geometry.ts` and
`emitter/comment_geometry.py`).

**LIVE, and it already caused a documentation defect.** The guide at
`docs/src/content/docs/guides/comments.mdx` showed a one-column gutter for years. Proposal 12's
implementer initially read that as the intended output. It was not — it was the formatter's edit,
applied silently on every `./scripts/fmt.sh` run and every pre-commit hook. Correcting the bytes
without disarming the formatter is impossible: fmt reverts them on the next run and the gate stays
green either way, so nothing reports the loss.

## What was measured

Proposal 12 probed the escape hatches directly:

- `{/* prettier-ignore */}` placed **immediately** before the fence — **honoured**.
- The same marker with a blank line between it and the fence — **not honoured**.
- `{/* oxfmt-ignore */}` in any position — **not honoured**.

Seven `{/* prettier-ignore */}` markers now sit in `comments.mdx` and are **load-bearing**. Removing
one silently restores the corruption. Nothing in the repo says so except a ledger entry and this
issue.

## The same defect class was already fixed once this round

Round 2 found `python -m ghagen_schema check` regenerating `packages/typescript/src/schema/` in place
and destroying uncommitted edits **while printing "Schema types are up to date"** — a tool that
rewrites your work and reports success. Proposal 23 **fixed** it: `scripts/ghagen_schema/check.py`
now snapshots the generated directory, regenerates, diffs, and restores on both the pass and the
fail path, so the verb is read-only and safe under a local gate and a pre-commit hook.

This is that shape again, one toolchain over: a formatter with write authority over content it
cannot distinguish from prose, and a gate that passes whichever way the bytes land. The precedent
matters — `check.py`'s remedy was to make the tool structurally incapable of writing, not to
document that it writes. Remedy 1 below is the analogue.

## Remedy — options, in preference order

1. **Make the marker unnecessary.** Generate the YAML blocks in the guides from a real `to_yaml()` /
   `toYaml()` run at docs-build time, the way `fixtures/expected/` already works for the suites. Then
   the formatter cannot disagree with the emitter, because the emitter writes the bytes. This is the
   only option that makes the class of defect go away rather than papering over one instance.
2. **Guard the markers.** A docs lint rule asserting that every fenced `yaml` block showing emitted
   output carries `{/* prettier-ignore */}` on the immediately preceding line. Cheap; catches
   removal, not new blocks written without it.
3. **Scope the formatter.** Configure `oxfmt` to leave fenced code blocks alone in `.mdx`. Least
   work, widest blast radius — it also stops the formatter fixing genuinely malformed examples.

Option 1 subsumes the byte oracle the repo already trusts and is the one worth costing first.

## Files

- `docs/src/content/docs/guides/comments.mdx` (seven load-bearing markers today)
- `scripts/fmt.sh` — `docs` scope
- `.pre-commit-config.yaml` — runs the same toolchain per commit
- Any other `.mdx` under `docs/src/content/docs/` containing emitted-output blocks; **the count was
  never taken.** Whoever picks this up should start by measuring it.

## Why it was deferred

Found mid-round while implementing an unrelated proposal, and the cheap fix (markers) was applied
inline to keep 12's own documentation honest. The real fix is option 1, which is a docs-build change
of its own size and has no business riding a comment-geometry refactor.

## Round 3: the root cause, and a second, worse instance

The mechanism is now identified, and it is wider than "oxfmt reformats yaml."

**A fence written directly against a JSX tag, with no blank line between them, is not parsed as a
code block at all.** oxfmt then formats its contents as **prose**: indentation is stripped and `_` is
read as emphasis. Minimal repro, reduced from `cookbook.mdx`:

````markdown
<TabItem label="Python">
```python
Job(
    runs_on="ubuntu-latest",
)
```
````

becomes `runs*on=` at column 0. Insert one blank line after the `<TabItem>` and oxfmt leaves the block
byte-identical.

That is not hypothetical. `main` shipped **syntactically invalid Python** in
`docs/src/content/docs/guides/cookbook.mdx` — `runs*on=`, `if*=`, `github.event*name`, five sites —
and `scripts/fmt.sh docs` passed on it, because the corrupt form was what the formatter considered
canonical. `docs/src/content/docs/guides/dry-patterns.mdx` was de-indented the same way. Both are
fixed; every `.mdx` under `docs/src/content/docs/` now has the blank line.

### The two defects are distinct and only one is fixed by the blank line

|                                                        | mechanism                                       | remedy                                                          |
| ------------------------------------------------------ | ----------------------------------------------- | --------------------------------------------------------------- |
| yaml gutter collapse (this issue, as originally filed) | oxfmt parses the block as yaml and reformats it | the eight `{/* prettier-ignore */}` markers, still load-bearing |
| code-fence prose mangling (new)                        | the block is not recognised as code at all      | a blank line after the JSX tag                                  |

Measured directly: removing the `prettier-ignore` markers from `comments.mdx` while the blank lines
are in place still collapses `on:  #` → `on: #`. The markers are not superseded.

### What is still open

The gate asymmetry the issue was filed for is unchanged: `scripts/fmt.sh docs` passes whichever way
the bytes land, so nothing reports the loss. A fence-adjacency check — no fence may sit against a JSX
tag — would make this class structurally impossible instead of relying on nobody deleting a blank
line. That check does not exist yet.

## Resolution

Remedy 1, in full. The guides no longer transcribe emitter output; they render it.

### The count the issue asked for, taken

**5** `.mdx` files under `docs/src/content/docs/`, **11** ` ```yaml ` fences between them:
`guides/comments.mdx` 8 (all eight carrying `{/* prettier-ignore */}`), `index.mdx` 1,
`guides/escape-hatches.mdx` 1, `guides/cookbook.mdx` 1 — the last three with **no marker at all**.

**The landing page was already wrong.** Emitting `index.mdx`'s own snippet and diffing against the
block it printed showed every sequence item indented two columns too far — `      - main` where the
emitter writes `    - main`, at `on.push.branches`, `on.pull_request.branches` and `jobs.test.steps`.
oxfmt's re-indentation, on the one page nobody had thought to protect. That is the argument for
remedy 1 over remedy 2 in one line: **a marker freezes bytes, it does not check they are right.**
`comments.mdx` was protected and correct; `index.mdx` was unprotected and wrong, and the gate was
green either way.

### Per-fence classification

| fence                                        | classification         | disposition                                                                                           |
| -------------------------------------------- | ---------------------- | ----------------------------------------------------------------------------------------------------- |
| `index.mdx` "generates clean, readable YAML" | emitted document       | generated (`docs_quickstart`)                                                                         |
| `comments.mdx` block comment on a `Job`      | emitted fragment       | generated, `region(…, "jobs.test")`                                                                   |
| `comments.mdx` EOL comment on a `Step`       | emitted fragment       | generated, `regionBody(…, "jobs.lint.steps")`                                                         |
| `comments.mdx` field-level block comment     | emitted fragment       | generated, `region(…, "name")`                                                                        |
| `comments.mdx` field-level EOL comment       | emitted fragment       | generated, `region(…, "on")`                                                                          |
| `comments.mdx` full example                  | emitted document       | generated (`docs_comment_full`)                                                                       |
| `comments.mdx` default header                | **not a transcript**   | left hand-written — see below                                                                         |
| `comments.mdx` closure header                | **not a transcript**   | left hand-written — see below                                                                         |
| `comments.mdx` header-against-body           | emitted document       | generated (`docs_header_verbatim`)                                                                    |
| `escape-hatches.mdx` `extras`                | emitted fragment       | generated, `regionBody(…, "jobs.build")`                                                              |
| `cookbook.mdx` `auto_dedent: false`          | **not emitter output** | left hand-written — a `.ghagen.yml` config file, an input to ghagen rather than a thing ghagen prints |

Two of the eleven are emitted _shapes_ whose payload is the reader's environment rather than
ghagen's output, and generating them would print something actively wrong for the reader:

- **the default header** — `# This file is generated by ghagen from {source_file}.` The variable is
  resolved from where _the reader's_ `Workflow` was constructed, relative to _their_ `.ghagen.yml`.
  Emitting it here would name `docs/src/snippets/emitted.ts`.
- **the closure header** — same, plus `{version}`, which is the installed package version. The two
  ports are not on the same version (`ghagen` 0.5.0, `@ghagen/ghagen` 0.4.0), so this is the one
  documented shape whose bytes genuinely _cannot_ be made to agree across the ports; pinning it
  would encode one port's release number into the guide.

Both were reworded to say so out loud ("the path you see is your own", "with your own source path,
and whichever ghagen version is installed") rather than reading as verbatim transcripts. Neither
needed its marker: both are comment-only blocks with nothing for oxfmt to re-indent, confirmed by
running `scripts/fmt.sh docs --fix` twice with the markers gone and diffing (byte-identical).

### The mechanism

`docs/src/snippets/emitted.ts` imports the emitter straight out of
`packages/typescript/src/index.ts` — Vite resolves and transpiles it in the SSR pass, so no build
step, no subprocess, no vendored copy. Each entry builds a real model, calls `toYaml`, and exports
the string; the `.mdx` renders it with Starlight's `<Code code={…} lang="yaml" />`. **There is no
longer a fence for the formatter to edit**, which is why all eight markers could go.

Only `Workflow` and `Action` are Documents, so four sections whose subject is a `Job` or a `Step`
cannot emit their subject standalone. Those are handled by `region` / `regionBody`, which address a
fragment **by key path** in a real emitted document and dedent it — so the slice tracks whatever the
emitter lays down instead of freezing a copy of it. Each of the four reproduced its section's
existing block byte-for-byte on first run, which is the check that the slicer is not inventing
geometry.

### The cross-port binding

The docs job has Node and no Python (`.github/workflows/docs.yml`), so the build can only run one
port. Every document is therefore also pinned to `fixtures/expected/docs_*.yml` — eight new files in
the directory that is already this repo's cross-port byte oracle — and
`packages/python/tests/test_integration/test_docs_snippets.py` builds the mirrored Python model and
byte-compares against the same eight files. **Both ports emit identical bytes for all eight
documented examples; no divergence was found.**

The docs-build check throws on mismatch, the same shape as `typeDocValidationGate` in
`astro.config.mjs` — the build has no exit code of its own to pick, so failing means throwing.
Re-taking the oracles after a deliberate emitter change is
`GHAGEN_DOCS_SNIPPETS_UPDATE=1 npm run build --prefix docs`, then `uv run pytest`.

### Proof it is load-bearing

`EOL_GUTTER` in `packages/typescript/src/emitter/comment-geometry.ts` was changed from `2` to `4`
and each half exercised:

1. **The guard fires.** `npm run build --prefix docs` exited **1** with
   `docs snippet 'docs_comment_eol' no longer matches fixtures/expected/docs_comment_eol.yml`,
   printing both sides. Under the old regime this change produced a green `scripts/fmt.sh docs` and
   a silently stale page.
2. **The page tracks the emitter.** Re-taking the oracles under the perturbation and rebuilding,
   `docs/dist/guides/comments/index.html` rendered `- name: Ruff    # fast Python linter` and
   `on:    # trigger configuration` — a four-column gutter, straight from the constant. Nothing was
   hand-edited to make that happen.
3. **The other port is held too.** With the perturbed oracles in place and Python untouched,
   `uv run pytest packages/python/tests/test_integration/test_docs_snippets.py` failed **3 of 8**
   (`test_docs_comment_eol`, `test_docs_comment_field_eol`, `test_docs_comment_full`) — every
   documented example that shows an EOL comment. A one-port emitter change cannot reach the guides
   without the other port's suite reporting it.

`EOL_GUTTER` and the oracles were then restored; the eight tests pass and the build is green.

### Collateral, deliberately fixed

The prose-mangling defect of the Round 3 section had left **committed damage** in the two files this
change touches — the blank lines that stop it recurring were added, but the already-mangled bytes
were never restored. Three Python fences were de-indented to column 0, two of them
(`comments.mdx`'s field-level examples and full example, `escape-hatches.mdx`'s `post_process`)
**syntactically invalid Python**, and the "chainable" example in `comments.mdx` had collapsed into a
one-line fence whose body was being read as an info string. All are repaired. Two TypeScript
snippets also imported from `"ghagen"` rather than `"@ghagen/ghagen"`, and two used `{ ... }`
placeholders where the model has to be real for the YAML below to be honest; both fixed. An empty
` ``` ` fence trailing the end of `escape-hatches.mdx` — rendering as an empty code block on the
published page — was removed. Every snippet that feeds a generated block now names the same model
the generator builds.

### Deliberately not done

- **The fence-adjacency check** (the issue's "What is still open"). Out of scope for this change and
  still absent. It is now smaller than it was — nine of the eleven yaml fences no longer exist to be
  mis-adjacent — but every `python` / `typescript` fence in the guides still depends on a blank line
  nobody is checking, and `dry-patterns.mdx` and `cookbook.mdx` were not touched here.
- **Generating the source snippets as well as the output.** The Python and TypeScript tabs remain
  hand-written, so "this code produces this YAML" is still a human-maintained correspondence — only
  the YAML half is machine-checked. Making it airtight means extracting the shown source from the
  snippet modules by region marker, which is a larger change and would force one import block to
  serve every example on a page.
- **Remedies 2 and 3.** Not implemented; remedy 1 subsumes 2 (there is nothing left to mark) and 3
  would have stopped oxfmt fixing genuinely malformed examples, which is how the collateral above
  was found in the first place.
- **`scripts/_gate.sh` was not changed.** The docs gate already covers this: `oxlint src` reaches
  `src/snippets/`, `oxfmt .` formats it, and `astro build` — i.e. `scripts/typecheck.sh docs` — is
  what runs the check. The mechanism is read-only unless `GHAGEN_DOCS_SNIPPETS_UPDATE` is set.

**Counts after the change:** `pytest 1016 passed` (was 1008; the eight new docs-snippet tests),
`vitest 1069 passed (46 files)` — unchanged. `scripts/fmt.sh docs --fix` rewrites nothing.
