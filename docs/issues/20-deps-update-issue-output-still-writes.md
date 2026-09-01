# `deps update --output issue` still rewrites source files

**Status:** closed — option 1 chosen: `--output issue` now implies no writes

`ghagen deps update --output issue` without `--dry-run` applies version bumps to the user's source
files and re-resolves the lockfile, exactly as `--output pr` does. The only difference `--output`
makes is which artifact the plan tells the caller to raise. The issue it describes updates that have
**already been written into the working tree**.

## LIVE, and documented rather than fixed

The behaviour predates round 2 — `upgrade()` applies bumps inside the sweep, and `deps update` calls
it. What round 2 changed is that it is now stated out loud, in both ports' CLI reference under
`## ghagen deps update` → `### Writes`:

> Without `--dry-run` this command modifies the working tree. Version bumps are written into your
> source files, and the lockfile is re-resolved when `refresh_lockfile` is true. That holds for
> `--output issue` too: the issue describes updates that have _already_ been applied locally.

Nothing is mis-stated today. The question deferred here is whether the behaviour is right.

## Why it is worth a decision

**`pr` and `issue` are not the same kind of request.** `--output pr` is "do the work and open a PR
for it" — writing is the point, and the branch/commit/push in the shipped `check-deps` action
consumes those writes. `--output issue` is "tell a human there is work" — the natural reading is
that nothing changed. A caller that picks `issue` precisely because it does not want automated
commits still gets a dirty tree, and whether that tree is then committed depends entirely on the
calling workflow's discipline.

**The shipped action does not commit on the `issue` path**, so the writes are currently _stranded_
rather than _shipped_: `check-deps` raises an issue and leaves the runner's checkout modified, which
is harmless on a throwaway runner and confusing anywhere else. On a developer's machine it is a
working tree they did not ask to have edited.

**The plan already carries the truth.** `apply_version_bumps` and `changed` report what happened, so
a caller can detect it. Detection is not the same as it being the right default.

## Options

1. **Make `--output issue` imply no source writes.** Cleanest reading of the flag. Cost: the plan's
   `apply_version_bumps` becomes a function of `--output`, and any caller relying on the current
   apply-then-describe flow changes behaviour. Pre-1.0, so the break itself is cheap.
2. **Split the axes.** Keep `--output` about the artifact and add an explicit apply/no-apply flag
   (or make `--dry-run` mean "no writes" while a new flag means "no artifact"). Honest, but adds a
   flag to a command that already has ten.
3. **Leave it and rely on the docs.** What the repo has now. Defensible only while the sole
   production caller is the shipped action on a throwaway runner.

## What a fix must not lose

The engine applies bumps iff `version_bumps` is non-empty, and `plan.apply_version_bumps ==
bool(report.version_bumps)` holds today. Whatever is chosen, the plan field and the actual write
must stay in agreement — the field is what the action's outputs publish and what the CI exercise
asserts on. A fix that makes them diverge is worse than the current behaviour.

## Files

- `packages/python/src/ghagen/cli/deps.py`, `packages/typescript/src/cli/deps.ts` — the `apply`
  decision, currently `apply = not dry_run`
- `packages/python/src/ghagen/pin/engine.py`, `packages/typescript/src/pin/engine.ts` — `upgrade()`
  applies bumps inside the sweep
- `docs/src/content/docs/python/cli.md`, `docs/src/content/docs/typescript/cli.md` — the `Writes`
  section that documents it
- `.github/actions/check-deps/action.yml` — the one production caller

## Why it was deferred

Found while implementing proposal 18, whose allowlist covered the CLI and the action but not
`pin/engine.*`. 18 preserved the existing behaviour and documented it rather than changing a
write-side default as an unannounced side effect of an action refactor. Changing which files a
command writes is a user-visible interface decision and deserves its own round.

## Resolution

Option 1: `--output issue` implies no writes, full stop, including without `--dry-run`. Pre-1.0, so
this is a clean break rather than a compat flag — no caller can have depended on the new behaviour
of a flag that was, until now, silently ignoring `output` for the write decision.

**The suppression is at the decision, not the outcome.** Both ports' `deps update` gate the engine's
`apply` parameter on `output == "pr"` (previously `apply = not dry_run`, blind to `output`):

```python
report = upgrade_engine(
    ghagen_app, client, user_files, mode=mode,
    apply=output == "pr" and not dry_run,
)
```

The engine never rewrites source under `--output issue`, so there is nothing to undo afterward.

**The plan agrees with the engine, not just the CLI.** `plan_update`/`planUpdate` computed
`apply_version_bumps` and `refresh_lockfile` from the report alone; a caller reading the plan's own
output had no way to see the write decision without also knowing what flags the CLI was invoked
with. Both fields are now `output == "pr" and (...)`:

```python
apply_version_bumps = output == "pr" and bool(report.version_bumps)

refresh_lockfile = (
    output == "pr"
    and app.lockfile_path is not None
    and (bool(report.version_bumps) or (report.checked_lockfile and bool(report.lockfile_stale)))
)
```

