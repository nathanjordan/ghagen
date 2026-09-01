# The docs formatter rewrites documented program output

**Status:** open — from round 2. Surfaced while implementing proposal 12

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

````
<TabItem label="Python">
```python
Job(
    runs_on="ubuntu-latest",
)
````

```

becomes `runs*on=` at column 0. Insert one blank line after the `<TabItem>` and oxfmt leaves the block
byte-identical.

That is not hypothetical. `main` shipped **syntactically invalid Python** in
`docs/src/content/docs/guides/cookbook.mdx` — `runs*on=`, `if*=`, `github.event*name`, five sites —
and `scripts/fmt.sh docs` passed on it, because the corrupt form was what the formatter considered
canonical. `docs/src/content/docs/guides/dry-patterns.mdx` was de-indented the same way. Both are
fixed; every `.mdx` under `docs/src/content/docs/` now has the blank line.

### The two defects are distinct and only one is fixed by the blank line

| | mechanism | remedy |
| --- | --- | --- |
| yaml gutter collapse (this issue, as originally filed) | oxfmt parses the block as yaml and reformats it | the eight `{/* prettier-ignore */}` markers, still load-bearing |
| code-fence prose mangling (new) | the block is not recognised as code at all | a blank line after the JSX tag |

Measured directly: removing the `prettier-ignore` markers from `comments.mdx` while the blank lines
are in place still collapses `on:  #` → `on: #`. The markers are not superseded.

### What is still open

The gate asymmetry the issue was filed for is unchanged: `scripts/fmt.sh docs` passes whichever way
the bytes land, so nothing reports the loss. A fence-adjacency check — no fence may sit against a JSX
tag — would make this class structurally impossible instead of relying on nobody deleting a blank
line. That check does not exist yet.
```
