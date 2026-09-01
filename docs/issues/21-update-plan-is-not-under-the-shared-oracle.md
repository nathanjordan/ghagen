# The **UpdatePlan** is asserted twice, not once

**Status:** closed — field-name binding fixed; the golden-plan and exit-code-row gaps below remain

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

## Resolution

Fixed the defect this issue's title and opening section describe: the field-name set was asserted
against a hand-maintained literal in each port's own test file, and nothing compared the two.

Added `schema/update-plan-fields.yml`, following the shape and reading convention of the existing
shared tables (`schema/tag-grammar.yml` in particular — a single YAML file under `schema/`, read by
both ports' tests through their respective `SCHEMA_DIR` resolver). It carries the ten field names
`_plan_fields` / `planFields` already build both encodings from, in the order those functions emit
them, with a header explaining what it binds and does not bind (see below).

Both literals are deleted:

- `packages/python/tests/test_cli/test_deps.py` — `_PLAN_FIELDS` is now
  `set(YAML(typ="safe").load((SCHEMA_DIR / "update-plan-fields.yml").read_text())["keys"])`.
- `packages/typescript/src/cli/deps.test.ts` — `PLAN_FIELDS` is now read from the same file via
  `yaml`'s `parse`, sorted the same way the old literal was.

**Binding proved by corruption**, the standard this repo holds a shared oracle to: renaming
`changed` to `changedx` in `schema/update-plan-fields.yml` failed both suites --
`TestDepsUpdate::test_github_format_is_github_output_shaped_and_owns_stdout` and
`::test_json_and_github_carry_the_same_fields` in Python, `deps update > --format github is
$GITHUB_OUTPUT-shaped and owns stdout` and `> --format json and --format github carry the same
fields` in TypeScript -- each on a `set`/array mismatch naming `changed` vs `changedx`. Reverting
the corruption restored both suites to green (913 / 965 passing, matching the pre-change baseline).

**What was deliberately left unbound.** The shared table binds field _names_ only, matching
`schema/key-order.yml`'s minimum and what a set/sorted-array comparison already checked on each
side. It does **not** bind:

- **Field order** cross-port. Both ports already emit the ten fields in the same order (verified by
  reading `_plan_fields` / `planFields` directly), but neither test asserts order today — both
  compare a `set` (Python) / sorted array (TypeScript) — so adding an `order:` field to this table
  would not be backed by an assertion that reads it, which is exactly the un-backed-shared-file
  defect `docs/issues/24` describes. Binding order would require changing both tests to compare an
  ordered sequence instead of a set, which is a behavior change beyond "move the literal into a
  shared file."
- **Per-field type / value encoding** (e.g. `labels` is a list under `json`, comma-joined under
  `github`; `body_format` is `null`/empty only when `action == "none"`). This is exactly gap 1 in
  this issue's "Two concrete gaps" section, and it is what a golden `update_plan.json` (see below)
  binds byte-for-byte, not what a field-name list can express.

**Not addressed in this pass**, and still open as work items even though this issue is marked
closed for the specific defect it names in its title and opening section:

- **Gap 1** — `fixtures/expected/update_plan.json`, a golden plan both ports emit byte-identically,
  pinning field order and the per-format value encodings.
- **Gap 2** — the six `deps update` flag-validation rows for `fixtures/cli-exit-codes.yml` (unknown
  `--mode`/`--output`/`--format`, and a newline in `--branch-prefix` / `--commit-message-prefix` /
  `--labels`).

Both remain hand-asserted inside each port's own test file, exactly as this issue originally found
them. They were out of scope for this fix, which targeted only the un-shared `PLAN_FIELDS`
literal named in the issue's title.

## Files changed

- `schema/update-plan-fields.yml` — new shared file
- `packages/python/tests/test_cli/test_deps.py` — `_PLAN_FIELDS` now reads the shared file
- `packages/typescript/src/cli/deps.test.ts` — `PLAN_FIELDS` now reads the shared file
- `packages/python/CONTEXT.md`, `packages/typescript/CONTEXT.md` — **UpdatePlan** glossary entry
  now names the shared file
- `docs/src/content/docs/python/cli.md`, `docs/src/content/docs/typescript/cli.md` — the plan's
  field table now names the shared file