This keeps the invariant the issue asked for ("the field and the actual write must stay in
agreement") but strengthens it: agreement now holds by construction for every combination of
`output` and `--dry-run`, not only for `pr` before this fix (issue mode was the one place the
invariant was silently false — `apply_version_bumps` said `true` for a run that, once this fix
landed, no longer applies anything).

`changed` needed no code change: it was already `bool(report.changed_files)` after the (now
correctly gated) apply step, so it falls out of the fix as `false` under `--output issue`
automatically.

**Docs restated, not amended.** Both ports' `## ghagen deps update` → `### Writes` sections were
rewritten (not appended to) to say plainly that `--output` now decides _whether_ the command writes,
not only which artifact it raises — `--output pr` is "do the work and open a PR for it";
`--output issue` is "tell a human there is work" and never writes, with or without `--dry-run`. The
field table's `apply_version_bumps`, `refresh_lockfile`, and `changed` rows were updated to say when
each is forced `false`.

**Bound with a test in both ports**, in each case invoking the real CLI end to end (not just
`plan_update`/`planUpdate` in isolation) against a project with pending version bumps and a stale
lockfile, and asserting the config file, the lockfile, and a synthesized workflow file are all
byte-identical before and after `--output issue` runs **without** `--dry-run`:

- Python: `packages/python/tests/test_cli/test_deps.py::TestDepsUpdateLeavesASynthesizableTree::test_output_issue_writes_nothing`
- TypeScript: `packages/typescript/src/cli/deps.test.ts` — `"--output issue asks the engine not to
apply, without --dry-run"` and `"--output issue synthesizes nothing"`

Decision-table coverage for the plan function itself was added alongside, in both ports'
`test_plan.py` / `plan.test.ts`, mirroring the existing lockfile/action tables.

**The shipped `check-deps/action.yml` composite action is unchanged in shape.** Its
`apply_version_bumps` was never an exposed action-level output before this fix (only `action`,
`total_updates`, `refresh_lockfile`, `branch`, `title`, `changed` are), and no step in this repo's
own workflows reads it — so its meaning changing is invisible at the action's outer contract, even
though the field's semantics inside the plan did change (see below). The one line changed in the
generated `check-deps-smoke.yml`'s "Issue output on the same fixture" case is an added assertion,
`[ "${{ steps.issue.outputs.changed }}" = "false" ]`, plus a comment explaining why that step keeps
`dry-run: 'true'` rather than exercising the no-`--dry-run` path over the network: `dry-run` also
gates the composite action's "Raise PR or issue" step independently of this issue's concern, and
dropping it there would file a real issue against this repository on every scheduled smoke run. The
no-`--dry-run` half of the fix is exercised offline instead, by the CLI tests listed above. Generated
via `uv run ghagen synth` from the edited `.github/ghagen_workflows.py`, never hand-edited; confirmed
with `uv run ghagen check-synced`.

**`apply_version_bumps` did change meaning.** Before: `bool(report.version_bumps)`, independent of
`output`. After: `output == "pr" and bool(report.version_bumps)` — `False` for every `--output
issue` run, including ones with pending bumps. This is exactly the "cost" option 1 named up front.
No consumer in this repo reads the field today: it is not one of the six keys in the composite
action's `outputs:` block, and nothing in `.github/` or `check-deps/` parses
`steps.*.outputs.apply_version_bumps`. It is also worth noting the task that reopened this issue
described `apply_version_bumps` as bound by a shared table at `schema/update-plan-fields.yml`; no
such file exists anywhere in this repository (`schema/` holds `key-order.yml`,
`conformance-values.yml`, `conformance-scopes.yml`, `workflow_schema.json`, `manifest.json`,
`conformance-gaps.yml`, `action_schema.json`, `comment-geometry.yml`, `tag-grammar.yml`) — the ten
plan fields are kept in sync between ports by the parallel decision tables in `test_plan.py` /
`plan.test.ts` and the CLI reference docs, not by a schema file of that name.

## Files changed

- `packages/python/src/ghagen/pin/plan.py`, `packages/typescript/src/pin/plan.ts` — gate
  `apply_version_bumps` / `applyVersionBumps` and `refresh_lockfile` / `refreshLockfile` on
  `output == "pr"`
- `packages/python/src/ghagen/cli/deps.py`, `packages/typescript/src/cli/deps.ts` — gate the
  engine's `apply` on `output == "pr" and not dry_run`
- `packages/python/tests/test_pin/test_plan.py`, `packages/typescript/src/pin/plan.test.ts` —
  decision-table coverage for issue output
- `packages/python/tests/test_cli/test_deps.py`, `packages/typescript/src/cli/deps.test.ts` — the
  end-to-end no-writes tests
- `docs/src/content/docs/python/cli.md`, `docs/src/content/docs/typescript/cli.md` — rewritten
  `### Writes` section and field table
- `.github/ghagen_workflows.py` (source) / `.github/workflows/check-deps-smoke.yml` (generated) —
  added `changed == "false"` assertion to the issue-output smoke case
