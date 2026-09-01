# The grammar-violation message advises an escape hatch the field cannot take

**Status:** resolved — from round 2. Surfaced while implementing proposal 10

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

## Resolution

Went with option 1: `ImageSnapshot.version` / `ImageSnapshotInput.version` widened to
`str | Raw[str] | None` / `string | Raw<string>`, matching the precedent already set by every other
bypassable published field (`permissions.*`, `job.runs_on`, `job.deployment`, `job.permissions`,
action `runs.using`). Pre-1.0, backward-compatible, no shim needed. The messages themselves
(`_base.py:239-240`, `_base.ts:366-367`) needed no wording change — they were already stating the
check's real design; what was false was that the one field reachable through them didn't implement
it. They are true now.

Went further than widening the field, closing the class rather than the instance:

1. **Byte-oracle fixture.** `Raw` reaches the emitter by a different path than a plain string
   (`unwrap_raw()` / `raw_scalar` bypass the block-scalar auto-promotion pass in
   `emitter/yaml_writer.py::_apply_block_scalar_style`), so what a `Raw` version emits had to be
   proven, not assumed. `fixtures/expected/escape_hatches.yml`'s `typed` job now sets
   `snapshot: {image-name: custom-image, version: latest}` — `"latest"` fails the field's own
   grammar, so accepting it proves the hatch bypasses the check rather than coincidentally matching
   it. Asserted byte-identical by `test_snapshots.py::test_escape_hatches` and
   `snapshots.test.ts`'s `"escape_hatches.yml"` case; a `Raw`/`raw()` version emits a plain scalar,
   same as an ordinary string.

2. **New conformance invariant: a field carrying a spec pattern MUST admit `Raw`.**
   `schema/conformance-values.yml`'s header now documents this as the sweep's third assertion (of
   four). Both ports execute the same check by the same means — construct every `reject` vector
   wrapped in `Raw(...)`/`raw(...)` and require it not to throw — reusing the table's existing
   `reject` vectors rather than adding new YAML data.
   - **Python** (`test_conformance.py::test_value_raw_hatch_bypasses_the_grammar`): runtime-executed
     and load-bearing on its own, because Pydantic validates a model's declared annotation on every
     construction. Narrowing `ImageSnapshot.version` back to `str | None` makes it fail with
     `pydantic_core._pydantic_core.ValidationError: ... Input should be a valid string
[type=string_type, input_value=Raw(''), input_type=Raw]`.
   - **TypeScript** has no runtime type information, so a plain constructed-vector test inside
     `conformance.test.ts` cannot be load-bearing: `tsconfig.json` excludes `src/**/*.test.ts` from
     `tsc --noEmit`, and JavaScript enforces nothing at runtime — a `raw()`-branded object sails
     through a plain-`string`-typed field with zero signal (confirmed: narrowing the field left both
     `npx vitest run` and `npm run typecheck` green). The fix was structural: the binding
     (`ValueBinding` + `VALUE_BINDINGS`) moved out of the test file into
     `packages/typescript/src/models/conformance-values.ts`, a normal `src/` module that `tsc
--noEmit` does visit. `conformance.test.ts` imports it and still executes it at runtime (the
     `"accepts a raw() value in place of the grammar"` case), so the invariant is both compile-time
     enforced and runtime executed. Narrowing the field back now fails `npm run typecheck` (the real
     `typecheck.sh` gate) with `error TS2322: Type 'string | Raw<string>' is not assignable to type
'string | undefined'. Type 'Raw<string>' is not assignable to type 'string'.` — `npx vitest run`
     alone stays green, which is the documented, fundamental TS/JS asymmetry with Python here, not a
     gap: the gate suite as a whole (`typecheck.sh` + `test.sh`) catches the regression in both ports.

3. **Docs.** `docs/src/content/docs/python/api/job.md`'s `ImageSnapshot` parameter table now reads
   `version: str | Raw[str] | None`. TypeScript's API reference is TypeDoc-generated from doc
   comments (no manually maintained page); `ImageSnapshotInput.version`'s doc comment was updated
   instead. Both `CONTEXT.md` files gained a note that a `patterns`-carrying field's input type must
   admit `Raw`/`Raw<...>`, pointing at `conformance-values.yml`'s check.

**Seeds issue 27.** The raw-hatch check's per-field `{spec, construct, constructCommented}` binding
table (`VALUE_BINDINGS` in both ports) is structurally the executed-vector table issue 27 proposes
(`schema/conformance-inputs.yml`) — this work did not build that table (out of scope here), but the
binding shape it needed is a natural seed for it.
