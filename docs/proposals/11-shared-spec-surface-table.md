# 11 — One shared spec-surface table both ports must satisfy

**Status:** proposed | **Ports:** both | **Effort:** L | **Depends on:** nothing — **ordered before [10](./10-delete-modelspec-order.md)** (10's per-spec sequence guard iterates the `models/registry.ts` this proposal creates) and **before [22](./22-collapse-ts-factory-bodies.md)** (22 declares `Depends on: 11`); **conflicts** with [09](./09-construction-time-validation-parity.md) (09 first — thirteen shared paths, no order dependency in either direction)

**There is no `09 → 11` order edge.** An earlier draft of this proposal declared `Depends on: 09` on
the grounds that the new trigger fields need a _rejection_ contract to be testable. Both halves of
that contract are already on `main`: `extra="forbid"` is set at
`packages/python/src/ghagen/models/_base.py:93`, and TypeScript already rejects an unknown `on()`
key without 09 — `on({ mergeGrup: {} })` is `TS2561: Object literal may only specify known
properties, but 'mergeGrup' does not exist in type 'WithMeta<OnInput>'. Did you mean to write
'mergeGroup'?`, while `on({ mergeGroup: {} })` compiles (verified with `tsc --strict` against
`models/trigger.ts` at HEAD). 09 gives this proposal nothing it does not already have, and 09's own
header now reads `conflicts with 11 (09 first)`. What survives is a **file conflict**, sized below.

## Files involved

### Modified

| Path                                                               | Lines | Role in this proposal                                                                                                               |
| ------------------------------------------------------------------ | ----- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `schema/conformance-scopes.yml`                                    | 44    | The shared table: 10 scopes → 28; integer path segments                                                                             |
| `schema/conformance-gaps.yml`                                      | 34    | Mirror the new scope keys (all empty after the field work)                                                                          |
| `packages/python/tests/test_schema/test_conformance.py`            | 203   | Bind 18 new scopes; widen `SchemaPath` to `str \| int`                                                                              |
| `packages/typescript/src/models/conformance.test.ts`               | 191   | Same; bind scopes through the new registry                                                                                          |
| `packages/python/src/ghagen/models/trigger.py`                     | 250   | `On` +8 events, `PRTrigger` +`tags`/`tags_ignore`, `ScheduleTrigger` +`timezone`, `WorkflowDispatchInput` +`deprecation_message`    |
| `packages/typescript/src/models/trigger.ts`                        | 496   | `OnInput`/`ON_SPEC` +2 events, +`deprecationMessage`, 3 new `workflowCall*` specs + `wrap`                                          |
| `packages/typescript/src/models/_base.ts`                          | 532   | `ModelKind` +3 members, 3 `ModelOf` aliases                                                                                         |
| `packages/python/src/ghagen/models/permissions.py`                 | 67    | +`artifact_metadata`, `attestations`, `models`                                                                                      |
| `packages/typescript/src/models/permissions.ts`                    | 96    | +`artifactMetadata`, `attestations`, `models`                                                                                       |
| `packages/python/src/ghagen/models/job.py`                         | 226   | `Environment` +`deployment`                                                                                                         |
| `packages/typescript/src/models/job.ts`                            | 428   | `EnvironmentInput`/`ENVIRONMENT_SPEC` +`deployment`                                                                                 |
| `packages/typescript/src/models/spec.test.ts`                      | 127   | Delete `ALL_SPECS`/`ALL_KINDS`; consume the registry                                                                                |
| `packages/python/tests/test_models/test_spec.py`                   | 78    | Harden `_all_model_classes()` with a package walk                                                                                   |
| `packages/typescript/src/models/trigger.test.ts`                   | 183   | New-field tests; `workflow_call` sub-model key order                                                                                |
| `packages/typescript/src/models/permissions.test.ts`               | 69    | New permission scopes; retitle the 13-scope test to 16                                                                              |
| `packages/typescript/src/models/job.test.ts`                       | 262   | `environment.deployment`                                                                                                            |
| `packages/python/tests/test_models/test_serialize.py`              | 134   | Emission for the new permissions / environment keys                                                                                 |
| `packages/typescript/src/integration/schema-validation.test.ts`    | 219   | `:118` "validates all 13 permission scopes" → 16, with the three new scopes in the body                                             |
| `packages/python/tests/test_integration/test_full_workflow.py`     | 411   | `:249` docstring and `:286` `assert len(perms) == 13` → 16                                                                          |
| `packages/typescript/src/index.ts`                                 | 203   | Export the 3 new model aliases (and the missing `DefaultsRunModel`)                                                                 |
| `docs/src/content/docs/python/api/triggers.md`                     | 234   | Hand-written parameter tables for the new trigger fields                                                                            |
| `docs/src/content/docs/python/api/permissions.md`                  | 90    | Hand-written scope table                                                                                                            |
| `docs/src/content/docs/python/api/job.md`                          | 172   | `Environment` parameter table                                                                                                       |
| `docs/issues/02-fixture-coverage-gaps.md`                          | 8     | Its canonical extras example (`merge_group`) becomes a typed field here; replace it, and record the new `workflow_call` fixture gap |
| `docs/adr/0003-schema-sync-dev-only-and-test-based-conformance.md` | 53    | Amendment (implementation phase — see last section)                                                                                 |
| `packages/python/CONTEXT.md`                                       | 114   | Glossary: **conformance scope** (implementation phase)                                                                              |
| `packages/typescript/CONTEXT.md`                                   | 119   | Same, plus the spec-registry surface note (implementation phase)                                                                    |

### New

| Path                                                | Role in this proposal                                                                                 |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `packages/typescript/src/models/registry.ts`        | `SPECS_BY_KIND satisfies Record<ModelKind, ModelSpec>` — the exhaustive-by-construction spec registry |
| `packages/python/tests/test_models/test_trigger.py` | Acceptance + rejection tests for the new Python trigger surface                                       |

Not touched, deliberately: `packages/typescript/src/_docs-api-triggers.ts` — the three new
`workflowCall*` sub-factories stay module-private, exactly like `workflowDispatchInputDef`
(`packages/typescript/src/models/trigger.ts:231`), so the hand-synced TypeDoc barrel
(`_docs-api-triggers.ts:1`: "Hand-synced with the index.ts barrel") is unchanged. The TypeScript API
pages under `docs/src/content/docs/typescript/api/` are build output (untracked) and regenerate from
the interfaces.

## Problem

`schema/conformance-scopes.yml` is the seam where "both ports model the same thing" is supposed to
be _enforced_ rather than asserted in prose. It works — and it is enforced over ten hand-picked
nodes. Everything the table does not name drifts freely, and it has.

### 1. The scope table covers ten nodes, all of them top-level shapes

The whole table is 10 scopes (`schema/conformance-scopes.yml:19-44`):

- `workflow_schema.json` → `workflow` (schema root), `job` (`definitions.normalJob` +
  `definitions.reusableWorkflowCallJob`), `step` (`definitions.step`).
- `action_schema.json` → `action`, `compositeRuns`, `dockerRuns`, `nodeRuns`, `actionInput`,
  `actionOutput`, `branding`.

Each port binds its own covering model to that shared key set — Python maps scope → Pydantic class
(`packages/python/tests/test_schema/test_conformance.py:71-88`), TypeScript maps scope → `ModelSpec`
(`packages/typescript/src/models/conformance.test.ts:55-72`) — and each asserts its key set equals
the shared table's (`test_conformance.py:186-203`, `conformance.test.ts:177-190`). Both suites are
green today: `vitest run src/models/spec.test.ts src/models/conformance.test.ts` reports 91 tests,
of which 11 are conformance (10 scope cases + the parity guard); the Python sweep has the same 11.

What the `workflow` scope actually checks is that `WORKFLOW_SPEC`/`Workflow` emit the eight root
keys `concurrency, defaults, env, jobs, name, on, permissions, run-name`. It says nothing about what
is _inside_ any of them. So the entire `on:` sub-tree (35 events), plus `definitions.permissions-event`,
`definitions.container`, `definitions.concurrency`, `definitions.defaults`, `definitions.environment`,
`definitions.snapshot` and `normalJob.properties.strategy` are unswept in **both** ports. That is the
substrate for §2.

Two corrections to the survey:

**`definitions.matrix` cannot be swept by this table shape at all.** The node itself
(`schema/workflow_schema.json`, `definitions.matrix`) has keys `$comment`, `description`, `oneOf`
and _nothing else_ — zero `properties` **and** zero `patternProperties`. Its `include`/`exclude`
live two levels down, at `definitions.matrix.oneOf[0].patternProperties["^(in|ex)clude$"]`, and even
that subschema's keys are `$comment` and `oneOf` — again no `properties` map. `_node_properties`
(`test_conformance.py:132-138`) and `nodeProperties` (`conformance.test.ts:113-125`) both union
`properties` plus `patternProperties[*].properties`, which is empty at every candidate node, so the
scope would resolve to zero properties and trip the sweeps' own `props, f"{snapshot}:{scope_name}
exposes no schema properties"` guard (`test_conformance.py:166`, `conformance.test.ts:152-154`).
Sweeping matrix needs a regex-key primitive that does not exist; it stays out.

**A `service` scope would be tautological and is not proposed.** `normalJob.properties.services`
is `additionalProperties: {$ref: "#/definitions/container"}` — the same node the `container` scope
already binds. Neither port could fail it independently: TypeScript's `SERVICE_SPEC`
(`packages/typescript/src/models/container.ts:45-49`) reuses the _same_ `CONTAINER_FIELD_MAP` and
`CONTAINER_ORDER` objects as `CONTAINER_SPEC` (`container.ts:38-42`), and Python has no
`SERVICE_SPEC` at all — `Service(Container)` (`packages/python/src/ghagen/models/container.py:36`)
inherits `CONTAINER_SPEC`. A scope that cannot fail is table noise.

### 2. What that lets drift — measured, not surveyed

The survey said "10 schema-declared trigger properties are missing from the Python models that
TypeScript has." The real number is **16** schema-declared properties unmodelled by at least one
port: **9** TypeScript-has/Python-lacks, plus **7** the schema declares and _neither_ port models.
All 16 are **live** — a user hits them today.

The 16 are the exact output of running the sweep this proposal proposes against today's models. The
Python side, over the 18 new scopes of §(a):

```text
on                       schema=35  missing=[branch_protection_rule, discussion, discussion_comment,
                                             gollum, merge_group, pull_request_review,
                                             pull_request_review_comment, repository_dispatch]
prTrigger                schema= 7  missing=[tags, tags-ignore]
scheduleTrigger          schema= 2  missing=[timezone]
workflowDispatchInput    schema= 6  missing=[deprecationMessage]
permissions              schema=16  missing=[artifact-metadata, attestations, models]
environment              schema= 3  missing=[deployment]
   (the other twelve new scopes: missing=[] )
```

and the TypeScript side, over the fifteen of those eighteen it can bind at all:

```text
on                       schema=35  missing=[pull_request_review, pull_request_review_comment]
workflowDispatchInput    schema= 6  missing=[deprecationMessage]
permissions              schema=16  missing=[artifact-metadata, attestations, models]
environment              schema= 3  missing=[deployment]
   (workflowCallInput / workflowCallOutput / workflowCallSecret: unbindable — no spec exists)
```

8 + 2 + 1 + 1 + 3 + 1 = **16** on the Python side; the 7 TypeScript also lacks are the
"neither port models" bucket.

**Top-level `on:` events.** The schema declares 35
(`properties.on.oneOf[2].properties`). TypeScript's `ON_SPEC.fieldMap`
(`packages/typescript/src/models/trigger.ts:428-462`) names 33. Python's `ON_SPEC.yaml_keys`
(`packages/python/src/ghagen/models/trigger.py:89-117`) names 27. Missing from Python but present in
TypeScript, exactly six:

```
branch_protection_rule   discussion   discussion_comment   gollum   merge_group   repository_dispatch
```

Missing from **both**: `pull_request_review`, `pull_request_review_comment`.

**Trigger sub-models.** `pull_request` / `pull_request_target` declare `tags` and `tags-ignore`
(`properties.on.oneOf[2].properties.pull_request.oneOf[1].allOf[0].properties`). TypeScript's
`PR_TRIGGER_SPEC` has both (`trigger.ts:97-98`); Python's `PR_TRIGGER_SPEC` has neither
(`trigger.py:30-39`), and neither does `PRTrigger` (`trigger.py:141-145`) — a straight port
divergence, since Python's `PushTrigger` _does_ carry `tags`/`tags_ignore` (`trigger.py:130-131`).
`schedule[].timezone` is declared (`properties.on.oneOf[2].properties.schedule.items.properties`);
`SCHEDULE_TRIGGER_SPEC` has it in TypeScript (`trigger.ts:153`) and not in Python, where
`ScheduleTrigger` is `cron: str` and nothing else (`trigger.py:41`, `trigger.py:148-153`).

**All sixteen are Python-visible and all sixteen raise.** Verified against the tree with
`extra="forbid"` in place — sixteen constructions, sixteen
`ValidationError: Extra inputs are not permitted [type=extra_forbidden]`:

```text
On(branch_protection_rule={})                     On(pull_request_review={})
On(discussion={})                                 On(pull_request_review_comment={})
On(discussion_comment={})                         WorkflowDispatchInput(deprecation_message='x')
On(gollum=None)                                   Permissions(artifact_metadata='read')
On(merge_group={'types': ['checks_requested']})   Permissions(attestations='read')
On(repository_dispatch={})                        Permissions(models='read')
PRTrigger(tags=['v*'])                            Environment(name='prod', deployment=False)
PRTrigger(tags_ignore=['v*'])
ScheduleTrigger(cron='0 0 * * *', timezone='UTC')
```

Two of the seven are TypeScript-visible as compile errors as well:
`on({ pullRequestReview: {} })` is `TS2561`.

**What `extra="forbid"` changed about severity.** It raised it, and it also removed the workaround's
last excuse. Before that hotfix these were silent no-ops: Pydantic's default `extra="ignore"`
accepted `On(merge_group=…)` and dropped the key, so a Python author who copied a TypeScript
workflow got YAML missing a trigger and no diagnostic — a wrong-output bug. Now the same call fails
loudly at construction, which is strictly better, but it converts a silent data loss into a **hard
port asymmetry**: the identical program is valid TypeScript and a runtime error in Python. The
sanctioned channel still exists — `On(extras={"merge_group": {...}})` works and, thanks to
`order=None` (`trigger.py:118`), interleaves alphabetically like a first-class event — but it is the
escape hatch, not the model, and it defeats the very reason `extra="forbid"` went in: catching
misspelled field names. Under `extras=`, `On(extras={"merge_grup": …})` is indistinguishable from a
real event. So the migration in §Migration below is not "add nice-to-have fields"; it is "stop making
the escape hatch the only route to six standard GitHub events."

**Beyond triggers, in both ports at once.** The same measurement over the nodes §1 leaves unswept:

| Scope (proposed)        | Schema node                                   | Missing from Python                           | Missing from TypeScript |
| ----------------------- | --------------------------------------------- | --------------------------------------------- | ----------------------- |
| `permissions`           | `definitions.permissions-event` (16 props)    | `artifact-metadata`, `attestations`, `models` | same three              |
| `workflowDispatchInput` | `definitions.workflowDispatchInput` (6 props) | `deprecationMessage`                          | `deprecationMessage`    |
| `environment`           | `definitions.environment` (3 props)           | `deployment`                                  | `deployment`            |

Three permission scopes GitHub has shipped are unreachable in both ports
(`packages/python/src/ghagen/models/permissions.py:13-27`,
`packages/typescript/src/models/permissions.ts:44-56`). `deprecationMessage` is modelled for
_action_ inputs in both ports but not for `workflow_dispatch` inputs — and the action side is
swept (`actionInput` scope), which is exactly why it did not drift. `environment.deployment`
(`false` lets a job use environment secrets without creating a deployment record) has no field in
either port. Every one of these is **live**, and every one would have been caught the day it
appeared if the corresponding scope existed.

One value-grammar note the coverage table cannot express: `permissions-event.models` is
`{"enum": ["read", "none"], "type": "string"}` — narrower than the `read | write | none`
`PermissionLevel` the other fifteen scopes take. Neither port enforces per-scope value grammars
today, and TypeScript's `fieldMap satisfies Record<keyof PermissionsInput, keyof SchemaPermissions>`
(`permissions.ts:57`) checks **keys only**. This proposal types `models` like its siblings and routes
the grammar to [09](./09-construction-time-validation-parity.md)'s
`schema/conformance-values.yml`, which exists for exactly this.

**An asymmetric spec set produces a live byte divergence — in all three `workflow_call` sub-maps.**
Python models each `workflow_call` input, output and secret as its own `GhagenModel` with its own
spec (`WORKFLOW_CALL_INPUT_SPEC` `trigger.py:59-67`, `WORKFLOW_CALL_OUTPUT_SPEC` `:69-72`,
`WORKFLOW_CALL_SECRET_SPEC` `:74-77`; the classes at `trigger.py:176-202`). TypeScript has none of
the three — `WorkflowCallInputDef` is a bare interface (`packages/typescript/src/models/trigger.ts:262-271`)
and `WORKFLOW_CALL_SPEC` carries no `wrap` for `inputs`/`outputs`/`secrets` (`trigger.ts:330-334`),
unlike `WORKFLOW_DISPATCH_SPEC` which does (`trigger.ts:247`). The values therefore reach the Emitter
as plain objects and emit in the author's insertion order. Measured on the same program:

```text
        inputs   outputs   secrets
Python  description, required, type   description, value   description, required
TS      type, description, required   value, description   required, description
```

Same program, three different YAML orderings, not one. **Live**, and invisible to every existing
gate: no file under `fixtures/expected/` contains `workflow_call` at all, no scope covers the node,
and the only TypeScript test (`trigger.test.ts:77-88`) asserts `toBeDefined()` on each of the three
sub-maps without looking at key order.

### 3. TypeScript's spec self-consistency test is not exhaustive; Python's peer is

`packages/typescript/src/models/spec.test.ts` maintains two lists by hand: `ALL_SPECS` (26 entries,
lines 36-63) and `ALL_KINDS` (26 entries, lines 66-93). The `ModelKind` union has **27** members
(`packages/typescript/src/models/_base.ts:160-187`). The odd one out is `"imageSnapshot"`
(`_base.ts:181`), and `IMAGE_SNAPSHOT_SPEC` exists
(`packages/typescript/src/models/image-snapshot.ts:28-32`) — it is simply absent from both lists.
The survey's claim holds exactly.

The consequence is that the test's headline assertion is **live-false**: the `it` is titled "every
ModelKind has exactly one spec" and does not check that:

```ts
// spec.test.ts:96-100
it("every ModelKind has exactly one spec", () => {
  const kinds = ALL_SPECS.map((s) => s.kind).sort();
  expect(kinds).toEqual([...ALL_KINDS].sort()); // 26 vs 26 — never sees ModelKind
  expect(new Set(kinds).size).toBe(ALL_SPECS.length);
});
```

`ModelKind` the _type_ is never mentioned in the body. The test compares one hand list against
another hand list, and both were edited by the same hand at the same time, so the omission cancels
out. This is not a latent defect with a false title; it is a **false assertion that passes** — the
stated contract is untrue of the tree right now, and 26 of 27 kinds is the only thing the suite
knows.

`IMAGE_SNAPSHOT_SPEC` is likewise exempt from every per-spec assertion in the file: the three
`it.each(ALL_SPECS)` blocks (duplicate order keys `:102`, order completeness `:109`, wrap keys ⊆
fieldMap `:117`) and the whole-list "only the `on` spec uses alphabetical order" check (`:123-126`).
I checked: it satisfies all four today, so no assertion currently _fails_ — but any future edit to
`IMAGE_SNAPSHOT_SPEC` lands in an unguarded spec.

Python's peer is genuinely exhaustive, as claimed. `_all_model_classes()`
(`packages/python/tests/test_models/test_spec.py:21-32`) walks `GhagenModel.__subclasses__()`
recursively and collects **31** concrete classes, `ImageSnapshot` included, and each of the five
tests (`test_spec.py:39,:44,:51,:59,:75`) iterates that list. One caveat worth fixing while we are
here: the reflection only sees classes whose modules have been imported, and `test_spec.py:12-15`
imports just `action`, `job`, `trigger`, `workflow`. `ImageSnapshot` is in scope only because
`job.py:12` happens to import it at runtime. Move that import under `TYPE_CHECKING` and Python's
sweep silently shrinks with no test failure — the same failure mode as TypeScript's hand list, one
refactor away.

Three more hand lists in the same file family have already drifted, which is the pattern argument:
`DefaultsRunModel` is declared at `_base.ts:279` and is **not** re-exported from the `index.ts`
type barrel (`packages/typescript/src/index.ts:31-68`, model aliases at `:42-67` — twenty-six aliases
for twenty-seven kinds); `_docs-api-triggers.ts:1` documents itself as "Hand-synced with the index.ts
barrel"; and `ALL_SPECS`/`ALL_KINDS` are two more. Every list of "all the model kinds" that is not
derived from `ModelKind` eventually loses an entry.

## Current interface

**The shared table** (`schema/conformance-scopes.yml`) is `<snapshot> → <scope> → list of schema
paths`, where a path is a list of keys walked before reading `properties`. Consumers:

- `_resolve(schema, path)` (`test_conformance.py:125-129`) — `node = node[key]` per segment;
  `SchemaPath = tuple[str, ...]` (`test_conformance.py:49`).
- `resolvePath(schema, path)` (`conformance.test.ts:105-111`) — the same walk;
  `type SchemaPath = readonly string[]` (`conformance.test.ts:42`).

Each port binds scope → covering model/spec locally, unions the paths' property names, subtracts
`schema/conformance-gaps.yml` and asserts nothing is left over, plus a staleness check on the
allow-list. The gaps file is empty for all ten scopes today
(`schema/conformance-gaps.yml:22-34`) — the ports really do cover everything the table names.

**The TypeScript spec registry** is `ALL_SPECS`/`ALL_KINDS` in a `.test.ts` file. **The Python
registry** is `GhagenModel.__subclasses__()` reflection.

A maintainer adding a model or a field must know, unwritten: which of ten nodes the sweep happens to
cover; that anything nested inside them is unchecked; that TypeScript's "every kind has a spec" test
does not consult `ModelKind`; and that four separate hand lists have to be updated in lockstep.

## Proposed interface

### (a) The scope table grows to the sub-tree, and path segments may be integers

10 scopes → 28 (21 under `workflow_schema.json`, the 7 action scopes unchanged):

```yaml
workflow_schema.json:
  workflow: [[]] # unchanged
  job: … # unchanged
  step: … # unchanged

  # --- the on: sub-tree ---
  on:
    - [properties, on, oneOf, 2] # the event-map alternative
  pushTrigger:
    - [properties, on, oneOf, 2, properties, push, oneOf, 1, allOf, 0]
  prTrigger:
    - [properties, on, oneOf, 2, properties, pull_request, oneOf, 1, allOf, 0]
    - [properties, on, oneOf, 2, properties, pull_request_target, oneOf, 1, allOf, 0]
  scheduleTrigger:
    - [properties, on, oneOf, 2, properties, schedule, items]
  workflowDispatch:
    - [properties, on, oneOf, 2, properties, workflow_dispatch]
  workflowDispatchInput:
    - [definitions, workflowDispatchInput]
  workflowCall:
    - [properties, on, oneOf, 2, properties, workflow_call]
  workflowCallInput:
    - [properties, on, oneOf, 2, properties, workflow_call, properties, inputs]
  workflowCallOutput:
    - [properties, on, oneOf, 2, properties, workflow_call, properties, outputs]
  workflowCallSecret:
    - [properties, on, oneOf, 2, properties, workflow_call, properties, secrets]

  # --- job sub-shapes ---
  permissions: [[definitions, permissions-event]]
  container: [[definitions, container]]
  strategy: [[definitions, normalJob, properties, strategy]]
  concurrency: [[definitions, concurrency]]
  defaults: [[definitions, defaults]]
  defaultsRun: [[definitions, defaults, properties, run]]
  environment: [[definitions, environment]]
  imageSnapshot: [[definitions, snapshot, oneOf, 1]]
```

The `oneOf` indices are the one new capability, and **10 of the 18 new scopes need them** (the nine
under `on:`, plus `imageSnapshot`'s `snapshot.oneOf[1]`). **Both resolvers already handle integer
segments at runtime** — Python's `node[key]` indexes a list when `key` is an `int`, and ruamel's
safe loader yields `int` for a bare `2`; JavaScript's `node[k]` indexes an array, and the `yaml`
package yields `number`. I verified this end-to-end through both loaders against the real snapshot,
resolving all 18 paths to non-empty property sets in both ports. Only the declared element types are
wrong today, so the change is two lines: `SchemaPath = tuple[str | int, ...]`
(`test_conformance.py:49`) and `type SchemaPath = readonly (string | number)[]`
(`conformance.test.ts:42`). Neither is enforced by a gate — `pyproject.toml:61` scopes pyright to
`src`, and `tsconfig.json:24` excludes `src/**/*.test.ts` — so they are two annotations kept honest
by review, not by CI.

The three `workflowCall*` scopes lean on the existing `patternProperties` union in
`_node_properties` / `nodeProperties`, which already handles the
`^[_a-zA-Z][a-zA-Z0-9_-]*$` input-id keys.

`workflowCallInput`/`Output`/`Secret` are the load-bearing additions for §2's byte divergence: Python
can bind all three today, TypeScript has nothing to bind them to, so the **existing** parity guard
(`test_scope_set_matches_shared_table` / `"scope set matches the shared scope table"`) fails on the
TypeScript side until the specs exist. The table does not merely document the gap; it forces it shut.

### (b) The fields the new scopes demand

Everything the table names must be covered or allow-listed. Measured, the work is:

| Port       | Model / spec                                                                                                                         | Adds                                                                                                                                                               |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Python     | `On` / `ON_SPEC`                                                                                                                     | `branch_protection_rule`, `discussion`, `discussion_comment`, `gollum`, `merge_group`, `repository_dispatch`, `pull_request_review`, `pull_request_review_comment` |
| TypeScript | `OnInput` / `ON_SPEC`                                                                                                                | `pullRequestReview`, `pullRequestReviewComment`                                                                                                                    |
| Python     | `PRTrigger` / `PR_TRIGGER_SPEC`                                                                                                      | `tags`, `tags_ignore`                                                                                                                                              |
| Python     | `ScheduleTrigger` / `SCHEDULE_TRIGGER_SPEC`                                                                                          | `timezone`                                                                                                                                                         |
| both       | `WorkflowDispatchInput`                                                                                                              | `deprecation_message` / `deprecationMessage`                                                                                                                       |
| both       | `Permissions`                                                                                                                        | `artifact_metadata`, `attestations`, `models`                                                                                                                      |
| both       | `Environment`                                                                                                                        | `deployment`                                                                                                                                                       |
| TypeScript | new `workflowCallInput`, `workflowCallOutput`, `workflowCallSecret` kinds + specs + `wrap: {…, mode: "map"}` on `WORKFLOW_CALL_SPEC` | mirrors Python's three existing specs                                                                                                                              |

That is **16 new key names in Python and 15 in TypeScript** (see §Scope boundaries — these are 10's
"restated key names," and they land in `yaml_keys`/`fieldMap` _and_ in `order`, at the same index,
unguarded by today's set-only assertions). Every other proposed scope passes as-is in both ports —
`pushTrigger`, `workflowDispatch`, `workflowCall`, `container`, `strategy`, `concurrency`,
`defaults`, `defaultsRun`, `imageSnapshot`. I ran the sweep against each;
`schema/conformance-gaps.yml` stays empty for all 28 scopes.

The three new TypeScript specs follow `WORKFLOW_DISPATCH_INPUT_SPEC` exactly
(`trigger.ts:218-248`) — a private `workflowCallInputDef` factory plus a `wrap` entry — so the
`workflow_call` sub-maps flow through `buildModel` and get Python's key order.

### (c) An exhaustive-by-construction spec registry in TypeScript

New source module, `packages/typescript/src/models/registry.ts`:

```ts
import type { ModelKind, ModelSpec } from "./_base.js";
// …one import per model module…

/** Every ModelSpec in the library, keyed by its discriminant. */
export const SPECS_BY_KIND = {
  step: STEP_SPEC,
  job: JOB_SPEC,
  // …
  imageSnapshot: IMAGE_SNAPSHOT_SPEC,
  workflowCallInput: WORKFLOW_CALL_INPUT_SPEC,
  // …
} satisfies Record<ModelKind, ModelSpec>;

export const ALL_SPECS: readonly ModelSpec[] = Object.values(SPECS_BY_KIND);
```

**Exactly what the `satisfies` clause buys, verified by construction** (three throwaway modules,
`tsc --strict`, this repo's compiler):

- **Missing key → `TS1360`, and it names the key.** Verbatim:
  `Type '{ a: ModelSpec; b: ModelSpec; }' does not satisfy the expected type 'Record<ModelKind, ModelSpec>'.`
  / `Property 'c' is missing in type '{ a: ModelSpec; b: ModelSpec; }' but required in type 'Record<ModelKind, ModelSpec>'.`
  This is the §3 fix: add a `ModelKind` member without an entry and the build fails, naming it.
- **Excess key → `TS2353`** (`Object literal may only specify known properties, and 'd' does not
exist in type 'Record<ModelKind, ModelSpec>'`). A bonus, not claimed before.
- **Key ↔ `spec.kind` mismatch → no error at all.** Binding `a: C_SPEC` where `C_SPEC.kind === "c"`
  compiles clean. This is the mechanism's limit, and it is why the runtime assertion below is not
  optional.

`ALL_KINDS` is deleted outright — `Object.keys(SPECS_BY_KIND)` _is_ the kind list.

**Why it must be a source module, not `spec.test.ts`.** Two consumers — `spec.test.ts` and
`conformance.test.ts` — so it can live in neither without one test file importing the other's
internals. That is the durable reason; it holds under any `tsconfig` arrangement. There is also a
CI reason _today_: `packages/typescript/tsconfig.json:24` excludes `src/**/*.test.ts` from `include`
and `npm run typecheck` is `tsc --noEmit` over that config (`package.json:43`), so
`scripts/typecheck.sh ts` never type-checks a test file — a `satisfies` clause written in
`spec.test.ts` would be enforced by an editor and by nothing in CI. **That second reason is not
load-bearing and may not survive the round:** 09's item (b) proposes a test-inclusive
`tsconfig.typecheck.json`, after which test files _are_ typechecked. The registry stays in `src/`
either way, on locality.

`registry.ts` is a leaf: it imports the model modules, and nothing under `models/` imports it. Note
that `models/` already contains a pre-existing **type-only** cycle independent of this proposal —
`_base.ts:3` imports `./spec.js` and `spec.ts:1` imports `./_base.js` — which `registry.ts` neither
joins nor worsens, since it only imports.

`spec.test.ts` keeps its behavioural assertions and drops both lists. `conformance.test.ts` binds
through the registry (`workflow: SPECS_BY_KIND.workflow`, …), replacing 12 individual spec imports
with one. It does **not** make scope keys compile-checked: `SPECS` is
`Record<string, Record<string, ModelSpec>>` (`conformance.test.ts:55`) and its keys stay free
strings. Scope-key correctness remains the runtime parity guard's job (`conformance.test.ts:177-190`),
which is where it already lives.

**Invariant the type cannot express:** that each entry's `kind` equals its key — the third bullet
above. A mapped type `{ [K in ModelKind]: ModelSpec & { kind: K } }` _would_ express it, but only if
every spec constant drops its `: ModelSpec` annotation for `satisfies ModelSpec` (30 declarations
after this proposal, and it changes their exported types). Rejected as disproportionate; a three-line
runtime test in `spec.test.ts`
(`for (const [k, s] of Object.entries(SPECS_BY_KIND)) expect(s.kind).toBe(k)`) covers it.

### (d) Python peer: make the reflection independent of import luck

`_all_model_classes()` (`test_spec.py:21-32`) keeps its `__subclasses__()` walk — it is already the
exhaustive half — but the four hand-written module imports at `test_spec.py:12-15` become a package
walk, so no import refactor elsewhere can shrink the sweep:

```python
import pkgutil
import ghagen.models

for mod in pkgutil.iter_modules(ghagen.models.__path__):
    importlib.import_module(f"ghagen.models.{mod.name}")
```

This is the Python-idiom equivalent of `satisfies Record<ModelKind, ModelSpec>`: coverage derived
from the language's own model of "all the model types," not from a list.

## What sits behind the seam

The shared table absorbs the question "do the two ports model the same property set?" for 28 schema
nodes instead of 10, and it absorbs it _as data_ — one YAML file, read identically by both sweeps,
with each port supplying only the binding it cannot serialize (a Pydantic class, a `ModelSpec`).
The parity guard that already exists turns a scope one port cannot bind into a test failure, which
is how (b)'s TypeScript work becomes mandatory rather than optional. The registry moves "the set of
all model kinds" from four hand-maintained lists to one declaration the compiler checks, and the
Python package walk moves it from "whatever got imported" to "whatever is in the package."

Leverage: one added line in `conformance-scopes.yml` buys a permanent cross-port coverage assertion
over a whole schema node, in both suites, forever. Locality: the answer to "which schema properties
are we on the hook for?" is one file; the answer to "what are all the model kinds?" is one
declaration per port.

**Deletion test, table extension.** Delete the 18 new scopes and the 16 measured gaps in §2 become
undetectable again — they were undetectable, for however long they have been there. Complexity does
not vanish; it reappears as drift across two ports. Earned.

**Deletion test, registry.** Delete `registry.ts` and `spec.test.ts` must re-grow two hand lists
(52 lines at today's sizes), `conformance.test.ts` re-grows 12 imports, and `imageSnapshot` falls
back out — the exact defect in §3. Compile-time exhaustiveness over a union has no runtime substitute
in TypeScript, so nothing else can hold the invariant. Earned. (It is not a pass-through:
`Object.values` of a checked map is not the same artifact as a list a human typed.)

**Deletion test, integer path segments.** Delete them and 10 of the 18 new scopes become
unreachable, because the `on:` event map is `oneOf[2]` and the image snapshot's object form is
`oneOf[1]`, with no other way to name either short of restructuring the upstream snapshot. Earned by
necessity, at a cost of two type annotations.

## Migration plan

Pre-1.0; clean breaks. Ordered so each step leaves both suites green.

1. **Registry first, no behaviour change.** Add `packages/typescript/src/models/registry.ts` with
   all 27 current kinds (`imageSnapshot` included — this is the §3 fix, and `tsc` proves the map is
   complete). Rewrite `spec.test.ts` to import `ALL_SPECS`/`SPECS_BY_KIND`; delete `ALL_KINDS`; add
   the key-equals-kind assertion. Rewrite `conformance.test.ts`'s `SPECS` to index the registry.
   Export `DefaultsRunModel` from `index.ts` while in the barrel (it is missing from `:31-68`;
   [22](./22-collapse-ts-factory-bodies.md) depends on it existing and [10](./10-delete-modelspec-order.md)
   does not claim it).
2. **Python reflection hardening.** Swap `test_spec.py`'s four module imports for the
   `pkgutil` walk. Class count must stay 31.
3. **Widen the path type.** `SchemaPath` gains `int` / `number` in both sweeps. No table change yet;
   both suites stay green.
4. **Field work, port by port** (the §b table). Each field lands with its spec entry and its
   `order` entry, so `test_explicit_order_is_complete` / `"explicit order is complete"` stay green.
   Python's `On` grows to 35 fields; TypeScript's `OnInput` to 35.
5. **Three new TypeScript kinds.** `workflowCallInput`, `workflowCallOutput`, `workflowCallSecret`
   in `ModelKind` (`_base.ts:160-187`) + `ModelOf` aliases + specs + private factories + the three
   `wrap` rules on `WORKFLOW_CALL_SPEC`. The registry `satisfies` forces the map entries. **This
   changes emitted bytes** for `workflow_call` inputs, outputs _and_ secrets — the intended fix from
   §2; Python is the reference order.
6. **Extend `conformance-scopes.yml` and `conformance-gaps.yml`** with the 18 scopes. Both parity
   guards now demand the bindings from steps 4-5. Gaps stay empty.
7. **The 13-scope tests become 16-scope tests.** `permissions.test.ts:13,:31`,
   `schema-validation.test.ts:118`, `test_full_workflow.py:249,:286` — see §Test impact.
8. **Docs.** The three hand-written Python API pages; `docs/issues/02`'s stale `merge_group` example;
   `scripts/test.sh all`; `uv run ghagen check-synced` (unchanged — no repo workflow uses the new
   fields); `PYTHONPATH=scripts uv run python -m ghagen_schema check`.

If a field in step 4 turns out to be genuinely unwanted, the escape valve is a
`conformance-gaps.yml` entry with the mandatory inline reason
(`schema/conformance-gaps.yml:19-20`) — but the default is to model it, since the whole point is
that both ports expose the same surface.

## Test impact

Suite deltas against the 562-pytest / 515-vitest baseline:

- **+18 scope tests per port** from the table extension. Python parametrizes over
  `_iter_scopes()` (`test_conformance.py:153-154`, wired at `:157-161`), so the count follows the
  table automatically; TypeScript generates one `it` per scope (`conformance.test.ts:149-174`).
  Each port's conformance file goes 11 → 29 tests (10 → 28 scope cases plus the one parity guard).
- **Vitest, `spec.test.ts`:** `ALL_SPECS` goes 26 → 30 entries. The file has **three**
  `it.each(ALL_SPECS)` blocks (`:102`, `:109`, `:117`) — not four; the "only the `on` spec uses
  alphabetical order" check at `:123-126` is a single whole-list assertion. So the parametrized count
  goes **3 × 26 = 78 → 3 × 30 = 90**, and the **file total 80 → 93** (90, plus the kind-set test, plus
  the alphabetical check, plus the new key-equals-kind test). Measured today: 80 for `spec.test.ts`,
  11 for `conformance.test.ts`, 91 for the two together. `imageSnapshot` enters the self-consistency
  assertions for the first time, and the "every ModelKind has exactly one spec" test stops being
  false — it compares against the compiler-checked registry.
- **New, `packages/python/tests/test_models/test_trigger.py`:** for each of the sixteen
  Python-visible gaps, a paired assertion — the field is accepted and reaches `to_data` with the
  right YAML key (`On(merge_group={"types": ["checks_requested"]})` → `{"merge_group": …}`), and a
  _neighbouring_ misspelling is still rejected (`On(merge_grup=…)` raises), so the `extra="forbid"`
  contract is visibly preserved rather than widened away. This file is the regression guard for §2;
  every acceptance assertion in it fails on `main` today.
- **`packages/typescript/src/models/trigger.test.ts`:** three `workflow_call` key-order tests —
  `toData(workflowCall({ inputs: { x: { type, description, required } } }))` must emit
  `description, required, default, type`, and the same for `outputs` (`description, value`) and
  `secrets` (`description, required`). All three fail on `main` today; the existing test at `:77-88`
  only asserts `toBeDefined()`. Plus `pullRequestReview` / `pullRequestReviewComment` emission.
- **Extended:** `permissions.test.ts` / `test_serialize.py` for the three new permission scopes;
  `job.test.ts` / `test_serialize.py` for `environment.deployment`.
- **Compile-time, not runtime:** the registry's exhaustiveness has no test, and cannot have one —
  `scripts/typecheck.sh ts` is the assertion, and it runs on a file `tsc` actually reads.

**Four existing tests change meaning and must be edited.** Each of these keeps passing after this
proposal and stops saying anything true:

- `permissions.test.ts:13` — `it("handles all 13 scopes")`, and `:31` `expect(Object.keys(data)).toHaveLength(13)`.
- `schema-validation.test.ts:118` — `it("validates all 13 permission scopes")`.
- `test_full_workflow.py:249` — `"""Workflow with all 13 permission scopes set."""`, and `:286`
  `assert len(perms) == 13`.

All four go to 16, with the three new scopes added to their bodies. This is a correction to an
earlier draft of this section, which claimed "no existing test changes meaning."

**The intended byte change has no shared oracle, and this proposal does not add one.** Step 5 changes
emitted bytes for all three `workflow_call` sub-maps, and it is proved by one per-port test each —
for a divergence that two independent per-port suites already failed to catch for as long as it has
existed. The right remedy is a `workflow_call` block in a shared `fixtures/expected/` document, which
would also discharge part of `docs/issues/02`. It is **not** taken here: `fixtures/expected/` is
[13](./13-unify-format-header-contract.md)'s byte-oracle territory this round, and a fixture added by
11 and rewritten by 13 is worse than a fixture added once. The gap is recorded in `docs/issues/02`
instead (that file already tracks the absence of a `defaults:` block and a present-null
`workflow_dispatch`; `workflow_call` joins the list, and its `merge_group` extras example is replaced
because 11 makes `merge_group` a typed field in both ports).

## Risks & alternatives

- **Risk: positional `oneOf` indices are brittle.** `properties.on.oneOf[2]` is the event-map
  alternative _today_; a SchemaStore reorder retargets nine scopes at once (ten counting
  `snapshot.oneOf[1]`). Mitigated, not eliminated: a retarget to a node without properties trips the
  existing "exposes no schema properties" guard (`test_conformance.py:166`,
  `conformance.test.ts:152-154`), and a retarget to a _different_ populated node produces a loud
  missing-properties failure naming the scope. Drift into the snapshot is itself gated by
  `ghagen_schema check` (ADR-0003 amendment), so the index and the snapshot move together under
  review.
- **Alternative: a structural selector instead of indices** — e.g. `[properties, on, oneOfWith,
branch_protection_rule]`, "the alternative whose `properties` contains X." Rejected for now: it
  adds a resolver primitive to _both_ ports (and to the shared file's grammar) to harden against a
  failure the existing guards already surface as a test failure rather than a silent pass. Worth
  revisiting if upstream reorders once.
- **Alternative: allow-list the gaps instead of modelling them.** `conformance-gaps.yml` would take
  16 entries with `# TODO: unmodeled` and the suites would go green with no model work. Rejected:
  the file's own contract is that an entry means "intentionally not exposed"
  (`conformance-gaps.yml:19-20`), and none of these sixteen are intentional — six are standard
  GitHub events one port already models, two more are events neither models, three are permission
  scopes GitHub ships, and the rest are plain omissions. Using the allow-list to record laziness
  destroys its signal.
- **Risk: `On` becomes a 35-field model in both ports.** Accepted. The fields are one line each, the
  schema is the authority for the list, and the alternative — routing six standard events through
  `extras=` — is what §2 shows is already failing users. The `extras=` channel remains for
  genuinely unmodelled keys.
- **Risk: three new `ModelKind` members enlarge the discriminant union.** Accepted; they mirror
  Python's existing `WorkflowCallInput`/`Output`/`Secret` (`trigger.py:176-202`), which the parity
  mandate says should not be one-sided, and they are what closes a live byte divergence.
- **Deletion test on the three new TS kinds:** delete them and all three `workflow_call` sub-maps go
  back to emitting in insertion order while Python sorts them — the divergence reappears in three
  places, not one. Earned.
- **Open — Phase 3 decision: who owns the `matrix_` rename.** TypeScript's `StrategyInput.matrix_`
  (`packages/typescript/src/models/job.ts:93`, mapped `matrix_ → "matrix"` in `STRATEGY_SPEC.fieldMap`
  at `job.ts:120`) versus Python's `Strategy.matrix` (`packages/python/src/ghagen/models/job.py:129`)
  is a live cross-port naming divergence. 09 raises it and explicitly declines to decide it
  (09 fixes only `to-data.test.ts:126`, the test the divergence broke). This proposal does not take
  it either, and the reason is specific rather than convenient: 11's `strategy` scope binds
  `[definitions, normalJob, properties, strategy]`, whose property set is `fail-fast`, `matrix`,
  `max-parallel` — and both ports already **cover** it, because the divergence is in the _input field
  name_, not the emitted YAML key. The conformance table is blind to it by construction, and
  `definitions.matrix` is carved out of the sweep entirely (§1). Neither 09 nor 11 has a mechanism
  that would catch a regression, so the rename needs an owner named at go/no-go, not an implicit one.

### Scope boundaries vs siblings

- **09 (construction-time validation parity) — a file conflict, 09 first; no order edge either way.**
  See the header note: 09 gives 11 nothing that is not already on `main`, and 11 gives 09 nothing it
  needs first. What is real is that the two proposals share **thirteen** paths — twelve
  unconditionally (`models/_base.ts`, `models/trigger.ts`, `models/permissions.ts`,
  `models/conformance.test.ts`, `src/index.ts`, `models/trigger.py`,
  `tests/test_schema/test_conformance.py`, `docs/…/python/api/job.md`,
  `docs/…/python/api/triggers.md`, both `CONTEXT.md`, and
  `docs/adr/0003-schema-sync-dev-only-and-test-based-conformance.md`, where **both append an
  amendment to the same 53-line file**) plus `models/trigger.test.ts` under 09's conditional item (b).
  There is one substantive coupling: 09 applies `Raw<string>` to every TypeScript permission scope,
  which is **13 today and 16 after this proposal** — 09 already states the post-11 count. On
  `packages/typescript/CONTEXT.md` the two collide on the same bullet at `:104-105`; 09 edits first,
  11 appends. The paired accept/reject tests in `test_trigger.py` assert 09's contract on new fields;
  they do not redefine it, so if 09 later changes what rejection looks like, only those assertions
  move.
- **10 (delete `order` from `ModelSpec`) — 11 lands first, and 11 changes 10's evidence.** Two
  things, both of which 10 currently does not account for:
  1. **10's per-spec sequence guard needs `registry.ts`.** 10 proposes a new guard that, "for every
     spec," builds a model with fields passed in reverse declaration order and asserts the emitted
     key _sequence_. In TypeScript the only existing "every spec" handle is `ALL_SPECS` in
     `spec.test.ts:36-63`, which omits `imageSnapshot` — a guard built on it would be non-exhaustive
     by exactly the defect it exists to diagnose, and 10 says so itself while noting the registry is
     11's territory. After step 1 here, `registry.ts`'s `SPECS_BY_KIND` is the exhaustive handle;
     **10 consumes `packages/typescript/src/models/registry.ts` and should list it.**
  2. **10's measured tables move.** 10's Problem section is built on `Python 30 specs / 29 explicit /
135 restated keys, TypeScript 27 / 26 / 134`. This proposal adds no Python spec literal but three
     TypeScript ones, so **TypeScript goes 27 → 30 spec literals and 26 → 29 explicit-order specs**,
     and 10's "all 57 spec literals (30 Python, 27 TS)" becomes 60. Restated key names: **+8 Python
     (135 → 143)** and **+13 TypeScript (134 → 147)** — every new field lands in `yaml_keys`/`fieldMap`
     _and_ in `order` at the same index, except the `On`/`OnInput` additions, whose spec is
     alphabetical and has no `order` list. Counting key names rather than order entries: **+16 Python,
     +15 TypeScript.** 10 then deletes all of them, which is 10's argument getting stronger, but its
     tables are wrong on landing unless restated.

  Beyond that the two are compatible: 10's deletion removes two of the assertions in `spec.test.ts`
  without touching the registry, and the `workflow_call` ordering fix in §2 survives 10 unchanged —
  it needs the sub-model _specs_ to exist, not the `order` field specifically.

- **22 (collapse the 27 identical TS factory bodies into `defineFactory(SPEC)`)** declares
  `Depends on: 11`, and correctly: this proposal adds three private sub-factories that 22 would
  immediately collapse, so **22 sweeps 30 factories, not 27**. 22's own count of 27 is measured
  against today's tree and is stale the moment 11 lands. Step 1 here also exports `DefaultsRunModel`
  from `index.ts`, which 22 needs.
- **24 (narrow `walk()`) — 11 changes what `walk()` visits, and closes a divergence in 24's favour.**
  24 currently analyses 11 as a textual overlap on `_base.ts` only. It is not: adding
  `wrap: { inputs | outputs | secrets: { factory, mode: "map" } }` to `WORKFLOW_CALL_SPEC` promotes
  those three sub-maps to `Model`s, so `scanForModels` (`_base.ts:413-427`) yields one extra node per
  input, output and secret. **Python already visits them** — measured on
  `WorkflowCallTrigger(inputs={…}, outputs={…}, secrets={…})`, Python's `walk()` yields
  `[WorkflowCallTrigger, WorkflowCallInput, WorkflowCallOutput, WorkflowCallSecret]` while
  TypeScript's yields `["workflowCall"]` and nothing else. So after 11 the two ports' traversal
  agrees on this sub-tree, and 24's node-sequence parity assertion gets easier, not harder. 24 should
  run after 11, or state the post-11 node counts.
- **20 (delete caller-less pin/spec surface)** owns two findings I hit and am leaving alone:
  `JobOutputInput` (`packages/typescript/src/models/job.ts:285-290`) is exported from
  `index.ts:106` and referenced by nothing, because `JobInput.outputs` is `Record<string, string>`
  (`job.ts:320`); and Python's `JobOutput` (`job.py:169-175`) models a `{description, value}` shape
  the workflow schema does not declare for `normalJob.outputs` (it declares
  `additionalProperties: {type: string}`). Neither gets a conformance scope here — there is no
  schema node to bind — and both are 20's call.
- **13 (unify `format_header`; headers under the shared byte oracle)** owns `fixtures/expected/`;
  this proposal adds no fixtures, which is why step 5's byte change has no shared oracle (see
  §Test impact).

## ADR / CONTEXT.md impact

- **ADR-0003 amendment, extend the existing paragraph.** The 2026-07-28 amendment already says "The
  two ports still enforce different things (TS compile-time, Python runtime-test). The shared
  conformance scope table drives coverage parity only; generated Python models stay removed."
  (`docs/adr/0003-schema-sync-dev-only-and-test-based-conformance.md:52-53`). No contradiction — this
  proposal reinforces it. Add: the table covers **nested** schema nodes, not only top-level document
  shapes; path segments may be integers to index a `oneOf`; a scope one port cannot bind is a parity
  failure by construction; and `definitions.matrix` is explicitly out of scope because neither that
  node nor its `oneOf[0]` alternative declares a `properties` map at all. **09 amends the same 53-line
  file**; the two amendments are adjacent paragraphs under one "Amendments" heading, 09's first.
- **ADR-0003's "the two languages enforce different things" consequence stands.** TypeScript keeps
  compile-time author-conformance (now including the spec registry) and Python keeps runtime
  Pydantic validation; the shared table still governs _coverage_ only. Nothing here re-suggests
  wiring generated Python models back in.
- **ADR-0001 / ADR-0002:** unaffected. No emission logic moves, no construction-time config.
- **`packages/typescript/CONTEXT.md:85-87` — new glossary term, inserted after **Drift** in the
  *Schema* section:** **conformance scope** — a named schema node (or set of nodes) in
  `schema/conformance-scopes.yml` that both ports must bind to a covering model, and whose property
  set both ports must emit. _Avoid_: "schema check", "coverage table". These three lines are 11's
  only claim in that section.
- **`packages/typescript/CONTEXT.md:104-105` — the generated-types / author-conformance bullet.**
  Append to it that `models/registry.ts` is the single `ModelKind → ModelSpec` map, checked
  exhaustive by `satisfies Record<ModelKind, ModelSpec>`, that both `spec.test.ts` and
  `conformance.test.ts` bind through it rather than through hand lists, and that `tsc` does not read
  `*.test.ts` today, so conformance guards belong in `src/`. **09 also edits this bullet** — 09 first,
  then 11 appends. If 09's item (b) lands, drop the last clause.
- **`packages/python/CONTEXT.md` — the mirror, per the parity mandate.** The same **conformance
  scope** term after **Drift** (`packages/python/CONTEXT.md:83-84`, in the _Schema_ section at `:78`),
  and one appended bullet in _Surface notes (Python)_ (the section's last bullet ends at `:107`) recording that
  model-set reflection (`GhagenModel.__subclasses__()`) is seeded by a `pkgutil` walk of
  `ghagen.models`, so coverage does not depend on which modules a test happens to import. Neither
  region is claimed by another proposal (10 holds `py:46-47`, 09 `py:100`, 15 `py:114`).
