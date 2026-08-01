# 22 — Collapse the identical TypeScript factory bodies into `defineFactory(SPEC)`

**Status:** proposed | **Ports:** typescript | **Effort:** M | **Depends on:** order chain
[09](./09-construction-time-validation-parity.md) → [11](./11-shared-spec-surface-table.md) → 22 —
09 adds the `ModelSpec.patterns` field this sweep must carry through, 11 adds three factories this
sweep must collapse and exports `DefaultsRunModel`; **conflicts** with
[20](./20-delete-callerless-pin-spec-surface.md) (`models/job.ts` and `packages/typescript/CONTEXT.md`,
disjoint regions — see _Scope boundaries_) and [10](./10-delete-modelspec-order.md) (10 runs solo and
last, after this proposal)

Effort is **M**, not S–M: the mechanical sweep is small, but the acceptance gate is a nine-entry-point
TypeDoc byte-diff that must be rebuilt against 22's own merge base (not today's `main`, which 09 and
11 both move), and that gate — not the edit — is the work.

## Files involved

All modified; no new files.

| Path                                               | Lines | Role in this proposal                                                                                                                                                                                                                                                                                      |
| -------------------------------------------------- | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/typescript/src/models/_base.ts`          | 532   | Add `defineFactory` beside `buildModel` (`:371-377`); it is the new single home for the meta-split (`extractMeta`, `:144`) and the `Record<string, unknown>` casts.                                                                                                                                        |
| `packages/typescript/src/models/action.ts`         | 406   | 7 factories collapse (`actionInputDef` `:274`, `actionOutputDef` `:295`, `branding` `:311`, `compositeRuns` `:333`, `dockerRuns` `:356`, `nodeRuns` `:379`, `action` `:403`). All seven carry the `as unknown as` laundering.                                                                              |
| `packages/typescript/src/models/container.ts`      | 96    | 2 factories collapse (`container` `:69`, `service` `:93`).                                                                                                                                                                                                                                                 |
| `packages/typescript/src/models/image-snapshot.ts` | 52    | 1 factory collapses (`imageSnapshot` `:49`). **Order edge 09 → 22** — 09 declares this model's version grammar in `IMAGE_SNAPSHOT_SPEC.patterns`, leaving the body empty of anything 22 must preserve.                                                                                                     |
| `packages/typescript/src/models/job.ts`            | 428   | 7 factories collapse (`matrix` `:82`, `strategy` `:125`, `concurrency` `:167`, `defaultsRun` `:219`, `defaults` `:236`, `environment` `:274`, `job` `:425`); 3 orphaned doc blocks re-attached; 2 `{@link buildModel}` references (`:70`, `:203`) retargeted. **Conflict edge 20 — 22**, disjoint regions. |
| `packages/typescript/src/models/permissions.ts`    | 96    | 1 factory collapses (`permissions` `:93`).                                                                                                                                                                                                                                                                 |
| `packages/typescript/src/models/step.ts`           | 94    | 1 factory collapses (`step` `:90`); the `run`-stays-raw comment (`:92`) moves into `STEP_SPEC`'s doc block.                                                                                                                                                                                                |
| `packages/typescript/src/models/trigger.ts`        | 496   | 7 factories collapse (`pushTrigger` `:65`, `prTrigger` `:124`, `scheduleTrigger` `:157`, `workflowDispatchInputDef` `:231`, `workflowDispatch` `:250`, `workflowCall` `:336`, `on` `:493`); 3 orphaned doc blocks re-attached. Post-11 this file also carries the three new `workflowCall*` sub-factories. |
| `packages/typescript/src/models/workflow.ts`       | 99    | 1 factory collapses (`workflow` `:96`).                                                                                                                                                                                                                                                                    |
| `packages/typescript/src/models/_base.test.ts`     | 208   | New `defineFactory()` describe block, a `sourceLocation` pin, and the `@function`-tag guard. Purely additive — see _Scope boundaries_ for the three-way contact with 09 and 10.                                                                                                                            |
| `packages/typescript/CONTEXT.md`                   | 119   | The **ModelSpec** glossary entry (`:40-46`) and the factory-functions surface-notes bullet (`:98`). **Conflict edge 20 — 22** and **11 — 22** on this file.                                                                                                                                                |

Not touched **by this proposal**: the nine `packages/typescript/src/_docs-api-*.ts` entry points
(6–14 lines each), `packages/typescript/src/index.ts` (203), `docs/astro.config.mjs` (191), and every
`*.test.ts` other than `_base.test.ts`. The docs evidence below shows why none of them needs to
change: `export const f = defineFactory<M, I>(SPEC)` re-exports and renders exactly as
`export function f(...)` did.

"Not touched by 22" is **not** "unchanged in the round". 09 adds `ModelInputError` to
`_docs-api-output.ts` (`09` §Modified — unconditional) and 11 adds three model aliases plus the missing `DefaultsRunModel`
to `index.ts` (`11` §Modified). The docs baseline 22 must diff against is 22's own merge base, not today's
`main`. `packages/typescript/src/models/spec.test.ts` (127) is 11's file; `models/registry.ts` is
11's new file and 22 adds nothing to it.

Python: no files. See _Proposed interface_ for why the Python port has no equivalent duplication.

## Problem

**There are 27 factory functions with 27 near-identical bodies today, and 30 after 11.** Measured
five ways, all reconciling:

- `rg -c 'buildModel[<(]'` over non-test `packages/typescript/src/` returns **28**. One of those is
  the _definition_ — `export function buildModel<M extends Model = Model>(` at `_base.ts:371`. So
  **27 call sites**, each one a factory. (`_base.ts:376` is the `new Model(...)` line inside that
  definition, not a call site; it is a common miscitation.)
- The `ModelKind` union declares **27** members (`_base.ts:161-187`).
- `ModelOf<K>` declares **27** aliases (`_base.ts:263-289`).
- There are **27** `ModelSpec` literals in the tree, 26 with `order.kind: "explicit"` and one
  (`ON_SPEC`, `trigger.ts:426`) with `alphabetical`.
- Eight model modules contain them: `action` 7, `job` 7, `trigger` 7, `container` 2, and one each in
  `step`, `permissions`, `workflow`, `image-snapshot`.

One kind, one spec, one factory, 27 times. **11 adds `workflowCallInput`, `workflowCallOutput` and
`workflowCallSecret` (`11` §(b) The fields the new scopes demand, mirroring Python's three existing specs at `trigger.py:179,190,199`)
and says verbatim "22 sweeps 30 factories, not 27" (`11` §Scope boundaries vs siblings).** Every count in this document is
therefore stated as _27 today, 30 post-11_ — 29 explicit-order specs plus `ON_SPEC`.

25 of the 27 are exported; `defaultsRun` (`job.ts:219`) and `workflowDispatchInputDef`
(`trigger.ts:231`) are module-private helpers reached only through a `WrapRule`. 11's three additions
are module-private too, by its own stated precedent (`11` §New: they stay out of
`_docs-api-triggers.ts`, "exactly like `workflowDispatchInputDef`"). **So post-11: 30 factories, 25
exported, 5 module-private** — and the exported count does not move.

**Fifteen** of the 27 are byte-for-byte the same four lines modulo three identifiers:

```ts
// packages/typescript/src/models/container.ts:69-72
export function container(input: WithMeta<ContainerInput>): ContainerModel {
  const [data, meta] = extractMeta(input);
  return buildModel<ContainerModel>(CONTAINER_SPEC, data as Record<string, unknown>, meta);
}

// packages/typescript/src/models/permissions.ts:93-96
export function permissions(input: WithMeta<PermissionsInput>): PermissionsModel {
  const [data, meta] = extractMeta(input);
  return buildModel<PermissionsModel>(PERMISSIONS_SPEC, data as Record<string, unknown>, meta);
}
```

The remaining twelve deviate in exactly four ways, none of them behavioural except the last:

| Deviation                                                  | Count | Sites                                                                                              |
| ---------------------------------------------------------- | ----- | -------------------------------------------------------------------------------------------------- |
| `extractMeta(input as unknown as Record<string, unknown>)` | 8     | `action.ts:275,296,312,334,357,380,404`; `trigger.ts:234`                                          |
| `oxfmt`-wrapped `buildModel` arguments                     | 3     | `trigger.ts:159-163`, `:235-239`, `:252-256` (`workflowDispatchInputDef` also wraps its signature) |
| one extra comment line                                     | 1     | `step.ts:92` (`run` stays raw; dedent at emit, ADR-0002)                                           |
| **behaviourally different**                                | 1     | `defaultsRun` (`job.ts:219-221`): no `extractMeta` call, `{}` hard-coded as meta                   |

The 8 laundering sites and the 3 wrapped sites overlap by one (`workflowDispatchInputDef` does both),
which is how 15 + 8 + 3 + 1 + 1 − 1 = 27. **The sweep normalizes nothing silently: `defaultsRun` is
the only body that does anything different, and its change is called out as step 4 of the migration.**

Two facts fall out of the shape.

**1. The `Record<string, unknown>` cast is written 35 times.** Each of the 27 carries one
`data as Record<string, unknown>` (`input as …` in `defaultsRun`), and eight carry a _second_,
stronger cast in the same body:

```ts
// packages/typescript/src/models/action.ts:275 — and 296, 312, 334, 357, 380, 404,
// plus trigger.ts:234
const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
```

`extractMeta` is `<T extends object>(input: T)` (`_base.ts:144`), so the split is **18 / 8 / 1**:
eighteen factories pass `input` straight through, eight launder it through `unknown` first, and
`defaultsRun` calls `extractMeta` at all. Nothing in the tree explains which group a new factory
belongs to; the author copies whichever neighbour they landed next to. `unknown` laundering is the
strongest cast TypeScript has, and seven of the eight are in one file (`action.ts`) whose own header
comment sells compile-time schema conformance.

(`rg 'as Record<string, unknown>'` over non-test model files returns 36 lines: the 35 above plus
`_base.ts:505`, which is `cloneRecord`'s and unrelated.)

**2. Six exported factories publish an empty description — LIVE, and the cause is not the bodies.**
Six of the 27 have no doc comment attached to the declaration, and all six are re-exported through a
`_docs-api-*.ts` entry point, so all six render on the published API site with an empty description
cell. Rebuilding the markdown from pristine `HEAD` (method in _Risks & alternatives_) yields exactly
six `&hyphen;` cells across the nine trees:

```
job/README.md:92        [matrix](functions/matrix.md)                     -> &hyphen;
job/README.md:130       [strategy](functions/strategy.md)                 -> &hyphen;
workflow/README.md:42   [defaults](functions/defaults.md)                 -> &hyphen;
triggers/README.md:90   [scheduleTrigger](functions/scheduleTrigger.md)   -> &hyphen;
triggers/README.md:102  [workflowCall](functions/workflowCall.md)         -> &hyphen;
triggers/README.md:114  [workflowDispatch](functions/workflowDispatch.md) -> &hyphen;
```

(A seventh `&hyphen;` at `app/README.md:21` belongs to the `App` class, not a factory.)

**All six were documented.** Every one of the six doc blocks still exists in the source, **orphaned**
— stranded above a `*_SPEC` constant that then acquired a doc comment of its own, so the factory
below inherits nothing. TypeScript binds only the _last_ preceding block to a declaration:

| Factory            | Authored block, now orphaned | Block that took the declaration                                | Factory left bare |
| ------------------ | ---------------------------- | -------------------------------------------------------------- | ----------------- |
| `matrix`           | `job.ts:51-65`               | `job.ts:66-74` → `MATRIX_SPEC` (`:75`)                         | `job.ts:82`       |
| `strategy`         | `job.ts:100-116`             | `job.ts:117` → `STRATEGY_SPEC` (`:118`)                        | `job.ts:125`      |
| `defaults`         | `job.ts:192-205`             | `job.ts:206-211` → `DEFAULTS_RUN_SPEC` (`:212`)                | `job.ts:236`      |
| `scheduleTrigger`  | `trigger.ts:139-149`         | `trigger.ts:150` → `SCHEDULE_TRIGGER_SPEC` (`:151`)            | `trigger.ts:157`  |
| `workflowDispatch` | `trigger.ts:192-211`         | `trigger.ts:212-217` → `WORKFLOW_DISPATCH_INPUT_SPEC` (`:218`) | `trigger.ts:250`  |
| `workflowCall`     | `trigger.ts:307-328`         | `trigger.ts:329` → `WORKFLOW_CALL_SPEC` (`:330`)               | `trigger.ts:336`  |

**Six blocks to re-attach, zero to write.** `workflowDispatch`'s prose — description, `@param`,
`@returns`, and a six-line `@example` — is sitting at `trigger.ts:192-211`, twenty lines above the
`WORKFLOW_DISPATCH_SPEC` one-liner at `:242` and fifty-eight above the factory it was written for.

The `job.ts:192-205` case is the clearest: a complete block with `@param`, `@returns` and a worked
`@example` for `defaults()`, followed on line 206 by a second `/**` — so those fourteen lines document
nothing and `defaults()` ships bare. No gate catches this. `tsc` does not read comments, `oxlint` does
not, and the docs build emits `&hyphen;` at zero warnings.

**This defect is independent of `defineFactory` and must not be sold as evidence for it.** It is caused
by declaration reordering putting a second `/** … */` between a block and its declaration. It is
landable today, in isolation, with no `defineFactory` anywhere. `defineFactory` does not remove that
failure mode; by shortening every factory to a single line it makes doc-block/declaration adjacency
_denser_, which slightly increases the chance of a repeat. **That is precisely why the `@function`
guard test below is a requirement and not a nicety** — the sweep inherits an already-realised failure
mode and must bring its own detector.

**There is no live runtime bug behind this proposal, and this document does not manufacture one.**
The 27 bodies are correct and behaviourally equivalent. The argument is locality: one behaviour
implemented 27 times (30 post-11), with the type-system escape hatch (`as unknown as`) replicated
eight of those times under no stated rule.

The one latent behavioural divergence among the 27 is `defaultsRun` (`job.ts:219-221`), which skips
`extractMeta` and hard-codes `{}` as meta. `DefaultsRunInput` (`job.ts:177-182`) declares only
`shell` and `workingDirectory`, and `DefaultsInput.run` is typed `DefaultsRunInput`
(`job.ts:187-190`), so excess-property checking rejects an object _literal_ carrying `comment` — but
`applyWrapRule` erases the type at the call (`_base.ts:381`:
`const factory = rule.factory as (input: unknown) => Model;`), so a value that reaches the wrap rule
by any other route has its meta keys dropped instead of promoted. **LATENT** — reachable only via a
widening the current types do not permit. It is fixed incidentally by this proposal (see _Migration
plan_ step 4), not by design; the general "unknown keys vanish" contract belongs to
[09](./09-construction-time-validation-parity.md).

## Current interface

To add a model type to the TypeScript port today, a contributor must know and hand-reproduce:

- **The body.** `extractMeta` → `buildModel<M>(SPEC, data as Record<string, unknown>, meta)`
  (`_base.ts:144`, `_base.ts:371-377`). Nothing declares this is the only legal shape; it is a
  convention observed by copy.
- **Which cast.** Whether to write `extractMeta(input)` or
  `extractMeta(input as unknown as Record<string, unknown>)` — an 18-vs-8 split with no stated rule
  (`defaultsRun` is the ninth case and calls neither).
- **Where the doc comment must sit.** Immediately above the `export function`, with no intervening
  `/** … */`, or it silently documents nothing — realised six times out of 27.
- **Four hand-maintained lists, all keyed off the same 27.** Two of the four have already drifted:

  | List                 | `path:line`                 | Entries | Drift                                       |
  | -------------------- | --------------------------- | ------- | ------------------------------------------- |
  | `ModelKind` union    | `_base.ts:161-187`          | **27**  | — (the reference)                           |
  | `ModelOf<K>` aliases | `_base.ts:263-289`          | **27**  | —                                           |
  | Factories            | 8 modules, enumerated above | **27**  | —                                           |
  | Alias barrel         | `index.ts:42-67`            | **26**  | `DefaultsRunModel` (`_base.ts:279`) missing |
  | `ALL_SPECS`          | `spec.test.ts:36-63`        | **26**  | `IMAGE_SNAPSHOT_SPEC` missing               |
  | `ALL_KINDS`          | `spec.test.ts:66-93`        | **26**  | `"imageSnapshot"` missing                   |

  The `spec.test.ts:95-99` guard — "every `ModelKind` has exactly one spec" — compares `ALL_KINDS`
  against `ALL_SPECS`. Both are hand-written, both dropped `imageSnapshot`, so the guard passes while
  omitting a model. **LATENT** (nothing user-visible breaks; the guard's coverage is a lie). This is
  the hole [11](./11-shared-spec-surface-table.md) closes with a
  `SPECS_BY_KIND satisfies Record<ModelKind, ModelSpec>` registry in a _source_ module, and 11 also
  closes the `DefaultsRunModel` barrel gap (`11` §Migration plan). **Neither is this proposal's to fix.**

Behind that interface sits nine lines of real implementation. The interface is larger than the
implementation, repeated 27 times.

## Proposed interface

One function in `_base.ts`, and 27 one-line bindings (30 post-11).

```ts
/**
 * Build the factory function for one {@link ModelSpec}.
 *
 * The single implementation of "split meta off the input, map fields through
 * the spec, return a Model of the spec's kind" — the body every model factory
 * used to repeat verbatim. Declare a factory by binding its spec and its two
 * type parameters; the `Record<string, unknown>` casts that each factory
 * carried live here once.
 *
 * Mark the resulting `const` with `@function` in its doc comment so TypeDoc
 * renders it as a function, not a variable.
 */
export function defineFactory<M extends Model, I extends object>(
  spec: ModelSpec,
): (input: WithMeta<I>) => M {
  return (input: WithMeta<I>): M => {
    const [data, meta] = extractMeta(input as unknown as Record<string, unknown>);
    return buildModel<M>(spec, data as Record<string, unknown>, meta);
  };
}
```

Each factory becomes its declaration and nothing else:

```ts
// container.ts
/**
 * Create a container model for use as a job-level container.
 * …
 * @function
 */
export const container = defineFactory<ContainerModel, ContainerInput>(CONTAINER_SPEC);

/**
 * Create a service container model.
 * …
 * @function
 */
export const service = defineFactory<ServiceModel, ContainerInput>(SERVICE_SPEC);
```

**`defineFactory` reads no `ModelSpec` field at all.** It forwards the whole `spec` object to
`buildModel`, which forwards it to `buildYamlData` (`_base.ts:315-365`). That is the property that
makes it compose with the rest of the round in both directions:

- **09 adds `patterns?: Readonly<Record<string, RegExp>>` to `ModelSpec`** (beside `wrap` `spec.ts:65`,
  `dynamicKeys` `:72`, `presentNullWhenEmpty` `:90`) and consumes it **inside `buildYamlData`'s
  `fieldMap` loop, after the `Commented` peel at `_base.ts:329-333` and before `applyWrapRule`**
  (`09` §(c) One home for the version grammar: a fourth declarative ModelSpec field, bound by a shared value table). `defineFactory` needs zero code for it, and `imageSnapshot` collapses
  unconditionally:

  ```ts
  // image-snapshot.ts, post-09 — the grammar is declared, the body is gone
  export const IMAGE_SNAPSHOT_SPEC: ModelSpec = {
    kind: "imageSnapshot",
    fieldMap: IMAGE_SNAPSHOT_FIELD_MAP,
    order: { kind: "explicit", keys: ["image-name", "version"] },
    patterns: { version: /^\d+(\.\d+|\*)?$/ },
  };

  /**
   * Create an image-snapshot model …
   * @function
   */
  export const imageSnapshot = defineFactory<ImageSnapshotModel, ImageSnapshotInput>(
    IMAGE_SNAPSHOT_SPEC,
  );
  ```

  The one requirement this places on `defineFactory`: it must be **transparent to the
  `ModelInputError` 09 throws** — no `try`/`catch`, no wrapping, no re-throw. The returned closure is
  a plain arrow function, so the error propagates with the user's call site intact.

- **20 deletes `extrasPlacement` from `spec.ts:73-84` entirely** (`20` §Modified — TypeScript source; the round has settled the
  deletion on 20, and 10's own text still claims it at `10` §What sits behind the seam — see _Scope boundaries_).
  `defineFactory` must **not** be written to handle `extrasPlacement`, and under the
  forward-the-whole-spec rule there is nothing to remove when it goes.

**Invariants the interface now states rather than implies.** A factory is exactly (model type, input
type, spec). The `WithMeta<I>` wrapping, the meta split, the field mapping and both casts are not a
factory's business and are no longer visible at a factory. `WithMeta`, `buildModel` and `extractMeta`
stop being imported by any of the eight model modules — verified on the full conversion, all three
disappear from all eight import lists. `WithMeta` survives in `defineFactory`'s return type and still
renders in every public signature, because the _type_ is unchanged.

**Error modes:** `defineFactory` adds none of its own — it composes `extractMeta` and `buildModel`
unchanged and has no failure path. Post-09 it is a transparent conduit for `ModelInputError`, as
above.

**Ordering:** every same-module `WrapRule` already references a factory declared _above_ it
(`job.ts:122` → `job.ts:82`; `job.ts:233` → `job.ts:219`; `job.ts:393-400` → `job.ts:125,167,236,274`;
`trigger.ts:247` → `trigger.ts:231`; `trigger.ts:466-471` → `trigger.ts:65,124,157,250,336`), so
losing function-declaration hoisting introduces no temporal-dead-zone hazard. Verified empirically,
not by inspection: the full 27-factory conversion is `tsc --noEmit` clean and runs the suite green
(below).

**`@function` is load-bearing and must be part of the convention**, not an afterthought. It is a
TypeDoc 0.28 modifier tag that makes TypeDoc reflect a function-typed `const` as a Function rather
than a Variable. Without it the rendered API degrades in three measured ways; with it the rendered
markdown is byte-identical. Both halves are measured in _Risks & alternatives_.

**Python needs no equivalent, and this proposal must not invent one.** Python has no factory
functions. A model is a Pydantic class binding its spec as a class variable — e.g.
`packages/python/src/ghagen/models/step.py:44,50`:

```python
class Step(GhagenModel):
    ...
    SPEC: ClassVar[ModelSpec] = STEP_SPEC
```

`rg 'SPEC: ClassVar\[ModelSpec\]'` over `packages/python/src/ghagen/models/` returns **31** hits:
**30 concrete class bindings plus the abstract annotation on the base class** at
`packages/python/src/ghagen/models/_base.py:98`. (30 rather than 27 because Python already has the
three `WorkflowCallInput`/`Output`/`Secret` classes 11 is porting to TypeScript
— `trigger.py:179,190,199` — plus `JobOutput` (`job.py:172`) which 20 deletes, and lacks a separate
`Service` class.) Construction is `BaseModel.__init__`, inherited once from `GhagenModel`
(`packages/python/src/ghagen/models/_base.py:67`) — Python already _has_ `defineFactory`; it is
called class inheritance, and `SPEC: ClassVar[...]` is already the one-line spec binding this
proposal is asking TypeScript for. There is nothing to change and no parity debt created: the two
ports end up with the same shape (one shared construction implementation, one per-model spec binding)
expressed in each language's idiom, which is exactly what `CONTEXT-MAP.md` calls a port difference
rather than a behaviour difference.

## What sits behind the seam

`defineFactory` is the seam between "which model is this" and "how is any model built". Behind it: the
meta/data split, the spec-driven field mapping, and the two `Record<string, unknown>` casts — 35 cast
sites collapsing to 2, in one file, next to the `buildYamlData` they are casting _for_.

Honest measurement of depth: the implementation is nine lines behind a three-token interface, so
`defineFactory` is **not deep**. Its case rests on locality and on the seam it creates, not on
leverage. But the locality is large — 27 adapters today and 30 post-11, in 8 modules, of a behaviour
with exactly one correct form — and "one adapter = hypothetical seam, two = real" is not close to the
deciding question here.

**Deletion test, stated honestly.** Delete `defineFactory` and 27 callers (30 post-11) must each
re-grow a four-line body; **35 casts reappear across 8 modules, including the eight `as unknown as`
launderings and the 18-vs-8 choice with no rule behind it.** Complexity reappears distributed. It
earns its keep — it is not a pass-through, because what it hides (the casts, the meta split, the
`WithMeta` wrapping) is exactly what its callers currently must restate.

What the deletion test does **not** show, contrary to an earlier draft of this document: it does not
give construction-time concerns "27 possible homes". 09's unknown-key rejection and its `patterns`
check both go into `buildYamlData` (`_base.ts:315-365`), which is already the single home for all 27
factories **with or without `defineFactory`**, because every one of them routes through `buildModel`
→ `buildYamlData` today. The deletion cost is the casts and the bodies, and that is a narrower claim
than "the next construction-time concern has nowhere to go."

**What it does not absorb, stated plainly:**

- **Exhaustiveness is [11](./11-shared-spec-surface-table.md)'s, not this proposal's.**
  `defineFactory` is a `ModelSpec → factory` function; it cannot know whether every `ModelKind` has a
  spec, because it never sees the set. 11's `packages/typescript/src/models/registry.ts` carrying
  `SPECS_BY_KIND satisfies Record<ModelKind, ModelSpec>` is the totality guarantee. The two compose
  without overlapping: 11 owns _"every kind has a spec"_, 22 owns _"every spec has one factory body"_.
  This proposal deliberately does **not** add a `Record<ModelKind, …>` of its own.

  **Carry 11's own caveat about the mechanism's limit** (`11` §(c) An exhaustive-by-construction spec registry in TypeScript, verified by construction): a
  _missing_ key is `TS1360` and names the key; an _excess_ key is `TS2353`; but a key ↔ `spec.kind`
  **mismatch produces no error at all**. `satisfies Record<ModelKind, ModelSpec>` is not a total
  guarantee that entry _k_ holds spec _k_ — which is why 11 keeps a three-line runtime assertion
  (`for (const [k, s] of Object.entries(SPECS_BY_KIND)) expect(s.kind).toBe(k)`). Nothing in this
  proposal narrows that gap either: `defineFactory<M, I>(SPEC)` does not check that `M` and `SPEC.kind`
  agree, for the same reason.

  11's justification for putting the registry in `src/` rather than a test file is _two_ reasons, and
  only one is durable: the load-bearing one is that both `spec.test.ts` and `conformance.test.ts`
  consume it. The second — that `tsconfig.json:24` excludes `src/**/*.test.ts` from `tsc`, so a
  `satisfies` clause in a test file is enforced by nothing in CI — **is voided if 09's item (b) lands**
  (`09` §(b) TypeScript typechecks its own tests, and 11 says so itself at `11` §(c) An exhaustive-by-construction spec registry in TypeScript). This document leans only on the durable reason.

  **Open — Phase 3 decision:** whether 09's item (b) ("TypeScript typechecks its own tests") becomes a
  17th proposal, **25**. If it lands, `tsconfig.json:24` no longer excludes test files and any
  argument in this round resting on that exclusion must be restated. This proposal does not decide it.

- **The `index.ts:42-67` alias barrel does not become derivable.** `StepModel` and friends are _type_
  aliases (`ModelOf<"step">`, `_base.ts:261-289`). `defineFactory` produces runtime values; a
  value-level helper cannot emit an `export type`, `satisfies` produces no type alias, and declaration
  merging cannot synthesize 27 named aliases. The change that _would_ make the barrel derivable is
  deleting the aliases in favour of callers writing `ModelOf<"step">` directly — a public API break
  with real ergonomic cost, and out of scope here. **The actual `DefaultsRunModel` gap is already
  closed by 11 before this proposal starts** (`11` §Migration plan, migration step 1 exports it from
  `index.ts`), so 22 neither closes it nor inherits it.

## Migration plan

Pre-1.0; a clean break, all in one commit. Sequenced after 09 and 11 merge.

1. Add `defineFactory` to `_base.ts` beside `buildModel` (`_base.ts:371-377`), with the doc comment
   above, including the `@function` instruction for implementers.
2. Convert the 21 factories that already carry an attached doc comment (24 post-11): replace the body
   with `export const NAME = defineFactory<Model, Input>(SPEC);` and add one `@function` line to the
   existing block. Drop `buildModel` / `extractMeta` / `WithMeta` from each module's imports — after
   conversion all three are unused in all eight model modules. Retarget the two `{@link buildModel}`
   references in `job.ts` doc comments (`:70`, `:203`) to `{@link defineFactory}`, and move the
   `run`-stays-raw note (`step.ts:92`) into `STEP_SPEC`'s doc block so it survives the body deletion.
3. **Re-attach all six orphaned doc blocks** — `job.ts:51-65`, `job.ts:100-116`, `job.ts:192-205`,
   `trigger.ts:139-149`, `trigger.ts:192-211`, `trigger.ts:307-328` — to their factories, each gaining
   `@function`. **No prose is written; all six blocks already exist.** This is the LIVE docs fix and
   the only intended change to rendered output: six `&hyphen;` cells become six descriptions.
4. Convert `defaultsRun` (`job.ts:219-221`) with the same helper. Its signature widens from
   `(input: DefaultsRunInput)` to `(input: WithMeta<DefaultsRunInput>)`, which is the sweep's **only**
   behavioural change: `run: { … }` shorthand now routes through `extractMeta`, so meta keys reaching
   it are promoted to meta instead of dropped. It is module-private and its only caller is
   `DEFAULTS_SPEC`'s wrap rule (`job.ts:233`), so no public signature moves. No current call shape can
   produce a meta key here (see _Problem_), so no emitted bytes change.
5. Run `scripts/typecheck.sh ts`, `scripts/test.sh ts`, `oxlint src`, `oxfmt --check .`. (Note:
   `scripts/lint.sh` defaults to the `all` scope at `lint.sh:6` and guards the `docs/` npm toolchain
   on `ts`/`all` at `lint.sh:20-26`, so a bare `scripts/lint.sh` needs `npm ci --prefix docs` first.)
6. **Run the TypeDoc byte oracle** (below) against 22's merge base and confirm the only diff is the
   six restored descriptions.

**Diffstat, measured on the full 27-factory conversion** in a `$TMPDIR` copy of
`packages/typescript/` (all steps except the step-3 prose, for which `/** @function */` stubs were
substituted to isolate the mechanism), with unused imports removed and `oxfmt` applied:

| Tag style                                                           | Insertions | Deletions | Net     |
| ------------------------------------------------------------------- | ---------- | --------- | ------- |
| `@function` on its own line after the existing prose (**proposed**) | 106        | 140       | **−34** |
| `@function` preceded by a blank `*` separator line                  | 127        | 140       | −13     |

Both include `defineFactory` and its 12-line doc comment. Both produce byte-identical TypeDoc output
(below). The net saving is real but style-dependent, and the honest headline is **−34 lines and 33
fewer casts**, not a dramatic reduction. An independent reviewer run measured 108/140, net −32 — the
few-line spread is the `defineFactory` doc comment's length, not a disagreement.

## Test impact

Baseline is **vitest 515 / 37 files** (re-confirmed on `HEAD`). The full 27-factory conversion is
`tsc --noEmit` clean and produces a test outcome **identical to an unconverted control run in the
same sandbox** — same 37 files collected, same pass/fail split, zero test edits. Every existing model
test is written against factory _behaviour_, so none of them notices. Python is untouched (pytest 562
unaffected).

- **New (`_base.test.ts`):** a `describe("defineFactory()")` block — the returned function splits meta
  from data, produces a `Model` whose `kind` comes from the passed spec, applies the spec's `wrap`
  rules, and honours `dynamicKeys`. This is what makes the deletion test cash out: the behaviour is
  asserted once instead of being implicitly re-asserted by 27 per-model suites.
- **New (`_base.test.ts`):** a `sourceLocation` assertion. `captureSourceLocation`
  (`packages/typescript/src/_source_location.ts:26-38`) skips **all** internal frames via
  `isInternalFrame` (`:32`) rather than a fixed count, so the extra `defineFactory` closure frame is
  transparent — but that is the kind of invariant that should be pinned rather than reasoned about,
  since a regression would silently degrade every `PinTransform` diagnostic.
- **New (`_base.test.ts`):** the `@function` presence guard. Read the eight model modules and assert
  every **exported** `defineFactory(` binding has `@function` in its preceding doc comment — 25
  bindings today and 25 post-11 (the 5 module-private ones render nowhere and need no tag). Source-text
  assertions are ugly, and this one is justified by evidence rather than taste: the identical failure
  mode — a doc comment that does not attach — is already live in six factories and passed `tsc`,
  `oxlint`, and a zero-warning docs build.

  Resolve the sibling modules with `fileURLToPath(new URL(".", import.meta.url))`, the pattern already
  in the suite at `packages/typescript/src/pin/sources.test.ts:33` — **not** `import.meta.dirname`,
  which requires Node ≥20.11 while `packages/typescript/package.json:73-75` declares `>=20.6`. (That
  floor is _already_ violated by `src/paths.ts:21`; raising `engines` is the right fix but it is a
  separate change and this test must not depend on it.)

- **Not changed:** `spec.test.ts` — 11's file. The `imageSnapshot` gap in `ALL_SPECS`/`ALL_KINDS` is
  11's to close.

**The presence guard does not guard tag _efficacy_.** A TypeDoc minor bump could stop honouring
`@function` and move all 25 pages to `variables/` with the guard still green. Closing that needs the
byte oracle described next, and this proposal treats it as a **mandatory pre-merge acceptance step**,
not a standing gate: `docs.yml:4-8` builds the site only on push to `main`, so there is no PR-time
docs job to hang it on. Turning the oracle into a standing CI gate means a new PR-triggered workflow,
which is a CI change this proposal should not smuggle in — it is recorded as a follow-up issue.

Net: the test surface improves because there is now one module to test for construction, and the 27
per-model suites stop being the only thing standing between a copy-paste slip and production.

## Risks & alternatives

**The TypeDoc risk — resolved by measurement, and the measurement is the acceptance gate.** The
round-1 ledger records `_docs-api-*.ts` as live TypeDoc entry points that must keep working
(`docs/proposals/README.md:47`; 07 KEPT them). `defineFactory` turns 27 `function` declarations into
`const` bindings, which TypeDoc reflects as _Variables_. This is the risk that could sink the
proposal, so it was measured before proposing — and the same measurement is step 6 of the migration.

### The byte oracle, concretely

This is the procedure, not a promise:

1. Copy `packages/typescript/{src,tsconfig.json,package.json}` into `$TMPDIR`, symlinking
   `node_modules`. Two copies: one at 22's **merge base** (not today's `main` — 09 moves
   `_docs-api-output.ts` and 11 moves `index.ts`), one with the branch applied.
2. Drive `typedoc@0.28.19` + `typedoc-plugin-markdown@4.11.0` from `docs/node_modules`
   programmatically (`Application.bootstrapWithPlugins`), passing the **verbatim** `sharedTypeDocConfig`
   object from `docs/astro.config.mjs:17-43`, once per entry point, over **all nine**
   `_docs-api-*.ts` files, with `out` under `$TMPDIR`.
3. `diff -r` the two generated markdown trees. **Empty diff is the pass condition.**
   `starlight-typedoc` consumes precisely this markdown, so identical markdown means identical pages,
   sidebar and slugs. (`astro build` is not run; nothing downstream of the markdown changes.)

Run against `HEAD` this produces 47 markdown files across nine trees, **0 errors and 0 warnings**. The
absolute warning count is driver-dependent — a run mediated by `starlight-typedoc`'s own option layer
reports a different, non-zero figure — so **the oracle asserts equality of the two counts, never a
constant.** The count identity is the invariant; the number is not.

### What was measured

_Without_ `@function`, converting all 27 and rebuilding, the render degrades in exactly three ways:

1. **Page slug moves** — `typescript/api/step/functions/step.md` → `…/variables/step.md`, for all 24
   docs-reachable factories. Every existing deep link and cross-reference breaks.
2. **Signature line changes** — verbatim, from
   `> **step**(`input`: `WithMeta`\<`StepInput`\>): `StepModel`` to
`> `const` **step**: (`input`: `WithMeta`\<`StepInput`\>) => `StepModel``, presenting a factory as
   a variable holding a function.
3. **The index heading flips** — `## Functions` becomes `## Variables` on every affected README, and a
   _partial_ conversion splits one table into two, so `on` and `prTrigger` would appear under different
   headings on the same page.

What did **not** degrade, even without the tag: the description, the `@param` table with its
per-parameter prose, the `@returns` section, `@example` blocks, and `{@link}` resolution all survived
intact. The damage is categorisation and URLs, not content.

_With_ `@function` on each converted binding and all 27 converted, `diff -r` across all nine entry
points is **empty** — same file tree, same slugs, same signature lines, same tables, same 0/0
error/warning counts. Reproduced with both tag styles from the diffstat table. `tsc --noEmit` clean,
suite outcome identical to control. The recovery is complete, not partial.

So: **not rejected, not narrowed.** The condition is that `@function` is treated as part of the
convention, guarded by the presence test, and verified by the byte oracle before commit — because the
tag is the whole of the recovery and nothing else in CI would notice its absence.

### Other risks and alternatives

**Alternative: keep thin named wrappers** — `export function step(i: WithMeta<StepInput>) { return stepImpl(i); }`.
Rejected. It preserves 27 function declarations purely to satisfy a docs tool, and 27 bodies is the
thing being removed. `@function` is one line and achieves a strictly better result (identical render)
than a wrapper would.

**Alternative: leave the bodies alone.** Rejected on the evidence in _Problem_: the 18-vs-8 cast split
with no stated rule is what 27 interchangeable bodies cost, and it is already realised, not
hypothetical. Note the six detached doc comments are **not** part of this justification — they are an
independent defect (see _Problem_), fixable without `defineFactory`, and are carried here only because
the sweep rewrites the same lines.

**Risk: `@function` is a TypeDoc-specific tag in library source.** Accepted. It is a documented
modifier tag in TypeDoc's default set, inert to `tsc`, `oxlint` and `oxfmt`, and the repo already
carries TypeDoc-shaped prose in these files (`@packageDocumentation`, `{@link}`, `@example`). The
alternative — shaping the source to a tool's default categorisation — is worse. The honest cost is
recorded in the ledger below.

**Risk: a stack frame is added between user code and `new Model`.** Not realised.
`captureSourceLocation` (`_source_location.ts:26-38`) skips every internal frame rather than a count,
so the closure is invisible to it; the full-conversion suite run confirms it. Pinned by a new test
regardless.

### Architecture ledger, honestly

35 casts → 2, plus one convention stated instead of implied, for net −34 lines. Per site, 4 lines → 2.
Concept count goes from "one shape you copy" to "one shape you copy plus one TypeDoc tag you must not
forget", backed by a guard test and a pre-merge byte oracle. **Modest but real.** This proposal does
not claim more than that, and in particular does not claim the LIVE docs defect as its own payoff.

### Scope boundaries vs siblings

- **09 → 22 (order edge, `models/spec.ts` + `models/_base.ts` + `image-snapshot.ts`).** 09 lands
  first. It adds `ModelSpec.patterns` and consumes it in `buildYamlData` (`_base.ts:329-333` peel,
  then the check), and it also adds the unknown-key rejection there. Both land in the one place all 27
  factories already route through, so **22's collapse of `imageSnapshot()` is unconditional and adds
  no code to `defineFactory`**. 09 explicitly rejected the two alternatives (`09` §(c) One home for the version grammar: a fourth declarative ModelSpec field, bound by a shared value table) — excluding `imageSnapshot`
  from this sweep (costs 22 its thesis and does not scale; there are four more Snapshot patterns at
  `workflow_schema.json:255,334,689,839`) and a `ModelSpec.validate?: (data) => void` callback (an
  opaque callback is exactly what 20 exists to delete, and a callback cannot be compared against the
  Snapshot). This proposal adds no validation, no rejection, and no error mode of its own.
- **11 → 22 (order edge; conflict on `packages/typescript/CONTEXT.md`).** 11 adds
  `models/registry.ts` with `SPECS_BY_KIND satisfies Record<ModelKind, ModelSpec>`, three new
  module-private `workflowCall*` factories, and the missing `DefaultsRunModel` export. 22 depends on
  11 and merges after it: it sweeps **30** factories, and it neither adds a kind-keyed map nor closes
  the barrel gap. On `CONTEXT.md` the regions are disjoint — 11 owns `:85-87` (new _conformance scope_
  term after **Drift**) and `:104-105`; 22 owns `:40-46` and `:98`. Serialized by the order edge
  anyway, but the ownership is now explicit.
- **20 — 22 (conflict edge, two files, both disjoint).** Named by neither proposal's table before now.
  - `packages/typescript/src/models/job.ts` (428): 22's regions are the factory bodies and doc blocks
    — `:51-74`, `:82`, `:100-125`, `:167`, `:177-190`, `:192-236`, `:274`, `:393-400`. 20's region is
    the `JobOutputInput` interface at `:281-290` (doc `:281-284`, declaration `:285-290`).
    **Disjoint** — no line is claimed twice.
  - `packages/typescript/CONTEXT.md` (119): 20's `:43` ("extras placement") is **nested inside** 22's
    `:40-46`, not adjacent to it. 20 declares it lands first in the round (`20` §20 — Delete caller-less pin/spec surface) and the
    09 → 11 → 22 chain puts 22 late, so in practice 20's deletion lands first and 22 rewrites the entry
    against a tree where "extras placement" is already gone. **If the order were reversed and 22 landed
    first, 22's rewrite of `:40-46` would drop "extras placement" on its own and 20's CONTEXT.md row
    would become a no-op** — worth stating so neither side reads a vanished phrase as a merge error.
  - Related: 20 deletes `extrasPlacement` from `spec.ts:73-84` entirely (`20` §Modified — TypeScript source). **Note for the
    orchestrator: 10's text still claims that deletion for itself** — `10` §What sits behind the seam reads "this proposal
    takes `extrasPlacement` because it becomes unimplementable here, and 20 should not also claim it"
    — while the round's `CONTEXT.md` region assignment gives `:43` to 20. One of the two documents
    needs a one-line correction; it is not 22's to make. Either way `defineFactory` is deliberately
    **not** written to handle `extrasPlacement`, or any other spec field, so 22 is indifferent to
    which proposal performs the deletion.
- **10 — 22.** 10 deletes `order` from every `ModelSpec` in both ports, runs solo and last, and depends
  on 22 merging first (`10` §Proposed interface). Nothing in this proposal reads or writes `spec.order`, so 10's
  sweep lands on 30 one-line bindings instead of 30 bodies — strictly less to rebase.
- **`_base.test.ts` is a three-way contact, all additive-or-disjoint.** 09 rewrites `:188-196`
  (`09` §Modified — unconditional), 10 renames a test at `:89` (`10` §Modified — TypeScript source), and 22 appends new describe blocks. No shared lines;
  serialization is by the round order, not by conflict.

## ADR / CONTEXT.md impact

- **No ADR is contradicted, and none is reopened.** ADR-0001 is unaffected: models stay data + spec and
  the Emitter keeps all recursion. ADR-0002 is reinforced — `defineFactory` takes its spec as a
  parameter at declaration and holds no module-level mutable state, so nothing about the
  no-construction-time-globals rule changes. ADR-0003 is untouched: TypeScript conformance stays
  compile-time via `satisfies` on the `fieldMap`s, which this proposal does not move.
- **`packages/typescript/CONTEXT.md`, "ModelSpec" entry (`:40-46`) — 22's region.** It already says
  "declared next to the factory" and "every factory builds through `buildModel`". Tighten the second
  clause to: every factory _is_ `defineFactory(SPEC)` — there is one construction body in the port, and
  a factory declaration carries no code. Rewrite against a tree in which 20 has already removed
  "extras placement" from `:43`; if the order reverses, drop the phrase here instead.
- **`packages/typescript/CONTEXT.md`, "Surface notes (TypeScript)" (`:98`) — 22's region.** The bullet
  "Models are products of **factory functions** (`workflow()`, `job()`, `step()`) over a `data` bag"
  stays true and should gain the fact that the factories are spec bindings, plus the `@function`
  requirement for TypeDoc — that requirement is a real constraint on contributors and belongs in the
  surface notes rather than only in a code comment.
- **No other line of either CONTEXT.md is 22's.** `:85-87` and `:104-105` are 11's; `:48-49` is 10's;
  `:43` is 20's; `ts:105` is 09's.
- **No new glossary term.** `defineFactory` is an implementation of the existing **ModelSpec** →
  factory relationship, not a new domain concept, and `CONTEXT-MAP.md`'s mirrored-glossary rule means a
  TypeScript-only helper should not become shared vocabulary. The Python port's
  `SPEC: ClassVar[ModelSpec]` binding is the same relationship and has no glossary entry either.
- **`packages/python/CONTEXT.md`:** no change. The Python port is untouched by this proposal.
- **Follow-up issues, not absorbed here:** (a) a PR-triggered docs job so the TypeDoc byte oracle can
  become a standing gate rather than a pre-merge ritual — `docs.yml:4-8` is push-to-`main` only;
  (b) raising `packages/typescript/package.json:73-75`'s `engines.node` floor from `>=20.6` to
  `>=20.11`, which `src/paths.ts:21` already violates with `import.meta.dirname`.
