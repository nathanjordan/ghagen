# 10 — Delete `order` from `ModelSpec`

**Status:** proposed | **Ports:** both | **Effort:** XL | **Depends on:** [06](./06-close-modelspec-escape-hatches.md) (landed; this narrows the `OrderMode` it introduced), **[11](./11-shared-spec-surface-table.md)** (HARD — the TypeScript sequence guard iterates the `models/registry.ts` `SPECS_BY_KIND` 11 creates), **[21](./21-hoist-field-collection-loop.md)** (HARD — migration step 3 edits the `collect_fields` 21 creates), **[20](./20-delete-callerless-pin-spec-surface.md)** and **[09](./09-construction-time-validation-parity.md)** (both reshape `ModelSpec` first); runs **solo and last**, in place on the merged tree, after all fifteen siblings

**Effort is XL, not L.** ~59 spec literals across two ports post-{11,20}, emitter rewrites in three
files, eight test files, four new test loops, two `CONTEXT.md` files, an atomic cross-port compile,
and — because this lands last — a full re-measurement of the survey against a tree fifteen proposals
deep. The sweep itself is L; the rebase and re-verification are what push it over.

> **Every count in this document is dated.** The survey was run against HEAD `e7a972c`. This
> proposal lands on a tree with fifteen siblings merged, four of which move these numbers
> ([11](./11-shared-spec-surface-table.md), [20](./20-delete-callerless-pin-spec-surface.md),
> [13](./13-unify-format-header-contract.md), [12](./12-ts-comment-geometry-module.md)). Where a
> figure changes, the **post-sibling** value is given first and the `e7a972c` value in parentheses.
> Migration step 0 re-derives all of them; see [Migration plan](#migration-plan).

## Files involved

Every `ModelSpec` literal in both ports is rewritten, so this table is the whole models surface.
No new files are created by this proposal; two are **consumed** from siblings.

### Modified — Python source

| Path                                                  | Lines | Role in this proposal                                                                                                                                                                                                                                                                                                                                                                        |
| ----------------------------------------------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/python/src/ghagen/models/spec.py`           | 41    | `order: tuple[str, ...] \| None` (`:40`) collapses to a two-value `OrderMode`; the `order` attribute docs (`:25-32`) rewritten; **module docstring (`:1-8`) fixed** — `:6` still points at `GhagenModel.to_commented_map`, removed by the ADR-0001 amendment (`docs/adr/0001-document-serialization-seam.md:34`). Post-09 this file also carries `patterns` (`09` §Modified — unconditional) |
| `packages/python/src/ghagen/models/action.py`         | 259   | 7 specs; 32 restated key names deleted                                                                                                                                                                                                                                                                                                                                                       |
| `packages/python/src/ghagen/models/container.py`      | 37    | 1 spec; 6 keys                                                                                                                                                                                                                                                                                                                                                                               |
| `packages/python/src/ghagen/models/image_snapshot.py` | 46    | 1 spec; 2 keys                                                                                                                                                                                                                                                                                                                                                                               |
| `packages/python/src/ghagen/models/job.py`            | 226   | 7 specs / 33 keys post-{11,20} (8 / 34 at `e7a972c`; 20 deletes `JOB_OUTPUT_SPEC` at `:48-51`, 11 adds `Environment.deployment`)                                                                                                                                                                                                                                                             |
| `packages/python/src/ghagen/models/permissions.py`    | 67    | 1 spec; 16 keys post-11 (13 today)                                                                                                                                                                                                                                                                                                                                                           |
| `packages/python/src/ghagen/models/step.py`           | 78    | 1 spec; 11 keys                                                                                                                                                                                                                                                                                                                                                                              |
| `packages/python/src/ghagen/models/trigger.py`        | 250   | 10 specs (9 explicit, 33 keys post-11 / 29 today) + `ON_SPEC` `order=None` (`:118`) → `"alphabetical"`                                                                                                                                                                                                                                                                                       |
| `packages/python/src/ghagen/models/workflow.py`       | 74    | 1 spec; 8 keys                                                                                                                                                                                                                                                                                                                                                                               |
| `packages/python/src/ghagen/models/_base.py`          | 231   | **New home for `_META_FIELDS`**, beside the four `exclude=True` declarations it names (`:100-103`) — see migration step 4                                                                                                                                                                                                                                                                    |
| `packages/python/src/ghagen/emitter/nodes.py`         | 209   | `order_entries` (`:52-84`) loses its explicit branch and its docstring's explicit clause (`:66-68`); `collect_fields` (created by 21 after `:84`) has its loop head, two dead guards and its docstring rewritten; `_META_FIELDS` (`:30`) moves out                                                                                                                                           |

`packages/python/src/ghagen/emitter/data.py` **is deliberately absent**. At `e7a972c` it carried a
verbatim copy of the collection loop (`:104-115`) that this proposal would also have had to edit.
[21](./21-hoist-field-collection-loop.md) collapses that copy into a single `collect_fields` call
sited in `nodes.py` (`21` §Modified — Python source, `21` §What sits behind the seam) — explicitly so that `order_entries` and `_META_FIELDS`
do not move and `data.py` drops out of this table (`21` §Risks & alternatives, `21` §Scope boundaries vs siblings). It lands first, so
it does.

### Modified — TypeScript source

| Path                                               | Lines | Role in this proposal                                                                                                                                                                                                                                                                                                                                                                               |
| -------------------------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/typescript/src/models/spec.ts`           | 91    | `OrderMode` (`:38-40`) collapses to a string union; the `ModelSpec.order` declaration (`:62-63`) becomes optional. **Line numbers shift**: 20 deletes `extrasPlacement` (`:73-84`) and 09 inserts `patterns` between `dynamicKeys` and `presentNullWhenEmpty` before this lands                                                                                                                     |
| `packages/typescript/src/models/_base.ts`          | 532   | `buildYamlData` doc (`:302-314`): `fieldMap` declaration order _is_ emission order. Co-claimants: 09 (`buildYamlData` body), 11 (`ModelKind`), 22 (`defineFactory` at `:371-377`), 24 (`:236-255`, `:413-427`) — all disjoint from this doc block                                                                                                                                                   |
| `packages/typescript/src/models/action.ts`         | 406   | 7 specs; 32 keys                                                                                                                                                                                                                                                                                                                                                                                    |
| `packages/typescript/src/models/container.ts`      | 96    | 2 specs sharing one `CONTAINER_ORDER` const (`:35`); the const dies                                                                                                                                                                                                                                                                                                                                 |
| `packages/typescript/src/models/image-snapshot.ts` | 52    | 1 spec; 2 keys                                                                                                                                                                                                                                                                                                                                                                                      |
| `packages/typescript/src/models/job.ts`            | 428   | 7 specs; 33 keys post-11 (32 today)                                                                                                                                                                                                                                                                                                                                                                 |
| `packages/typescript/src/models/permissions.ts`    | 96    | 1 spec; 16 keys post-11 (13 today)                                                                                                                                                                                                                                                                                                                                                                  |
| `packages/typescript/src/models/step.ts`           | 94    | 1 spec; 11 keys                                                                                                                                                                                                                                                                                                                                                                                     |
| `packages/typescript/src/models/trigger.ts`        | 496   | 10 specs post-11 (7 today; 11 adds `workflowCallInput/Output/Secret`), 9 explicit / 33 keys + `ON_SPEC` (`:426-473`, mode at `:463`)                                                                                                                                                                                                                                                                |
| `packages/typescript/src/models/workflow.ts`       | 99    | 1 spec; 8 keys                                                                                                                                                                                                                                                                                                                                                                                      |
| `packages/typescript/src/emitter/yaml-writer.ts`   | 480   | `orderedEntries` (`:189-215`) loses its explicit branch and `orderExplicit` (`:221-226`) is deleted; the function doc (`:178-188`) is rewritten. **20 lands first** and already deletes the `withinOrder` branch (`:202-205`) and the `extrasPlacement` clauses of that same doc comment (`:180`, `:185-187`), so this is **one** surviving branch to remove, not two, against shifted line numbers |

### Modified — tests

| Path                                                     | Lines | Role in this proposal                                                                                                                                                                                                                                                                                                                                                                                                      |
| -------------------------------------------------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/python/tests/test_models/test_spec.py`         | 78    | `test_explicit_order_has_no_duplicates` (`:51-56`) and `test_explicit_order_is_complete` (`:59-72`) replaced by the sequence + uniqueness guards; `test_only_on_uses_alphabetical_order` (`:75-78`) reads `m.SPEC.order is None` and must read `== "alphabetical"`; the `_META_FIELDS` import (`:16`) re-points to `models/_base`. Co-claimant: **11** (`11` §Modified, hardens `_all_model_classes()` at `:21-32`)        |
| `packages/python/tests/test_emitter/test_yaml_writer.py` | 205   | `test_order_entries_explicit` (`:64-67`) and `test_order_entries_explicit_remaining_insertion_order` (`:70-74`) deleted; `test_order_entries_alphabetical_interleaves_extras` (`:77-80`) swaps `order=None` for `order="alphabetical"`. Co-claimants: **12** (`:1-10` docstring), **13** (`:91-95`) — disjoint                                                                                                             |
| `packages/python/tests/test_models/test_serialize.py`    | 134   | docstring at `:48` names `order=None`. Co-claimant: **11** (`11` §Modified)                                                                                                                                                                                                                                                                                                                                                |
| `packages/typescript/src/models/spec.test.ts`            | 127   | the two `order` `it.each` blocks (`:102-107`, `:109-115`) replaced; `only the \`on\` spec uses alphabetical order` (`:123-126`) reads `s.order.kind === "alphabetical"`and must read`s.order === "alphabetical"`. **11 rewrites this file first** (deletes `ALL_SPECS`/`ALL_KINDS`, consumes the registry)                                                                                                                 |
| `packages/typescript/src/models/container.test.ts`       | 60    | `expect(c.spec.order).toEqual(s.spec.order)` (`:58`) becomes vacuous; compare `fieldMap` identity                                                                                                                                                                                                                                                                                                                          |
| `packages/typescript/src/models/_base.test.ts`           | 208   | test name "carries its spec (kind + key order)" (`:89`); **three ad-hoc `order: []` literals** in `buildYamlData()` specs (`:179`, `:192`, `:202`) — all behind `as unknown as ModelSpec` casts, so they compile either way, but they are stale the moment `OrderMode` is a string. Co-claimants: **09** (rewrites `:188-196`, a replacement — re-anchor by test name, not line), **22** (appends a `defineFactory` block) |
| `packages/typescript/src/emitter/yaml-writer.test.ts`    | 244   | `simpleModel`'s `order` parameter (`:17-28`) and its three call sites (`:102`, `:193`, `:194`); the ordering test (`:89-99`). Co-claimants: **09** (`TS2345` narrowing), **12** (`:125,141`), **13** (`:34-64`) — disjoint                                                                                                                                                                                                 |

### Consumed — files created by siblings

| Path                                                          | Created by | Role in this proposal                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/typescript/src/models/registry.ts`                  | **11**     | `SPECS_BY_KIND` is the only exhaustive "every spec" handle in TypeScript; the new per-spec sequence guard iterates it. **Not** `ALL_SPECS` — see Problem §5                                                                                                                                                          |
| `packages/python/tests/test_emitter/test_field_collection.py` | **21**     | 21's per-rule unit tests over `collect_fields`; migration step 3 repoints exactly that loop, so two of them change. **Conditional — depends on merge order:** if 21 does not land, this row disappears and step 3 becomes two edits, at `nodes.py:174` and `data.py:105`, with `data.py` re-entering the table above |

### Not touched, deliberately

- `packages/typescript/src/emitter/to-data.test.ts` (150) — `emits keys in canonical order`
  (`:34-42`) and `merges extras after ordered keys` (`:44-52`) are both order-sensitive and both stay
  **green and unedited**. The first is the one-model prototype of the new guard; the second still
  holds because extras still append after the ordered keys under `declared`. Leaving them untouched
  keeps an independent oracle across the change.
- `packages/typescript/src/models/conformance.test.ts` (191) and
  `packages/python/tests/test_schema/test_conformance.py` (203) — assert spec key _sets_ against the
  generated schema; neither reads `order`. Both are rewritten by **11**, not by this.
- `packages/typescript/src/index.ts` (203) and `packages/python/src/ghagen/__init__.py` —
  `OrderMode` is not exported from either (verified: the only repo-wide Python occurrence of the
  name is the cross-reference at `spec.py:31`), and the TypeDoc entry points are the
  `_docs-api-*.ts` facades (`docs/astro.config.mjs:126-182`). The published surface does not move.
- `packages/typescript/src/models/index`-level factory bodies — **22**'s territory.
  `DefaultsRunModel`'s absence from `index.ts:31-68` is **11**'s fix (`11` §Scope boundaries vs siblings), not this one.

### Modified — docs

| Path                             | Lines | Role in this proposal                                                                                                                                                                                                                                                                   |
| -------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/python/CONTEXT.md`     | 114   | **ModelSpec** glossary entry (`:40-44`) — uncontested, 22 states "`packages/python/CONTEXT.md`: no change" (`22` §Migration plan); **OrderMode** glossary entry (`:46-47`)                                                                                                              |
| `packages/typescript/CONTEXT.md` | 119   | **OrderMode** glossary entry (`:48-49`); one **Surface notes** bullet appended after the final bullet (the `src/paths.ts` bullet, `:113`). **Ceded:** `:40-46` (**ModelSpec**) to **22** and `:43` (extras placement) to **20** — see [ADR / CONTEXT.md impact](#adr--contextmd-impact) |

## Problem

`ModelSpec` writes the same key sequence down twice — three times in Python — and only the
_set_ relation between the copies is tested.

**1. `order` is a verbatim restatement of the key map's declaration order. Verified mechanically,
in both ports, three independent ways.**

Two throwaway sweeps enumerated every live `ModelSpec` in both ports and compared `order` against
`tuple(yaml_keys.values())` / `Object.values(fieldMap)` **as sequences** — Python by runtime
introspection of the imported model modules, TypeScript by a `tsx` pass importing the real modules
and reading the live spec objects:

| Port       | Spec literals | Explicit-order specs | Sequence mismatches | Restated key names |
| ---------- | ------------- | -------------------- | ------------------- | ------------------ |
| Python     | **29** (30)   | **28** (29)          | **0**               | **141** (135)      |
| TypeScript | **30** (27)   | **29** (26)          | **0**               | **147** (134)      |

Post-sibling first, `e7a972c` in parentheses. **59 spec literals, 288 restated key names** on the
tree this lands on. The deltas: **20** deletes `JOB_OUTPUT_SPEC` (`job.py:48-51`, 2 keys) and its
`JobOutput` model (`:169-175`); **11** adds three TypeScript specs (`workflowCallInput` /
`Output` / `Secret`, 8 keys) plus fields on `On` (+8 Py / +2 TS), `PRTrigger` (+2 Py),
`ScheduleTrigger` (+1 Py), `WorkflowDispatchInput` (+1 both), `Permissions` (+3 both) and
`Environment` (+1 both) — **+16 Python / +15 TypeScript key names**, but only **+8 / +13** entries in
an `order` list, because the `On`/`OnInput` additions land on the one alphabetical spec
(`trigger.py:118`, `trigger.ts:463`), which has no `order` list to restate them in.

Per file, post-{11,20}:

| Module           | Py specs / explicit / keys | TS specs / explicit / keys | Mismatches |
| ---------------- | -------------------------- | -------------------------- | ---------- |
| `action`         | 7 / 7 / 32                 | 7 / 7 / 32                 | 0          |
| `container`      | 1 / 1 / 6                  | 2 / 2 / 12                 | 0          |
| `image_snapshot` | 1 / 1 / 2                  | 1 / 1 / 2                  | 0          |
| `job`            | 7 / 7 / 33                 | 7 / 7 / 33                 | 0          |
| `permissions`    | 1 / 1 / 16                 | 1 / 1 / 16                 | 0          |
| `step`           | 1 / 1 / 11                 | 1 / 1 / 11                 | 0          |
| `trigger`        | 10 / 9 / 33                | 10 / 9 / 33                | 0          |
| `workflow`       | 1 / 1 / 8                  | 1 / 1 / 8                  | 0          |

The one non-explicit spec in each port is `ON_SPEC` — Python `trigger.py:118` `order=None`,
TS `trigger.ts:463` `order: { kind: "alphabetical" }`. Every other row is a sequence-exact copy.

**Zero mismatches is a property of `e7a972c`, not of the tree this sweeps.** Each field 11 adds must
be inserted into _both_ `yaml_keys`/`fieldMap` **and** `order` at the same index, and nothing checks
that it was — which is precisely the drift documented in §2. Migration step 0 re-runs the sweep and
treats any non-zero mismatch as a stop-and-report, not a fixup.

**A stronger TypeScript proof.** Building all 27 (`e7a972c`) specs through the real `buildModel`
supplying every field in **reverse declaration order**, then running the real `toData`: the emitted
key sequence equalled `fieldMap` declaration order for all 26 explicit specs and sorted order for
`ON_SPEC`. **27/27, zero mismatches.** This establishes both the redundancy and that the sequence
guard proposed below is green on landing.

**Container is the only structural asymmetry, and it is the one freedom the deletion removes.**
TS `container.ts` counts two specs because `CONTAINER_SPEC` (`:38-42`) and `SERVICE_SPEC`
(`:45-49`) both reference one shared `CONTAINER_ORDER` const (`:35`) over one shared
`CONTAINER_FIELD_MAP` (`:26-33`); Python's `Service` inherits `Container.SPEC`
(`container.py:36`) — the same object, not a copy. Today the two _could_ be given different
orders over the same field map; afterwards they cannot without splitting the const.
`container.test.ts:52-59` asserts nobody wants that.

Python restates the sequence a **third** time. The field-collection loop builds its pre-order dict
by iterating Pydantic field declaration order, not the spec:

```python
# packages/python/src/ghagen/emitter/nodes.py:173-184 (at e7a972c; post-21 this body lives
# in collect_fields, hoisted beside order_entries)
raw: dict[str, Any] = {}
for field_name in type(model).model_fields:      # ← Pydantic class field order
    ...
    raw[spec.yaml_keys.get(field_name, field_name)] = value
```

The same sweep confirmed that for all **31** concrete `GhagenModel` subclasses carrying a `SPEC`,
`[f for f in model_fields if f not in _META_FIELDS]` equals `list(SPEC.yaml_keys)` **as a
sequence** — zero divergences. So today: Pydantic field order == `yaml_keys` order == `order`
sequence, three copies, agreeing by hand.

**On "30" versus "31", settled.** There are **32** concrete `GhagenModel` subclasses; **31** carry a
`SPEC` (`Document` is the sole one that does not); those 31 `SPEC` attributes resolve to **30
distinct spec objects**, because `Service` inherits `Container`'s and it is literally the same
object. This document counts **spec literals** (30 at `e7a972c`);
[21](./21-hoist-field-collection-loop.md) counts **models** (31, `21` §Problem). Both are correct about
different things.

Cost in source, measured at `e7a972c`: **103** physical lines of `order=` in Python (by AST, over
the `keyword` node's full extent) and **108** physical lines of `order:` in TypeScript (27 property
blocks, eight of them multi-line — `permissions.ts:58` alone is 18 lines and `job.ts:367` is 25),
plus the `CONTAINER_ORDER` const — **212 lines, 269 restated names**. The sibling deltas move both
figures; step 0 re-measures.

**2. Only the _set_ relation is tested. The sequence relation is entirely unguarded — live.**

Python `tests/test_models/test_spec.py:59-72`:

```python
def test_explicit_order_is_complete() -> None:
    for model in _all_model_classes():
        if model.SPEC.order is None:
            continue
        order = set(model.SPEC.order)
        keys = set(model.SPEC.yaml_keys.values())
        assert order == keys, ...
```

TypeScript `src/models/spec.test.ts:109-115`:

```ts
it.each(ALL_SPECS)("$kind: explicit order is complete (== fieldMap values)", (spec) => {
  if (spec.order.kind !== "explicit") return;
  const emitted = new Set(Object.values(spec.fieldMap));
  expect(new Set(spec.order.keys)).toEqual(emitted); // ← sets, not sequences
});
```

**Correction to the survey brief.** The brief predicted that adding a field and forgetting to add
it to `order` would silently tail-sort the new key. It does **not** — the set assertion catches
that case. Adding `"hostname": "hostname"` to `CONTAINER_SPEC.yaml_keys` (plus the Pydantic field)
without touching `order`:

```
FAILED packages/python/tests/test_models/test_spec.py::test_explicit_order_is_complete
AssertionError: Container: order {...} must equal emitted keys {..., 'hostname', ...}
```

The live defect is **positional**, not membership. Add the same field in the _middle_ of
`yaml_keys` and at the _tail_ of `order` — the natural thing to do, since appending to a tuple is
easier than splicing into it — and everything passes while the emitted YAML contradicts how the
source reads:

```
$ uv run pytest packages/python/tests/test_models/test_spec.py -q
5 passed
$ to_data(Container(image='i', hostname='h', env={'A':'B'}, options='o'))
['image', 'env', 'options', 'hostname']     # 'hostname' declared 4th, emitted last
```

The TypeScript port is identical. The equivalent edit to `container.ts` leaves
`spec.test.ts` + `container.test.ts` green (85 tests passed), and a spec built through the real
`buildModel` shows the split directly:

```
data (insertion order == fieldMap):  [ 'image', 'hostname', 'options' ]
emitted (== spec.order.keys):        [ 'image', 'options', 'hostname' ]
```

`buildYamlData` (`_base.ts:315-365`) writes `yamlData` by iterating `Object.entries(spec.fieldMap)`
(`:322`), so `model.data` already carries declaration order. `orderedEntries`
(`yaml-writer.ts:207-210`) then throws it away and re-derives the sequence from `spec.order.keys`.
The `fieldMap` reading is the one a maintainer trusts; the `order` array is the one that ships.

The round-1 plan claimed this was already solved — `docs/architecture-deepening-plan.md:107`:
"add a field = one edit in one file; ordering cannot drift from the field map". It is two
edits in one file, and the drift is set-guarded only.

**3. `order`'s entire behavioural footprint is three synthetic unit tests.**

Neutralising `order` and emitting in declaration order — Python `order_entries`' explicit branch
replaced by `list(raw.items()) + list(extras.items())`, TS `orderedEntries`' explicit branch by
`dataKeys.map(...)` — then running the full suites at `e7a972c` (baseline pytest 562, vitest 515):

| Port       | Result                   | Failures                                                                                                      |
| ---------- | ------------------------ | ------------------------------------------------------------------------------------------------------------- |
| Python     | **560 passed, 2 failed** | `test_yaml_writer.py::test_order_entries_explicit`, `::test_order_entries_explicit_remaining_insertion_order` |
| TypeScript | **514 passed, 1 failed** | `yaml-writer.test.ts > key ordering > orders keys according to keyOrder, then remaining in insertion order`   |

All three failures feed deliberately scrambled dicts into the ordering function directly; none goes
through a factory. Every model test, every emitter test, both conformance sweeps, and the ten shared
golden YAML fixtures (`fixtures/expected/*.yml`, read by
`packages/python/tests/test_integration/test_snapshots.py:39` and
`packages/typescript/src/integration/snapshots.test.ts`) are **byte-identical** without `order`.
212 lines and 269 restated names buy exactly three assertions about a function that would not exist.

**4. Weaker on the TS side than the set test suggests — live, and it forces a hard order edge.**
`ModelKind` declares 27 members (`_base.ts:160-187`, including `"imageSnapshot"` at `:181`), but the
hand-maintained `ALL_KINDS` (`spec.test.ts:66-93`) and `ALL_SPECS` (`spec.test.ts:36-63`) each list
26 and both omit the image snapshot. `spec.test.ts:96-100` ("every ModelKind has exactly one spec")
therefore passes by comparing two lists that drifted together. Breaking `IMAGE_SNAPSHOT_SPEC.order`
outright — `keys: ["version"]`, dropping `image-name` — leaves `spec.test.ts` and
`conformance.test.ts` green (91 tests passed). Python does not have this hole: `_all_model_classes()`
(`test_spec.py:21-32`) derives the list from `__subclasses__()`.

This is not merely an aside. **The new sequence guard needs an exhaustive "every spec" handle, and
in TypeScript `ALL_SPECS` is not one.** A guard built on it would be non-exhaustive by exactly the
defect it exists to diagnose. [11](./11-shared-spec-surface-table.md) creates
`packages/typescript/src/models/registry.ts`, whose `SPECS_BY_KIND` is exhaustive by construction —
so `11 → 10` is a **hard order edge**, declared in the header and in
[Scope boundaries](#risks--alternatives).

Carry 11's caveat verbatim, because the guard must not be assumed stronger than it is:
`satisfies Record<ModelKind, ModelSpec>` catches a **missing key** (`TS1360`, naming the key) and an
**excess key** (`TS2353`), but produces **no error at all** when a registry key disagrees with the
bound spec's own `kind` (`11` §(c) An exhaustive-by-construction spec registry in TypeScript). That is why 11 also keeps a runtime assertion
(`11` §(c) An exhaustive-by-construction spec registry in TypeScript), and why the sequence guard keys off the spec objects rather than the registry keys.

**5. `fieldMap` is type-linked to the schema; `order` is linked to nothing.** Eight TS field maps —
`action.ts:246`, `container.ts:33`, `image-snapshot.ts:25`, `job.ts:149`, `job.ts:259`,
`permissions.ts:57`, `step.ts:51`, `workflow.ts:60` — close with a `satisfies` clause tying them to
the generated schema types; `trigger.ts` is the one model file with none. That is a compiler tie on
eight of the 27 field maps, over seven of the eight model files. `order` is a bare
`readonly string[]` / `tuple[str, ...]` everywhere, tied to nothing, in all 27. Deleting it moves
the emission sequence _into_ the structure that already has a compiler tie where any tie exists at
all, instead of beside it.

## Current interface

- Python `ModelSpec` (`spec.py:39-41`): `yaml_keys`, `order: tuple[str, ...] | None = field(default_factory=tuple)`
  (a tuple = explicit, `None` = alphabetical), `present_null_when_empty`. **Post-09 a fourth field,
  `patterns`, joins them** (`09` §Modified — unconditional, `09` §(c) One home for the version grammar: a fourth declarative ModelSpec field, bound by a shared value table).
- TS `ModelSpec` (`spec.ts:57-91`): `kind`, `fieldMap`, `order: OrderMode`
  (`{ kind: "explicit"; keys }` | `{ kind: "alphabetical" }`, `:38-40`), `wrap`, `dynamicKeys`,
  `extrasPlacement`, `presentNullWhenEmpty`. **On the tree this lands on, `extrasPlacement` is
  already gone** (deleted by [20](./20-delete-callerless-pin-spec-surface.md), `20` §Modified — TypeScript source) and
  `patterns?` has been added by [09](./09-construction-time-validation-parity.md) — expect a
  four-declarative-field spec: `wrap`, `dynamicKeys`, `patterns`, `presentNullWhenEmpty`, plus
  `kind`, `fieldMap` and `order`.
- Consumers: Python `order_entries` (`nodes.py:52-84`), called from `nodes.py:193` and
  `data.py:120`; TS `orderedEntries` (`yaml-writer.ts:189-215`) with `orderExplicit`
  (`:221-226`), called from `yaml-writer.ts:73` and `:311`.

To add one field a maintainer must edit the key map **and** `order`, keep them in the same
sequence with nothing checking that they are, and — in Python — keep the Pydantic field list in
that sequence too. To read what a model emits they must cross-reference two lists in two shapes
(a `dict`/object literal and a flat tuple/array) and know that the second wins.

## Proposed interface

`order` stops naming keys. The key map's declaration order _is_ the emission order.

```python
# packages/python/src/ghagen/models/spec.py
OrderMode = Literal["declared", "alphabetical"]

@dataclass(frozen=True)
class ModelSpec:
    yaml_keys: Mapping[str, str]
    order: OrderMode = "declared"
    present_null_when_empty: frozenset[str] = frozenset()
    # patterns: Mapping[str, re.Pattern[str]]  — added by 09, unchanged here
```

```ts
// packages/typescript/src/models/spec.ts
export type OrderMode = "declared" | "alphabetical";

export interface ModelSpec {
  readonly kind: ModelKind;
  readonly fieldMap: Readonly<Record<string, string>>;
  readonly order?: OrderMode; // default "declared"
  readonly wrap?: Readonly<Record<string, WrapRule>>;
  readonly dynamicKeys?: boolean;
  readonly patterns?: Readonly<Record<string, RegExp>>; // added by 09, unchanged here
  readonly presentNullWhenEmpty?: readonly string[];
}
```

Every spec literal drops its `order` entirely; `ON_SPEC` keeps `order: "alphabetical"` in both
ports. `CONTAINER_ORDER` (`container.ts:35`) disappears.

**What changed versus 06, precisely.** Proposal 06 introduced `OrderMode` to fix a real divergence:
"empty `order`" meant _insertion order_ in the TS Emitter and _alphabetical_ in the Python one, and
the `on()` factory pre-sorted to paper over it. That fix stands untouched — `alphabetical` remains a
declared mode, owned by the Emitter, identical in both ports, and `ON_SPEC` is still its sole user
in each. 06 also established `dynamicKeys`, `presentNullWhenEmpty`, and the "every factory builds
through `buildModel`" invariant; all three are load-bearing here and are kept.

This proposal narrows exactly one thing, and it is a reversal of a shape 06 chose deliberately:

- 06 specified the union as `{ kind: "explicit"; keys } | { kind: "alphabetical" }`
  (`06:119-121`), and Python's mirror as `order: tuple[str, ...] | None = ()` (`06:237`) — where the
  **`()` default is "explicit with no keys"**, not "alphabetical". Both the `keys` payload and the
  `()` default are retired here.
- **Open — Phase 3 decision:** reversing 06's `OrderMode` union shape (`06:119-121`, `06:237`) less
  than one round after it landed. The friction is measured above — 288 restated key names across 59
  literals post-siblings, zero of them guarded as sequences — but 06 is recent, deliberate, and the
  reversal is not free: `alphabetical` survives, so the _mode_ concept 06 introduced is affirmed
  while its payload is deleted. This document does not decide it.
- **Open — Phase 3 decision:** `06:318` records "**Risk:** `extrasPlacement`/`dynamicKeys` add spec
  surface few models use. **Accepted.**" That acceptance is the same judgement this proposal
  contests for `order`'s payload — a declared seam kept against a hypothetical adapter. Note that
  [20](./20-delete-callerless-pin-spec-surface.md) independently reopens the identical line for
  `extrasPlacement`, with evidence this proposal endorses rather than duplicates: `06:155-159` named
  `On` as the intended adapter, and `ON_SPEC` shipped `alphabetical` (`trigger.ts:463`), under which
  the field is moot **by its own documentation** (`spec.ts:81-82`). `dynamicKeys` is not contested
  by either proposal — it has a real setter (`MATRIX_SPEC`, `job.ts:79`). **`extrasPlacement` is
  20's in full; this proposal does not claim it and does not need it.** It is already deleted on the
  tree this lands on.

**How the Emitter reads declaration order.**

TypeScript — `buildYamlData` (`_base.ts:315-365`) already populates `yamlData` by iterating
`Object.entries(spec.fieldMap)` (`:322`), so `model.data`'s insertion order is `fieldMap`
declaration order by construction; the dynamic-key passthrough (`_base.ts:352-362`) appends after
it. `orderedEntries` collapses to:

```ts
function orderedEntries(model: Model): [string, unknown][] {
  const { data } = model;
  const extras = model.meta.extras ?? {};
  if (model.spec.order === "alphabetical") {
    const all = [...new Set([...Object.keys(data), ...Object.keys(extras)])].sort();
    return all.map((k) => [k, k in data ? data[k] : extras[k]]);
  }
  return [...Object.entries(data), ...Object.entries(extras)];
}
```

`orderExplicit` is deleted. This is byte-identical to today for every spec: with
`orderKeys === Object.values(fieldMap)` and `dataKeys` already in that order,
`orderExplicit(dataKeys, orderKeys)` returns `dataKeys` unchanged, and the dynamic/extra remainder
was already appended in insertion order.

Python — `order_entries` keeps only its `alphabetical` branch (`nodes.py:70-72`), the rest becoming
`list(raw.items()) + list(extras.items())`. The field-collection loop moves from
`for field_name in type(model).model_fields` to `for field_name in spec.yaml_keys`, so the spec —
not the Pydantic class — is the single declaration. That substitution is safe today by construction
(`test_spec.py:44-48` already asserts `set(SPEC.yaml_keys) == set(model_fields) - _META_FIELDS`) and
provably invisible today (with a complete explicit `order`, `raw`'s insertion order is never
observed — 21 measured this directly as probe P6, "**562 passed**", `21` §The probe: make the two passes disagree, watch the suite pass). It is exactly that
invisibility the new guard closes.

**Why declaration order is guaranteed.**

- Python: `dict` preserves insertion order as a language guarantee since 3.7, and a dict _literal_
  inserts in source order. The project floor is 3.11 (`pyproject.toml:7`,
  `requires-python = ">=3.11"`).
- JavaScript: `OrdinaryOwnPropertyKeys` yields integer-index keys first in ascending numeric order,
  _then_ string keys in property-creation order. Every YAML key produced from a `fieldMap` is a
  string key — the sweep checked all 27 TS field maps and all 30 Python key maps against
  `/^(0|[1-9]\d*)$/` and found **zero** integer-like values (they are identifiers, `kebab-case`, or
  `snake_case`). The only channels that could ever carry one are `dynamicKeys` (set by
  `MATRIX_SPEC` alone, `job.ts:79`) and `meta.extras`, both user-supplied — and both are _already_
  ordered by `Object.keys()` today (`yaml-writer.ts:192-193, 211-213`). The caveat is pre-existing
  and unchanged in scope, not introduced. Python has no such caveat at all, which is the honest
  asymmetry to record in the TS CONTEXT.md surface notes.
- Every `yaml_keys` / `fieldMap` in production is a dict/object literal or a named literal const —
  no `**` merge, no comprehension, no `Object.fromEntries`, no spread — so "declaration order" is
  always source order, not a computed order.
- Nothing mutates `data` into a new order after construction. Production has exactly two
  `new Model(` sites: `clone()` (`_base.ts:233`), which rebuilds via `cloneRecord`
  (`_base.ts:508-513`) using `Object.entries` — order-preserving — and `buildModel`
  (`_base.ts:371-377`, the `new Model(` at `:376`). There are exactly **two** runtime writes into an
  existing `model.data`: `pin/sites.ts:48` (`this.model.data[this.field] = wrapped`) and
  `emitter/yaml-writer.ts:48` (`node.data["run"] = dedentScript(...)`, guarded at `:47` on the key
  already being a string). Both assign to an **already-present** key, which does not move it in JS
  or in Python.

`OrderMode` stays internal to `spec.ts` / `spec.py` exactly as today — it is not in
`packages/typescript/src/index.ts`'s type export list (`:31-68`; `ModelSpec` at `:38`), nor in
any TypeDoc entry point (`docs/astro.config.mjs:126-182` reference only the `_docs-api-*.ts`
facades), nor in `packages/python/src/ghagen/__init__.py`. A string union needs no import to
satisfy.

## What sits behind the seam

`ModelSpec` remains the single home for a model type's emission surface; it just stops saying the
same thing twice. The key map keeps the field→key fact _and_ takes the sequence fact, which it was
already carrying implicitly in both ports — provably so, since neither Emitter's output changes.
The Emitter's ordering module shrinks from two functions and four branches to one function and two
branches, and the one remaining declaration (`alphabetical`) is a genuine choice rather than a
restatement.

**Deletion test, applied to `order`.** Delete it and does complexity reappear across N callers?
No — the ports emit identically (560/2 and 514/1 at `e7a972c`, with the three failures being direct
unit tests of the deleted function, and all ten shared golden fixtures unmoved). It is a
pass-through: it restates what `fieldMap` / `yaml_keys` already says, and the restatement is not
even guarded. Contrast `alphabetical`, which survives: delete it and `On` must either regain a
hand-written 27-key order or the `on()` factory must regain the pre-sort that 06 removed —
complexity that genuinely reappears. One mode earns its keep; the other does not.

**Deletion test, applied to what is added.** Nothing is added. `OrderMode` narrows from a
two-variant discriminated union carrying a payload to a two-value string union; the interface a
caller must know shrinks by 288 names.

## Migration plan

Pre-1.0; clean break. This must land atomically — the spec type and every literal compile together.
**This proposal runs solo and last, in place on the merged tree, with no worktree of its own.**
Nothing downstream may trust a number printed in this document.

0. **Re-measure before editing anything.** Re-run both sweeps against the merged tree and record:
   spec-literal count per port, explicit-order count, **sequence mismatches**, restated key names,
   and physical `order=` / `order:` line counts. Expected: **Python 29 / 28 / 0 / 141, TypeScript
   30 / 29 / 0 / 147**. Re-run the integer-like-key check and the "every key map is a literal" check.
   Re-enumerate `new Model(` sites and writes into an existing `model.data` (two of each at
   `e7a972c`). **A non-zero mismatch count is a stop-and-report, not a fixup** — it means a sibling
   introduced exactly the drift this proposal exists to make impossible, and that finding is worth
   more than the sweep. Also re-read the current `fixtures/expected/` inventory: post-13 it is
   **16** `.yml` goldens, not ten, and post-12 `comments.yml:3` differs from `e7a972c`.
1. Change `ModelSpec.order` in both ports: Python `spec.py:40` → `order: OrderMode = "declared"`;
   TS `spec.ts` → `readonly order?: OrderMode` and `OrderMode` to a string union. Fix the stale
   module docstring at `spec.py:6` (`GhagenModel.to_commented_map` no longer exists — ADR-0001
   amendment, `docs/adr/0001-document-serialization-seam.md:34`) and rewrite the `order` attribute
   docs at `spec.py:25-32` and `spec.ts:26-37`. **Do not touch `extrasPlacement` or `patterns`** —
   the first is already deleted by 20, the second is 09's.
2. Rewrite the Emitters: `order_entries` (`nodes.py:52-84`) keeps only the alphabetical branch and
   loses the explicit clause of its docstring (`:66-68`); `orderedEntries` (`yaml-writer.ts:189-215`)
   likewise, `orderExplicit` (`:221-226`) is deleted, and the function doc (`:178-188`) is rewritten
   — post-20 that doc block has already lost its `extrasPlacement` clauses (`:180`, `:185-187`) and
   the `withinOrder` branch (`:202-205`) is gone, so this is **one** branch to remove.
3. **Repoint Python's field collection at the spec. This is five edits inside `collect_fields`, not
   one.** Post-21 the loop lives once, in `nodes.py` beside `order_entries` (`21` §Proposed interface,
   `21` §Migration plan); 21's own text calls it "exactly one edit inside `collect_fields`" (`21` §Test impact) and
   that undercounts. Switching the loop head to `for field_name in spec.yaml_keys:` also:
   - **(a)** makes the `_META_FIELDS` skip **structurally dead**. A meta field can never appear in
     `yaml_keys` — guaranteed by `test_spec_covers_exactly_the_content_fields`
     (`test_spec.py:44-48`), which asserts `set(SPEC.yaml_keys) == set(model_fields) - _META_FIELDS`
     for every model. Delete the skip; do not leave a guard that cannot fire.
   - **(b)** makes `spec.yaml_keys.get(field_name, field_name)` **unreachable**. Left in place it is
     dead code; worse, it silently redefines the unmapped-field case from "emit under the field
     name" to "drop". Replace it with `spec.yaml_keys[field_name]`, which is total by (a)'s same
     guarantee.
   - **(c)** invalidates **rules 1 and 4** of 21's `collect_fields` docstring contract (`21` §Proposed interface,
     `21` §What sits behind the seam) and its closing "Returns … in Pydantic field-declaration order" line, which becomes
     "in `spec.yaml_keys` declaration order" (`21` §Scope boundaries vs siblings). The docstring rewrite is part of this diff.
   - **(d)** requires rewriting two tests in 21's new
     `packages/python/tests/test_emitter/test_field_collection.py`. The **meta-field** test does not
     fail — it becomes **unfalsifiable**, passing for a structural reason after the guard it was
     written to exercise is gone; it must be deleted or re-sited as an assertion about `yaml_keys`.
     The **rule-4 unaliased-field** test genuinely **inverts**: a field absent from `yaml_keys` is no
     longer emitted under its own name, it is dropped.
   - **(e)** `collect_fields` must take (or read) the spec for its loop head; 21 already threads
     `spec` at both call sites (`21` §Proposed interface).
4. **Dispose of `_META_FIELDS`.** Step 3 removes both of its production readers (`nodes.py:175`,
   `data.py:106`), leaving the constant at `nodes.py:30` with **zero production consumers** and one
   surviving reference — a test import at `test_spec.py:16,36`, in the very test that certifies its
   redundancy. Its role would change silently from _enforcement_ to _assertion input_, and it would
   be a serialization-policy constant sitting in the emitter with no emitter use.
   **Decision: relocate it to `packages/python/src/ghagen/models/_base.py`, immediately beside the
   four `exclude=True` field declarations it enumerates (`:100-103`).** That is where the fact
   actually lives, it keeps the import direction correct (nothing in `models/` gains an `emitter/`
   import; `emitter/` simply stops needing it), and `test_spec.py:16` then imports it from its
   declaration site. 21 anticipated exactly this move and deferred it here: "natural _after_ 10
   lands, as a pure move with no logic change — noted, not proposed here" (`21` §Risks & alternatives).
5. Sweep all **59** spec literals (29 Python, 30 TypeScript — re-confirmed by step 0): delete
   `order=` / `order:`; set `order="alphabetical"` / `order: "alphabetical"` on the two `ON_SPEC`s.
   Delete `CONTAINER_ORDER` (`container.ts:35`) and inline nothing in its place. Mechanical — a
   scripted pass, reviewed against step 0's table.
6. Rewrite the tests listed under **Test impact**, including the three ad-hoc `order: []` literals in
   `_base.test.ts` (`:179`, `:192`, `:202`) — re-anchor by test name, because 09 replaces `:188-196`.
7. Gates: `scripts/test.sh all`, `scripts/typecheck.sh all`, `scripts/lint.sh all`,
   `uv run ghagen check-synced`, `uv run ghagen deps check-synced`,
   `PYTHONPATH=scripts uv run python -m ghagen_schema check`. Note that `scripts/lint.sh` defaults to
   the `all` scope (`scripts/lint.sh:6`) and the `ts`/`all` scopes pull in the `docs/` npm toolchain
   (`:20-26`), which needs `npm ci --prefix docs`; `scripts/lint.sh py` runs ruff only.
   The success criterion is stated in advance and is absolute: **zero** byte changes to
   `fixtures/expected/*.yml` and to `.github/workflows/*.yml` under `check-synced` — measured
   against **the merged tree at land time**, not against `e7a972c`. 12 changes
   `fixtures/expected/comments.yml:3` and 13 adds six `header_*.yml` goldens; both land first, and
   both are part of the baseline this proposal must not move. 13 states the same requirement from
   its side (`13` §Risks & alternatives).

## Test impact

**Deleted** (the assertions exist only because `order` exists):

- Python `test_spec.py:51-56` `test_explicit_order_has_no_duplicates` and `:59-72`
  `test_explicit_order_is_complete`.
- Python `test_yaml_writer.py:64-67` `test_order_entries_explicit` and `:70-74`
  `test_order_entries_explicit_remaining_insertion_order`.
- TS `spec.test.ts:102-107` and `:109-115` (the two `order` `it.each` blocks).
- TS `yaml-writer.test.ts:89-99`, which constructs `new Model(JOB_SPEC, {steps, name, "runs-on",
env}, {})` with deliberately scrambled data and relies on `order` to re-sort it. Rewritten to
  build through `job()` and assert emitted order matches `JOB_SPEC.fieldMap` declaration order —
  which is what the test was always trying to express. The `order` parameter of the `simpleModel`
  helper (`yaml-writer.test.ts:17-28`) goes with it, along with its three positional call sites
  (`:102`, `:193`, `:194`).

**Rewritten — the two mode-identity tests, which break under the new union:**

- Python `test_spec.py:75-78` `test_only_on_uses_alphabetical_order` reads
  `m.SPEC.order is None`; it becomes `m.SPEC.order == "alphabetical"`.
- TS `spec.test.ts:123-126` `only the \`on\` spec uses alphabetical order`reads`s.order.kind === "alphabetical"`; it becomes `s.order === "alphabetical"`. Post-11 it also
iterates the registry rather than `ALL_SPECS`.
- Python `test_yaml_writer.py:77-80` `test_order_entries_alphabetical_interleaves_extras`
  constructs `ModelSpec(yaml_keys={}, order=None)`; `order="alphabetical"`. The assertion is
  unchanged — this is the one `order` unit test that survives, because `alphabetical` survives.

**New** — the sequence guard that does not exist today, in both ports: **for every spec**, build a
populated model through the factory/constructor **passing the fields in reverse declaration order**,
and assert `to_data` / `toData` returns keys equal to `list(yaml_keys.values())` /
`Object.values(fieldMap)` — as a _list_, not a set. Today's set assertions cannot express this;
after the change it is the definition, and the test is the regression guard against a future
Emitter regaining a re-sort.

- **TypeScript: iterate `SPECS_BY_KIND` from `packages/typescript/src/models/registry.ts`**
  (created by 11). Not `ALL_SPECS` — see Problem §4. The prototype already exists for one model:
  `to-data.test.ts:34-42` (`step({ timeoutMinutes, name, uses, id })` →
  `["id","name","uses","timeout-minutes"]`); the new test generalises it across all 30.
- **Python: iterate `_all_model_classes()`** (`test_spec.py:21-32`), which is already exhaustive by
  `__subclasses__()` and which 11 hardens further with a package walk. This is the Python peer
  `to-data.test.ts:34-42` never had.

**New** — `fieldMap` / `yaml_keys` **values** must be unique. Two fields mapping to one YAML key
silently drop one of them in `buildYamlData` (`_base.ts:349`) and in `collect_fields`, and nothing
checks it today: the set comparison at `test_spec.py:68-70` and `spec.test.ts:113-114` is satisfied
by a duplicate. Verified: zero duplicates exist today in either port, so the guard is green on
landing. This replaces the deleted `no-duplicates` assertions with a strictly stronger one about the
surviving structure.

**Rewritten** — TS `container.test.ts:52-59`, whose `expect(c.spec.order).toEqual(s.spec.order)`
becomes vacuous (both `"declared"`), asserts `c.spec.fieldMap === s.spec.fieldMap` instead — which
is the actual shared-shape claim, and which also pins the `CONTAINER_FIELD_MAP` sharing that is now
the only thing making the two specs agree. TS `_base.test.ts:89` (test name) and Python
`test_serialize.py:48` (docstring) need naming updates only; `_base.test.ts:179,192,202` drop their
stale `order: []` literals.

**Changed by step 3** — two tests in `packages/python/tests/test_emitter/test_field_collection.py`
(21's new file): the meta-field rule test becomes unfalsifiable and is deleted or re-sited; the
rule-4 unaliased-field test inverts. See migration step 3(d).

**Unchanged and deliberately so:** `to-data.test.ts:34-42` and `:44-52` (both order-sensitive, both
stay green — an independent oracle across the change); `models/conformance.test.ts` and
`test_schema/test_conformance.py` (set assertions against the schema, no `order` reader).

Net counts must be re-derived at land time — the baselines move with 11, 13, 20 and 21. At
`e7a972c` the shape is: pytest 562 → 562 (−4, +4, the two new guards run as loops rather than
parametrised cases); vitest 515 → ~514 (−3, +2). Coverage of the emitted-key _sequence_ goes from
zero specs to all 59.

## Risks & alternatives

- **Alternative: keep `order` and upgrade the self-consistency tests from set to sequence
  equality.** This closes the drift with a two-line change. Rejected: it makes the duplication
  permanent and mandatory — 212 lines and 288 names retained forever to satisfy a test that only
  asserts they were copied correctly. The deletion test says the module is a pass-through; a
  tighter guard on a pass-through is still a pass-through.
- **Alternative: keep 06's `{ kind: "explicit" }` object variant, minus `keys`.** Considered.
  Once `keys` is gone the union is two nullary variants, and `"explicit"` no longer means anything —
  the whole point is that nothing is stated explicitly. `"declared" | "alphabetical"` says what the
  modes are, reads identically in both ports, and removes the `.kind` indirection from the Emitter.
  If minimal churn to 06's shape is preferred,
  `{ kind: "declared" } | { kind: "alphabetical" }` is a drop-in; the substantive change (deleting
  `keys`) is unaffected either way.
- **Risk: `fieldMap` declaration order becomes load-bearing, so reordering it silently changes
  YAML.** Real, and the honest cost of the change. Today a `fieldMap` can be reshuffled with no
  effect; afterwards it cannot.

  **The golden fixtures do not back-stop this, and an earlier draft of this proposal claimed they
  did. That claim is withdrawn.** Traced through all ten `fixtures/expected/*.yml` goldens, the four
  `check-synced` workflows and both generated actions:

  | Spec               | Keys | Max observed simultaneously       |
  | ------------------ | ---- | --------------------------------- |
  | `JOB_SPEC`         | 20   | 8                                 |
  | `ON_SPEC`          | 27   | 4 (and it is alphabetical anyway) |
  | `PERMISSIONS_SPEC` | 13   | 3                                 |
  | `STEP_SPEC`        | 11   | 4                                 |
  | `DOCKER_RUNS_SPEC` | 9    | 7                                 |

  Worse in aggregate: **8 of 30 Python specs have zero golden-fixture coverage at all**
  (`DEFAULTS_SPEC`, `DEFAULTS_RUN_SPEC`, `ENVIRONMENT_SPEC`, `JOB_OUTPUT_SPEC`, `WORKFLOW_CALL_SPEC`,
  `WORKFLOW_CALL_INPUT_SPEC`, `WORKFLOW_CALL_OUTPUT_SPEC`, `WORKFLOW_CALL_SECRET_SPEC` — seven of
  them also invisible to `check-synced`); **11 of 30 never emit two or more keys anywhere**, so no
  ordering is observable for them at all; and only **8 of 30** have every key exercised. Post-20
  `JOB_OUTPUT_SPEC` is deleted; post-11 the three new TypeScript `workflowCall*` specs join the
  zero-coverage set; post-13 the golden set grows to 16 but the six additions are header fixtures
  over minimal workflows and move none of these figures materially. A zero-byte delta is a
  **necessary** acceptance criterion for the migration and nowhere near a sufficient regression
  guard.

  **What actually back-stops it, in order of strength:**
  1. **The new per-spec sequence guard**, in both ports, over an exhaustive spec handle
     (`SPECS_BY_KIND` in TypeScript, `_all_model_classes()` in Python). It is _constructive_ — it
     builds each model with every field supplied in reverse declaration order — so it observes the
     full key sequence of **all 59 specs**, including the ones with no fixture at all. It is the
     only mechanism in the repo that sees them.
  2. **The `fieldMap` / `yaml_keys` value-uniqueness guard**, which closes the one silent-drop
     failure mode the change makes structural.
  3. **`satisfies Record<keyof XInput, keyof SchemaX>`** on eight TypeScript field maps — a compiler
     tie on _membership_, not order, but it makes a field-map edit visible to `tsc` where today it
     is visible to nothing.
  4. The goldens and `check-synced`, as the byte oracle for the migration being a no-op — used for
     what they are, not as the ordering guard.

  Note this is not a new class of hazard — it is the same hazard `order` has today, relocated to the
  structure a maintainer is already looking at, and reduced from two places that can disagree to one
  that cannot.

- **Risk: JS integer-like key ordering.** Bounded and pre-existing. Zero integer-like keys exist in
  any field map in either port (checked mechanically); the only paths that could carry one —
  `dynamicKeys` on `MATRIX_SPEC` and `meta.extras` — already flow through `Object.keys()` today, so
  their behaviour is unchanged. Worth one sentence in the TS CONTEXT.md surface notes as a
  Python/TS asymmetry.
- **Risk: a future model wants emission order ≠ declaration order.** The answer is to reorder the
  field map, which is where a reader looks anyway. If a model genuinely cannot (e.g. a field map
  generated rather than written), `alphabetical` is still available, and a third mode can be added
  then — one adapter is a hypothetical seam; there is not a second today.
- **Risk: `CONTAINER_SPEC` / `SERVICE_SPEC` lose an unused degree of freedom.** They share one
  `CONTAINER_FIELD_MAP` (`container.ts:26-33`) and one `CONTAINER_ORDER` (`:35`); Python's `Service`
  inherits `Container.SPEC` outright (`container.py:36`). Today the two could be given different
  orders over the same field map; afterwards that requires splitting the const. Accepted:
  `container.test.ts:52-59` asserts the opposite is wanted, and the rewritten version pins it more
  precisely (`fieldMap` identity, not `order` equality).

**Scope boundaries vs siblings.** This is the exhaustive sweep: it rewrites every `ModelSpec`
literal in both ports and must compile atomically, so it runs **solo and last**, in place on the
merged tree, after all fifteen siblings have landed and the survey has been re-measured (step 0).
File-level serialisation beyond that is unnecessary — the line regions are disjoint — but the
contacts are real and none of them is with an unlanded proposal:

- **11 — HARD order edge, `11 → 10`.** The TypeScript sequence guard iterates
  `models/registry.ts`'s `SPECS_BY_KIND`; `ALL_SPECS` omits `imageSnapshot` (Problem §4). 11 also
  moves every number in the Problem section, which is why step 0 exists. 11 states the same edge
  from its side (`11` §11 — One shared spec-surface table both ports must satisfy, `11` §Scope boundaries vs siblings).
- **21 — HARD order edge, `21 → 10`.** Migration step 3 edits the `collect_fields` 21 creates and
  the tests 21 adds; 21 sites it in `nodes.py` specifically so `order_entries` and `_META_FIELDS` do
  not move and `data.py` leaves this table (`21` §What sits behind the seam, `21` §Risks & alternatives). 21 touches no TypeScript.
- **20 — lands first; `extrasPlacement` is 20's in full and is not claimed here.** 20 also deletes
  `JOB_OUTPUT_SPEC` (`job.py:48-51`) and `JobOutput` (`:169-175`), and edits three doc-comment
  regions this proposal then rewrites around: `spec.ts:53`, `yaml-writer.ts:180` and `:185-187`.
- **09 — lands first.** Adds a fourth declarative `ModelSpec` field, `patterns`, to `models/spec.ts`,
  `models/spec.py` and `models/_base.py`; rewrites `_base.test.ts:188-196` (re-anchor by test name)
  and touches `buildYamlData`'s body while this proposal touches only its doc block.
- **22** sweeps the TypeScript factory bodies — **30** post-11, not 27. (The 27 figure at `e7a972c`
  is four-way confirmed: `grep -c 'buildModel[<(]'` over non-test `src/` gives **28**, minus the
  definition at `_base.ts:371`, across eight model files.)
- **24** narrows `walk()` in `_base.ts` (`:236-255`, `:413-427`) and explicitly disclaims
  `yaml-writer.ts`, `test_spec.py` and `test_yaml_writer.py` (`24` §Not touched, deliberately), so the contact reduces to
  `_base.ts` at disjoint regions.
- **12 and 13 do overlap this proposal, contrary to an earlier draft's claim that they do not.**
  `yaml-writer.ts` has four table-row claimants (10, 12, 13, 20), `test_yaml_writer.py` three
  (10 `:64-74`, 12 `:1-10`, 13 `:91-95`), `yaml-writer.test.ts` four (09, 10, 12 `:125,141`,
  13 `:34-64`). Every region is disjoint from this proposal's, so no file-level serialisation is
  needed — but the scheduling claim was wrong and is withdrawn. 12 additionally changes
  `fixtures/expected/comments.yml:3` and 13 adds six goldens, both of which redefine the byte
  baseline in step 7. `test_spec.py` has two claimants, **10** and **11** (`11` §Modified); 12 and 24
  dropped it.
- **18 is not a `models/` claimant** — its `models/action.py` mention is prose (`18` §2. ghagen deps update — one process, one sweep, one answer), not a
  table row. **14–17, 19** and **23** have no contact.

## ADR / CONTEXT.md impact

- **No ADR is contradicted.** ADR-0001 (`docs/adr/0001-document-serialization-seam.md:34`) says
  models carry "their **ModelSpec** (YAML key names + emission order)" — still exactly true; the
  spec keeps the ordering fact, it just stops writing it twice. Worth a one-word note there during
  implementation that the order is the key map's declaration order. ADR-0003 (schema sync /
  test-based conformance) and ADR-0005 (transform ordering) are untouched — this is emission key
  order, not transform order.
- **Absorbed Phase 7 bookkeeping item.** `packages/python/src/ghagen/models/spec.py:6` still names
  `GhagenModel.to_commented_map`, deleted by the ADR-0001 amendment (`0001-…:34`). Fixed in
  migration step 1 — this retires the item rather than deferring it again.
- **OrderMode glossary entry** — `packages/python/CONTEXT.md:46-47` and
  `packages/typescript/CONTEXT.md:48-49` carry the same sentence today, "A ModelSpec's
  emission-order rule — an explicit key list, or alphabetical (extras interleaved)." Both become:
  the ModelSpec key map's declaration order (`declared`), or alphabetical with extras interleaved
  (`alphabetical`).
- **ModelSpec glossary entry, Python** — `packages/python/CONTEXT.md:40-44`, **uncontested**
  (22 states "`packages/python/CONTEXT.md`: no change", `22` §Migration plan): state that the key map's
  declaration order _is_ the emission order.
- **ModelSpec glossary entry, TypeScript — CEDED.** `packages/typescript/CONTEXT.md:40-46` belongs
  to **22** and `:43` (the "extras placement" clause of the declarable-rules list) to **20** under
  the round's region map. This proposal makes **no edit** there; it hands 22 a one-sentence insert
  ("the key map's declaration order is the emission order") to land inside 22's own edit, and 20's
  deletion already removes the extras-placement clause. This proposal must not also delete it.
- **`packages/typescript/CONTEXT.md` surface notes:** one bullet **appended after the final bullet**
  in the block — the `src/paths.ts` bullet at `:113` — recording the Python/TS asymmetry: Python
  `dict` preserves insertion order for all keys, JS object literals order integer-like string keys
  first, which is why the field maps must not use numeric YAML keys. Appending at the end keeps it
  clear of **24**'s `:98-102`, **22**'s `:98` and **11**'s `:104-105`; note 24 appends after
  "amended." at `:101`, leaving `:98-100` byte-identical, so the bullet indices above are stable.
- **No Python surface-notes bullet is needed.** The asymmetry it would record is the JS one. 24's
  table lists this proposal as a co-claimant on `packages/python/CONTEXT.md`'s surface-notes block;
  that claim is released — this proposal's Python footprint is the two glossary entries only.
- No new glossary terms. **OrderMode** already exists in both glossaries; this narrows its
  definition rather than adding vocabulary.
