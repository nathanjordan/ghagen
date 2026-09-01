# Four caller-less exports in `pin/github.ts`

**Status:** closed — no longer true; verified round 3

Four exports in `packages/typescript/src/pin/github.ts` have no caller in production or in either
suite. Unlike the surface proposal 20 deleted, these are not branched on and cost nothing at runtime
— the fix is an `@internal` marker or a `_` prefix, not a deletion, so it was not worth an agent in
round 2.

Check against proposal 16 as landed before touching them: 16 rewrote both production adapters, and
some of these may have acquired a caller or been removed outright.

## Resolution

No change needed. This issue told its own reader to re-check it against proposal 16 as landed, and
that check now says the premise is false on both counts.

All four exports carry callers in `packages/typescript/src/pin/github.test.ts`:

| export            | site                | caller               |
| ----------------- | ------------------- | -------------------- |
| `_refUrls`        | `pin/github.ts:427` | `pin/github.test.ts` |
| `_isAnnotatedTag` | `pin/github.ts:434` | `pin/github.test.ts` |
| `_commitSha`      | `pin/github.ts:439` | `pin/github.test.ts` |
| `_parseNextLink`  | `pin/github.ts:453` | `pin/github.test.ts` |

And all four already carry the `_` prefix this issue proposed as the remedy, so the marker work is
done as well. An export exercised by the suite is not a caller-less export; it is a deliberately
tested internal, which is what the `_` prefix is for.
