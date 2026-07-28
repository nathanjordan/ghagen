# 06 — Close the ModelSpec / Emitter escape hatches

**Status:** proposed | **Ports:** typescript (led) / python (mirror) | **Depends on:** interacts with [02](./02-emitter-test-seam.md)

## Problem

`ModelSpec` is supposed to be the single declaration of a model type's emission surface (kind,
field→YAML-key map, order, wrap rules), and `buildModel` the single path from input to a `Model`.
Several factories route **around** both, hand-building `data` and pre-computing ordering — so the
spec no longer fully describes what gets emitted, and one such bypass silently drops user comments.

**1. `on()` pre-sorts keys in the factory, bypassing the spec's ordering.**
`ON_SPEC.order` is `[]` (`packages/typescript/src/models/trigger.ts:455`) — the declarative signal
for "no canonical order." But instead of letting the Emitter honour that, the factory sorts eagerly:

```ts
// packages/typescript/src/models/trigger.ts:484-495
export function on(input: WithMeta<OnInput>): OnModel {
  const [data, meta] = extractMeta(input);
  const yamlData = buildYamlData(ON_SPEC, data as Record<string, unknown>);
  const sortedData: Record<string, unknown> = {};
  for (const key of Object.keys(yamlData).sort()) {   // ← ordering escapes the Emitter
    sortedData[key] = yamlData[key];
  }
  return new Model(ON_SPEC, sortedData, meta) as OnModel;   // ← bypasses buildModel
}
```

The Emitter's `getOrderedKeys` (`yaml-writer.ts:172-192`) already appends non-ordered keys — but in
**insertion order**, so an empty `order` there means "insertion order," not "alphabetical." The two
ports even disagree on this: Python's `to_ordered_commented_map`
(`packages/python/src/ghagen/emitter/nodes.py:63-72`) appends leftover keys via `sorted(...)` —
**alphabetical**. So Python emits `on:` alphabetically *at the Emitter*, while TS only matches
because the factory pre-sorts. "Empty order = alphabetical" is a real emission rule that is currently
implemented in one port's Emitter and the other port's factory.

**2. `meta.extras` are appended after the ordered keys, escaping `fieldMap` and `order`.**
Both ports splice extras onto the end of the ordered entries, outside the spec's ordering:

- TS `yaml-writer.ts:74-76`: `if (model.meta.extras) entries.push(...Object.entries(model.meta.extras));`
- Python `nodes.py:171`: `for key, value in list(ordered.items()) + list(model.extras.items()):`

Extras are how dynamic keys reach YAML (matrix axes, uncommon `on:` events), so they must exist — but
their placement is a hard-coded "after everything," never expressible in the spec.

**3. Three TS factories bypass `buildModel`.**

- `matrix()` — `job.ts:78-81`: `new Model(MATRIX_SPEC, data, meta)`. Justified today because matrix
  axis keys (`"node-version"`, `"os"`) are dynamic and `MATRIX_SPEC.fieldMap` names only
  `include`/`exclude` (`job.ts:72-76`), so `buildYamlData` would drop the dynamic keys.
- `on()` — `trigger.ts:484-495`, per #1.
- `defaults()` — `job.ts:214-229`: hand-builds the nested `run` map:

  ```ts
  const runData: Record<string, unknown> = {};
  if (data.run.shell !== undefined) runData["shell"] = data.run.shell;
  if (data.run.workingDirectory !== undefined) runData["working-directory"] = data.run.workingDirectory;
  yamlData["run"] = runData;
  ```

  This is a **latent comment-drop bug.** `DefaultsRunInput.shell` is typed `string`, but
  `withComment("bash", "note")` returns type `T` (`_base.ts:37`), so a caller can legally pass a
  `Commented` wrapper. The hand-build stores it into a *plain* nested object; the Emitter's
  plain-object branch (`yaml-writer.ts:144-155`) unwraps `Commented` via `toYamlValue` but never
  calls `attachFieldComment`, so **the comment is silently lost.** The spec-aware peel/re-apply in
  `buildYamlData` (`_base.ts:323-342`) exists precisely to preserve this — but only for a spec's
  top-level fields, and `shell`/`workingDirectory` are not fields of any spec here.

  The Python port does **not** have this bug: `Defaults.run` is a proper `DefaultsRun` model
  (`packages/python/src/ghagen/models/job.py:159,162-168`) with `DEFAULTS_RUN_SPEC`
  (`job.py:43-46`), so shell/working-directory go through the normal emitter path and their
  `Commented` wrappers survive. This is a port divergence the parity mandate says should not exist.

**4. Python mirror smell: `On` smuggles `Raw(None)` past `exclude_none` with `object.__setattr__`.**
`packages/python/src/ghagen/models/trigger.py:257-272`:

