# 01 — ModelSpec as the sole key-name authority

**Status:** proposed | **Ports:** python / typescript | **Depends on:** none (interacts with [02](./02-emitter-test-seam.md) and [06](./06-close-modelspec-escape-hatches.md))

## Problem

In the Python port, the single fact "field `if_` emits as the YAML key `if`" is written down **four times**, in three files, with a fourth algorithm re-deriving it:

1. The Pydantic `serialization_alias` on the field —
   `packages/python/src/ghagen/models/step.py:56` (`serialization_alias="if"`), and 19 more
   across `step.py`, `job.py`, `workflow.py`, `action.py`, `permissions.py`, `trigger.py`,
   `image_snapshot.py`.
2. `ModelSpec.yaml_keys` — `packages/python/src/ghagen/models/step.py:15-27` (`"if_": "if"`).
3. `ModelSpec.order` — `packages/python/src/ghagen/models/step.py:28-40` (`"if"` in the tuple).
4. A third algorithmic re-derivation in the conformance sweep:
   `packages/python/tests/test_schema/test_conformance.py:124-129`, where
   `_model_property_names` recomputes the emitted name as
   `info.serialization_alias or info.alias or field_name`.

The emitter does **not** read the alias. It reads `spec.yaml_keys` —
`packages/python/src/ghagen/emitter/nodes.py:162`:

```python
raw[spec.yaml_keys.get(field_name, field_name)] = value
```

So `serialization_alias` carries **no production behaviour**. The only reader of the alias-resolution
helper `_yaml_key` (`packages/python/src/ghagen/emitter/yaml_writer.py:30-36`) is test code:
`packages/python/tests/test_models/test_spec.py:17` and
`packages/python/tests/test_emitter/test_yaml_writer.py:26`. It is production-dead.

The redundancy then forces tests whose only job is to police the copies against each other:

- `test_spec.py:52-64` (`test_yaml_keys_agree_with_pydantic_aliases`) exists solely to prove copy #1
  and copy #2 agree.
- `test_yaml_writer.py:209-245` monkeypatches `FieldInfo.validation_alias` / `.alias` to exercise
  `_yaml_key`'s branches — branches no live model ever reaches (no model sets `validation_alias`;
  a grep for it across `models/` returns nothing). These are tests for dead code.

The four homes must be edited in lockstep for every new field, and two test files exist only to
detect when someone forgets. This is the textbook shape of an un-earned duplicate: delete any one
copy and the fact is still fully specified by the others — except the copy the emitter actually
reads.

### TypeScript is already fine

In the TS port there is one home. Each `X_SPEC.fieldMap` is the field→YAML-key map, and it is
type-checked against the generated schema types with `satisfies` (e.g.
`packages/typescript/src/models/job.ts:145`,
`CONCURRENCY_SPEC.fieldMap … satisfies Record<keyof ConcurrencyInput, keyof SchemaConcurrency>`).
There is no second alias-like source. TS needs no structural change; see *ADR / CONTEXT.md impact*
for the one-line parity note.

## Current interface

What a maintainer must know today to add or rename a Python field:

- Set the Pydantic `serialization_alias` if the YAML key differs from the field name.
- Add the field→key entry to `ModelSpec.yaml_keys`.
- Add the YAML key to `ModelSpec.order` (or leave `order` empty for alphabetical — only `On`).
- Trust that `test_yaml_keys_agree_with_pydantic_aliases` will fail loudly if #1 and #2 drift.

The interface a caller of "what key does this field emit as" must consult is ambiguous: three
answers exist and only one (`spec.yaml_keys`) is load-bearing.

## Proposed interface

Make `ModelSpec` the **single interface** for emitted key names. Concretely, **direction (a): drop
`serialization_alias` from the models; `ModelSpec.yaml_keys` is the authority.**

A Python model field declares only its Python-side concerns; the YAML key lives once, in the spec:

```python
# step.py — after
STEP_SPEC = ModelSpec(
    yaml_keys={
        "id": "id",
        "name": "name",
        "if_": "if",                       # the ONLY home for if_ -> if
        "uses": "uses",
        "with_": "with",
        "working_directory": "working-directory",
        # …
    },
    order=("id", "name", "if", "uses", "run", "with", "env", "shell",
           "working-directory", "continue-on-error", "timeout-minutes"),
)


class Step(GhagenModel):
    SPEC: ClassVar[ModelSpec] = STEP_SPEC

    id: str | None = None
    name: str | None = None
    if_: str | None = Field(                # no serialization_alias
        None,
        description="Conditional expression that must evaluate to true …",
    )
    uses: str | None = None
    run: str | None = None
    with_: OrRaw[dict[str, Any]] | None = None
    # … working_directory, continue_on_error, timeout_minutes: plain fields
```

`Field(...)` is retained only where it still carries a Python-side payload (`description`,
`default_factory`, `exclude=True` on the meta fields). Where the only thing a `Field(...)` provided
was `serialization_alias`, the field collapses to a bare annotation
(`working_directory: str | None = None`).

**Invariants (unchanged emitted bytes):**

- The emitter already keys off `spec.yaml_keys` (`nodes.py:162`); removing the alias changes no
  output because the alias was never read at emit time.
- Construction is unaffected: `serialization_alias` never influenced input parsing. Fields are
  populated by their Python name (`if_=…`, `with_=…`), and `populate_by_name=True` is retained.
  There is **no `validation_alias`** on any model, so input names do not move.
- `model_config` keeps `populate_by_name=True`, `use_enum_values=True`,
  `arbitrary_types_allowed=True` (`_base.py:104-108`).

**Error modes:** the existing spec-vs-fields guard stays and becomes the *sole* consistency check.
`test_spec.py:45-49` (`test_spec_covers_exactly_the_content_fields`) already asserts
`set(model.SPEC.yaml_keys) == content_fields(model)`. That is the one invariant worth keeping: the
spec must name exactly the model's content fields. After this change it is the only key-name
consistency test, because there is no second copy to diverge from.

### Does anything rely on `model_dump(by_alias=True)`?

No. A full grep of `packages/python/src` for `model_dump` returns only the docstring at
`nodes.py:131` ("no `model_dump`") — the emitter walks `model_fields` directly and never calls
`model_dump`. `by_alias` appears nowhere. The pin transform mutates model fields in place and
re-emits through the emitter; it never serializes via Pydantic. Dropping `serialization_alias` is
therefore behaviourally inert outside the emitter, which does not read it.

## What sits behind the seam

`ModelSpec` becomes a genuinely deep module: a small, single interface (`yaml_keys` + `order`) that
is now the *only* place the field→key and ordering facts live, consumed by the emitter's recursion
(`nodes.py`) and — after this proposal — by the conformance sweep. Nothing else needs to know how a
field name becomes a YAML key. The Pydantic layer shrinks to what it is good at: input validation
and Python-side field metadata.

## Migration plan

Pre-1.0; clean break, no compat shim.

1. **Rewrite the conformance re-derivation to read the spec.** In
   `test_conformance.py`, replace `_model_property_names` (lines 124-129) so it reads the spec
   instead of Pydantic aliases:

   ```python
   def _model_property_names(model: type[GhagenModel]) -> set[str]:
       """Emitted YAML key names for a model — sourced from its ModelSpec."""
       return set(model.SPEC.yaml_keys.values())
   ```

   This is the load-bearing step and must land **before** the aliases are removed, or the sweep
   breaks. It also drops the `pydantic.BaseModel` typing of the parameter in favour of
   `GhagenModel` (every scoped model is one), so `SPEC` is visible.

2. **Delete `serialization_alias=` from every model field.** Mechanical, `sed`-able across
   `models/*.py`. Where a `Field(...)` is left with no remaining arguments, collapse the field to a
   bare annotated default. Verified sites: `step.py` (5), `workflow.py` (1), `job.py` (7),
   `action.py` (7), `permissions.py` (4), `trigger.py` (4), `image_snapshot.py` (1).

3. **Delete `_yaml_key`** from `emitter/yaml_writer.py:30-36` and its `FieldInfo` import.

4. **Delete the redundancy-guard tests** (see *Test impact*).

