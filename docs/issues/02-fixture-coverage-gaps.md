# Integration fixture coverage gaps

**Status:** open — from round 1 test-integrity review

`fixtures/expected/` exercises none of: a `defaults:` block, empty `workflow_dispatch`
(present-null), a dynamic extras interleave on an alphabetical spec (e.g. `merge_group`), or
SHA-pinned `uses:` refs. The round's "snapshots are the byte oracle" claim is hollow for exactly
the paths it changed; those are unit-covered only. Add one workflow fixture covering all four.

**Amendment (proposal 13):** the inventory above was incomplete — **headers** were a fifth gap of
the same kind, and a larger one. Every one of the ten shared goldens passed `header=None`, so the
byte oracle contained zero header bytes and never saw a live five-way byte divergence between the
ports. Closed by `fixtures/expected/header_*.yml` (six files, read byte-for-byte by both suites).
The four gaps listed above remain open; they are body-shape gaps and 13 adds no body coverage.
Scheduling note: the remedy above and the header goldens touch the same two test files
(`test_snapshots.py`, `snapshots.test.ts`) and the same directory, so a single pass over
`fixtures/expected/` avoids a second round of conflicts.
