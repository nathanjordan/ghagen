# Integration fixture coverage gaps

**Status:** open — from round 1 test-integrity review

`fixtures/expected/` exercises none of: a `defaults:` block, empty `workflow_dispatch`
(present-null), a dynamic extras interleave on an alphabetical spec (e.g. `merge_group`), or
SHA-pinned `uses:` refs. The round's "snapshots are the byte oracle" claim is hollow for exactly
the paths it changed; those are unit-covered only. Add one workflow fixture covering all four.
