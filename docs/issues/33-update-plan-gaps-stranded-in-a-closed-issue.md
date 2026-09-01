# The two `deps update` oracle gaps are stranded inside a closed issue

**Status:** closed — both gaps built and proved load-bearing

`docs/issues/21` is marked **closed**, correctly: it names one defect in its title (the un-shared
`PLAN_FIELDS` literal) and that defect is fixed by `schema/update-plan-fields.yml`. But its
Resolution then records two further gaps under the heading "**Not addressed in this pass**, and
still open as work items even though this issue is marked closed" — and nothing tracks them. Open
work living in a closed issue is work nobody will find.

This issue exists to carry them. Both are quoted from 21's own Resolution, unchanged in substance.

## Gap 1 — `fixtures/expected/update_plan.json`

`schema/update-plan-fields.yml` binds field **names** only. It does not bind:

- **Field order across the ports.** Both already emit the ten fields in the same order — verified by
  reading `_plan_fields` / `planFields` directly — but neither suite asserts it: Python compares a
  `set`, TypeScript a sorted array. Adding an `order:` key to the shared table without changing both
  comparisons to ordered sequences would produce exactly the un-backed shared file that
  `docs/issues/24` was filed for.
- **Per-field type and value encoding.** `labels` is a list under `json` and comma-joined under
  `github`; `body_format` is `null`/empty only when `action == "none"`. A field-name list cannot
  express that.

Both are what a golden `fixtures/expected/update_plan.json` binds byte-for-byte, in the same way
`fixtures/expected/` already binds emitted YAML. That is the fix.

## Gap 2 — six missing `fixtures/cli-exit-codes.yml` rows

`deps update`'s flag validation is hand-asserted inside each port's own test file rather than driven
from the shared exit-code oracle. Six rows are missing:

- unknown `--mode`
- unknown `--output`
- unknown `--format`
- a newline in `--branch-prefix`
- a newline in `--commit-message-prefix`
- a newline in `--labels`

## Standard both fixes must meet

`fixtures/expected/` and `fixtures/cli-exit-codes.yml` are shared oracles, so the repo rule applies:
corrupt one byte of the new fixture and confirm **both** suites go red. A golden file that only one
port reads is not an oracle.

## Files

- `docs/issues/21-update-plan-is-not-under-the-shared-oracle.md` — the closed issue this came from
- `schema/update-plan-fields.yml` — binds names; the order/encoding axes are what is missing
- `fixtures/cli-exit-codes.yml` — where gap 2's six rows go
- `fixtures/expected/` — where gap 1's golden plan goes

## Resolution

Both gaps are closed. Every binding below is read by **both** ports, and every one was proved
load-bearing by corrupting it and watching both suites go red (the full log is in the commit
message; a summary is at the end of this section).

### Gap 1 — order, type, and encoding

`schema/update-plan-fields.yml` grew from a bare `keys:` name list into a `fields:` **sequence** of
rows, one per field, each carrying:

- `name` — as before.
- position in the sequence — the **order** axis. Both CLI suites now compare
  `list(json.loads(stdout))` / `Object.keys(JSON.parse(...))` against the file's order. The Python
  suite compared a `set` and the TypeScript suite a `.sort()`ed array; both comparisons are gone,
  which is what `docs/issues/24` demands of a new key — the axis is asserted, not merely declared.
- `json` — `string` / `integer` / `boolean` / `string-array`.
- `github` — `verbatim` / `decimal` / `lowercase-bool` / `comma-joined`, the rule that turns the
  JSON value into a `$GITHUB_OUTPUT` `key=value` right-hand side. This is where `labels` being a
  JSON array and a comma-joined string lives, as data rather than as a sentence in a comment.
- `null_when: {field: action, equals: none}` — on `body_format` and nowhere else. A row with no
  `null_when` is never null, so the table states both halves of the biconditional.

