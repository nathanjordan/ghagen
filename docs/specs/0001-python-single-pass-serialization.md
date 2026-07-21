# 0001 — Python single-pass YAML serialization

**Status:** implemented

Port the TypeScript single-pass serialization shape to Python. Replace the multi-pass
`model_dump` → patch-up chain in `GhagenModel.to_commented_map` with one recursive Emitter
free helper (`to_yaml_node`), collapsing `to_commented_map` to a thin method that mirrors
TS's `toYamlMap`. Public interface (`to_commented_map`, `Document.to_yaml` / `to_yaml_file`)
is unchanged.

## 1. Problem

`GhagenModel.to_commented_map` in `packages/python/src/ghagen/models/_base.py:263-334` builds
YAML in eight stages, most of which exist only to undo work an earlier stage did:

1. `model_dump(by_alias, exclude_none, exclude_unset, exclude={meta})` — Pydantic walks the
   whole tree, coercing every nested `GhagenModel` into a plain `dict` and stripping the
   `Commented` / `Raw` wrappers' identity (it can't serialize them, so it warns and passes them
   through).
2. `_unwrap_commented_dict` (`:59-73`) — re-walks the dumped dict to unwrap `Commented` values
   the serializer left behind.
3. `unwrap_raw` (`:299`) — re-walks again to unwrap `Raw`.
4. `_restore_nested_models` (`:336-381`) — re-walks the *original model fields* a third time to
   replace the `dict`s that step 1 produced with real `CommentedMap`s from
   `child.to_commented_map()`. This is pure undo of step 1.
5. `to_ordered_commented_map` — apply key ordering.
6. `_collect_commented_fields` (`:192-224`) — a *fourth* field walk to harvest per-field
   comments from `Commented` wrappers (the same wrappers step 2 discarded).
7. extras merge + `attach_field_comments`.
8. `post_process`.

The chain suppresses Pydantic serializer warnings (`warnings.catch_warnings()`,
`:276-292`) for the very `Commented` / `Raw` wrappers it then unwinds by hand — it asks Pydantic
to serialize values it knows Pydantic can't, silences the complaint, and cleans up after.

Costs:

- **Far-away diffs.** A bug in any single pass surfaces as a YAML difference three passes
  downstream, with no local cause. The model tree is walked four times over
  (`model_dump`, `_unwrap_commented_dict`/`unwrap_raw`, `_restore_nested_models`,
  `_collect_commented_fields`), and the passes must agree on alias resolution, exclusion
  semantics, and wrapper handling to stay consistent.
- **Duplicated alias resolution.** The YAML-key derivation block is copied verbatim in
  `_collect_commented_fields:207-217` and `_restore_nested_models:354-365`:

  ```python
  # Determine the YAML key name (alias or field name)
  alias = field_info.alias or field_name
  if field_info.validation_alias and isinstance(
      field_info.validation_alias, str
  ):
      alias = field_info.validation_alias
  ser_alias = (
      field_info.serialization_alias
      if field_info.serialization_alias
      else alias
  )
  ```

  Two copies that must never drift, plus a third alias resolution implicitly inside
  `model_dump(by_alias=True)`.
- **No direct unit tests.** `_unwrap_commented_dict`, `_restore_nested_models`,
  `_serialize_value`, and `_collect_commented_fields` are private passes with no unit coverage;
  they are exercised only end-to-end through the snapshot tests
  (`tests/test_integration/test_snapshots.py`). A regression in a pass is only ever caught as a
  whole-file snapshot mismatch.

TypeScript has none of this. `Model.toYamlMap` (`packages/typescript/src/models/_base.ts:254-301`,
~47 lines) walks `this.data` once, ordering keys and collecting comments inline, and delegates
every value to the single recursive `toYamlValue` (`:694-781`). There is no dump-then-restore,
no warning suppression, and no duplicated alias block — TS resolves YAML keys once, at
construction, so `this.data` already holds kebab keys.

## 2. Design

Introduce one recursive Emitter free helper and slim `to_commented_map` to a thin method over it,
matching the TS `toYamlValue` / `toYamlMap` split. **No `model_dump` is used for YAML
serialization** — fields are walked directly, exactly as TS walks `this.data`.

