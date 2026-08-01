# Integration fixture coverage gaps

**Status:** open — from round 1 test-integrity review

`fixtures/expected/` exercises none of: a `defaults:` block, empty `workflow_dispatch`
(present-null), a dynamic extras interleave on an alphabetical spec, or SHA-pinned `uses:` refs. The
round's "snapshots are the byte oracle" claim is hollow for exactly the paths it changed; those are
unit-covered only. Add one workflow fixture covering all four.

The extras example used to be `merge_group`, which is a typed `On` field as of round 2 (proposal
11). `on:` now models every event the canonical Snapshot declares — asserted scope-wide by the
conformance sweep — so the extras half of that fixture needs a key the Snapshot does not carry
(an event GitHub ships ahead of the Snapshot), not a real-but-unmodelled event.

Also added in round 2: no file under `fixtures/expected/` contains `workflow_call` at all. Proposal
11 gave the three `workflow_call` sub-map defs their own TypeScript specs so both ports emit them in
the same canonical key order; that byte change has unit coverage in both ports and no shared
fixture oracle. A `workflow_call` block with inputs, outputs, and secrets belongs in the same
fixture.
