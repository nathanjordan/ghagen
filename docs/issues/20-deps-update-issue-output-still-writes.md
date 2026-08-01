# `deps update --output issue` still rewrites source files

**Status:** open — from round 2. Surfaced while implementing proposal 18

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