### 2.1 `to_yaml_node(value)` — the recursive helper

New free function in `packages/python/src/ghagen/emitter/yaml_writer.py`, the Python peer of
`toYamlValue`. It is the single place a value becomes a YAML node. Recursion cases, in order
(mirroring the current `_serialize_value:226-245` + `_serialize_list:247-261` exactly, so
behavior is preserved byte-for-byte):

| Case | Handling |
| --- | --- |
| `Commented` wrapper | unwrap and recurse on `.value` (comment already harvested by caller) |
| `Raw` wrapper | `unwrap_raw(value)` — preserves `PlainScalarString` wrapping so the block-scalar auto-cast is bypassed |
| `GhagenModel` | `value.to_commented_map()` (recursion into the thin method) |
| `CommentedMap` | pass through unchanged (already a YAML node) |
| `dict` | build a `CommentedMap`, recursing `to_yaml_node` over each value |
| `list` (incl. `CommentedSeq`) | build a `CommentedSeq` via `_to_yaml_seq`, attaching item comments from `GhagenModel` entries |
| scalar / other | `unwrap_raw(value)` (identity for plain scalars) |

The one wrinkle versus TS: the helper lives in the Emitter module but must recognise
`GhagenModel`, and `models/_base.py` already imports from `yaml_writer`. To avoid an import
cycle, `to_yaml_node` does a **function-local** `from ghagen.models._base import GhagenModel`
— the established pattern in this package (`emitter/emit.py:_dedent_steps` lazily imports
`Step`, and `to_yaml` lazily uses model types). This keeps the Document serialization seam
(ADR-0001) intact: the Emitter owns value-to-node conversion; the model owns field walking and
comment/extras/ordering policy.

### 2.2 `_yaml_key(field_name, field_info)` — one alias resolver

The duplicated alias block (§1) collapses to a single free helper in `yaml_writer.py`:

```python
def _yaml_key(field_name: str, field_info: FieldInfo) -> str:
    """Resolve the YAML key for a model field: serialization_alias wins,
    then a string validation_alias, then alias, else the field name."""
    alias = field_info.alias or field_name
    if isinstance(field_info.validation_alias, str):
        alias = field_info.validation_alias
    return field_info.serialization_alias or alias
```

Called once per field in the single walk. `model_dump(by_alias=True)`'s implicit third alias
path is gone with `model_dump`.

### 2.3 Slimmed `to_commented_map`

One field walk that replicates `exclude_none` / `exclude_unset` (see §5), orders keys, harvests
comments inline, merges extras, attaches comments, and runs `post_process` — the exact shape of
TS `toYamlMap:254-301`.

## 3. Before / After

### 3.1 Before — the pass chain (`_base.py:263-334`)

```python
def to_commented_map(self) -> CommentedMap:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Pydantic serializer warnings",
            category=UserWarning,
        )
        data = self.model_dump(
            by_alias=True,
            exclude_none=True,
            exclude_unset=True,
            exclude={"extras", "post_process", "comment", "eol_comment"},
        )
    data = _unwrap_commented_dict(data)          # pass 2: undo Commented
    data = unwrap_raw(data)                       # pass 3: undo Raw
    self._restore_nested_models(data)             # pass 4: undo model_dump's dict coercion
    cm = to_ordered_commented_map(data, self._get_key_order())
    field_comments, field_eol_comments = self._collect_commented_fields()  # pass 5
    for key, value in self.extras.items():
        if is_commented(value):
            if value.comment:
                field_comments[key] = value.comment
            if value.eol_comment:
                field_eol_comments[key] = value.eol_comment
            cm[key] = self._serialize_value(value.value)
        else:
            cm[key] = self._serialize_value(value)
    attach_field_comments(
        cm,
        field_comments=field_comments or None,
        field_eol_comments=field_eol_comments or None,
    )
    if self.post_process is not None:
        self.post_process(cm)
    return cm
```

Deleted along with it: `_unwrap_commented_dict` (`:59-73`), `_restore_nested_models`
(`:336-381`, incl. the second alias-block copy at `:354-365`), `_serialize_value` (`:226-245`)
and `_serialize_list` (`:247-261`) as methods (their logic moves into the free helper), and the
alias block inside `_collect_commented_fields` (`:207-217`). `_collect_commented_fields` itself
folds into the single walk (its comment-harvesting is done inline while iterating fields).

