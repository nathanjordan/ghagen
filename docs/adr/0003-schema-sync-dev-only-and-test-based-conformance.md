# Schema sync is dev-only; Python conformance is test-based

**Status:** accepted

Fetching the upstream GitHub Actions JSON schema, detecting drift, and generating types are
**maintainer/dev-only** concerns, not shipped runtime features. There is one **canonical schema
snapshot** (single copy) consumed by both test suites, TypeScript codegen, and drift detection.
ghagen **hand-writes** its ergonomic models and treats the schema as a **conformance target**, not
a generation source.

## Why

End users writing workflows never fetch schemas or check drift — that is ghagen-maintainer work.
The Python `schema/` package already imported dev-only `httpx`, so it never functioned as a shipped
feature; it is moved to dev tooling. The auto-generated Python models (`datamodel-code-generator`
output) were imported by no production code — only diffed — so drift is detected from the schema
JSON directly and the generated models are deleted, dropping the `datamodel-code-generator`
dependency.

## Considered options

- **Generate-and-use-directly** (Kubernetes clients, AWS CDK L1, Pulumi, cdktf): regenerate models
  from the schema on every change. Works cleanly when you _control or version_ the schema — CDK's
  team owns the CloudFormation spec, so it needs no drift detection. ghagen does **not** control
  SchemaStore's schema, which is exactly why it needs drift detection instead.
- **Hand-written models + schema as conformance target** (chosen): far better DX than the hideous
  generated identifiers (`HttpsJsonSchemastoreOrgGithubWorkflowJson`).

## Consequences

The two languages enforce **different** things, by nature — do not "fix" this into false parity:

- **TypeScript**: compile-time author-conformance. Generated types are imported into the
  hand-written models; `tsc` fails if they diverge from the schema. No runtime validation.
- **Python**: runtime user-input validation via Pydantic on the hand-written models. Python lacks
  the structural typing to import a generated type and check a hand-written class against it, so its
  _schema faithfulness_ rests on integration tests that validate emitted YAML against the canonical
  snapshot.

Do not re-suggest wiring the generated Python models back in for conformance — it was deliberately
removed. A coarser test-based conformance check (walk schema properties, assert models cover them,
with an explicit allow-list for gaps) is a tracked stretch item and needs no code generation.

## Amendment (2026-07-28): the ghagen_schema orchestrator

- The dev-only pipeline is now driven through one orchestrator, `scripts/ghagen_schema`, with
  three verbs: `sync` (network refresh of the Snapshot), `generate` (offline TS codegen), and
  `check` (offline regenerate-and-diff staleness guard, run in CI's lint-meta job).
- `check` closes the gap where stale committed `*.generated.ts` passed silently unless `tsc`
  happened to collide; TS author-conformance is now actively enforced.
- Drift handling is detect → PR (with an issue fallback), not detect → issue-with-diff.
- The two ports still enforce different things (TS compile-time, Python runtime-test). The shared
  conformance scope table drives coverage parity only; generated Python models stay removed.

## Amendment (2026-07-31): schema conformance vs. the model input contract

The "No runtime validation" above is about **schema conformance** — whether the hand-written model
surface matches the Snapshot. That is unchanged: generated types stay imported into the TypeScript
models, `tsc` stays the conformance check, generated Python models stay removed, and the two ports
still enforce conformance differently.

A model's own **construction-time input contract** is a separate invariant, and it _is_
port-symmetric: unknown input keys are an error in both ports, escape hatches are opt-in in both
ports, and a value grammar declared in a model's `ModelSpec` is enforced in both ports. The shared
`schema/conformance-values.yml` extends the `conformance-scopes.yml` mechanism from property
coverage to value grammars; the Snapshot remains the single home for each grammar and the ports
remain bound to it by test, not by codegen. Read `:34`'s "No runtime validation" as scoped to schema
conformance, not as a prohibition on this contract.

## Amendment (2026-07-31): the scope table covers the sub-tree, and what it still cannot say

The "coarser test-based conformance check" this ADR sanctioned shipped as a ten-scope table, and ten
scopes turned out to mean the sweep saw the top of each Snapshot and nothing nested inside it. The
scope table is now 28 scopes and reaches the `on:` sub-tree and the job sub-shapes
(`schema/conformance-scopes.yml`). Three consequences are worth recording, because each is a
boundary of the mechanism rather than a detail of this change.

**A schema path segment may be an integer.** Ten of the eighteen added scopes name a `oneOf`
alternative positionally — the `on:` event map is `properties.on.oneOf[2]` and the mapping form of
`snapshot` is `definitions.snapshot.oneOf[1]` — and there is no other way to name either without
restructuring the upstream Snapshot, which is not ghagen's to restructure. Positional indices are
brittle by construction. The mitigation is that a retarget lands on a node with no `properties` map
and trips the sweep's "exposes no schema properties" assertion, so a silent loss of coverage is not
one of the failure modes; a confusing error message is.

**Coverage parity is not shape parity.** A scope binds one model per port and asserts that model
emits every property the schema node declares. It does not assert the two ports bind the _same_
model, nor that a key modelled in both emits in the same order. Both gaps were real: the three
`workflow_call` sub-map defs were separate Python models with their own key order and plain objects
in TypeScript, so the identical program produced different YAML orderings, and no scope could have
caught it because both ports "covered" the properties. TypeScript now carries
`workflowCallInput`/`workflowCallOutput`/`workflowCallSecret` specs, and emission order is asserted
per port by unit test. The shared byte oracle for it belongs in `fixtures/expected/`, tracked in
`docs/issues/02-fixture-coverage-gaps.md`.

**Not every declared grammar fits the value table.** `schema/conformance-values.yml` binds a
`ModelSpec.patterns` entry to a `pattern` **string** at a schema path. The `permissions-event.models`
scope narrows that one permission to `read | none` with an `enum`, not a `pattern`, so its grammar
cannot be expressed in that table as built. `Permissions.models` is therefore typed like its fifteen
siblings (`PermissionLevel | Raw[str]`) and the narrower enum is documented, not enforced. Extending
the value table to enums is a real option and is deliberately not taken here — a one-off enum entry
would be a second grammar dialect in a table whose whole value is that both ports read it the same
way.
