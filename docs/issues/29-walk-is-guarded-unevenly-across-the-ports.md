# `walk()` is guarded unevenly across the ports, and one guard asserts a set

**Status:** closed — fixed directly, round 3. From round 2. Found by the whole-branch adversarial
review (test-suite integrity)

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

## Resolution

Verified empirically, not just by reading: each of the three `_scan_for_models` branches
(`packages/python/src/ghagen/models/_base.py:63-64` `Commented`, `:65-66` `Raw`, `:70-72`
`list`/`tuple`, plus `:67-69` `dict`) was broken one at a time — return early instead of recursing,
or recurse in `reversed()` order — and the full `packages/python` suite was run after each break.
`dict` and `list`/`tuple` _existence_ were already well-guarded (breaking either failed ~50 tests
across `test_pin`/`test_synth`). `Commented` and `Raw` were not: breaking either left **913/913
passing, zero failures**. Reversing the `list`/`tuple` iteration order likewise left 913/913
passing — the real gap in the third branch wasn't existence, it was that nothing observed _order_
there, which is exactly proposal 24's point: order is what determines emission order now that the
explicit `order` payload is gone.

`packages/python/tests/test_models/test_walk.py` gained two tests and one strengthened assertion,
each mirroring a TypeScript twin in `packages/typescript/src/models/walk.test.ts`:

- `test_walk_traverses_commented_wrappers_but_not_into_raw` — peer of "traverses through Commented
  wrappers but not into Raw". Covers both the `Commented` branch (`:55`/`63-64`) and the `Raw`
  branch (`:57`/`65-66`) in one test, same as the TypeScript twin. Python attaches a `Commented`
  wrapper to a whole field's value rather than to one list item (`_preserve_commented` re-attaches
  the wrapper to the _field_ after validation — pydantic's `list[OrRaw[Step]]` item type rejects a
  bare `Commented` list element, unlike TypeScript's looser array dispatch) — so `steps` is built
  with `with_comment([Step(...)], "pin me")` instead of wrapping one list element directly. Same
  branch, same guarantee, a construction shape native to this port.
- `test_walk_visits_depth_first_pre_order_over_a_nested_document` replaces
  `test_walk_reaches_steps_inside_workflow_jobs` — peer of "visits depth-first, pre-order, over a
  nested document". This is both the line-41 set→order fix and the third branch's peer: expanded
  to two jobs (`build`, `lint`) like the TypeScript twin, and asserts the full ordered sequence via
  a `_visit_labels` helper (the peer of `visitLabels`) instead of `{s.uses or s.run for s in steps}
== {...}`. A set assertion is blind to a job or step reordering; this one is not.
- `test_children_yields_direct_nested_models` gained the same ordered-list assertion the
  TypeScript twin's "yields bare Models, not key/model records" already had (`toEqual([...])`);
  the Python peer previously checked only `isinstance` + `len`.

Red-green proof, one branch at a time (break → run `test_walk.py` → restore → confirm green;
`_base.py` diffed byte-identical to its pre-break state after each restore):

| Branch                                                                                          | Break                                                                   | Test that went red                                                                                                   |
| ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `Commented` (`:63-64`)                                                                          | `elif isinstance(value, Commented): return`                             | `test_walk_traverses_commented_wrappers_but_not_into_raw` (`[] == ['actions/checkout@v4']`)                          |
| `Raw` (`:65-66`)                                                                                | `elif isinstance(value, Raw): yield from _scan_for_models(value.value)` | `test_walk_traverses_commented_wrappers_but_not_into_raw` (leaked `actions/never-seen@v1`)                           |
| `list`/`tuple` order (`:70-72`)                                                                 | `for item in reversed(value):`                                          | both `test_children_yields_direct_nested_models` and `test_walk_visits_depth_first_pre_order_over_a_nested_document` |
| `dict` order (`:67-69`, bonus — not one of the three cited branches, but the same order defect) | `for v in reversed(list(value.values())):`                              | `test_walk_visits_depth_first_pre_order_over_a_nested_document`                                                      |

Reverse direction checked: every Python test in `test_walk.py` has a structural TypeScript peer in
`walk.test.ts` (by name and shape); Python guards nothing TypeScript does not. TypeScript's ninth
test, "dedents an extras-nested step's run at emit", has no Python peer either, but it is an
emitter-level H14 regression check (`toYaml` output), not a `_scan_for_models`/`walk()` branch
guard, so it is out of this issue's scope and left untouched.

`uv run --directory packages/python pytest` (full `packages/python` suite): **914 passed** (913 →
914; one test replaced, two added, one net addition after the replacement). `npx vitest run`
(`packages/typescript`, unmodified by this fix) was independently confirmed to already read **965
passed (45 files)** at this branch point before any change here — the round-3 baseline quoted
elsewhere as 970 does not match `HEAD` on this worktree; not caused by, or a regression from, this
fix.

Proposal 24's `walk-order` table (a shared traversal table per model kind, item 3 of the issue's
Fix section) was not built — out of scope for a test-parity fix; left as a follow-up if the drift
recurs.