### 3.2 After — `yaml_writer.py` (new free helpers)

```python
def _to_yaml_seq(items: list[Any]) -> CommentedSeq:
    """Serialize a list to a CommentedSeq, attaching item comments from
    GhagenModel entries (mirrors the old _serialize_list)."""
    from ghagen.models._base import GhagenModel  # local: avoid import cycle

    seq = CommentedSeq()
    for item in items:
        seq.append(to_yaml_node(item))
    for idx, item in enumerate(items):
        if isinstance(item, GhagenModel):
            if item.comment:
                attach_comment(seq, idx, comment=item.comment)
            if item.eol_comment:
                attach_comment(seq, idx, eol_comment=item.eol_comment)
    return seq


def to_yaml_node(value: Any) -> Any:
    """Convert any model value to a YAML node in one recursive pass.

    Python peer of TypeScript's ``toYamlValue``. This is the single place a
    Commented/Raw/GhagenModel/dict/list/scalar becomes a ruamel node.
    """
    from ghagen.models._base import GhagenModel  # local: avoid import cycle

    if isinstance(value, Commented):
        return to_yaml_node(value.value)
    if isinstance(value, Raw):
        # Route through unwrap_raw to keep PlainScalarString wrapping of
        # Raw[str] (bypasses the block-scalar auto-cast).
        return unwrap_raw(value)
    if isinstance(value, GhagenModel):
        return value.to_commented_map()
    if isinstance(value, CommentedMap):
        return value
    if isinstance(value, dict):
        cm = CommentedMap()
        for k, v in value.items():
            cm[k] = to_yaml_node(v)
        return cm
    if isinstance(value, list):
        return _to_yaml_seq(value)
    return unwrap_raw(value)


def _yaml_key(field_name: str, field_info: FieldInfo) -> str:
    alias = field_info.alias or field_name
    if isinstance(field_info.validation_alias, str):
        alias = field_info.validation_alias
    return field_info.serialization_alias or alias
```

(`yaml_writer.py` gains imports of `Commented`/`is_commented` from `ghagen._commented` and
`FieldInfo` from `pydantic.fields`; `attach_comment`, `unwrap_raw`, `CommentedMap`,
`CommentedSeq`, `to_ordered_commented_map` are already in the module.)

### 3.3 After — `to_commented_map` (thin method on `GhagenModel`)

```python
_META_FIELDS = frozenset({"extras", "post_process", "comment", "eol_comment"})


def to_commented_map(self) -> CommentedMap:
    """Serialize this model to a CommentedMap in a single field walk.

    Walks the model's own fields directly (no model_dump): applies
    exclude_none / exclude_unset semantics, canonical key ordering, harvests
    per-field comments from Commented wrappers, merges extras, and runs the
    post_process hook. Python peer of TypeScript's Model.toYamlMap.
    """
    # Single walk: collect set, non-None fields under their YAML keys.
    raw: dict[str, Any] = {}
    for field_name, field_info in type(self).model_fields.items():
        if field_name in _META_FIELDS:
            continue
        if field_name not in self.model_fields_set:  # exclude_unset
            continue
        value = getattr(self, field_name, None)
        if value is None:  # exclude_none (checked on the raw wrapper, as model_dump did)
            continue
        raw[_yaml_key(field_name, field_info)] = value

    ordered = to_ordered_commented_map(raw, self._get_key_order())

    cm = CommentedMap()
    field_comments: dict[str, str] = {}
    field_eol_comments: dict[str, str] = {}

    for key, value in ordered.items():
        if is_commented(value):
            if value.comment:
                field_comments[key] = value.comment
            if value.eol_comment:
                field_eol_comments[key] = value.eol_comment
            value = value.value
        cm[key] = to_yaml_node(value)

    for key, value in self.extras.items():
        if is_commented(value):
            if value.comment:
                field_comments[key] = value.comment
            if value.eol_comment:
                field_eol_comments[key] = value.eol_comment
            value = value.value
        cm[key] = to_yaml_node(value)

    attach_field_comments(
        cm,
        field_comments=field_comments or None,
        field_eol_comments=field_eol_comments or None,
    )

    if self.post_process is not None:
        self.post_process(cm)

    return cm
```

