# Latent holes in the gates themselves

**Status:** open — from round 2. Found by the whole-branch adversarial review

Three places where a gate reports success on input it cannot actually see. All LATENT — no argv
reaches them today — and all verified by direct read while triaging. They are grouped because they
share one failure mode: **the check is narrower than the reassurance it prints.**

## 1. `ghagen_schema check` cannot see a generated file that was never committed

`scripts/ghagen_schema/check.py:42-44` probes staleness with:

```python
diff = subprocess.run(["git", "diff", "--exit-code", "--", str(rel)], cwd=REPO_ROOT)
```

inside a snapshot/restore `try/finally`. `git diff` is blind to untracked paths. If a generated file
is never committed, regeneration creates it, `git diff` reports no change to any tracked path, and the
script prints **"Schema types are up to date"** and exits 0.

LATENT: every generated path is currently tracked. It bites on the next generator output added — and
it is the same failure shape proposal 23 says it fixed (the old script "printed 'Schema types are up
to date'" while destroying edits). The message survived the rewrite, one layer down.

Fix: add `git status --porcelain --untracked-files=all -- <rel>` to the staleness test, or `git add -N`
the generated paths before diffing.

## 2. The `sys.path` window in `pin/sources.py` can still leak

Proposal 20 item D gave the config loaders' `sys.path` insertion a lifetime, which was the right
change. The cleanup guard at `packages/python/src/ghagen/pin/sources.py:76` is:

```python
if inserted and sys.path and sys.path[0] == parent:
    del sys.path[0]
```

Correct in the common case, but it only removes the entry when it is still at index 0. If anything
executed during `resolve_app` — the user's own config module, most plausibly — inserts at position 0,
the guard finds a different value there and silently declines to clean up. The entry then leaks for
the life of the process.

The `finally:` blocks hand-restoring globals in `test_sources.py` are the smell that this is fragile
rather than solved.

Fix: remove by identity rather than by position (`sys.path.remove(parent)` guarded by `inserted`), or
capture and restore the whole list.

## 3. Pattern anchors are decoration in Python and load-bearing in TypeScript

`packages/python/src/ghagen/models/_base.py` uses `pattern.fullmatch`, so the `^`/`$` in each pattern
are redundant — the docstring says so, and says they are kept only so `.pattern` stays byte-identical
to the string `schema/conformance-values.yml` compares. TypeScript uses `pattern.test`, which depends
on those anchors entirely.

The two ports therefore agree today by coincidence of the anchors being present. The next grammar
copied from a JSON Schema `pattern` — where **unanchored is the norm** — makes Python reject
`"abc1def"` against `\d+` and TypeScript accept it. `conformance-values.yml`'s reject vectors catch
this only if someone happens to add a superstring vector.

Fix: assert in the shared conformance sweep that every bound pattern source starts with `^` and ends
with `$`, or have TypeScript wrap as `^(?:…)$` so the anchors stop being load-bearing in either port.

## Related

`docs/issues/09` — neither port type-checks its own tests. `docs/issues/17` — `scripts/` is outside
every Python gate, which is where item 1 lives. Same family; worth one pass.
