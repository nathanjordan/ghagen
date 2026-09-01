# The two `deps update` oracle gaps are stranded inside a closed issue

**Status:** open — bookkeeping defect found in round 3

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