`_collect_commented_fields`, `_serialize_value`, `_serialize_list`, `_restore_nested_models`,
`_unwrap_commented_dict` are removed. `warnings` and `unwrap_commented` imports in `_base.py`
drop out (no serializer warnings to suppress; unwrap happens in `to_yaml_node`).
`children()` / `walk()` / `_scan_for_models` are untouched — they are a separate traversal
primitive, not part of serialization.

## 4. Behaviour preservation

`model_dump(exclude_none=True, exclude_unset=True, exclude={meta}, by_alias=True)` must be
replicated exactly by the field walk. Precise rules — a field emits **iff all** hold:

1. **Not a meta field.** `field_name not in _META_FIELDS`. (These carry `exclude=True` today;
   they are structurally excluded from output.)
2. **Set (`exclude_unset`).** `field_name in self.model_fields_set`. The wrap validator
   `_preserve_commented` (`:126-151`) validates the cleaned input dict, so every user-supplied
   key — including `Commented`-wrapped ones — is in `model_fields_set`; re-setting the wrapper
   via `object.__setattr__` afterwards does not remove it. `On._normalize_workflow_dispatch`
   (`trigger.py:168-183`) rewrites an already-set field to `Raw(None)` in place, so it stays
   set.
3. **Not None (`exclude_none`).** `value is None` is checked on the **raw attribute value**
   (the wrapper), *before* unwrapping — precisely what `model_dump` saw, since it never looked
   inside `Commented` / `Raw`. Consequence: a field normalized to `Raw(None)` (empty
   `workflow_dispatch`) is **not** None (it is a `Raw` object), so it survives the filter and
   `to_yaml_node` → `unwrap_raw` renders it as a bare null key — identical to today. A
   hypothetical `Commented`/`Raw` wrapping `None` is likewise kept (no factory produces one;
   noted for completeness).

4. **YAML key** comes from `_yaml_key` — the single alias resolver — matching
   `by_alias=True` plus the two hand-rolled copies it replaces.

Other preserved semantics:

- **Key ordering** is unchanged: `to_ordered_commented_map` (`yaml_writer.py:39-62`) still
  places `key_order` keys first, then remaining keys **alphabetically**. Extras are still
  appended after ordered fields, in `extras` insertion order.
