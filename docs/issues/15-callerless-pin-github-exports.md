# Four caller-less exports in `pin/github.ts`

**Status:** open — from round 2, cosmetic

Four exports in `packages/typescript/src/pin/github.ts` have no caller in production or in either
suite. Unlike the surface proposal 20 deleted, these are not branched on and cost nothing at runtime
— the fix is an `@internal` marker or a `_` prefix, not a deletion, so it was not worth an agent in
round 2.

Check against proposal 16 as landed before touching them: 16 rewrote both production adapters, and
some of these may have acquired a caller or been removed outright.
