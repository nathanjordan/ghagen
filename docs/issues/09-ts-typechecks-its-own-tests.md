# The TypeScript typecheck gate skips three things, including every test file

**Status:** open — from round 2. Deferred out of proposal 09 (item (b)); scope widened by proposal 23

`packages/typescript/tsconfig.json` excludes:

```json
"exclude": [
  "node_modules", "dist", "src/**/*.test.ts",
  "src/integration/test-utils.ts", "src/pin/transport-contract.ts", "src/paths.ts"
]
```

`scripts/typecheck.sh ts` therefore checks none of them. A `*.test.ts` file can reference a field
that no longer exists and nothing fails until the test runs — and for a type-only mistake, not even
then.

**The list grows.** Proposal 16 added `src/pin/transport-contract.ts` during round 2 — a test-only
module living under `src/`, excluded for exactly the reason `src/integration/test-utils.ts` already
was. That is the shape of the defect: every new shared test helper is a correct-by-local-reasoning
addition to a list nobody is auditing, and each one silently removes a real module from the gate.
Round 2 alone took the list from three entries to four.

**Measured, not inferred.** Proposal 23's implementer probed the gate by injecting
`export const zz: number = "nope";` into `src/paths.ts` and the gate returned **rc=0**. Re-probing
through an included file (`src/models/_base.ts`) returned rc=2, so the gate is sound for what it
covers — the hole is exactly the exclude list.

Note `src/paths.ts` is also the file at the centre of `docs/issues/08` (the `FIXTURES_DIR`
collision). Two round-2 issues land on one unchecked file.

## Why it was deferred, and what to check first

**Not for cost.** Turning it on voids proposal 11's stated rationale for `registry.ts`, which
proposal 22 then quotes approvingly in its own argument. Both siblings were ready at the time;
landing this mid-round would have forced two ready proposals to rewrite their reasoning.

Whoever picks this up must re-read 11 and 22 **as landed** and check whether those rationales still
stand, before touching `tsconfig.json`.

Related: `docs/issues/17` — `scripts/` is outside every Python gate. Same shape of defect in the
other port; worth fixing in one pass.
