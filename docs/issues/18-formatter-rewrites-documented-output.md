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