```python
@model_validator(mode="after")
def _normalize_workflow_dispatch(self) -> On:
    wd = self.workflow_dispatch
    is_empty_model = isinstance(wd, WorkflowDispatchTrigger) and wd.inputs is None
    is_empty_map = isinstance(wd, dict) and len(wd) == 0
    if is_empty_model or is_empty_map:
        object.__setattr__(self, "workflow_dispatch", Raw(None))   # emitter knowledge in the model
    return self
```

The domain rule "an empty `workflow_dispatch` emits as a bare `workflow_dispatch:` (present null),
not `workflow_dispatch: {}`" is an **emission** decision, but it is encoded in the *model* layer by
mutating a validated instance with `object.__setattr__` and abusing `Raw` (the user-facing escape
hatch) as an internal present-null signal. Emitter knowledge has leaked into the model.

Net: the spec describes *most* of emission, and the gaps are filled by ad-hoc factory code and a
model-layer mutation. A reader cannot trust the spec as the whole story.

## Current interface

- `ModelSpec` (TS `spec.ts:36-49`): `kind`, `fieldMap`, `order` (empty = "insertion order" per the TS
  Emitter, but "alphabetical" per the Python Emitter), optional `wrap`.
- `ModelSpec` (Python `spec.py:16-31`): `yaml_keys`, `order` (empty = alphabetical).
- `buildModel` / `buildYamlData` (TS `_base.ts:310-360`): the spec-driven input→data path, with
  `Commented` peel/re-apply — but only across `fieldMap` keys, and callers may skip it entirely.
- Extras: merged after ordered keys, unconditionally, in both Emitters.

A maintainer must know, per factory, whether it goes through `buildModel` or hand-rolls `data`, and
must know that "empty order" means different things in the two Emitters.

## Proposed interface

Make every gap expressible **declaratively in `ModelSpec`**, and route every factory through
`buildModel`.

### (a) An explicit order mode — kill the `on()` pre-sort and unify the ports

Replace the overloaded "empty `order`" signal with a named mode:

```ts
// spec.ts
export type OrderMode =
  | { readonly kind: "explicit"; readonly keys: readonly string[] }  // ordered, then extras
  | { readonly kind: "alphabetical" };                               // all keys sorted at emit

export interface ModelSpec {
  readonly kind: ModelKind;
  readonly fieldMap: Readonly<Record<string, string>>;
  readonly order: OrderMode;
  readonly wrap?: Readonly<Record<string, WrapRule>>;
  readonly dynamicKeys?: boolean;                 // see (c)
  readonly extrasPlacement?: "afterOrdered" | "withinOrder"; // see (b), default "afterOrdered"
}
```

```ts
// trigger.ts — ON_SPEC
order: { kind: "alphabetical" },

// on() collapses to the common path
export function on(input: WithMeta<OnInput>): OnModel {
  const [data, meta] = extractMeta(input);
  return buildModel<OnModel>(ON_SPEC, data as Record<string, unknown>, meta);
}
```

`getOrderedKeys` reads the mode: `alphabetical` sorts *all* keys (including extras) at emit;
`explicit` keeps today's "ordered first, remainder appended." The sort now lives in the Emitter, in
one place, identically for both ports. Python's `ModelSpec.order` gains the same two-mode shape
(`OrderMode` as a small frozen dataclass union, or `order: tuple[...] | None` where `None` =
alphabetical), and `to_ordered_commented_map`'s implicit `sorted()` becomes the explicit
`alphabetical` branch — so the two Emitters stop disagreeing about what an unordered spec means.

### (b) Route extras through spec-aware emission

Extras placement becomes a spec field, `extrasPlacement` (default `"afterOrdered"`, preserving
today's behaviour). Under `alphabetical`, extras participate in the single sort (so a dynamic `on:`
event like `merge_group` interleaves alphabetically instead of being force-appended). This makes the
"extras go last" rule a declared default rather than a hard-coded Emitter step, and lets the one
model that wants interleaving (`On`) get it declaratively.

### (c) A documented dynamic-keys path through `buildModel`

Add `dynamicKeys?: boolean` to the spec. When true, `buildYamlData` maps the `fieldMap` keys as
usual **and** passes through any input key not in `fieldMap` (after `extractMeta` removes the meta
keys), instead of dropping it:

```ts
// _base.ts buildYamlData, after the fieldMap loop:
if (spec.dynamicKeys) {
  const mapped = new Set(Object.keys(spec.fieldMap));
  for (const [k, v] of Object.entries(data)) {
    if (!mapped.has(k) && v !== undefined) yamlData[k] = v;   // dynamic axis passes through
  }
}
```