The type/encoding/null axes are driven from `tests/test_pin/test_plan.py` and
`src/pin/plan.test.ts` rather than from the CLI suites, because they need two plans — one with
`action == "none"` and one without — and `plan_update`/`planUpdate` are pure, so both are one line
each there. The name and order axes stay driven from the CLI suites against a live invocation.

`fixtures/expected/update_plan.json` and `fixtures/expected/update_plan_github.txt` are the golden
renders the issue named. They bind one plan's bytes in both encodings — the two-space JSON indent,
the one-element-per-line array, the trailing newline, the literal `key=value` line form — which is
serialization detail the table has no vocabulary for. Both ports render the same plan (same fixed
`today`, same inputs) and compare byte for byte against the same two files.

### Gap 2 — the six exit-code rows

All six are in `fixtures/cli-exit-codes.yml`, and both ports' drivers iterate the table, so a row
is consumed by both by construction:

| row                                 | argv                                              | exit |
| ----------------------------------- | ------------------------------------------------- | ---- |
| `bad-update-mode-value`             | `deps update --mode bogus`                        | 2    |
| `bad-update-output-value`           | `deps update --output bogus`                      | 2    |
| `bad-update-format-value`           | `deps update --format bogus`                      | 2    |
| `newline-in-branch-prefix`          | `deps update --branch-prefix "…\nname=forged"`    | 2    |
| `newline-in-commit-message-prefix`  | `deps update --commit-message-prefix "…\nname=…"` | 2    |
| `newline-in-labels`                 | `deps update --labels "ci\nname=forged"`          | 2    |

The codes were **measured**, not guessed: each argv was run through both ports' `main()` in a fresh
empty directory before any row was written. Both ports answered `2` on all six, with the message on
stderr in both, so there was no parity bug to fix and neither port was changed. That both ports
reach the check at all from an empty directory is itself part of the contract and is why these rows
work without a fixture project: `deps update` validates its flags *before* config discovery, so a
bad flag is a usage error and never gets downgraded to `1` ("no config file found").

### Corruption proof

Thirteen corruptions, each one byte or one row, each run through `./scripts/test.sh py` and
`./scripts/test.sh ts` separately (`test.sh all` is `set -e`, so a Python failure would hide the
TypeScript result). **All thirteen failed both suites**; the tree was restored after each.

| corruption                                                     | pytest | vitest |
| -------------------------------------------------------------- | ------ | ------ |
| `bad-update-mode-value` exit `2` → `1`                          | fail   | fail   |
| `bad-update-output-value` exit `2` → `1`                        | fail   | fail   |
| `bad-update-format-value` exit `2` → `1`                        | fail   | fail   |
| `newline-in-branch-prefix` exit `2` → `1`                       | fail   | fail   |
| `newline-in-commit-message-prefix` exit `2` → `1`               | fail   | fail   |
| `newline-in-labels` exit `2` → `1`                              | fail   | fail   |
| table: `- name: branch` → `- name: branc`                       | fail   | fail   |
| table: swap the `branch` and `title` rows (same set, new order) | fail   | fail   |
| table: `labels` `json: string-array` → `string`                 | fail   | fail   |
| table: `labels` `github: comma-joined` → `verbatim`             | fail   | fail   |
| table: `body_format` `equals: none` → `equals: create-pr`       | fail   | fail   |
| golden json: `"total_updates": 2` → `3`                         | fail   | fail   |
| golden github: `labels=ci,deps,automated` → `…automate`         | fail   | fail   |

The order row is the one worth naming: swapping two rows leaves the field *set* identical, so it is
invisible to every comparison that existed before this change and fails only because both ports now
compare sequences.

### Also changed

- `packages/python/CONTEXT.md`, `packages/typescript/CONTEXT.md` — the glossary said the shared file
  declares the wire *shape*; it now says which four things it declares.
- `docs/src/content/docs/{python,typescript}/cli.md` — the same, plus a sentence naming
  `fixtures/cli-exit-codes.yml` as what holds the six flag-validation checks. Both pages already
  claimed the two encodings carry their fields "in the same order"; until this change nothing held
  either port to that.
