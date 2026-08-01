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

**Amendment (proposal 13):** the inventory above was incomplete — **headers** were a gap of the
same kind, and a larger one. Every one of the ten emitter goldens passed `header=None`, so the byte
oracle contained zero header bytes and never saw a live five-way byte divergence between the ports.
Closed by `fixtures/expected/header_*.yml` (six files, read byte-for-byte by both suites). The gaps
listed above remain open; they are body-shape gaps and 13 adds no body coverage. Scheduling note:
the remedy above and the header goldens touch the same two test files (`test_snapshots.py`,
`snapshots.test.ts`) and the same directory, so a single pass over `fixtures/expected/` avoids a
second round of conflicts.
