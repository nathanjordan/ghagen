# The Snapshot is a month of upstream drift behind

**Status:** open — found in round 3 while auditing the `schema-drift/*` branch pileup

`schema/manifest.json` points the Snapshot at `json.schemastore.org`, and the weekly Schema Drift
Check has been faithfully reporting that upstream has moved. Nobody merged it. As of 2026-08-31 the
newest drift branch carries, against `origin/main`:

| file                                                         | delta                         |
| ------------------------------------------------------------ | ----------------------------- |
| `schema/workflow_schema.json`                                | +1033 / -563                  |
| `schema/action_schema.json`                                  | +61                           |
| `packages/typescript/src/schema/workflow-types.generated.ts` | regenerated, ~751 lines moved |

`origin/schema-drift/20260831` supersedes every other drift branch: it is cut from current `main`
(`behind=0`) and carries the newest upstream bytes. `git merge-tree origin/main
origin/schema-drift/20260831` is **clean**, and the merged tree keeps all nine files in `schema/` —
round 2's `key-order.yml`, `comment-geometry.yml`, `tag-grammar.yml`, `conformance-values.yml`,
`conformance-scopes.yml`, `conformance-gaps.yml` all survive. (A two-dot `git diff` against those
branches _appears_ to delete them; that is a diff artifact of the older branches' base, not a merge
hazard.)

## Why this was not merged as part of round 3

Round 3 is about seam enforcement — interfaces that state invariants their implementations do not
hold. A thousand-line upstream schema refresh is a different risk class and deserves its own
red-green pass, because merging it can only do three things and each wants review:

1. Regenerate TypeScript's `workflow-types.generated.ts` — mechanical, already done on the branch.
2. Open **new** conformance gaps. New upstream fields are, by construction, fields neither port
   models. `schema/conformance-gaps.yml` is where they have to land, and deciding which are gaps
   versus which are worth modelling is a judgement call, not a merge.
3. Expose the **port asymmetry below**, which has no owner today.

## The asymmetry a refresh exposes

The Snapshot has exactly one generated consumer, and it is TypeScript-only:
`packages/typescript/src/schema/workflow-types.generated.ts`. Python has no generated peer — its
models are hand-written. So `ghagen_schema generate` mechanically advances one port's view of the
schema and leaves the other port's to be advanced by a human reading a diff.

That is precisely the shape round 2 and round 3 have been closing everywhere else: a contract with
one enforced side. It is not clear this should be fixed by generating Python types; the cheaper
answer may be a shared table that binds "fields upstream declares" against "fields each port
models", making the gap visible rather than latent. Either way it is a design question, not a merge.

## What a fix must do

1. Merge `origin/schema-drift/20260831` (or a fresh `ghagen_schema sync` + `generate`, whichever is
   newer at the time) onto a branch of its own.
2. Run the full gate set, and read what `PYTHONPATH=scripts uv run python -m ghagen_schema check`
   says about the regenerated types.
3. Triage every newly-appearing upstream field into `schema/conformance-gaps.yml` or into the
   models, with the reasoning recorded — a gap row is a claim, not a shrug.
4. Decide the Python-side question above, and either close it or file it deliberately.

## Files

- `schema/manifest.json` — the upstream sources
- `schema/workflow_schema.json`, `schema/action_schema.json` — the Snapshot
- `packages/typescript/src/schema/workflow-types.generated.ts` — the only generated consumer
- `schema/conformance-gaps.yml` — where new upstream fields land
- `.github/ghagen_workflows.py` — `_schema_drift_workflow`, whose dedupe defect is fixed separately
