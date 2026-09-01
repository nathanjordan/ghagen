# The Snapshot is a month of upstream drift behind

**Status:** closed — Snapshot refreshed from a fresh `sync`, new fields triaged, and item 4's
premise measured false; the real asymmetry (the inverse one, compile-time) closed with a
reverse conformance assertion both ports read

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

## Resolution

Items 1-3 done from a fresh sync. Item 4's premise was measured and is false as filed; the
asymmetry that does exist runs the other way, and it is closed.

**1. The refresh came from a fresh `sync`, not the drift branch.** `origin/schema-drift/20260831`
is a month old itself: diffing its Snapshot against a fresh
`PYTHONPATH=scripts uv run python -m ghagen_schema sync` shows 869 insertions / 798 deletions
between them, and the difference is substantive (new `dependencies` blocks, restructured
`oneOf`/`anyOf` nodes), not cosmetic. The fresh sync was used, followed by
`python -m ghagen_schema generate`. Against `origin/main` the landed refresh is
`schema/workflow_schema.json` +1151/-472, `schema/action_schema.json` +108/-38, and the two
generated TypeScript type modules +559/-206. `ghagen_schema check` reports "stale" from a working tree, by design --
it regenerates, `git diff --exit-code`s against **HEAD**, and restores; it can only go green once
the regenerated types are committed, which they are in this commit.

**2. What the refresh forced, beyond regeneration.** Four upstream restructurings moved nodes that
the shared tables pin positionally, and each one failed a test until it was repointed -- which is
the point of pinning them positionally:

- `on.workflow_dispatch` is now wrapped in its own two-way `oneOf` (the bare `null` form, or the
  object with `inputs`), so `conformance-scopes.yml`'s `workflowDispatch` path gained a trailing
  `oneOf, 1`.
- `definitions.workflowDispatchInput` restructured from an `allOf` of `if`/`then` clauses into a
  five-branch `oneOf` keyed on the sibling `type`. The rule is unchanged; the paths are not. The
  `constraints` row in `conformance-gaps.yml` and the `type_paths` in `conformance-inputs.yml` were
  both repointed, and the row's `requires_prose` now records that the restructuring happened.
- `workflowCallInput.default` is spelled as a three-branch `anyOf` where it was a single `type`
  list; three explicit paths replace the one.
- `definitions.container` **split** into `definitions.jobContainer` (the six keys ghagen models)
  and `definitions.serviceContainer` (those six plus `command` and `entrypoint`). This is the one
  that surfaced as a compile error rather than a test failure -- `TS2724: has no exported member
named 'Container'. Did you mean 'JobContainer'?` in
  `packages/typescript/src/models/container.ts` -- which is item 4's real subject, below.

**3. Every new upstream field triaged.** Modelled in both ports: three `permissions` scopes
(`code-quality`, `copilot-requests`, `vulnerability-alerts`) and `concurrency.queue`. Upstream
narrows `copilot-requests` to `write` and `vulnerability-alerts` to `read | none`; both are typed
like their siblings (`PermissionLevel | Raw[str]`) for the same reason `models` already is, with the
narrowing recorded in a comment rather than in the type. `queue` is `"single" | "max" | Raw<string>`.
GitHub also forbids `queue: max` together with `cancel-in-progress: true`, but the Snapshot states
that only in prose -- it is not a schema rule, so it is deliberately **not** a `constraints` row
either (those record rules the Snapshot enforces and the ports do not). Seven fields were recorded
as gaps rather than modelled, because they are two whole features and a refresh should not smuggle
in a feature: `background`, `cancel`, `parallel`, `wait`, `wait-all` on `step` (a recursive step
array, a present-null keyword, and a new six-branch step-kind `oneOf`), and `command` /
`entrypoint` on `serviceContainer`. Both are filed as
`docs/issues/37-the-refresh-brought-two-unmodeled-upstream-features.md`, and each of the seven gap
rows names it.

**4. The premise of item 4 is false, in both halves.** Item 4 says the Snapshot "has exactly one
generated consumer, and it is TypeScript-only," so a refresh advances one port's view and leaves
the other's to a human reading a diff. Measured, that is not what happens.

- _Python is enforced against upstream drift too, and equally._ The Python sweep reads the Snapshot
  JSON directly -- not the generated TypeScript types -- so upstream drift reaches it through the
  same file. Corrupting `"shell": "shell"` to `"shellx"` in
  `packages/python/src/ghagen/models/step.py` on the pre-refresh tree produced
  `FAILED test_scope_properties_covered[workflow_schema.json:step]` and
  `FAILED test_key_sequence_matches_shared_table[step]` -- 2 failed, 99 passed. Neither port is the
  one holding the Snapshot.