```ts
// job.ts — MATRIX_SPEC
export const MATRIX_SPEC: ModelSpec = {
  kind: "matrix",
  fieldMap: { include: "include", exclude: "exclude" },
  order: { kind: "explicit", keys: ["include", "exclude"] },  // dynamic axes follow, then emit order
  dynamicKeys: true,
};
export function matrix(input: WithMeta<MatrixInput>): MatrixModel {
  const [data, meta] = extractMeta(input);
  return buildModel<MatrixModel>(MATRIX_SPEC, data as Record<string, unknown>, meta);  // no bypass
}
```

Now `matrix()` is on the common path; the "dynamic axes pass through" fact is declared in the spec,
not implied by a raw `new Model(...)`. (Python's `Matrix` uses `extras` for axes and already goes
through the normal emitter path via `_model_to_map`; `dynamicKeys` is the TS-idiom equivalent that
keeps the ergonomic index-signature `MatrixInput` API while still flowing through `buildModel`.)

### (d) Fix `defaults()` by mirroring Python's `DefaultsRun` model

Model the nested `run` as its own `Model` with a spec, exactly as Python does, so its fields flow
through `buildYamlData` and the `Commented` peel/re-apply preserves comments:

```ts
// job.ts
export const DEFAULTS_RUN_SPEC: ModelSpec = {
  kind: "defaultsRun",
  fieldMap: { shell: "shell", workingDirectory: "working-directory" },
  order: { kind: "explicit", keys: ["shell", "working-directory"] },
};
function defaultsRun(input: DefaultsRunInput): DefaultsRunModel {
  return buildModel<DefaultsRunModel>(DEFAULTS_RUN_SPEC, input as Record<string, unknown>, {});
}

export const DEFAULTS_SPEC: ModelSpec = {
  kind: "defaults",
  fieldMap: { run: "run" },
  order: { kind: "explicit", keys: ["run"] },
  wrap: { run: { factory: defaultsRun, mode: "objectModel" } },  // promote inline run → model
};
export function defaults(input: WithMeta<DefaultsInput>): DefaultsModel {
  const [data, meta] = extractMeta(input);
  return buildModel<DefaultsModel>(DEFAULTS_SPEC, data as Record<string, unknown>, meta);  // no hand-build
}
```

Add `"defaultsRun"` to `ModelKind` and a `DefaultsRunModel` alias. `withComment("bash", …)` on
`run.shell` now survives to YAML, in both ports.

### (e) Python mirror: replace the `On` `Raw(None)` smuggle with a declared present-null rule

Move the emission decision into the spec/Emitter. Add a declarative flag naming fields whose empty
sub-model emits as a bare null key:

```python
# spec.py
@dataclass(frozen=True)
class ModelSpec:
    yaml_keys: Mapping[str, str]
    order: tuple[str, ...] | None = ()          # None = alphabetical (see (a))
    present_null_when_empty: frozenset[str] = frozenset()   # YAML keys: empty map -> "key:" (null)
```

```python
# trigger.py — ON_SPEC gains the rule; the validator and object.__setattr__ are DELETED
ON_SPEC = ModelSpec(
    yaml_keys={..., "workflow_dispatch": "workflow_dispatch", ...},
    order=None,                                        # alphabetical, declaratively
    present_null_when_empty=frozenset({"workflow_dispatch"}),
)
```

The Emitter, when a `present_null_when_empty` field resolves to an empty map (an empty
`WorkflowDispatchTrigger` or `{}`), emits `workflow_dispatch:` (null) instead of `{}`. `On`
`_normalize_workflow_dispatch` (`trigger.py:257-272`) is removed entirely — no `model_validator`, no
`object.__setattr__`, no `Raw(None)` abuse. `Raw` returns to meaning only "user escape hatch." A
boolean `workflow_dispatch: true` is untouched (it is not an empty map). The TS peer is the same
`presentNullWhenEmpty?: readonly string[]` on `ModelSpec`, so both Emitters read the rule from the
spec.

**Invariants / error modes:** all four spec additions are optional with behaviour-preserving
defaults (`extrasPlacement="afterOrdered"`, `dynamicKeys=false`, `presentNull*` empty), so unrelated
models are unchanged. Emitted bytes for existing documents stay identical except the intended fix
(d) (comments now preserved) — a strict improvement.

## What sits behind the seam

`ModelSpec` absorbs the last emission decisions that were leaking into factories and the model layer:
ordering mode, extras placement, dynamic-key passthrough, and present-null-when-empty. `buildModel`
becomes the *only* input→Model path — no factory hand-rolls `data`. The Emitter's `getOrderedKeys`
grows one branch (alphabetical vs explicit) and owns sorting for both ports, ending the
`sorted()`-vs-insertion-order divergence. The spec once again describes the whole of a model's
emission, which is the property the whole ModelSpec design is supposed to guarantee.