- **Nested models** render via `child.to_commented_map()` (the `GhagenModel` case in
  `to_yaml_node`), exactly as `_restore_nested_models` / `_serialize_value` did — the
  intermediate `dict` coercion is simply never created. Note the current Python behavior that a
  nested single model's own `comment` / `eol_comment` is attached **only** for list items
  (via `_to_yaml_seq`) and at the top level (via `emit.to_yaml`); this spec preserves that as-is
  (aligning single-value nested comments with TS is spec 0003's concern, not this one).
- **`Raw[str]` block-scalar bypass**, multiline auto-literal, comment column alignment, and the
  `dump_yaml` pass all live downstream in `yaml_writer.py` and are untouched.

**Warnings suppression is removed.** With no `model_dump` call, Pydantic never tries to
serialize a `Commented` / `Raw` wrapper, so there is no `UserWarning` to filter. If any warning
surfaces during the test run, it is a real defect, not noise.

**ADRs preserved.** ADR-0001 (Document serialization seam): `to_yaml` / `to_yaml_file` stay on
`Document` only; `emit.to_yaml` still calls `model.to_commented_map()` and attaches the
top-level `comment` (`emit.py:55-61`) — its contract is unchanged. ADR-0002 (serialization-time
`auto_dedent`): `_dedent_steps` (`emit.py:21-36`) runs before `to_commented_map` and is
untouched; `Step.run` still holds the raw string until emit.

**Safety net:** the existing snapshot suite (`tests/test_integration/test_snapshots.py` — 11
snapshots covering CI, matrix, comments, multiline, escape hatches, full-featured workflow, three
action kinds, triple-quoted run) plus `test_full_workflow.py`, `test_action.py`, `test_header.py`
must remain byte-for-byte green with no snapshot regeneration.

## 5. Test plan

New direct unit tests give the recursive helper the coverage the private passes never had. Add
to `tests/test_emitter/test_yaml_writer.py`:

- `to_yaml_node` on plain scalars → identity (`"x"`, `42`, `True`, `None`).
- `to_yaml_node` on `Raw("x")` → `"x"`; on `Raw` multiline `str` → a `PlainScalarString` (not
  promoted to a block literal by the downstream cast).
- `to_yaml_node` on `Commented`-wrapped scalar → inner value (comment harvesting is the caller's
  job; the node is just the value).
- `to_yaml_node` on a plain `dict` → a `CommentedMap` with recursively converted values; on a
  `CommentedMap` → same object passed through.
- `to_yaml_node` on a `list` of scalars → `CommentedSeq`; on a list containing a `GhagenModel`
  with `comment` / `eol_comment` → item comment attached at the right index (assert via
  `dump_yaml`).
- `to_yaml_node` on a `GhagenModel` (e.g. a `Step`) → a `CommentedMap` equal to
  `step.to_commented_map()`.
- `_yaml_key`: field name, `alias`, `validation_alias` (string), and `serialization_alias`
  precedence — one parametrized test over a throwaway model or `Step`'s `if_` / `working_directory`
  fields.

Add to `tests/test_models/` (or a new `test_models/test_serialize.py`):

- `to_commented_map` **exclude semantics**: a `Step(name="x")` emits only `name` (unset fields
  dropped); a field explicitly set to `None` is dropped; `On` with empty `workflow_dispatch`
  emits a present null `workflow_dispatch` key.
- `to_commented_map` **extras + comments** ordering: extras appended after ordered fields;
  block/eol comments from `Commented` field values and `Commented` extras land on the right keys.

Existing tests: **unchanged and green.** No snapshot regeneration. `test_yaml_writer.py`'s
existing `unwrap_raw` / `to_ordered_commented_map` / `attach_comment` / `dump_yaml` tests are
unaffected.

## 6. Acceptance criteria

- [ ] `to_yaml_node(value)` and `_to_yaml_seq` exist in `emitter/yaml_writer.py`, handling
      Commented / Raw / GhagenModel / CommentedMap / dict / list / scalar, with a function-local
      `GhagenModel` import (no import cycle).
- [ ] `_yaml_key(field_name, field_info)` is the **only** alias resolver; both verbatim copies
      (`_collect_commented_fields`, `_restore_nested_models`) and the `by_alias=True` path are
      gone.
- [ ] `GhagenModel.to_commented_map` is a single field walk (no `model_dump`), ≤ ~40 lines,
      structurally mirroring TS `toYamlMap`.
- [ ] `_unwrap_commented_dict`, `_restore_nested_models`, `_serialize_value`, `_serialize_list`,
      `_collect_commented_fields`, and the `warnings.catch_warnings()` block are deleted; the now
      unused `warnings` / `unwrap_commented` imports are removed from `_base.py`.
- [ ] Public interface unchanged: `to_commented_map()` on every model; `to_yaml` / `to_yaml_file`
      on `Document` only.
- [ ] ADR-0001 and ADR-0002 behaviour intact (seam gating; serialization-time dedent).
- [ ] All existing snapshot / integration / model / emitter tests pass with **no** snapshot
      regeneration.
- [ ] New unit tests for `to_yaml_node`, `_yaml_key`, and `to_commented_map` exclusion semantics
      pass.
- [ ] `ruff` / `ruff-format` clean; no new Pydantic serializer warnings emitted during the suite.

## 7. Conflicts

Spec 0003 (comment-attachment consolidation) edits the same files (`_base.py`, `yaml_writer.py`)
and reworks how nested-model `comment` / `eol_comment` are attached — including the single-value
nested-model case this spec deliberately leaves as-is (§4). **Spec 0001 must land first**: it
establishes the single `to_yaml_node` recursion and the thin `to_commented_map` that 0003 then
extends (adding nested-comment attachment inside the `GhagenModel` branch of `to_yaml_node`,
paralleling TS `toYamlValue:713-733`). Sequencing 0003 before 0001 would mean re-doing the
consolidation against the old multi-pass chain and then again after this refactor. Land 0001,
re-baseline snapshots as green, then build 0003 on top.
