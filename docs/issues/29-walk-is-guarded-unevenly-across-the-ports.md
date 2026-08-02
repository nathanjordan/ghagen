# `walk()` is guarded unevenly across the ports, and one guard asserts a set

**Status:** open — from round 2. Found by the whole-branch adversarial review (test-suite integrity)

Proposal 24 narrowed `walk()` — correctly. A reviewer re-verified on `main` that the prune protocol
really was caller-less in both ports and that `test_walk_paths_track_field_keys` tested a deleted
feature, so nothing of value was removed. This issue is about what the _remaining_ tests do and do not
bind.

## Python's `walk()` has three branches TypeScript guards and Python does not

`packages/python/src/ghagen/models/_base.py:55`, `:57`, and `:59-64` are each covered by a
TypeScript-side test with no Python peer. The two ports' recursion is supposed to agree — it is the
mechanism behind every cross-port byte guarantee in the repo — and here one port's implementation is
tested three branches deeper than the other's.

## `tests/test_models/test_walk.py:41` asserts a set where its TypeScript twin asserts an ordered list

The Python assertion compares set membership; the TypeScript one compares an ordered sequence. So
Python's suite cannot observe a change in traversal **order**, and TypeScript's can.

This is the same defect proposal 10 was built to close one layer up: `test_spec.py` and `spec.test.ts`
both asserted only _set_ equality of key names, which is why `ModelSpec.order`'s sequence duplication
went unguarded for two rounds. The lesson did not reach `test_walk.py`.

Traversal order is not incidental — it determines emission order for anything downstream of the walk,
which is precisely what round 2 made load-bearing by deleting the explicit `order` payload.

## Fix

1. Change `tests/test_models/test_walk.py:41` to assert the ordered sequence, matching the TypeScript twin. Show it red
   by reversing the recursion order before landing it.
2. Add Python peers for the three guarded branches.
3. Better than both: bind the traversal to a shared table so the two ports cannot drift again. Round 2
   built this pattern four times over (`conformance-scopes`, `conformance-values`, `tag-grammar`,
   `fixtures/expected/`) — a `walk-order` table per model kind is the same move, and it composes with
   the key-order table the review recommended for `ModelSpec`.

## Files

- `packages/python/src/ghagen/models/_base.py:55,57,59-64`
- `packages/python/tests/test_models/test_walk.py:41` — `assert {s.uses or s.run for s in steps} ==
{"actions/checkout@v4", "pytest"}` — and its TypeScript twin
- `docs/proposals/24-narrow-walk.md` — what was deliberately removed, so this does not get re-litigated
