# `schema/conformance-gaps.yml` is inert, and its top-level key can be garbled unnoticed

**Status:** open — from round 2. Found by the whole-branch adversarial review (test-suite integrity)

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
