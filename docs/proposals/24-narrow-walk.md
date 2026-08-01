# 24 — Narrow `walk()`

**Status:** proposed | **Ports:** both | **Effort:** M | **Depends on:** nothing hard; scheduled after [20](./20-delete-callerless-pin-spec-surface.md) and [11](./11-shared-spec-surface-table.md) (**semantic** — between them they close the visit-set divergence this proposal's contract asserts). [12](./12-ts-comment-geometry-module.md) shares one file name and zero lines — hand-merge, do not serialise. [10](./10-delete-modelspec-order.md) depends on this landing first

Effort was **S**; it is **M** because part (b) — the extras-traversal parity fix — is attached. Part
(a) alone is S. If the Phase 3 decision below splits (b) out, 24 returns to S.

**Read the honesty label first.** Part (a) of this proposal — deleting the key path, the argument
order and the prune protocol — is **prophylactic**. It fixes no bug, no caller is harmed today, and
the plan's own words put 24 in the round's "most speculative" bucket. It is argued on locality and
interface size, and the deletion test it passes is a clean one (below), not a dramatic one. Part (b)
— extras traversal — is the one live defect, it was found while verifying what `walk()` actually
visits, and it is **cleanly separable from (a)**. If (b) is taken out, 24 contains no live defect at
all and should be prioritised as the prophylactic change it is.

## Files involved

### Modified — Python source

| Path                                         | Lines | Role in this proposal                                                                                                                                               |
| -------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/python/src/ghagen/models/_base.py` | 231   | `_scan_for_models` (`:47-64`) drops its `key` parameter; `children` (`:142-150`) yields bare models and moves `extras` last; `walk` (`:152-168`) yields bare models |
| `packages/python/src/ghagen/pin/sites.py`    | 87    | `:76` `for _path, model in document.walk():` → `for model in document.walk():`. The **only** production call site that changes in either port                       |

### Modified — TypeScript source

| Path                                      | Lines | Role in this proposal                                                                                                                                                                |
| ----------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `packages/typescript/src/models/_base.ts` | 532   | `children` (`:236-241`) yields bare `Model`s and adds `meta.extras`; `walk` (`:243-255`) drops `path` and the prune protocol; `scanForModels` (`:413-427`) drops its `key` parameter |

### Modified — tests

| Path                                                     | Lines | Role in this proposal                                                                                                                                                                                               |
| -------------------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/python/tests/test_models/test_walk.py`         | 72    | Four sites unpack `walk()`'s tuple (`:25,41,42,58`) and one unpacks `children()`'s (`:13`); `test_walk_paths_track_field_keys` (`:62-72`) is deleted with its subject; extras-traversal and extras-last tests added |
| `packages/python/tests/test_emitter/test_dedent_emit.py` | 188   | `:100`, inside `_rename_transform`: `for _path, node in item.walk():` → `for node in item.walk():`                                                                                                                  |
| `packages/python/tests/test_pin/test_sites.py`           | 210   | New case: a `uses:` on a model nested in `extras` yields a site — the regression guard for the parity fix                                                                                                           |
| `packages/typescript/src/pin/sites.test.ts`              | 195   | The mirror case. It returns **zero** sites on `main` today (measured below)                                                                                                                                         |

### Modified — CONTEXT.md

Both files were previously listed under "Not touched, deliberately" while the last section instructed
edits to them. They are real rows and they carry real edges.

| Path                             | Lines | Role in this proposal                                                                                                                                                                                                                                                                                                 |
| -------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/typescript/CONTEXT.md` | 119   | Surface-notes bullet `:98-101` (blank line at `:102`) gains the narrowed traversal contract, **appended** to the existing bullet. Region `:98-102` per the round's map. Co-claimants on this file: **22** (`:40-46` and the same `:98` bullet), **20** (`:43`), **10** (`:48-49` + one appended surface-notes bullet) |
| `packages/python/CONTEXT.md`     | 114   | "Surface notes (Python)" (`:94-107`) has no traversal note; gains the mirror sentence. Co-claimant: **10** (`:46-47` + one appended surface-notes bullet)                                                                                                                                                             |

### New

| Path                                          | Role in this proposal                                                                                                                                                                                                           |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/typescript/src/models/walk.test.ts` | The TypeScript port has no test for `walk()` or `children()` at all. Traversal order, root-first, `Raw` opacity, `Commented` transparency, extras traversal, and the `toYaml` byte regression for an extras-nested step's `run` |

### Not touched, deliberately

- `packages/typescript/src/emitter/yaml-writer.ts` (480) — its `clone.walk(...)` call site (`:46`,
  inside `dedentSteps` at `:44-52`) compiles unchanged. Measured, not assumed: after patching only
  `_base.ts`, this file is **byte-identical to `main`**. See the `12 — 24` entry in
  [Risks & alternatives](#risks--alternatives).
- `packages/typescript/src/pin/sites.ts` (82) — `document.walk((model) => {…})` (`:67`) compiles
  unchanged and is likewise byte-identical after the patch.
- `packages/typescript/src/models/_base.test.ts` (208) — contains no `walk`/`children` test to
  update. Verified: no `.test.ts` file anywhere under `packages/typescript/src` calls `walk()` or
  `children()`.
- `packages/typescript/src/index.ts` (203) — `Model` is exported at `:27`, but the class identity is
  unchanged, so the barrel is not.
- `packages/python/tests/test_models/test_spec.py` (78),
  `packages/python/tests/test_emitter/test_yaml_writer.py` (205) — `test_spec.py` is owned by
  [10](./10-delete-modelspec-order.md) (`10` §Modified — TypeScript source); `test_yaml_writer.py` by 10 (`10` §Modified — TypeScript source) and
  [12](./12-ts-comment-geometry-module.md) (`12` §Modified).
- `packages/python/tests/test_emitter/test_field_collection.py` — the new file created by
  [21](./21-hoist-field-collection-loop.md). **Not applicable, unconditionally:** post-revision, 21's
  file contains per-rule unit tests over `collect_fields` and no traversal (`21` §New — tests, `21` §Migration plan,
  `21` §Test impact), and 21's agreement invariant stays in `test_to_data.py`, which does not call `walk()`.
  There is no merge-order condition left to state.
- `docs/specs/0001-python-single-pass-serialization.md` (421) — see
  [ADR / CONTEXT.md impact](#adr--contextmd-impact); no amendment.

## Problem

`walk()` is the model layer's traversal primitive. Its interface is three things wide — a key path,
an argument order, and (in TypeScript) a prune protocol — and the width is not load-bearing. A
fourth thing the interface does _not_ state — what it visits — is where the one live defect lives.

### 1. No production caller in either port reads the key path. _(latent)_

An exhaustive grep for `.walk(` across the whole repository — both ports' source and tests, `docs/`,
`scripts/`, `.github/` — returns exactly nine hits. Three are production:

```python
# packages/python/src/ghagen/pin/sites.py:76
    for _path, model in document.walk():
```

```ts
// packages/typescript/src/pin/sites.ts:67
  document.walk((model) => {
```

```ts
// packages/typescript/src/emitter/yaml-writer.ts:46
  clone.walk((node) => {
```

Python's caller discards the path with the conventional `_` prefix; both TypeScript callers do not
even declare the second parameter. The remaining six hits are Python tests, five of which unpack the
tuple only to throw the path away (`test_walk.py:25,41,42,58`, `test_dedent_emit.py:100`).

The **only** consumer of the path anywhere is a test asserting the path exists:

```python
# packages/python/tests/test_models/test_walk.py:62-72
def test_walk_paths_track_field_keys():
    wf = Workflow(
        name="CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={"test": Job(runs_on="ubuntu-latest", steps=[Step(run="pytest")])},
    )
    # A dict field contributes its *key* to the path (matching the TS walk):
    # a job under jobs["test"] with steps yields step paths like ["test", "steps"].
    step_paths = [p for p, m in wf.walk() if isinstance(m, Step)]
    assert step_paths
    assert all(p == ["test", "steps"] for p in step_paths)
```

Read what that test pins down. The `jobs` field key never appears — the dict branch substitutes the
dict key for the field key (`_base.py:59-61`, `_base.ts:423-424`) — and every list item inherits its
parent's key (`_base.py:62-64`, `_base.ts:418-421`), so **all** steps in a job share the path
`["test", "steps"]`. The path is neither unique nor addressable: you cannot re-locate a node from
it, and you cannot tell two siblings apart. It is a breadcrumb trail that does not lead back.

### 2. The two ports disagree about it twice over. _(one live-for-readers, one unreachable)_

**(a) Argument order is reversed.** Python yields `(path, model)`; TypeScript passes `(model, path)`:

```python
# packages/python/src/ghagen/models/_base.py:152
    def walk(self) -> Iterator[tuple[list[str], GhagenModel]]:
```

```ts
// packages/typescript/src/models/_base.ts:245
  walk(fn: (model: Model, path: string[]) => void | false): void {
```

**(b) The path vocabulary differs at the source — but the divergence is unreachable by
construction.** The path element for a child is whatever key `children()` found it under, and the
two `children()` implementations iterate different things:

```python
# packages/python/src/ghagen/models/_base.py:149-150
        for field_name in type(self).model_fields:
            yield from _scan_for_models(field_name, getattr(self, field_name, None))
```

```ts
// packages/typescript/src/models/_base.ts:238-239
    for (const [key, value] of Object.entries(this.data)) {
      yield* scanForModels(key, value);
```

Python's keys are Pydantic **field names**; TypeScript's are the keys of `data`, which
`buildYamlData` (`_base.ts:315`) has already mapped through `fieldMap` — i.e. **emitted YAML keys**.

An earlier draft of this document argued this was harmless by dumping one "maximal" document through
both ports and observing seventeen identical rows. **That evidence is withdrawn: the document was not
maximal** — it omitted `prTrigger`, `scheduleTrigger`, `workflowCall` and the `workflow_call`
input/output/secret definitions, all of which are reachable from a `Workflow`. A fixture cannot
establish this claim. The derivation can, and it is stronger:

A path element can differ between the ports only for a field whose **emitted YAML key differs from
Python's field name**, _and_ which can hold a `GhagenModel` / `Model`. Enumerated against `main`:

- **Python: 32 renamed entries** across 32 specs (`spec.yaml_keys` entries where field ≠ key).
  Model-capable: exactly **two** — `Step.with_` and `Job.with_`, both
  `dict[str, Any] | CommentedMap | None`, both emitted as `"with"`.
- **TypeScript: 51 renamed `fieldMap` entries** across 27 specs. Five carry a `wrap` rule and are
  therefore model-capable: `STRATEGY_SPEC.matrix_ → "matrix"` and the four `ON_SPEC` triggers
  (`pullRequest → pull_request`, `pullRequestTarget → pull_request_target`,
  `workflowDispatch → workflow_dispatch`, `workflowCall → workflow_call`). **None of the five is a
  vocabulary divergence**: TypeScript's camelCase→snake_case rename lands on exactly the string
  Python already uses as its field name (`Strategy.matrix`, `On.pull_request`,
  `On.pull_request_target`, `On.workflow_dispatch`, `On.workflow_call`).

That leaves `with_ → "with"` as the sole candidate on either side — and it cannot reach the path,
because its value is a **dict**, and the dict branch substitutes the dict's own key for the field key
in both ports (`_base.py:59-61`, `_base.ts:423-424`). So the vocabularies are unreachable-divergent
**by construction**, not by fixture choice. The divergence becomes observable the first time someone
adds a model-valued field whose YAML key differs from its Python field name — `Job.with_` holding a
`Model` value would do it. **Latent.** Nobody is harmed; but two ports holding the same fact in two
different alphabets is exactly the parity debt that is cheapest to retire while it is theoretical.

### 2c. A third divergence — the visit sets themselves — which two siblings close before this lands.

`walk()`'s post-narrowing contract asserts that the two ports visit the same set of nodes. On `main`
that is **false**, and the falsity is not in `walk()`: it is in the model layer. Four shapes are
Python `GhagenModel`s and TypeScript plain interfaces, so Python's traversal yields a node where
TypeScript's cannot:

| Shape                  | Python                                      | TypeScript                                           |
| ---------------------- | ------------------------------------------- | ---------------------------------------------------- |
| job output             | `JobOutput` (`job.py:169-175`)              | `JobOutputInput` interface (`job.ts:285-290`)        |
| `workflow_call` input  | `WorkflowCallInput` (`trigger.py:176-185`)  | `WorkflowCallInputDef` interface (`trigger.ts:262`)  |
| `workflow_call` output | `WorkflowCallOutput` (`trigger.py:187-194`) | `WorkflowCallOutputDef` interface (`trigger.ts:276`) |
| `workflow_call` secret | `WorkflowCallSecret` (`trigger.py:196-203`) | `WorkflowCallSecretDef` interface (`trigger.ts:286`) |

Counted: Python has **31** concrete model classes, TypeScript **27** `ModelKind` members
(`_base.ts:160-187`). The difference is exactly these four plus TypeScript's `service`, which Python
models as `Service(Container)` (`container.py:36`) — 31 − 4 = 27 = 27 − 1 + 1. There is no other gap.

Both gaps are already claimed, by proposals that land ahead of this one:

- **[20](./20-delete-callerless-pin-spec-surface.md) item F** deletes Python's `JOB_OUTPUT_SPEC` and
  `JobOutput` and narrows `Job.outputs` to `dict[str, OrRaw[str]] | None` (`20` §Modified — Python source, `20` §F. Python JobOutput — ALIVE, wrong, and documented public API,
  `20` §Migration plan). That **removes a node from every Python `walk()`** and closes the first row.
- **[11](./11-shared-spec-surface-table.md)** adds `workflowCallInput` / `workflowCallOutput` /
  `workflowCallSecret` kinds, specs and private factories plus
  `wrap: { inputs | outputs | secrets: { …, mode: "map" } }` on `WORKFLOW_CALL_SPEC` (`11` §(b) The fields the new scopes demand,
  `11` §Migration plan). That promotes the three sub-maps to `Model`s, so `scanForModels` (`_base.ts:413-427`)
  yields **three extra nodes**, and closes the other three rows. 11 states this itself at
  `11` §Scope boundaries vs siblings, with its own measurement: today Python yields
  `[WorkflowCallTrigger, WorkflowCallInput, WorkflowCallOutput, WorkflowCallSecret]` where TypeScript
  yields `["workflowCall"]`.

Both are semantic edges — neither shares a file with this proposal. **Both must land first for this
proposal's contract sentence to be true on the day it lands.** If either slips, the contract must be
weakened to "the same traversal _rule_, over each port's own model set", with the unclosed rows named
explicitly. That weakening is stated here so nobody has to rediscover it at merge time.

### 3. TypeScript's prune protocol has zero callers and zero tests. _(latent)_

```ts
// packages/typescript/src/models/_base.ts:243-255
  /** Depth-first walk. `fn` receives each model + key path.
   * Return false to skip children. */
  walk(fn: (model: Model, path: string[]) => void | false): void {
    function visit(model: Model, path: string[]) {
      if (fn(model, path) === false) {
        return;
      }
      for (const { key, model: child } of model.children()) {
        visit(child, [...path, key]);
      }
    }
    visit(this, []);
  }
```

Both TypeScript callers pass block-bodied arrows that return `undefined`
(`pin/sites.ts:65-82`, `emitter/yaml-writer.ts:44-52`). No test exercises it — the TypeScript port
has **no test that calls `walk()` or `children()` at all**. Python has no equivalent: `walk()` is a
generator, so a caller can `break` (abort the whole traversal) but cannot skip a subtree. So the
protocol is a one-port capability with zero adapters — not even a hypothetical seam.

It is also an **invisible** protocol. `void | false` means an expression-bodied callback that happens
to evaluate to `false` prunes silently: `m => flags.has(m.kind) && rewrite(m)` stops descending the
moment `flags` misses, and nothing in either port's types or tests would catch it.

**Precision about what fixes this.** Narrowing the signature to `(model: Model) => void` does _not_
make the hazardous callback a type error — TypeScript's void-return assignability accepts any return
type against a `void` return position. Measured: with the narrowed signature applied,
`m.walk((n) => flags.has(n.kind))` still typechecks, `tsc --noEmit` exit 0. What removes the hazard is
**deleting the runtime `=== false` check**: after that, the callback's return value is ignored and no
traversal can be silently truncated. The fix is behavioural, not type-level; the type merely stops
advertising a capability that no longer exists.

### 4. The one thing the interface does _not_ state is the one thing that is wrong. _(LIVE — H14)_

`walk()` says nothing about **what it visits**, and the two ports answer differently — at a cost.

Python's `extras` is a model field (`packages/python/src/ghagen/models/_base.py:100`):

```python
    extras: dict[str, Any] = Field(default_factory=dict, exclude=True)
```

so `children()`'s `model_fields` loop (`_base.py:149-150`) descends into it. TypeScript's extras live
in `meta`, not `data` — declared on `ModelMeta` (`_base.ts:117`) and split off the factory input by
`META_KEYS` / `extractMeta` (`_base.ts:141-155`) — and `children()` reads only `this.data`
(`_base.ts:238`). **TypeScript's `walk()` never sees a model nested in `extras`.**

Both ports **emit** such a model. Reproduced on one document — a job whose `extras` carries a
`hidden` step with `uses:` and an over-indented `run:` — run through both ports with `header=None`:

```
# Python:      SITES = ['actions/setup-node@v4', 'actions/checkout@v4']
#              NODES = ['Workflow', 'On', 'PushTrigger', 'Job', 'Step', 'Step']
# TypeScript:  SITES = ["actions/checkout@v4"]
#              NODES = ["workflow", "on", "pushTrigger", "job", "step"]
```

```yaml
# Python — packages/python/src/ghagen/emitter
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
    hidden:
      uses: actions/setup-node@v4
      run: |-
        echo one
        echo two
```

```yaml
# TypeScript — packages/typescript/src/emitter, same input
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
    hidden:
      uses: actions/setup-node@v4
      run: |2-
              echo one
              echo two
```

Two live consequences, both TypeScript-side, both traceable to `children()`:

- **`ghagen pin` silently skips the ref.** `iterUsesSites` (`packages/typescript/src/pin/sites.ts:65-82`)
  is a `walk()` consumer, so it never reaches the extras-nested `uses:`. A user pinning a TypeScript
  project gets an unpinned action with no diagnostic — the exact failure mode the pin engine exists
  to prevent.
- **Dedent does not run.** `dedentSteps` (`packages/typescript/src/emitter/yaml-writer.ts:44-52`) is
  the other `walk()` consumer, hence the `|2-` block above. Python's dedent is not walk-based — it
  folds into the Emitter's single field pass, which merges `extras` — so the two ports emit different
  bytes for the same document.

This is a parity defect the standing mandate says should not exist, and it is live today.

**Open — Phase 3 decision:** H14 can be fixed _alone_, without any of this proposal's narrowing, as a
**6-line standalone hotfix on `main`** ahead of the round. Should it be, as a 7th hotfix? Measured
independently, both halves:

- `packages/typescript/src/models/_base.ts` **+3 lines** inside the existing `children()`, signature
  unchanged — a second loop over `Object.entries(this.meta.extras ?? {})`. File goes 532 → 535.
  `tsc --noEmit` exit 0; vitest result bit-identical to the unpatched baseline in the same
  environment.
- `packages/python/src/ghagen/models/_base.py` **+3 lines** in `children()` — skip `"extras"` in the
  `model_fields` loop and re-scan it last, needed so the ports agree on visit _order_ as well as visit
  set. Signature unchanged. **pytest 562 passed, 0 failed — zero existing tests changed, zero call
  sites touched.**

Against the coupled version's 6 pytest failures to repair, 1 test deleted and 1 production call site
edited. The reason this document gave for coupling them — that the narrowing is what makes the extras
contract _statable_ — is a documentation argument, not a technical one, and it is not strong enough to
decide the question. **This is the user's call at go/no-go; it is not decided here.** If H14 splits
out, this proposal contains no live defect at all and its priority should drop accordingly.

## Current interface

Everything a caller must know to use `walk()` on `main`:

**Python** (`packages/python/src/ghagen/models/_base.py:152-168`)

- `walk() -> Iterator[tuple[list[str], GhagenModel]]`, depth-first pre-order, root yielded first
  with `[]`.
- The path is the parent's path plus "the key the child was found under" — where _key_ means a
  Pydantic field name for a direct field, the **dict key** for a mapping entry (the field name is
  discarded), and the **parent's key** for every item of a list (so siblings collide).
- Traversal reaches `extras` (it is a field), and reaches it **first**, because base-class fields
  precede subclass fields in `model_fields`. Measured above: the extras-nested step is yielded before
  the `steps` list.
- `Raw` is opaque, `Commented` is transparent (`_scan_for_models:53-64`).
- Generator: `break` aborts; there is no way to skip a subtree.

**TypeScript** (`packages/typescript/src/models/_base.ts:243-255`)

- `walk(fn: (model: Model, path: string[]) => void | false): void` — same traversal, **arguments
  reversed**.
- The path uses **emitted YAML keys**, not input field names.
- Traversal does **not** reach `meta.extras`.
- Returning `false` skips the subtree; returning anything else does not.

Neither port states what it visits, and — per §2c — the visit sets are not the same set today.

Plus two supporting functions per port whose only reason to carry a key is the path:

- `children()` — `Iterator[tuple[str, GhagenModel]]` / `Iterable<{ key, model }>`. Exactly one
  caller in each port, and it is `walk` itself (`_base.py:165`, `_base.ts:250`).
- `_scan_for_models(key, value)` / `scanForModels(key, value)` — the `key` parameter is threaded
  through four recursive branches solely to feed `children()`, which feeds `walk()`'s path, which
  nobody reads. A three-function thread for a dead value.

## Proposed interface

One sentence, identical in both ports: **every model in this document, root first, depth-first;
within a model, its schema fields in declaration order, then its extras.**

**That is deliberately _not_ "in emission order", and the distinction is load-bearing.**
`docs/specs/0001-python-single-pass-serialization.md:301-302` records that traversal is a separate
primitive from serialization; blurring the two here would contradict it. Traversal order is the
model's _declaration_ order (Python `type(self).model_fields`; TypeScript `data` insertion order,
which `buildYamlData` derives from `fieldMap` declaration order). Emission order is
`ModelSpec.order`, resolved by `order_entries` (`nodes.py:52-84`, called at `nodes.py:193` and
`data.py:120`) and `orderedEntries` (`yaml-writer.ts:189-215`). They are **not** the same relation,
and `On` proves it on `main`:

|                                                                                                                   | order                                               |
| ----------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| Emitted (`ON_SPEC.order=None` → alphabetical, `nodes.py:70-72`; `order: {kind:"alphabetical"}`, `trigger.ts:463`) | `pull_request`, `push`, `schedule`, `workflow_call` |
| Traversed (`On` field declaration order, `trigger.py:224-230`)                                                    | `push`, `pull_request`, `workflow_call`, `schedule` |

The contract therefore promises **a single sequence that both ports produce**, not a sequence that
matches the emitted file. No caller of `walk()` depends on order beyond "the two ports agree."

**Python** — `packages/python/src/ghagen/models/_base.py`

```python
def _scan_for_models(value: Any) -> Iterator[GhagenModel]:
    """Yield every GhagenModel reachable from *value*.

    Recurses through Commented wrappers, dicts, and lists. Raw-wrapped
    values are opaque escape hatches and are not traversed.
    """
    if isinstance(value, GhagenModel):
        yield value
    elif isinstance(value, Commented):
        yield from _scan_for_models(value.value)
    elif isinstance(value, Raw):
        return
    elif isinstance(value, dict):
        for v in value.values():
            yield from _scan_for_models(v)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _scan_for_models(item)
```

```python
    def children(self) -> Iterator[GhagenModel]:
        """Yield every nested GhagenModel, in traversal order.

        Schema fields first, in declaration order, then :attr:`extras`.
        This is *traversal* order, not emission order -- emission order is
        the spec's, resolved by :func:`~ghagen.emitter.nodes.order_entries`.
        Recurses through Commented wrappers, dicts, and lists; Raw values
        are opaque.
        """
        for field_name in type(self).model_fields:
            if field_name == "extras":
                continue
            yield from _scan_for_models(getattr(self, field_name, None))
        yield from _scan_for_models(self.extras)

    def walk(self) -> Iterator[GhagenModel]:
        """Depth-first pre-order iterator over self and every descendant.

        The root is yielded first. Read the yielded models to inspect the
        tree, or mutate their fields in place (e.g. the pin transform
        rewrites ``uses``).
        """

        def _visit(model: GhagenModel) -> Iterator[GhagenModel]:
            yield model
            for child in model.children():
                yield from _visit(child)

        yield from _visit(self)
```

Only `extras` needs the skip-and-append: of the four meta fields
(`extras`, `post_process`, `comment`, `eol_comment`) it is the only one that can hold a model, so
this needs no import of the Emitter's `_META_FIELDS` (`emitter/nodes.py:30`) and does not disturb
the one-way `emitter → models` dependency.

**TypeScript** — `packages/typescript/src/models/_base.ts`

```ts
  /** Yield every child Model, in traversal order: data fields, then extras. */
  *children(): Iterable<Model> {
    for (const value of Object.values(this.data)) {
      yield* scanForModels(value);
    }
    for (const value of Object.values(this.meta.extras ?? {})) {
      yield* scanForModels(value);
    }
  }

  /** Depth-first pre-order visit of this model and every descendant. */
  walk(fn: (model: Model) => void): void {
    function visit(model: Model) {
      fn(model);
      for (const child of model.children()) {
        visit(child);
      }
    }
    visit(this);
  }
```

```ts
function* scanForModels(value: unknown): Iterable<Model> {
  if (value instanceof Model) {
    yield value;
  } else if (isCommented(value)) {
    yield* scanForModels(value.value);
  } else if (Array.isArray(value)) {
    for (const item of value) {
      yield* scanForModels(item);
    }
  } else if (typeof value === "object" && value !== null && !isRaw(value)) {
    for (const v of Object.values(value)) {
      yield* scanForModels(v);
    }
  }
}
```

**Invariants and error modes.** Pre-order, root first, `Raw` opaque, `Commented` transparent — all
unchanged. Deleted: the path, the argument-order question, and the runtime prune check. Added: extras
participate, last, in both ports. There is no cycle guard in either port today and none is added; the
models are trees by construction.

**Why TypeScript stays callback-shaped.** Making it a generator would be nicer, and is argued and
rejected in [Risks & alternatives](#risks--alternatives) on schedule grounds. After the narrowing the
_interface_ is identical across ports — same traversal rule, same order, same guarantees; only the
delivery idiom differs, exactly as `Document.to_yaml()` (method) and `toYaml()` (free function)
already do. **Same visit _set_** additionally requires 20 and 11 to have landed; see §2c. That
precondition belongs in the merge order, not in the sentence — the contract as written is about the
rule, and the rule is genuinely identical the moment this lands.

## What sits behind the seam

Three callers each get a whole recursion for free: descent through dicts, lists, `Commented` wrappers
and now `extras`; `Raw` treated as an opaque escape hatch; pre-order with the root included. That is
the leverage, and it is unchanged — this proposal does not touch the implementation's reach, only
what the caller must know to invoke it.

What improves is locality. "What counts as a child of a model" becomes the _entire_ interface of
`walk()`, stated in one function per port, and the two functions become directly comparable — which
is how the extras divergence stops being invisible. Today that fact is spread across `data` vs
`model_fields`, `meta` vs field, and a key threaded through three functions; a maintainer comparing
the ports has to hold four differences in mind to notice that one of them is a bug.

**Deletion test, applied three ways — with the honest verdict on each:**

- **Delete `walk()` outright.** Its three callers each re-grow the same six-line depth-first
  recursion over `children()`. Complexity reappears in three places, in two ports, in two
  subsystems (pin and the Emitter). `walk()` earns its keep. **Keep the module, delete the width.**
- **Delete the path.** **Passes cleanly, and this is measured, not argued.** Applying the full
  narrowing to a copy of `packages/typescript/src` with only `_base.ts` patched: `tsc --noEmit` exit
  0, `pin/sites.ts` and `emitter/yaml-writer.ts` **byte-identical to `main`**, vitest results
  bit-identical to the unpatched copy. On the Python side exactly one production line changes
  (`pin/sites.py:76`). One test disappears with its subject; a `key` parameter stops being threaded
  through four recursive branches in each port. Complexity vanishes rather than reappearing.
- **Delete the prune protocol.** **Passes cleanly.** Zero callers, zero tests, no Python peer.
  Nothing reappears anywhere. A caller who later needs pruning can filter in the callback or, better,
  propose the generator shape (below) and use `break`.

**What the deletion test does not establish.** That either deletion fixes anything. Nobody is calling
the width, so nobody is harmed by it; passing the deletion test cleanly and fixing a defect are
different results, and only the first is claimed here for part (a). The case for (a) is locality and
interface size, stated plainly: after it, one sentence per port is the whole contract, and the ports
can be compared by reading two twelve-line functions side by side.

`children()` deserves the same test and does not obviously pass it: one caller in each port, both
inside `walk`. It is kept anyway, on locality rather than caller count — it is where the
child-policy is declared, and after this change that policy is the whole contract the two ports must
agree on. Folding it into `walk` would bury the one fact this proposal is trying to surface.

## Migration plan

Pre-1.0; clean break, no compatibility shim, no deprecation period.

1. **TypeScript `_base.ts`** — narrow `scanForModels`, `children`, `walk`; add the extras loop. No
   caller edits. Verified on a copy: `tsc --noEmit` exit 0, `pin/sites.ts` and
   `emitter/yaml-writer.ts` byte-identical to `main`.
2. **Python `_base.py`** — the same three functions.
3. **Python `pin/sites.py:76`** — the single production call-site edit in the whole change.
4. **Tests** — per [Test impact](#test-impact).
5. Full suite both ports, plus `uv run ghagen check-synced` (the repository's own workflows must
   still regenerate byte-identically — they contain no extras-nested models, so they will).

Net line count on `packages/typescript/src/models/_base.ts` is **zero** as prototyped (`children`
+3, `walk` −3): measured on the patched copy, the file is still **532 lines**, `buildYamlData` is
still at `:315`, and nothing above `:236` or below `:427` moves. That matters for
[10](./10-delete-modelspec-order.md) — see below.

## Test impact

Measured, not estimated. Running the current Python suite with the narrowing applied to
`children`/`walk`/`_scan_for_models` and to `iter_uses_sites`: **556 passed, 6 failed**, against the
562 baseline. Every failure is a signature update:

- `packages/python/tests/test_models/test_walk.py` — 5 failures.
  - `test_children_yields_direct_nested_models` (`:12-13`) stops unpacking `(key, model)`.
  - `test_walk_yields_self_first_with_empty_path` (`:23-27`) becomes
    `test_walk_yields_self_first` — `next(iter(wf.walk())) is wf`.
  - `test_walk_reaches_steps_inside_workflow_jobs` (`:41-42`) and
    `test_walk_reaches_steps_inside_composite_action_runs` (`:58`) drop the `_p`.
  - **`test_walk_paths_track_field_keys` (`:62-72`) is deleted.** Its subject no longer exists, and
    it is the only test in the repository that reads a path.
- `packages/python/tests/test_emitter/test_dedent_emit.py:100` — 1 failure, inside
  `_rename_transform`; the loop drops `_path`.

None is an output diff. Separately measured: the **extras half alone** (part (b), no narrowing) is
**562 passed, 0 failed** — it changes no existing Python test at all.

The TypeScript suite is unchanged by the patch: run against a copy with only `_base.ts` patched, the
results are bit-identical to the same copy unpatched. Baseline in the checkout is **515 passed, 0
failed** — the narrowing plus the extras traversal breaks nothing, and no existing fixture or
integration snapshot nests a model in `extras`.

New tests:

- **`packages/typescript/src/models/walk.test.ts` (new).** The port has no `walk()`/`children()`
  test today; this is the gap that let the extras divergence live. Covers: root yielded first;
  pre-order sequence over a nested document; `Raw` not traversed; `Commented` traversed through;
  models nested in `extras` visited, and visited **after** data fields; and the byte regression —
  `toYaml` of a workflow whose job carries an extras-nested `step({ run: <indented> })` must dedent,
  matching Python's output above. **6 cases.**
- **`packages/python/tests/test_models/test_walk.py`** gains the two extras tests (visited at all;
  visited last), so the two ports' traversal contracts are asserted symmetrically.
- **`packages/python/tests/test_pin/test_sites.py` / `packages/typescript/src/pin/sites.test.ts`** each
  gain "a `uses:` on a model nested in `extras` is a site." The TypeScript one fails on `main`
  (measured: zero sites) — it is the regression guard for the live defect.

Net arithmetic, corrected: pytest **562 → 564** (5 rewritten in place, 1 deleted, 2 added to
`test_walk.py`, 1 added to `test_sites.py`, 1 mechanical). vitest **515 → 522** (6 in the new
`walk.test.ts`, 1 in `sites.test.ts`).

**Test hole this leaves open.** Nothing in either port asserts that Python's `model_fields`
declaration order matches TypeScript's `fieldMap` declaration order — and that correspondence is the
_sole_ guarantor of the sequence half of the contract. It already diverges harmlessly: `On` declares
`workflow_run` sixth in Python (`trigger.py:229`) and last in `ON_SPEC.fieldMap`
(`trigger.ts:461`), which costs nothing only because that field holds a plain dict. A cross-port
sequence test belongs with [11](./11-shared-spec-surface-table.md)'s conformance table, which already
walks every spec pair; it is not built here and this proposal does not claim it.

## Risks & alternatives

**`12 — 24` — the correction, and the narrowed form.** The dependency graph asserts an edge on the
grounds that 24 touches `clone.walk` in `packages/typescript/src/emitter/yaml-writer.ts`.
[12](./12-ts-comment-geometry-module.md)'s author is right that there is no `_clone.ts` and that
`walk` is defined at `packages/typescript/src/models/_base.ts:245` — 12 lists `_base.ts` under "Not
touched" for exactly that reason (`12` §New). But `yaml-writer.ts:46` _is_ a `walk` call site: `clone`
is a local variable assigned at `:45` from `cloneModel(model)`, not a module.

**This proposal does not edit `packages/typescript/src/emitter/yaml-writer.ts`.** Because the
narrowing removes parameters rather than adding them, `clone.walk((node) => {…})` remains
well-typed — a one-parameter callback satisfies a one-parameter signature, and its block body already
returns `undefined`. Verified by `tsc --noEmit` over a copy of `packages/typescript/src` with only
`_base.ts` patched: exit 0, and `yaml-writer.ts` and `pin/sites.ts` byte-identical.

**Narrowed form of the edge, stated for the scheduler.** The only contact is the `clone.walk` call
site. 24 changes zero lines in `yaml-writer.ts`; 12's edits there are `:389-405`, `:430-433`,
`:447` and `:450` (`12` §Modified), none of which is inside `dedentSteps` (`:44-52`). **Zero shared lines.**
24 also disclaims `test_yaml_writer.py` and `test_spec.py`, which it does not touch — and that
disclaimer survives every amendment in this revision. What remains is a compile-compatibility
obligation, not a textual conflict: whichever lands second must keep `dedentSteps`'s callback
assignable. 12's revision reaches the same conclusion independently and states it as "Residual
overlap: the file name only. Hand-merge; do not serialize." (`12` §Scope boundaries vs siblings). **Agreed — do not
serialise this pair.**

**Alternative: give TypeScript a generator-shaped `walk()`.** `*walk(): Iterable<Model>`, matching
Python exactly. It is the better long-run shape: it would delete the buffer array in `iterUsesSites`
(`pin/sites.ts:66,81` — `const sites: UsesSite[] = []` … `yield* sites`), which exists _only_
because a callback cannot be piped lazily through a generator, and `break` would subsume the prune
protocol properly. **Rejected for this round on schedule grounds**: it edits `yaml-writer.ts:44-52`
and `pin/sites.ts:65-82`, converting the `12 — 24` edge from zero-shared-lines to a real one and
adding overlap with 13 inside the same crowded file, in exchange for an idiomatic gain and a nine-line
deletion. Worth proposing once `yaml-writer.ts` settles; the narrowing here is a strict prerequisite
either way.

**Alternative: keep the path and fix it instead.** Make it addressable — full key path including
`jobs`, list indices, one vocabulary across ports. Rejected. Zero callers want it, it costs a list
allocation per node on every traversal, and an addressable locator is a _different_ module with a
different contract (round-trip: `locate(document, path) is node`) that should be built when
something needs it. One adapter is a hypothetical seam; here there are none.

**Alternative: leave the extras traversal alone and ship only the narrowing.** Cleanly separable, and
now measured on both sides — see the Phase 3 line in §4. Shipping (a) alone keeps 24 purely mechanical
and zero-behaviour-change; shipping (b) alone is a 6-line hotfix with zero test churn. The reason this
document couples them is that the narrowing is what makes the extras contract _statable_: once
`walk()`'s interface is "every model in this document", the ports disagreeing about which models those
are is a contradiction sitting in the one remaining sentence. **That is a documentation argument, and
it is not decisive** — the Phase 3 decision may split them, and this proposal is written so that it
can.

**Risk: the extras fix changes emitted bytes in TypeScript.** Only for documents that nest a model
inside `extras`, and only in the direction of matching Python. No repository fixture or snapshot does
this — verified by the unchanged vitest result and by the fact that all six Python failures are
`walk()` signature updates, none an output diff. The direction of the fix is set by emission: both
Emitters already write extras-nested models, so a traversal that claims to visit "every model in this
document" must reach them. The alternative — making Python stop visiting extras — would leave a model
that is emitted but invisible to every transform, which is worse.

**Risk: extras traversal order.** Python visits `extras` **first** today, an accident of
`model_fields` putting base-class fields before subclass fields — measured above, the extras step is
yielded before the `steps` list. The proposal moves it last in both ports. The binding reason is
parity: the two ports must yield one sequence. "Last" is chosen because it is where the Emitter puts
extras under the **explicit** order mode — `order_entries` ends with `result.extend(extras.items())`
(`nodes.py:83`) and `orderedEntries` appends them in the same position
(`yaml-writer.ts:211-212`) — which makes it the least surprising of the two available conventions.
It is **not** a claim that traversal follows emission: under the alphabetical mode extras interleave
with the typed fields in a single sort (`nodes.py:70-72`, `yaml-writer.ts:196-199`), and traversal
deliberately does not replicate that. Traversal has one order; emission has a per-spec order; §"Proposed
interface" says which is which. Verified after the change: both ports yield the identical node
sequence on the extras document, and `iter_uses_sites` / `iterUsesSites` return refs in the same order
(`actions/checkout@v4` then `actions/setup-node@v4`).

**Risk: `children()` and `walk()` are exported surface.** `Model` is exported from
`packages/typescript/src/index.ts:27` and `GhagenModel.walk` is public in Python, so this is a
breaking API change. Pre-1.0, breaking changes are allowed, and the blast radius is verifiably
small: neither method appears anywhere under `docs/src/content/docs/`, and neither is reachable from
a TypeDoc entry point — the entry points are only the nine `_docs-api-*.ts` barrels
(`docs/astro.config.mjs:126,133,140,147,154,161,168,175,182`), none of which exports `Model`.

### Scope boundaries vs siblings

- **[21](./21-hoist-field-collection-loop.md) — hoist the duplicated field-collection loop.
  Semantic only; no shared file in either direction.** 21's revision dissolved the file contact: its
  agreement invariant already exists at `test_to_data.py:130-161` and stays there (that file does not
  call `walk()`), and its new `test_field_collection.py` is per-rule unit tests that do not traverse
  (`21` §New — tests, `21` §Migration plan, `21` §Test impact). 21 records the dissolution itself at `21` §Scope boundaries vs siblings, inside its `24`
  scope-boundary bullet at `21` §Scope boundaries vs siblings. **Merge order is free in both directions.** The substantive
  agreement stands and is worth restating: `GhagenModel.children()` (`_base.py:142-150`) is a third
  `model_fields` loop in the Python port but with opposite semantics — no `_META_FIELDS` skip, no
  `exclude_unset`/`exclude_none`, no YAML-key mapping — because traversal must reach every nested
  model _regardless of whether it will be emitted_, so it must not consume `collect_fields`
  (`21` §Scope boundaries vs siblings). One refinement: this proposal makes `children()` skip exactly one name (`"extras"`)
  and re-scan it last, which is an _ordering_ rule, not the emission-eligibility rule `collect_fields`
  owns; the two must stay separate.
- **[20](./20-delete-callerless-pin-spec-surface.md) — delete caller-less pin/spec surface.
  Semantic edge, previously recorded here as "no edge" — that was wrong.** File-level overlap is
  genuinely zero: 20 touches neither `models/_base.ts` nor `models/_base.py`, nor `pin/sites.ts`/`.py`,
  nor `pin/sites.test.ts`, nor `test_walk.py`. But 20 item F deletes Python's `JobOutput`
  (`job.py:169-175`), which **removes a node from every Python `walk()`** — precisely the visit-set
  fact this proposal's contract asserts, and it closes one of the four rows in §2c. **20 must land
  first.** Second, documentary interaction: 20 deletes `extrasPlacement`, so the
  `yaml-writer.ts:202-205` `withinOrder` branch disappears and the extras-ordering note above cites
  only the alphabetical interleave once 20 has landed. Third: both proposals edit
  `packages/typescript/CONTEXT.md`, 20 at `:43` and this proposal at `:98-102` — disjoint.
- **[11](./11-shared-spec-surface-table.md) — one shared spec-surface conformance table. Semantic
  edge in this proposal's favour, previously analysed here as textual-only — that was wrong.**
  Textually, 11 touches `_base.ts` for `ModelKind` (`:160-187`, +3 members) and three `ModelOf`
  aliases (`ModelOf` at `:261`, concrete aliases from `:263`); `ModelKind` ends forty-nine lines
  above `children()` and the aliases begin five lines below the class's closing brace at `:256` —
  non-overlapping, but tight on the lower side. **Semantically it is bigger than that**: 11's
  `wrap: { inputs | outputs | secrets: { …, mode: "map" } }` on `WORKFLOW_CALL_SPEC` promotes those
  three sub-maps to `Model`s, so `scanForModels` (`_base.ts:413-427`) yields **three extra nodes**.
  Python already visits them (`trigger.py:176-203`), so **after 11 the two ports' traversal agrees on
  that sub-tree** — closing three of §2c's four rows. **11 should land first**; 11 says the same at
  `11` §Scope boundaries vs siblings. A three-way merge of 11, 22 and 24 on `_base.ts` is textually clean; if the round
  wants zero merge risk, sequence 24 last of the three — it is the smallest and, unlike them, touches
  no other file in that directory.
- **[10](./10-delete-modelspec-order.md) — delete `order` from every `ModelSpec`.** Runs solo and
  last, after this. _Python:_ 10's table does **not** list
  `packages/python/src/ghagen/models/_base.py` — it lists `models/spec.py`, the nine spec modules,
  and the two Emitter files — so on the Python side there is **no source overlap at all**.
  _TypeScript:_ we do both edit `packages/typescript/src/models/_base.ts`, but in disjoint regions —
  10 rewrites the `buildYamlData` doc comment at `:302-314`; this proposal rewrites `:236-255` and
  `:413-427`. Since the change is net zero lines in that file (measured: 532 → 532), 10's citation
  survives verbatim: `buildYamlData` remains at `:315`. No test file is shared. **Both `CONTEXT.md`
  files are shared**, in disjoint regions: 10 owns the **OrderMode** glossary entries
  (`typescript:48-49`, `python:46-47`) plus one _appended_ surface-notes bullet in each; this proposal
  extends the existing traversal bullet at `typescript:98-101` and adds one sentence inside the Python
  surface-notes block at `python:94-107`. Append points differ; sequence either way.
- **[22](./22-collapse-ts-factory-bodies.md) — collapse the TypeScript factory bodies into
  `defineFactory(SPEC)`.** In `models/_base.ts`, 22 adds `defineFactory` beside `buildModel`
  (`:371-377`) — well clear of `:236-255` and `:413-427` — and it does not change _what a factory
  stores in `data`_, so it cannot move what `children()` sees. Its other shared-directory file is
  `models/_base.test.ts` (208), which this proposal does not touch. **One real contact:
  `packages/typescript/CONTEXT.md`.** 22 rewrites the surface-notes bullet at `:98` (`22` §Migration plan) and
  this proposal extends the same bullet. Resolution: this proposal stays inside its assigned region
  `:98-102` and **appends** a clause after "amended." at `:101` rather than rewriting `:98`, so 22's
  edit and this one merge without conflict in either order.

## ADR / CONTEXT.md impact

- **ADR-0001 (Document serialization seam, 2026-07-21 amendment) — reinforced, not reopened.**
  `walk()` is traversal, not serialization; models still do not serialize themselves and the
  Emitter still owns all emission recursion. The extras change makes traversal _agree with_ what the
  Emitter already emits — it moves no emission decision into the model layer. The proposed contract
  deliberately says "traversal order", not "emission order", to keep the two apart.
- **ADR-0006 (pin collects parsed refs, not strings) — unaffected in shape.** `iterUsesSites` keeps
  returning parsed `UsesSite`s; the TypeScript port simply stops missing some of them. No amendment.
- **No other ADR is touched**, and no ADR describes the traversal primitives.
- **`packages/typescript/CONTEXT.md` — region `:98-102`, append-only.** The surface-notes bullet at
  `:98-101` says the shared `Model` class provides "`walk()` / `children()`". **Append** one clause
  to the end of that bullet (after "amended." at `:101`), leaving `:98-100` byte-identical so
  [22](./22-collapse-ts-factory-bodies.md)'s rewrite of `:98` merges cleanly: _traversal visits every
  model in the document, root first, depth-first, data fields then extras — no path, no pruning; that
  is traversal order, not emission order._ No line outside `:98-102` is claimed.
- **`packages/python/CONTEXT.md`, "Surface notes (Python)" (`:94-107`)** — has no traversal note
  today. Add the same sentence so the two files state one contract. This is the point: after the
  change there is only one sentence to keep in sync.
- **No new glossary term.** "Traversal" needs no domain vocabulary; `walk` is an implementation
  name, not a domain noun like **Document** or **uses-site**.
- **`docs/specs/0001-python-single-pass-serialization.md:301-302`** — "`children()` / `walk()` /
  `_scan_for_models` are untouched — they are a separate traversal primitive, not part of
  serialization." The claim is scoped to that landed migration and remains true of _serialization_;
  the sentence's substance — traversal is not serialization — is exactly what this proposal
  preserves, and is the reason the contract avoids the phrase "emission order". **No amendment;
  named here so a reviewer need not re-derive it.**
