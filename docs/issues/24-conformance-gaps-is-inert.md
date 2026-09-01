# `schema/conformance-gaps.yml` is inert, and its top-level key can be garbled unnoticed

**Status:** closed — from round 2. Found by the whole-branch adversarial review (test-suite integrity)

`schema/conformance-gaps.yml` sits alongside `conformance-scopes.yml` and `conformance-values.yml` —
two files that are genuinely load-bearing shared oracles, each proven to fail both suites when
corrupted by a single byte. `conformance-gaps.yml` is not in that class. Nothing drives it, and its
top-level key can be renamed without any gate noticing.

That is worse than an absent file. It reads like a peer of the two tables that work, so the next
person to record a known conformance gap will write it here and believe it is bound.

## Two ways out

1. **Drive it.** Give it the same treatment its siblings have: a sweep in each port that reads every
   row and asserts the gap is still present (a gap table whose entries have silently been _closed_ is
   also information — it means a row can be deleted). This makes the file honest and turns the gap
   list into a regression guard against re-introducing a closed gap.
2. **Delete it** and move its content into `docs/issues/`, where unfixed things already live and
   nobody expects a gate.

Option 1 is the better fit if the gaps are genuinely per-schema facts that both ports must agree
about; option 2 if the list is really a to-do. Read the file's current contents before choosing —
that is the deciding evidence, and it changed during round 2.

## Related, same shape

- The tag-grammar "consumed every row" guards are tautological in at least one port — the assertion
  reduces to comparing a dict's key set to itself. A table with a tautological driver is
  indistinguishable from a table with no driver. (Being fixed in the round-2 review pass; check
  whether the fix covers both ports.)
- `docs/issues/21` records that `UpdatePlan`'s field list is hand-mirrored between the two suites with
  nothing comparing them — the same failure mode one layer up.

## Files

- `schema/conformance-gaps.yml`
- `schema/conformance-scopes.yml`, `schema/conformance-values.yml` — the working peers, for the shape
  a driver should take

## Resolution

Took option 1 (drive it), not option 2 (delete). Reading the file's current contents was the
deciding evidence the issue asked for: every scope's allow-list is empty (no genuine gap survives
as of round 2 -- the last one, `job.snapshot`, closed when `ImageSnapshot` landed). An empty table
is still real per-schema data both ports must agree on -- "we currently know of zero intentional
gaps" -- so the fix is to make the file's own shape and its (currently vacuous) rows both
load-bearing, the same way `conformance-scopes.yml` is load-bearing independent of whether any of
its scopes end up empty.

Both sweeps (`packages/python/tests/test_schema/test_conformance.py`,
`packages/typescript/src/models/conformance.test.ts`) already read the file per-scope via
`.get(key, {})`, which is exactly why corruption was invisible: a garbled or missing key silently
degrades to "no gaps recorded," indistinguishable from the file's actual (empty) content. Two
additions close that:

1. **A parity guard**, `test_gap_set_matches_sweep` / "gap set matches the sweep," mirroring the
   existing `test_scope_set_matches_shared_table` pattern: both sweeps now assert the gaps file's
   top-level snapshot keys, and each snapshot's scope keys, equal the sweep's key set exactly. This
   is what makes the file load-bearing _regardless of row content_ -- garbling
   `workflow_schema` -> `workflow_schemas`, or any scope key under it, now fails both suites even
   though every allow-list is empty.
2. **A "closed gap" assertion** inside the existing per-scope test: a listed name must not only
   still exist upstream (already checked, "stale") but must still be _uncovered_ by the port's
   model. If the model now covers it, the gap was fixed without the row being deleted, and the test
   fails until it is. This is the "assert the gap is still present" mechanism the issue asked for --
   a recorded gap is now a test that the gap still exists, not a comment that happens to be YAML.

**Proof both suites fail on single-byte / single-key corruption** (`schema/conformance-gaps.yml`,
reverted after each check):

- Top-level key garbled (`workflow_schema:` -> `workflow_schemas:`):
  - Python: `test_gap_set_matches_sweep` --
    `AssertionError: conformance-gaps.yml top-level keys diverge from the sweep: sweep has
['action_schema', 'workflow_schema'], conformance-gaps.yml has ['action_schema',
'workflow_schemas'].`
  - TypeScript: `schema conformance sweep > gap set matches the sweep` --
    `AssertionError: expected [ 'action_schema', 'workflow_schema' ] to deeply equal [
'action_schema', 'workflow_schemas' ]`
- Scope key garbled one level down (`job: []` -> `jobb: []`): same test, same shape of failure in
  both ports (`'job'` extra on one side, `'jobb'` on the other).
- Closed-gap regression (`job: []` -> `job: [snapshot]`, a property `Job`/`ImageSnapshot` already
  covers):
  - Python: `test_scope_properties_covered[workflow_schema.json:job]` --
    `AssertionError: workflow_schema.json:job allow-list names ['snapshot'] that Job now covers --
the gap has been closed. Remove them from conformance-gaps.yml.`
  - TypeScript: `workflow_schema.json:job model covers every schema property` --
    `AssertionError: workflow_schema.json:job allow-list names ["snapshot"] that the model now
covers -- the gap has been closed. Remove them from conformance-gaps.yml.`

`packages/python/CONTEXT.md` and `packages/typescript/CONTEXT.md` each gain a **Gap** glossary
entry next to **Scope**, stating the three claims a row now carries. Gate numbers after the change:
pytest 913 -> 914, vitest 965 -> 966 (45 files), one new test per suite.
