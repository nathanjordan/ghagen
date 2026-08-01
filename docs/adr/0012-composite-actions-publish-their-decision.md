# A composite action publishes the decision it makes

**Status:** accepted (2026-07-31)

The shipped `check-deps` composite action exposes six action-level `outputs:` — `action`,
`total_updates`, `refresh_lockfile`, `branch`, `title`, `changed` — each an `ActionOutput` whose
`value` forwards the corresponding `steps.plan.outputs.*`.

This reverses an explicit design note in `docs/specs/0005-typed-engine-report-seam.md`, which read:

> - The action exposes no action-level `outputs:`; it only uses per-step `$GITHUB_OUTPUT` +
>   `steps.detect.outputs.*`, so no `ActionOutput` is needed.

The spec is amended in place (proposal 18) rather than left standing with a contradicting
implementation.

## Why the original note was right at the time

When 0005 was written the action made no decision. It ran `deps upgrade`, parsed the report with an
inline `python3 -c` one-liner, and branched in bash. Every intermediate value was a shell variable
in one step read by an `if:` in the next. Per-step `$GITHUB_OUTPUT` was the whole mechanism, and
adding an `ActionOutput` would have published a value nothing outside the action had a use for —
surface with no caller, which is exactly what round 2 spent proposals 20 and 11 deleting.

## What changed

Proposal 18 pulled the decision across the CLI seam. `deps update` now computes an **UpdatePlan** —
what action to take (`pr` / `issue` / `none`), how many updates, whether the lockfile needs
refreshing, what branch and title to use, and whether anything was written — and the action's
`plan` step publishes it. The bash no longer interprets the report; it forwards a decision that was
made in typed code and tested there.

Once the action _makes_ a decision, hiding it is a defect:

**A caller is entitled to know what was decided.** A workflow writing `uses: ./check-deps` gets an
opaque box otherwise — it cannot gate a later job on "a PR was opened", cannot report the update
count, cannot distinguish "nothing to do" from "did it". Per-step `$GITHUB_OUTPUT` is invisible
outside the action by construction; `steps.plan.outputs.*` is not addressable by the caller.

**It is what makes the action assertable.** `docs/issues/05-check-deps-action-untested.md` asked for
a CI exercise of this action. A composite action with no outputs can only be asserted by observing
its side effects — a real branch, a real `gh pr create`, a network round-trip. With the decision
published, a CI job runs the action against a fixture and asserts on the outputs, no network
involved. That is what closed issue 05.

The general form: **per-step `$GITHUB_OUTPUT` is an implementation detail; action-level `outputs:`
are the interface.** A composite action that only sequences steps needs none. One that decides
something must publish that decision, or the decision is unobservable and untestable from outside.

## Consequences

**`ActionOutput` is the mechanism for this, and it is not dead surface.** It was carried in the
typed workflow model with no user before proposal 18; it has six now.

**Do not re-suggest deleting these outputs as unused.** They are the action's interface, not
leftovers, and the CI exercise reads them. This differs from the caller-less surface round 2 deleted
(`extrasPlacement`, the per-repo tag caches) precisely because a published decision has a caller by
definition — the workflow that invoked the action.

**A future composite action that branches internally should publish its branch condition the same
way.** The three near-identical "dated branch + dedupe + commit + push + `gh pr create`" shells that
proposal 18 factored are the population this applies to next.