- _The "shared table binding fields upstream declares against fields each port models" already
  exists._ It is `schema/conformance-gaps.yml` plus `schema/conformance-scopes.yml`, read
  identically by both sweeps, and it was already doing exactly what item 4 proposes building.

**5. The asymmetry that does exist is the inverse one, and it is compile-time.** The coverage sweep
asserts **upstream ⊆ model**: every property the Snapshot declares is emitted by some model, or
allow-listed. Nothing asserted **model ⊆ upstream**. In TypeScript, something partly did, in the
compiler: `} satisfies Record<keyof StepInput, keyof SchemaStep>` binds every emitted YAML key to a
property name the generated type declares, so a typo is TS2322 and an upstream rename is the TS2724
above. In Python a `ModelSpec.yaml_keys` value is a free string with no upstream binding at all, and
ADR-0003 deleted the generated Python models, so generating Python types is off the table. So the
gap was: `"shell": "shel"` -- or a key GitHub retired two years ago -- passed every check in the
conformance family while ghagen emitted a workflow GitHub refuses.

**6. What was built instead: the reverse assertion, in both ports.**
`test_scope_emits_only_declared_keys` (Python) and `"scope emits only declared keys"` (TypeScript)
assert, per scope, that `set(spec.yaml_keys.values()) - upstream_props(scope) - allowed` is empty --
the exact mirror of the coverage assertion. Both ports read it, rather than one being exempted,
because the exemption is not available: there are seven `satisfies Record<keyof ...>` clauses in the
TypeScript models and they cover **eight of the sweep's twenty-nine scopes**. Explaining why
twenty-one scopes are unbound would cost more than binding them. Exceptions live under a new
reserved `undeclared:` key in `schema/conformance-gaps.yml` -- the same file, following the
precedent the `constraints` key already set for "a second kind of gap in the same file," rather than
a ninth table nothing else reads. `undeclared` is empty today (**zero** emitted keys in either port
are undeclared upstream) and is held load-bearing the same three ways the property gaps are: a
listed name must still be emitted, must still be absent upstream, and the section's snapshot/scope
key set must equal the sweep's (`test_undeclared_set_matches_sweep` / `"undeclared set matches the
sweep"`) -- which is what makes an all-empty table a test rather than decoration. Both loaders now
filter a shared `RESERVED_KEYS` set, so neither reserved section leaks into the property sweep.

**7. The load-bearing experiment.** Two runs, both reverted.

- _Naive_: `"shell": "shell"` → `"shellx"` in `step.py`. Three conformance failures, the new one
  among them -- but `test_scope_properties_covered` and `test_key_sequence_matches_shared_table`
  also fire, so this does not isolate the new assertion.
- _Decisive_: add a field whose emitted key upstream does not declare, and make the rest of the
  family agree with it -- `"retries": "retries"` added to `STEP_SPEC.yaml_keys` with a matching
  `Step.retries` field and a matching `retries` row in `schema/key-order.yml`. Result across the
  **entire** Python suite: `1 failed, 1041 passed`, the single failure being
  `test_scope_emits_only_declared_keys[workflow_schema.json:step]`. Nothing else in the repository
  catches it. The TypeScript peer was run on a scope with **no** `satisfies` clause --
  `retries: "retries"` added to `STRATEGY_SPEC.fieldMap` -- and `"workflow_schema.json:strategy
scope emits only declared keys"` was likewise the only test to fire. Both reverted; the suites are
  green as committed.

**8. Re-measurement of the "definitions with `properties`" question.** On the old Snapshot, of the
unswept `workflow_schema.json` definitions, **zero** carried properties -- so the coverage sweep had
no blind spot to speak of. After the refresh the answer is **still zero**, but only because the
container split was triaged rather than absorbed: `jobContainer` and `serviceContainer` both carry
properties, and both would have been unswept-with-properties had the `container` scope simply been
repointed. Instead `container` now names `definitions.jobContainer` and a **new** `serviceContainer`
scope names `definitions.serviceContainer`, bound to `Service` / `SERVICE_SPEC` in both ports, so
the two service-only keys are counted as gaps rather than being invisible. `action_schema.json` has
one unswept definition carrying properties, `outputs` (`description`), which is pre-existing,
unchanged by the refresh, and a strict subset of the swept `outputs-composite` -- not a hole.

**9. Counts.** Python `1011 → 1042 passed` (identical under `CI=true`); TypeScript
`1074 → 1105 passed`, 46 files. The +31 in each is 29 parametrized reverse assertions, one key-set
guard, and one scope (`serviceContainer`) added to the existing coverage sweep.
