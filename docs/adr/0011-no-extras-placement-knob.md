# `ModelSpec` has no extras-placement knob

**Status:** accepted (2026-07-31)

`ModelSpec.extrasPlacement` is deleted from `packages/typescript/src/models/spec.ts`, together with
its `withinOrder` branch in `orderedEntries` (`emitter/yaml-writer.ts`). `meta.extras` land after
the ordered keys, unconditionally, in both ports. **No peer field is added to Python's `ModelSpec`,
and the TypeScript field is not to be reintroduced.**

This reverses a risk that round-1 proposal 06 explicitly accepted
(`docs/proposals/06-close-modelspec-escape-hatches.md:318`):

> **Risk: `extrasPlacement`/`dynamicKeys` add spec surface few models use.** Accepted — each is
> optional with a behaviour-preserving default, and each replaces a _harder-to-see_ bespoke code path
> with a _visible_ declaration.

That acceptance bundled two fields. One round later they have diverged completely, so the bundle no
longer holds and the two halves are decided separately.

## Why

**`dynamicKeys` acquired its adapter; `extrasPlacement` never did.** `MATRIX_SPEC` sets
`dynamicKeys` (`models/job.ts`), read in `models/_base.ts` — a real seam with a real implementation
on the other side. `extrasPlacement` had **zero setters** across all eight files holding `ModelSpec`
literals, and **zero tests**: the `withinOrder` body was untested dead code, not merely unused
configuration.

**Its one named candidate took the other road on the day 06 landed.** Proposal 06 named the intended
adapter outright — "lets the one model that wants interleaving (`On`) get it declaratively" — and
`ON_SPEC` shipped with `order: { kind: "alphabetical" }`. Under `alphabetical` the field is moot by
its own documentation. The single candidate declined it at birth and no other has appeared since.

**The only reachable consequence of ever setting it was a parity break.** Python has no peer field.
A spec choosing `withinOrder` would make TypeScript emit a key order Python cannot reproduce, in a
port pair whose parity is enforced by shared golden fixtures. The knob's entire realizable behaviour
was "diverge from the other port."

**One adapter is a hypothetical seam; zero is not a seam at all.** A spec field is a seam by
construction — a place a model can alter behaviour without editing the emitter. That is exactly why
it needs an adapter to justify itself. Deleting it concentrates nothing and loses nothing, which is
the deletion test answering in the negative.

## Consequences

**Do not re-add `extrasPlacement`, and do not add a Python `extras_placement`.** Reopen only with a
concrete model that needs interleaved extras *and* a plan for emitting the same bytes from both
ports. Symmetry with `dynamicKeys` is not a reason — that field earned its place by acquiring an
adapter, and this one is being judged by the same standard, not a different one.

**`OrderMode` is a two-case union.** `{explicit}` (order = declaration order) `| {alphabetical}`,
with no third mode and no placement modifier layered on top. Proposal 06's union shape follows from
this deletion rather than being decided separately.

**Round-1 risk acceptances are revisitable on evidence, not on taste.** The argument here is not
"06 was wrong" — it is that the acceptance rested on "few models use it" and one of the two fields
turned out to be used by *none*, with its named candidate having already chosen otherwise. A round-1
acceptance stands until the specific condition it rested on is measured false.