## Migration plan

Pre-1.0; clean breaks.

1. Add `OrderMode` + the optional spec fields (TS `spec.ts`, Python `spec.py`). Update every spec
   literal to the new `order` shape (mechanical: `order: [...]` → `order: { kind: "explicit", keys:
   [...] }`; `order: []` → `order: { kind: "alphabetical" }`; Python `order=(...)` unchanged,
   `On` → `order=None`).
2. Teach `getOrderedKeys` / `to_ordered_commented_map` the two modes and `extrasPlacement`; add the
   `present_null_when_empty` check at map emission.
3. Add `dynamicKeys` passthrough to `buildYamlData`; convert `matrix()` to `buildModel`.
4. Add `DefaultsRunModel` / `DEFAULTS_RUN_SPEC` / `defaultsRun`; convert `defaults()` to `buildModel`
   with a `wrap` on `run`.
5. Convert `on()` to `buildModel`; delete its pre-sort.
6. Delete Python `On._normalize_workflow_dispatch`; add `present_null_when_empty` to `ON_SPEC`.
7. Full suite + integration snapshots; the only intended byte change is comment preservation on
   `defaults.run.*`.

## Test impact

- **New:** a defaults comment-preservation test in both ports —
  `defaults({ run: { shell: withComment("bash", "login shell") } })` must emit the `# login shell`
  comment. This is the regression guard for the fixed bug; it fails on `main` (TS) today.
- **New:** an `on()`/`On` test asserting alphabetical emission *including* a dynamic extra event
  (e.g. `merge_group`) interleaves alphabetically — observed via `toData` / `to_data`
  (see [02](./02-emitter-test-seam.md)), not by probing `model.data`.
- **New:** a matrix test asserting dynamic axes emit through `buildModel` (axis keys present, after
  `include`/`exclude`), via `toData`.
- **Rewritten:** any existing `on()` test asserting `model.data` insertion order moves to asserting
  emitted key order via `toData`.
- **Deleted:** Python `test_pin`/`test_serialize` assertions tied to the `Raw(None)` workflow_dispatch
  path shift to asserting the emitted `workflow_dispatch:` present-null key (e.g.
  `test_serialize.py:32` `to_data(On(workflow_dispatch={}))` should show `{"workflow_dispatch": None}`).

## Risks & alternatives

- **Alternative for `on()`: keep the factory sort.** Rejected — it duplicates an ordering rule the
  Emitter already owns for `explicit` specs, and it is *why* the two ports silently disagree about
  empty-`order` semantics. Declaring the mode fixes both.
- **Alternative for `matrix()`: keep the `new Model(...)` bypass.** Rejected — "some factories go
  through `buildModel`, some don't" is exactly the inconsistency this proposal closes; `dynamicKeys`
  makes the passthrough a declared, testable property.
- **Alternative for present-null: leave `Raw(None)` in the model.** Rejected — it puts an emission
  decision in the model layer via `object.__setattr__`, and overloads the user-facing `Raw` escape
  hatch as an internal signal. A spec flag keeps the decision in the Emitter, where ADR-0001 puts all
  emission logic, and is symmetric across ports.
- **Risk: `extrasPlacement`/`dynamicKeys` add spec surface few models use.** Accepted — each is
  optional with a behaviour-preserving default, and each replaces a *harder-to-see* bespoke code path
  with a *visible* declaration. Net interface complexity drops because three factory special-cases
  and one model-layer validator disappear.
- **Deletion test:** remove `dynamicKeys` and `matrix()` must re-grow its `new Model` bypass in one
  caller — a real, earned keep, not a pass-through. Same for `present_null_when_empty` (the `On`
  validator reappears) and the `defaultsRun` model (the comment-drop bug reappears).

## ADR / CONTEXT.md impact

- **No ADR-0001 contradiction; it is reinforced.** Every change moves an emission decision *out* of
  factories/models and *into* the spec the Emitter reads. Recursion and emission logic stay in the
  Emitter; models stay data + spec.
- **ADR-0002 (no construction-time config globals):** unaffected — these are per-spec static
  declarations, not runtime config.
- **CONTEXT.md (both), "ModelSpec" entry:** note the order mode (explicit | alphabetical), the
  dynamic-keys passthrough, and the present-null-when-empty rule as declared parts of the spec; and
  that **all** factories build through `buildModel` / the spec (no hand-rolled `data`).
- **New glossary terms (both CONTEXT.md):** **OrderMode** (explicit key list vs alphabetical
  emission) and **present-null-when-empty** (a spec-declared field whose empty sub-model emits as a
  bare null key). Consider a **DefaultsRun** entry mirroring the existing Python model into the TS
  surface notes.