5. Run the full suite; emitted YAML and all integration snapshots must be byte-identical.

## Test impact

**Deleted (test dead or redundant code):**

- `test_spec.py:52-64` `test_yaml_keys_agree_with_pydantic_aliases` — nothing left to agree with;
  the aliases are gone. Also delete its import `from ghagen.emitter.yaml_writer import _yaml_key`
  (`test_spec.py:17`).
- `test_yaml_writer.py:209-245` — the four `_yaml_key` tests, including the two `monkeypatch`
  tests that fabricate `validation_alias`/`alias` on a `FieldInfo` to reach branches no model uses.
  Remove the `_yaml_key` import (`test_yaml_writer.py:26`).

**Kept (now the sole authority check):**

- `test_spec.py:45-49` `test_spec_covers_exactly_the_content_fields` — unchanged.
- `test_spec.py:67-91` order tests — unchanged.

**Rewritten:**

- `test_conformance.py::_model_property_names` — before/after:

  ```python
  # before — re-derives from Pydantic, a third copy of the key fact
  names.add(info.serialization_alias or info.alias or field_name)

  # after — reads the single authority
  return set(model.SPEC.yaml_keys.values())
  ```

The conformance assertions themselves (`test_scope_properties_covered`) are unchanged; they now
compare the schema's property set against spec-derived names. Because the emitter and the conformance
sweep now read the *same* `yaml_keys`, a model that emits a wrong key can no longer pass conformance
by having a matching-but-unused alias — the test surface and the production surface are the same map.

The bulk of model tests (`test_step.py`, `test_action.py`, …) are unaffected by this proposal; they
assert on emitted keys via `_model_to_map`, whose privacy [02](./02-emitter-test-seam.md) addresses
separately.

## Risks & alternatives

**Alternative (b): derive `yaml_keys` from Pydantic aliases at spec construction.** Rejected. It
keeps the alias as the real source of truth and makes `yaml_keys` a generated shadow, which is the
opposite of "ModelSpec is the single interface." It also re-introduces the coupling ADR-0003 pushes
against (models are hand-written; the spec should be authored, not back-derived from a second
authored source). And it leaves `serialization_alias` — production-dead metadata — littering every
model.

**Risk: losing a Pydantic-native representation of the key.** Low. `serialization_alias` only ever
mattered for `model_dump(by_alias=True)`, which ghagen does not call. No public API exposes the
alias. IDE navigation is unaffected — the spec lives in the same file as the model.

**Risk: someone re-adds a field without a `yaml_keys` entry.** Caught by the retained
`test_spec_covers_exactly_the_content_fields`, which fails if `yaml_keys` is not exactly the content
fields.

## ADR / CONTEXT.md impact

- **No ADR contradiction.** ADR-0001 (amended) says models carry "only data plus their **ModelSpec**
  (YAML key names + emission order)." This proposal makes that literally true by removing the
  competing alias home. It extends ADR-0001, does not touch its recursion decision.
- **ADR-0003** (hand-written models, schema as conformance target) is reinforced: the conformance
  sweep now reads the authored spec rather than re-deriving from a parallel authored source.
- **CONTEXT.md (Python), "ModelSpec" entry:** already says "YAML key names (field → emitted key)".
  Add a sentence: "It is the single home for the emitted-key fact — models carry no
  `serialization_alias`."
- **CONTEXT.md (TypeScript), parity note (no code change):** add under *Surface notes* that the
  TS `fieldMap` is the port-equivalent single home, type-checked against generated schema types with
  `satisfies`; the invariant "one home for the field→key fact" now holds identically in both ports
  (surface differs by idiom, per the parity mandate).
- **Ordering vs. sibling proposals:** land this proposal's conformance rewrite (step 1) independently
  of [02](./02-emitter-test-seam.md). The two interact only in `test_yaml_writer.py`, which both
  edit; sequence 01 before 02 so the key-authority story ("spec is the authority") is settled before
  02 builds the public observation surface that reads spec-derived keys. See
  [02 — Risks & alternatives](./02-emitter-test-seam.md) for the reciprocal note.
