# The grammar-violation message advises an escape hatch the field cannot take

**Status:** open — from round 2. Surfaced while implementing proposal 10

Both ports reject a value that violates a spec-declared grammar with a message that tells the caller
how to bypass it:

- `packages/python/src/ghagen/models/_base.py:175-178` —
  `"{field} {value!r} must match {pattern}; wrap the value in Raw(...) to bypass the grammar"`
- `packages/typescript/src/models/_base.ts:349-352` —
  `"...must match {pattern}. Wrap the value in \`raw()\` to bypass the grammar."`

**Following that advice does not work on the only field the message can currently fire for.**
`ImageSnapshot.version` is annotated `str | None` (`models/image_snapshot.py:36`) and
`ImageSnapshotInput.version` is `version?: string` (`models/image-snapshot.ts:19`). Passing
`Raw("...")` to a `str | None` field yields a Pydantic `string_type` error; the TypeScript peer is a
compile error. The caller is walked from one rejection into another.

## LIVE — but only in the message, not the check

The check itself is right and its design is deliberate: `_enforce_spec_patterns` skips non-`str`
values precisely so `Raw` **is** the escape hatch, for any field whose annotation admits one. The
defect is that the message states that unconditionally, while `spec.patterns` today names exactly
one field — `version` — and that field's type does not admit one. So the advice is wrong 100% of the
time it is currently reachable.

## Two ways out, and they are not equivalent

1. **Widen the field to accept the hatch.** `version: str | Raw[str] | None` in Python, the
   TypeScript peer likewise. Makes the message true and matches the check's stated design. Cost: it
   is a published-surface change in both ports, and `Raw` values reach the emitter by a different
   path than plain strings — this needs a byte-oracle fixture proving what a `Raw` version emits
   before it lands.
2. **Make the message tell the truth per field.** Only offer the hatch when the annotation admits
   it. Cheap in Python (`type(self).model_fields[field].annotation`); **not available in
   TypeScript**, whose factory has no runtime type information. Doing it in one port only trades a
   wrong message for a cross-port message divergence, which is the kind of drift this round spent
   proposals 11 and 13 closing.

Option 1 is the one that keeps the two ports saying the same thing. It is also the larger change.

A third option — delete the advice clause — is worse than it looks: it makes the message honest by
making the escape hatch undiscoverable, and the hatch is real for any future field typed to take it.

## Files

- `packages/python/src/ghagen/models/_base.py:152-179` — `_enforce_spec_patterns`
- `packages/typescript/src/models/_base.ts:341-353` — `formatModelInputProblem`
- `packages/python/src/ghagen/models/image_snapshot.py:20,36` — the only `patterns` entry
- `packages/typescript/src/models/image-snapshot.ts:19,40` — its peer
- `schema/conformance-values.yml` — binds the pattern strings; a new grammar-carrying field
  reaches this message through it

## Why it was deferred

Found by proposal 10's implementer, who lost an iteration to it while building a spec-sweep helper —
which is the evidence that the message misleads. It is outside proposal 10's allowlist (10 deletes
`ModelSpec.order`; it does not touch `patterns`), and both remedies are interface changes rather
than message edits.
