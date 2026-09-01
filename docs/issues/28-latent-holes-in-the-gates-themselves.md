# Latent holes in the gates themselves

**Status:** closed — from round 2. Found by the whole-branch adversarial review

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

## Resolution

All three re-verified against the current tree first (line numbers had moved since `scripts/` was
pulled into the ruff/pyright gates by issue 17); all three still reproduced exactly as described.
Widened the check at all three sites rather than narrowing the message — nothing here was reassuring
about something disproportionate to fix.

1. **`ghagen_schema check` untracked-file blindness** (`scripts/ghagen_schema/check.py`). Added a
   `git status --porcelain --untracked-files=all -- <rel>` alongside the existing `git diff
--exit-code`, inside the same snapshot/restore window; either one reporting non-clean now fails
   the gate. Test: `packages/python/tests/test_schema/test_check.py`, a throwaway git repo (never the
   real one — `check.REPO_ROOT`/`GENERATED_TYPES_DIR` are monkeypatched onto it) with one committed
   file, then a `generate.run` stub that writes a second, never-committed file into the generated
   dir. Red on the pre-fix code (`0 == 1`, "Schema types are up to date" printed for the untracked
   file), green after.

2. **`pin/sources.py` sys.path cleanup by position.** Changed the `finally` guard from `sys.path[0]
== parent: del sys.path[0]` to `parent in sys.path: sys.path.remove(parent)` — removal by
   identity, which finds the entry wherever something else's insertion during `resolve_app` left it,
   and (per the existing idempotency test) still leaves an unrelated identical-string entry the
   caller owns untouched, since `remove` only deletes the first occurrence. Test:
   `test_sys_path_entry_is_removed_even_if_something_shifts_it` in
   `packages/python/tests/test_pin/test_sources.py` — a config that itself does `sys.path.insert(0,
...)` during import, pushing the tracked entry to index 1. Red on the pre-fix code (leaked
   `True`), green after. (First draft of this test had its own `finally` block silently cleaning up
   `parent` before the assertion ran, which made it pass unconditionally regardless of the fix —
   caught by deliberately checking it went red against the reverted source, not just green against
   the fix.)

3. **Pattern anchors decorative in Python, load-bearing in TypeScript.** Went with the sweep-assertion
   option over the `^(?:…)$`-wrapping option: the assertion is enforced identically in both ports
   already (mirrored sweep files), needs no runtime wrapping logic in either, and fails at the moment
   a new unanchored pattern is bound rather than only when someone happens to add a superstring reject
   vector. Added `test_value_pattern_is_anchored` (Python,
   `packages/python/tests/test_schema/test_conformance.py`) and its mirror (TypeScript,
   `packages/typescript/src/models/conformance.test.ts`), parametrized over the same
   `conformance-values.yml` bindings as the existing pattern-identity check, asserting each bound
   pattern's source starts with `^` and ends with `$`. Today's one real binding
   (`imageSnapshot.version`) is already anchored, so that parametrized test alone can never turn red
   against current data — it guards the _next_ pattern, not this one. To get an actual red/green
   proof, the anchor check itself was factored out (`_assert_pattern_anchored` / `assertPatternAnchored`,
   test-only, not production code) and exercised directly against a synthetic unanchored pattern
   (`re.compile(r"\d+")` / `/\d+/`) in both ports: it raises for that input and not for `^\d+$`. This
   is the one site where testing the production data path red/green wasn't possible without
   fabricating a fake grammar binding in the real spec registry — disproportionate for what is, in
   effect, a lint rule on future pattern additions — so the direct unit test on the extracted
   assertion is what stands in for it.

No `AGENTS.md` changes: it names `python -m ghagen_schema check` as "the ADR-0003 schema staleness
guard" without describing what it does or does not see, so widening the check doesn't make that
description stale.

Gates green: `typecheck.sh all`, `lint.sh all`, `fmt.sh all`, `test.sh all` (919 pytest passed, up
from a verified 913 baseline on this branch point; 968 vitest passed / 45 files, up from 965),
`ghagen check-synced`, `ghagen deps check-synced`, `python -m ghagen_schema check`.
