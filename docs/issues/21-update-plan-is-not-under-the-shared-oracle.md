# The **UpdatePlan** is asserted twice, not once

**Status:** open — from round 2. Surfaced while implementing proposal 18

The plan `ghagen deps update` prints is the newest cross-port contract in the repo and the only one
of its kind that is **not** bound by a shared file. Both ports assert it against a hand-maintained
literal in their own test file:

- `packages/python/tests/test_cli/test_deps.py:477-488` — `_PLAN_FIELDS`, a ten-name `set`
- `packages/typescript/src/cli/deps.test.ts:215-225` — `PLAN_FIELDS`, the same ten names as a
  sorted array

Nothing compares the two. Adding an eleventh field to one port and its test passes both suites, and
the divergence surfaces only when a workflow reads a `$GITHUB_OUTPUT` key the other port never
writes.

## Why this is the wrong shape for this repo

Every other cross-port contract here is a **file both suites read**:
`fixtures/cli-exit-codes.yml` for exit codes, `schema/conformance-scopes.yml` for spec surface,
`fixtures/expected/` for emitted bytes — including `fixtures/expected/upgrade_report.json`, the
golden for the _report_ the plan is derived from. The plan is the one link in that chain with no
peer file. Two hand-maintained lists that no test compares is exactly the defect round 2's
proposal 11 found in `spec.test.ts:96-100` and replaced with a typed map.

## Two concrete gaps

**1. No `fixtures/expected/update_plan.json`.** A golden plan both ports must emit byte-identically
for the same fixture project, sitting next to `upgrade_report.json`. It pins the field _set_, the
field _order_ (both formats promise the same order), and the value encodings the two formats differ
on — `labels` is comma-separated under `github` and a list under `json`, which is precisely the kind
of per-format rule a shared golden catches and a field-name set does not.

**2. No `deps update` rows in `fixtures/cli-exit-codes.yml`.** The fixture has
`bad-format-value` and `bad-mode-value` rows for `deps upgrade` but none for `deps update`, whose
flag validation is strictly larger: unknown `--mode`, unknown `--output`, unknown `--format`, and a
newline in `--branch-prefix` / `--commit-message-prefix` / `--labels`. All six exit `2` and all six
are asserted only inside each port's own test file
(`test_deps.py::TestDepsUpdateFlagValidation`, `deps.test.ts` `describe("deps update flag
validation")`).

The newline rows are the ones worth having shared: under `--format github` a newline in a value
forges extra `$GITHUB_OUTPUT` keys, so that check is an output-injection guard, and a port that
loses it loses it silently.

## What a fix looks like

Add the golden and the rows, then delete both `PLAN_FIELDS` literals in favour of reading the shared
file — the same move `test_exit_codes.py` and `exit-codes.test.ts` already make for their table. The
inline assertions are not wrong; they are just unbound, and the repo already owns the binding
mechanism.

## Files

- `fixtures/expected/update_plan.json` — to create
- `fixtures/cli-exit-codes.yml` — six rows to add
- `packages/python/tests/test_cli/test_deps.py:477-488` — literal to delete
- `packages/typescript/src/cli/deps.test.ts:215-225` — literal to delete
- `fixtures/expected/upgrade_report.json` — the precedent to copy

## Why it was deferred

Both `fixtures/` files were **outside proposal 18's allowlist**. 18 built the plan, published it as
composite-action outputs, and asserted it in both ports — mirrored by hand rather than shared,
deliberately and with the mirror flagged, rather than silently editing files another proposal owned.
Whoever owns `fixtures/` should close it.
