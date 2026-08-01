# `FIXTURES_DIR` names two different directories in the two ports

**Status:** open — deferred out of proposal 23 (dev-script hygiene), round 2

One name, one sentence of documentation, two directories:

```python
# scripts/ghagen_schema/paths.py
#: Shared golden fixtures consumed by both ports' test suites.
FIXTURES_DIR = REPO_ROOT / "fixtures"
```

```ts
// packages/typescript/src/paths.ts
/** Shared golden fixtures consumed by both ports' test suites. */
export const FIXTURES_DIR = resolve(REPO_ROOT, "fixtures", "expected");
```

`fixtures/` contains exactly one entry, `expected/`, so the Python constant points at the parent of
the only thing anyone wants — and both its callers say so immediately:

- `packages/python/tests/test_integration/test_snapshots.py` imports `FIXTURES_DIR`, then
  `SNAPSHOT_DIR = FIXTURES_DIR / "expected"`.
- `packages/python/tests/test_cli/test_deps.py` imports it _as_ `_FIXTURES_ROOT`, then
  `FIXTURES_DIR = _FIXTURES_ROOT / "expected"`, rebinding the name to mean what the TypeScript port
  already means by it.

The TypeScript caller (`packages/typescript/src/integration/test-utils.ts`) uses it directly.

**LIVE divergence, LATENT breakage — and the breakage would be loud, not silent.** Nothing fails
today; both ports resolve real paths and both suites are green. Under the remedy below the failure
is an `ImportError` in Python and a `tsc` error in TypeScript. Under any align-one-port variant it
is `ENOENT`, because `fixtures/` contains **only** `expected/`, so `fixtures/<golden>` can never
resolve to a real-but-wrong file. What is live is the _authoring_ trap: someone writing a cross-port
test reads one doc comment and gets different directories depending on which port they are in, and
`test_deps.py`'s rebinding shows someone has already worked around it. The Python constant also
fails the deletion test on its own terms — every caller strips it back to a pass-through by
re-appending `expected`.

## Remedy

Delete the ambiguous name from both ports and replace it with two unambiguous ones, mirrored:

```python
FIXTURES_ROOT = REPO_ROOT / "fixtures"            # the directory
EXPECTED_DIR = FIXTURES_ROOT / "expected"         # the golden files both ports read
```

```ts
export const FIXTURES_ROOT = resolve(REPO_ROOT, "fixtures");
export const EXPECTED_DIR = resolve(FIXTURES_ROOT, "expected");
```

Then `EXPECTED_DIR` means one directory in both ports, and `test_deps.py`'s rebinding and
`test_snapshots.py`'s re-append both disappear.

## Files

- `scripts/ghagen_schema/paths.py`
- `packages/typescript/src/paths.ts`
- `packages/python/tests/test_integration/test_snapshots.py`
- `packages/python/tests/test_cli/test_deps.py`
- `packages/typescript/src/integration/test-utils.ts`

One more file carries a stale reference to the same constant and belongs with the fix:
`docs/specs/0005-typed-engine-report-seam.md:127` says the golden fixtures are loaded by Python
`tests/test_integration/` via `conftest.py` → `FIXTURES_DIR`, but that `conftest.py` imports only
`SCHEMA_DIR`; the `FIXTURES_DIR` import is in `test_snapshots.py`.

## Why it was deferred

Fixing it means touching five files under `packages/` and `scripts/ghagen_schema/`, which turns a
dev-tooling change into a two-port change and serialises it against test-file work in several
round-2 proposals that took a hard dependency on today's values. Sequence it after those land.
