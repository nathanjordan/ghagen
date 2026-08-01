# 21 — Hoist the duplicated field-collection loop

**Status:** proposed | **Ports:** python | **Effort:** S | **Depends on:** nothing; [10](./10-delete-modelspec-order.md) depends on this landing first

Effort stays **S** — confirmed by review, and the review made it smaller: the cross-pass agreement
guard is a **one-line fixture edit to an existing test**, not a new test (see
[Test impact](#test-impact)).

## Files involved

### Modified — Python source

| Path                                          | Lines | Role in this proposal                                                                                                                                                                                        |
| --------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `packages/python/src/ghagen/emitter/nodes.py` | 209   | New `collect_fields` beside `order_entries` (inserted after `:84`); `_model_to_map`'s collection loop (`:170,172-184`) collapses to one call                                                                 |
| `packages/python/src/ghagen/emitter/data.py`  | 174   | `_model_to_data`'s collection loop (`:102,104-115`) collapses to one call; the imports of `dedent_script` (`:27`), `_META_FIELDS` (`:29`) and `Step` (`:31`) all drop out — each is used _only_ by that loop |

### Modified — Python tests

| Path                                                 | Lines | Role in this proposal                                                                                                                                                                                                                                                                                           |
| ---------------------------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/python/tests/test_emitter/test_to_data.py` | 161   | **One line.** `test_deep_structure_matches_emitted_yaml` (`:130-161`) already _is_ the cross-pass agreement test; its fixture `Job` (`:144-156`) gains `needs=[]` so the document under test contains an empty list. That single addition is what makes probes P4 and P5 fail — see [Test impact](#test-impact) |

### New — tests

| Path                                                          | Lines | Role in this proposal                                                                                                                                   |
| ------------------------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/python/tests/test_emitter/test_field_collection.py` | new   | Per-rule unit tests over `collect_fields` — one per collection rule plus the dedent rule. **No agreement test here**; that invariant has a home already |

### Not touched, deliberately

- `packages/python/tests/test_models/test_spec.py` (78) — `_META_FIELDS` stays exported from
  `ghagen.emitter.nodes`, so its import at `:16` and its use at `:36` are unchanged.
  [10](./10-delete-modelspec-order.md) rewrites this file; this proposal must not collide there.
- `packages/python/tests/test_emitter/test_yaml_writer.py` (205) — the `order_entries` unit tests
  (`:61-81`) are untouched, and the new `collect_fields` tests go in their own file rather than
  beside them. [10](./10-delete-modelspec-order.md), [12](./12-ts-comment-geometry-module.md) and
  [13](./13-unify-format-header-contract.md) all edit this file.
- `packages/python/tests/test_integration/test_snapshots.py` (451) and `fixtures/expected/` (10
  `.yml` fixtures) — **untouched but load-bearing.** They are the shared byte oracle, and they are
  the reason the "emitted bytes are unchanged" claim below is bounded the way it is: ten fixtures do
  not exercise all 31 spec-carrying models, so the byte guarantee this proposal can actually assert
  is _the fixture set plus this repo's own regenerated workflows_, not "every possible document".
  [12](./12-ts-comment-geometry-module.md) and [13](./13-unify-format-header-contract.md) both edit
  this file and the fixture set; this proposal edits neither.
- Every TypeScript file — see [Problem](#problem), point 4.
- `docs/specs/0001-python-single-pass-serialization.md` (421) — a landed migration spec, archival.
  Its §4 contract (`:304-326`) is cited here, not rewritten.
- `packages/python/CONTEXT.md` (114) / `packages/typescript/CONTEXT.md` (119) — no new domain term
  and **no region claimed in either file**; see [ADR / CONTEXT.md impact](#adr--contextmd-impact).

## Problem

The Python Emitter runs two whole-model passes — the ruamel walk that produces files, and the
plain-data walk that is the supported observation surface — and **each one independently decides
which fields exist**.

**1. The loop is duplicated character-for-character.**
`_model_to_map` (`packages/python/src/ghagen/emitter/nodes.py:150`) and `_model_to_data`
(`packages/python/src/ghagen/emitter/data.py:89`) open with the same block. Diffing
`nodes.py:169-184` against `data.py:101-115` mechanically, with blank and comment-only lines dropped
and trailing comments stripped:

```
a: 14  b: 14  identical: True
```

**14 identical code lines**, and **15** if you extend one line further to
`present_null = spec.present_null_when_empty` (`nodes.py:186` / `data.py:117`), which is also
identical. The raw `diff -u` over the two blocks reports exactly **two** hunks, and **both are
comments**:

```diff
     spec = type(model).SPEC
     is_step = isinstance(model, Step)

-    # Single walk: collect set, non-None fields under their YAML keys.
     raw: dict[str, Any] = {}
     for field_name in type(model).model_fields:
         if field_name in _META_FIELDS:
@@
         if field_name not in model.model_fields_set:  # exclude_unset
             continue
         value = getattr(model, field_name, None)
-        if value is None:  # exclude_none (checked on the raw wrapper)
+        if value is None:  # exclude_none
             continue
         if auto_dedent and is_step and field_name == "run" and isinstance(value, str):
             value = dedent_script(value)
```

There is no executable difference at all.

**2. The ordering half of this exact loop was already hoisted — for exactly this reason.**
`order_entries` (`nodes.py:52-84`) exists, and its docstring says why (`nodes.py:57-61`):

```python
    """Resolve a model's emitted ``(key, value)`` entries in canonical order.

    The single home for emission ordering, shared by the ruamel walk
    (:func:`_model_to_map`) and the plain-data walk
    (:func:`ghagen.emitter.data._model_to_data`), so the two cannot disagree.
```

`is_empty_map` (`nodes.py:87-94`) was hoisted on the same reasoning: "one check serves both Emitter
passes" (`nodes.py:92`). So the _ordering_ of the emitted keys cannot drift, and the _present-null_
rule cannot drift — but the **membership** was left behind in both call sites. The two passes can
still disagree about which fields exist at all, which is the larger of the two facts. The precedent
is the argument: the same module boundary, drawn one step earlier in the same function.

**3. Both passes derive membership from Pydantic introspection, not from the `ModelSpec` — a third
restatement.** Both build `raw` by iterating `type(model).model_fields` (`nodes.py:174`,
`data.py:105`) and only then consult the spec, for the key name alone
(`raw[spec.yaml_keys.get(field_name, field_name)] = value`, `nodes.py:184` / `data.py:115`). So
"which fields a model has" is written down in three places: the Pydantic class body, `spec.yaml_keys`,
and — for the emitted order — `spec.order`.

Proposal 10's author reports these three agree across every concrete model and that the agreement is
unguarded. Re-verified here, with the counts reconciled and two corrections:

- **The model census, stated once so it stops looking like a disagreement between documents.**
  Enumerating every `GhagenModel` subclass: **32 subclasses**, **31 carry a `SPEC`**, and those 31
  share **30 distinct `SPEC` objects** — `Service` and `Container` are bound to _literally the same
  object_. `Document` is the sole subclass without a `SPEC`; `On` is the sole `order=None`
  (alphabetical) spec. **10's "30 spec literals" and this document's "31 models" are both correct
  and describe different things** (objects vs. classes).
- The _equality_ holds. For all 31, the Pydantic content-field order equals
  `list(spec.yaml_keys.values())` equals the `spec.order` tuple. Zero set mismatches and zero
  sequence mismatches.
- "Nothing tests it" is **half stale**. `test_spec_covers_exactly_the_content_fields`
  (`packages/python/tests/test_models/test_spec.py:44-48`) and `test_explicit_order_is_complete`
  (`:59-72`) _do_ guard the relationship — but with `set(...)` on both sides. The **sets** are
  guarded; the **sequence** is not.
- And the sequence turns out to be **inert today**, which is worth saying plainly rather than
  overselling. Because `test_explicit_order_is_complete` forces `set(spec.order) == set(yaml_keys)`,
  every collected key is named in `spec.order`, so `order_entries`' explicit branch (`nodes.py:74-83`)
  re-orders all of them and its "remaining keys in insertion order" fallback (`:80-82`) never fires.
  Probe P1 below confirms it: reversing the collection order in one pass changes nothing.

So the argument from point 3 is **not** an ordering bug. It is that emission membership is derived
from a coincidence between two declarations rather than read from one — and the hoisted module is
the single place from which that source can later be switched (see the [10 handoff](#scope-boundaries-vs-siblings)).

**4. TypeScript has one collection _site_ — but the parity story is narrower than it looks.**
A TS `Model`'s field membership is decided **once**, at **construction**, by `buildYamlData`
(`packages/typescript/src/models/_base.ts:315-365`), which iterates `Object.entries(spec.fieldMap)`
(`:322`) and stores the result in `model.data`. Both Emitter passes then read that one record
through the shared `orderedEntries` (`packages/typescript/src/emitter/yaml-writer.ts:189-215`, which
opens `const data = model.data;` at `:190`): `modelToYamlMap` calls it at `:73`, `modelToData` at
`:311`. There is no second membership loop to hoist, and the bypasses proposal
[06](./06-close-modelspec-escape-hatches.md) described are gone — the only two `new Model(` sites
left in TS source are `clone()` (`_base.ts:233`) and the one inside `buildModel` itself
(definition at `_base.ts:371`, the construction at `:376`), and **27** factory call sites route
through `buildModel<…>` (`rg -c 'buildModel[<(]'` over non-test `src/` gives 28; minus the
definition, 27. [11](./11-shared-spec-surface-table.md) takes it to 30.)

Two corrections that both _narrow_ the parity claim:

- **`buildYamlData` is not `collect_fields`' peer.** It runs at **construction**; `collect_fields`
  runs at **emission**. It is an input _normalizer_ as much as a collector — it also applies
  `applyWrapRule` (`_base.ts:335-338`, definition `:380`), promoting shorthand objects to models,
  which has no Python counterpart at all. And its iteration source is `spec.fieldMap`, which is
  precisely what [10](./10-delete-modelspec-order.md) changes Python to. So this proposal gives
  Python one collection **site**; the **source** difference is closed only by 10, and the **phase**
  difference by nothing in this round.
- **TypeScript still implements rule 5 twice.** The Step-`run` dedent exists as `dedentSteps`
  (`yaml-writer.ts:44-52`), called by `toYaml` at `:425`, **and** inline in `modelToData` (`:313`
  binds `isStep`, `:321-322` applies `dedentScript`). The two do not even share a default:
  `toYaml` uses `options?.autoDedent ?? true` (`:425`), `toData` uses `options?.autoDedent ?? false`
  (`:302`). So "TypeScript is structurally correct already" is true of **membership** and false of
  the dedent rule.

**TypeScript still needs no change under this proposal.** The rule-5 duplication above is a
separate, TypeScript-only finding with its own asymmetric-defaults question; it is out of scope here
and belongs in `docs/issues/`, not bolted onto a Python hoist.

### Defect classification

- **LATENT — wrong output.** No input today makes the two passes disagree: the code is
  character-identical, so `to_data` and `emit` cannot currently differ on membership. Nobody can hit
  a bug.
- **LIVE — locality, and a _fixture_ hole in an otherwise-owned invariant.** The property "the two
  passes agree on membership" **is** owned by a test —
  `test_deep_structure_matches_emitted_yaml` (`packages/python/tests/test_emitter/test_to_data.py:130-161`),
  which compares `to_data(wf, auto_dedent=True)` against the _parsed emitted YAML_ and whose own
  comment states the intent: "the two duplicated recursions cannot diverge on
  exclude/unwrap/present-null/dedent — not just top-level ordering". What is missing is not the
  test; it is **fixture coverage**. The document at `:136-158` contains no empty list, which is
  exactly why probes P4 and P5 slip past it. That is live today: a whole class of one-sided edit
  ships green _right now_, and it is the class the hoist makes unexpressible.

### The probe: make the two passes disagree, watch the suite pass

Baseline: `uv run pytest packages/python/tests` → **562 passed**. Six one-sided mutations, one file
each, run against the full Python suite. **Method:** the source tree was copied out of the checkout,
mutated in the copy, and imported via `PYTHONPATH` — the shared working tree was never written to,
and `git status --short` shows no tracked-file change at any point.

| #   | Mutation                                                                                       | Result               |
| --- | ---------------------------------------------------------------------------------------------- | -------------------- |
| P1  | `nodes.py`: iterate `reversed(list(type(model).model_fields))` — collection **order** diverges | **562 passed**       |
| P2  | `data.py`: delete the `_META_FIELDS` skip (`:106-107`)                                         | 4 failed, 558 passed |
| P3  | `data.py`: delete the `exclude_unset` guard (`:108-109`)                                       | **562 passed**       |
| P4  | `nodes.py`: emit side only, skip empty-list fields                                             | **562 passed**       |
| P5  | `data.py`: observation side only, skip empty-list fields                                       | **562 passed**       |
| P6  | `data.py`: collect from `spec.yaml_keys` instead of `model_fields`                             | **562 passed**       |

Five of six one-sided membership edits are invisible to 562 tests. **P2 is the one that is caught,
and it is caught by four tests, not one:**

- `test_emitter/test_to_data.py::test_extras_merged_after_ordered_keys`
- `test_emitter/test_to_data.py::test_nested_model_own_comment_surfaced_with_comments_true`
- `test_emitter/test_to_data.py::test_deep_structure_matches_emitted_yaml`
- `test_models/test_serialize.py::test_on_emits_alphabetically_interleaving_extras`

The third of those **is** the cross-pass agreement test. So membership agreement is being checked —
by a real oracle, through the real byte path — and P4/P5 evade it only because its fixture happens
to contain no empty list.

P5 made concrete, with a `Job` carrying two empty lists:

```
--- with P5 applied (data.py skips empty lists, nodes.py does not) ---
to_data -> {'runs-on': 'ubuntu-latest'}
emit    -> {'runs-on': 'ubuntu-latest', 'needs': [], 'steps': []}
pytest: 562 passed
--- unpatched baseline ---
to_data -> {'runs-on': 'ubuntu-latest', 'needs': [], 'steps': []}
emit    -> {'runs-on': 'ubuntu-latest', 'needs': [], 'steps': []}
```

This is the worst shape the divergence can take. `to_data` is the **supported observation surface**
(`data.py:1-19`; ADR-0001 amendment; [02](./02-emitter-test-seam.md)) — it is what tests assert
against precisely so they need not read ruamel internals. When it disagrees with the ruamel walk,
every test written through it is asserting a fiction about the emitted file, and the suite reports
green while doing so.

P6 is worth a separate note: swapping one pass's collection source from `model_fields` to
`spec.yaml_keys` is _also_ invisible. That is point 3's coincidence, measured — the two sources are
interchangeable today, and nothing says so.

## Current interface

Two module-private functions each implement the same collection contract inline:

- `_model_to_map(model, *, auto_dedent=False) -> CommentedMap` (`nodes.py:150-209`) — collection at
  `:172-184`.
- `_model_to_data(model, *, auto_dedent, comments) -> dict[str, Any]` (`data.py:89-142`) — collection
  at `:104-115`.

The contract itself is already written down, once, as a normative four-rule list —
`docs/specs/0001-python-single-pass-serialization.md:307-326`, "a field emits **iff all** hold"
(`:307`) — covering meta-field exclusion, `exclude_unset`, `exclude_none`-on-the-raw-wrapper, and the
YAML-key mapping. Since that spec landed, the Step `run` dedent rule (`nodes.py:182-183` /
`data.py:113-114`) was added as a fifth. **One written contract, two implementations, no seam between
them.** A maintainer changing any of the five rules must know, unaided, that there is a second copy
in the other module — the only hint is a docstring cross-reference in `_model_to_data` ("the peer of
`_model_to_map`", `data.py:92`) that names the peer but does not share code with it.

The shallowness is visible from the dependency edges: `data.py` imports `dedent_script` (`:27`),
`_META_FIELDS` (`:29`) and `Step` (`:31`) from three different modules, and **every one of those
three imports exists solely to serve this loop** (`dedent_script` at `:114`, `_META_FIELDS` at
`:106`, `Step` at `:102` — no other use in the file). The observation surface pulls in the dedent
module and a concrete model class only because it is re-implementing collection.

TypeScript, for contrast, has one collection site — but at construction, not emission, and it is
`buildYamlData` (`_base.ts:315`) rather than a peer of `collect_fields`; see
[Problem](#problem), point 4.

## Proposed interface

One function, next to `order_entries`, in the module that already hosts the shared emission core
(`_META_FIELDS`, `order_entries`, `is_empty_map`):

```python
# packages/python/src/ghagen/emitter/nodes.py — inserted after order_entries (:84)

def collect_fields(model: GhagenModel, *, auto_dedent: bool) -> dict[str, Any]:
    """Collect a model's emitted fields under their YAML keys.

    The single home for emission *membership*, shared by the ruamel walk
    (:func:`_model_to_map`) and the plain-data walk
    (:func:`ghagen.emitter.data._model_to_data`), so the two cannot disagree
    about which fields exist — the peer of :func:`order_entries`, which is the
    single home for the order they come out in.

    A field is collected iff all of these hold (the contract stated in
    ``docs/specs/0001-python-single-pass-serialization.md`` §4):

    1. it is not a meta field (``_META_FIELDS``) — those carry serialization
       policy, not YAML content;
    2. it is set (``model_fields_set`` — ``exclude_unset``);
    3. its value, wrapper and all, is not ``None`` — ``exclude_none`` is checked
       on the *raw* attribute, before any ``Commented`` / ``Raw`` see-through, so
       a ``Raw(None)`` survives;
    4. the key it lands under is ``spec.yaml_keys[field]``, defaulting to the
       field name.

    When *auto_dedent* is true a :class:`~ghagen.models.step.Step`'s ``run``
    string is dedented here, at collection — no model mutation, no copy
    (ADR-0002). This is the sole home of the dedent-at-emit rule for both job
    steps and composite-action ``runs.steps``.

    Returns the ``{yaml_key: value}`` mapping in Pydantic field-declaration
    order; :func:`order_entries` decides the emitted order from there.
    """
    spec = type(model).SPEC
    is_step = isinstance(model, Step)

    raw: dict[str, Any] = {}
    for field_name in type(model).model_fields:
        if field_name in _META_FIELDS:
            continue
        if field_name not in model.model_fields_set:  # exclude_unset
            continue
        value = getattr(model, field_name, None)
        if value is None:  # exclude_none (checked on the raw wrapper)
            continue
        if auto_dedent and is_step and field_name == "run" and isinstance(value, str):
            value = dedent_script(value)
        raw[spec.yaml_keys.get(field_name, field_name)] = value
    return raw
```

Both call sites become three lines:

```python
# nodes.py, _model_to_map                    # data.py, _model_to_data
spec = type(model).SPEC                      spec = type(model).SPEC
raw = collect_fields(model, auto_dedent=auto_dedent)
present_null = spec.present_null_when_empty  present_null = spec.present_null_when_empty
```

`spec` stays at each call site — both still need `present_null_when_empty` (`nodes.py:186` /
`data.py:117`) and both pass `spec` to `order_entries` (`nodes.py:193` / `data.py:120`).

**Invariants / error modes:** unchanged. The body is moved verbatim; `auto_dedent` keeps its
keyword-only shape at both call sites (`_model_to_map` defaults it to `False`, `_model_to_data`
requires it — that stays as it is, at the callers). The returned mapping's iteration order is
Pydantic field-declaration order, which — per probe P1 — no consumer can observe, and the docstring
now says so instead of leaving it implied. Emitted bytes are unchanged for the fixture set and for
this repo's own regenerated workflows (see [Migration plan](#migration-plan)); this is a pure hoist,
so the claim generalises by construction rather than by coverage.

**Public vs private:** `collect_fields` takes the same no-underscore name as its two neighbours
`order_entries` and `is_empty_map`, both of which are already imported across the module boundary by
`data.py:29`. It is not added to `ghagen.emitter.__all__` (`__init__.py:28`) — the package's public
surface stays `emit` / `emit_file` / `to_data` / `CommentNode`, and the PEP 562 lazy `__getattr__`
(`__init__.py:35-44`) that keeps `models` from importing `nodes`/`data` at load time is untouched.

## What sits behind the seam

Five emission rules, behind a two-argument call:

1. meta-field exclusion (`_META_FIELDS`),
2. `exclude_unset`,
3. `exclude_none`-checked-on-the-wrapper (the subtle one — it is what lets a `Raw(None)` reach YAML
   as a present-null key, per `docs/specs/0001-python-single-pass-serialization.md:317-323`),
4. field → YAML key mapping through `spec.yaml_keys`,
5. the Step `run` dedent-at-emit rule.

**This is a locality argument, not a depth argument.** The interface
`(model, auto_dedent) -> dict[str, Any]` is barely narrower than the fourteen straight-line,
branch-free lines behind it, and the leverage is small — two callers. What the hoist buys is that
the five rules acquire **one address**: exactly the trade `order_entries` already made, and is
documented as making, in the same module (`nodes.py:59-61`).

**Deletion test, applied to `collect_fields`.** Delete it and both `_model_to_map` and
`_model_to_data` must re-grow the identical fourteen lines, `data.py` must re-acquire its
`dedent_script` / `_META_FIELDS` / `Step` imports, and the five rules go back to having two
implementations that nothing forces to agree — the exact state probes P3–P6 show the suite cannot
fully detect. Complexity reappears across both callers: an earned keep, not a pass-through. Contrast
a genuine pass-through: a hypothetical `_yaml_key(field_name, spec)` wrapping the single
`spec.yaml_keys.get(...)` lookup would be a one-line indirection whose deletion costs nothing. That
is not what this is; the lookup stays inline inside `collect_fields`.

The seam is also **where proposal 10 lands its change**: after this, "collect from the spec instead
of from `model_fields`" is one edit in one function instead of the same edit twice in two modules —
though not _only_ one edit; see the [10 handoff](#scope-boundaries-vs-siblings) for what else that
edit takes with it.

## Migration plan

Pre-1.0; a clean move, no shim, no deprecation.

1. Add `collect_fields` to `nodes.py` after `order_entries` (`:84`), body moved verbatim from
   `_model_to_map`.
2. Replace `_model_to_map`'s `is_step` binding (`:170`) and loop (`:172-184`) with the single call.
3. Replace `_model_to_data`'s `is_step` binding (`:102`) and loop (`:104-115`) with the same call;
   import `collect_fields` in the existing `from ghagen.emitter.nodes import …` line (`:29`) and drop
   `_META_FIELDS` from it; delete the now-unused `dedent_script` (`:27`) and `Step` (`:31`) imports.
4. Add `needs=[]` to the `Job` in `test_to_data.py`'s
   `test_deep_structure_matches_emitted_yaml` fixture (`:144-156`, one line after `runs_on` at
   `:145`) — the fixture-coverage fix.
5. Add `packages/python/tests/test_emitter/test_field_collection.py` (see below).
6. Gates: `scripts/test.sh py`, `scripts/lint.sh py` (ruff only on the `py` scope — it will confirm
   step 3's three imports are dead, a mechanical check that the hoist was complete),
   `scripts/typecheck.sh py`, `uv run ghagen check-synced` (byte-identical regeneration of this
   repo's own workflows). Note that a bare `scripts/lint.sh` defaults to the `all` scope
   (`scripts/lint.sh:6`) and pulls in the `docs/` npm toolchain (`:20-26`), which needs
   `npm ci --prefix docs`; the `py` scope does not.

No TypeScript step. No fixture, workflow, or schema-snapshot change: emitted bytes are unchanged.

## Test impact

**Modified — one line.** The cross-pass agreement invariant **already has a home**, and it is a
better oracle than a new test would be: `test_deep_structure_matches_emitted_yaml`
(`packages/python/tests/test_emitter/test_to_data.py:130-161`) builds a rich `Workflow` (`:136-158`),
emits it, parses the emitted YAML, and asserts `to_data(wf, auto_dedent=True) == parsed`. It
compares the observation surface against the **real byte path**, not against the other pass's
in-memory output.

Its only defect is fixture coverage: the document contains no empty list, so an empty-list
divergence is unobservable. Adding **`needs=[]`** to its `Job` (`:144-156`) fixes that. Measured
against the real loop-level mutations:

| Tree state                                           | `test_deep_structure_matches_emitted_yaml` |
| ---------------------------------------------------- | ------------------------------------------ |
| baseline, fixture unchanged                          | passes                                     |
| P4 (`nodes.py` skips empty lists), fixture unchanged | **passes** — the miss                      |
| P5 (`data.py` skips empty lists), fixture unchanged  | **passes** — the miss                      |
| baseline, `needs=[]` added                           | passes                                     |
| P4, `needs=[]` added                                 | **fails**                                  |
| P5, `needs=[]` added                                 | **fails**                                  |

One line, no new file, and it closes both probes the suite was blind to.

**New — `packages/python/tests/test_emitter/test_field_collection.py`:** per-rule unit tests over
`collect_fields`, giving the newly named seam direct coverage at rule level:

- one test per collection rule against a small model — a meta field is never collected; an unset
  field with a non-`None` default is not collected; a `None` field is not collected while a
  `Raw(None)` field _is_; a field with a `yaml_keys` alias lands under the aliased key, and an
  unaliased field lands under its own name (the `.get(field_name, field_name)` fallback).
- one dedent test: `collect_fields(step, auto_dedent=True)` dedents `run`, `auto_dedent=False` does
  not.

Rule 3's wrapper subtlety is today asserted only **end-to-end**, via
`test_models/test_serialize.py:26-39` and `test_models/test_document.py:39-47` (the empty
`workflow_dispatch` → present-null path). Pinning it at rule level is new.

**Deliberately not written here:** a second cross-pass agreement test. Building one — walking the
tree and comparing `to_data(node)` against `dict(_model_to_map(node))` per node — would put a
_weaker_ oracle (private function to private function, bypassing the byte path) in a _second_ home
for an invariant that already has one. That is the duplication this proposal exists to remove, and
it would be perverse to add it in the same change.

**Also deliberately not written:** any assertion on `collect_fields`' return _order_. Per P1, no
consumer can observe it; that fact lives in the docstring instead of in a test that would pin an
unobservable.

**Total:** 562 → 562, plus the new file's tests. No existing test's expectations change; the one
edit is a fixture addition that makes an existing assertion stricter.

**Why not just fix the fixture and leave the duplication?** The fixture fix catches divergence but
does not prevent it, and it would leave the five rules with two implementations. The hoist makes one
whole class of divergence unexpressible; the fixture fix covers the class that remains — including
divergence _downstream_ of collection (a rule added to `_model_to_map`'s emission loop at
`nodes.py:193-204` but not to `_model_to_data`'s at `data.py:120-141`), which the hoist alone does
not prevent. Both, not either.

One caveat that the existing test already encodes and must keep encoding: `_model_to_map` runs
`post_process` (`nodes.py:206-207`) and `_model_to_data` deliberately does not (`data.py:96-97`), so
the fixture sets no `post_process` — it asserts the passes agree, not that `to_data` reproduces the
hook.

## Risks & alternatives

- **Alternative: a new `packages/python/src/ghagen/emitter/fields.py` module** holding
  `collect_fields` plus the other backend-neutral pieces `data.py` already borrows from `nodes.py`
  (`_META_FIELDS`, `order_entries`, `is_empty_map`). Architecturally tidier — it names the shared
  slice that is quietly accreting inside a module whose docstring calls itself "the emitter's
  recursion core: value → ruamel node dispatch" (`nodes.py:1`). **Rejected for this proposal**, on
  three grounds. (a) Precedent: `order_entries` and `is_empty_map` are already sited in `nodes.py`
  for the same shared-by-both-passes reason; putting the third one somewhere else splits the group
  rather than fixing it. (b) Scheduling: moving `order_entries` collides head-on with
  [10](./10-delete-modelspec-order.md), which rewrites its body, and moving `_META_FIELDS` drags
  `test_spec.py:16` in, which 10 also rewrites. (c) Blast radius: siting in `nodes.py` is what keeps
  `test_yaml_writer.py` out of this proposal's table entirely **and drops `data.py` out of 10's
  Files-involved table** (see the handoff below). If the slice is worth naming, it is worth naming
  _after_ 10 lands, as a pure move with no logic change — noted, not proposed here.
- **Risk: the hoist changes emitted bytes.** Essentially nil — the body moves verbatim. The
  end-to-end checks are `uv run ghagen check-synced` (this repo's own workflows regenerate
  byte-identically) and the ten `fixtures/expected/*.yml` snapshots. Bounded honestly: those ten
  fixtures do not exercise all 31 spec-carrying models, so the byte guarantee rests on the move
  being verbatim, with the fixtures and `check-synced` as corroboration rather than proof.
- **Effort: S, confirmed.** Two source files, ~24 lines removed, one function added, one test-fixture
  line, one new unit-test file. The review lowered rather than raised the work by replacing a new
  agreement test with a one-line fixture edit. Every probe and citation in this document was
  re-verified against HEAD; nothing found raises the estimate.
- **Risk: `collect_fields` is a two-caller module, so the seam is hypothetical.** Under the corpus
  rule _one adapter = hypothetical seam, two adapters = real seam_, two callers is exactly the
  threshold — and unlike a plugin seam, these two callers are not interchangeable adapters, they are
  two mandatory passes over the same data that the design requires to agree. The deletion test above
  is the real justification, not the caller count.
- **Rejected: "delete `_model_to_data` and derive `to_data` from the ruamel walk."** That would
  remove the duplication outright, but it reintroduces exactly what `data.py:9-15` exists to avoid —
  the observation surface would then run the ruamel-backend passes and depend on ruamel node types,
  which [02](./02-emitter-test-seam.md) and the `data.py` docstring rule out. Two passes are
  intentional; only the duplicated collection is not.

### Scope boundaries vs siblings

- **[10](./10-delete-modelspec-order.md) — delete `order` from `ModelSpec`.** Direct overlap, and
  10's own table names it: it changes "`raw` construction (`:172-184`) iterates `spec.yaml_keys`
  instead of `model_fields`" in `nodes.py` **and** "same `raw` change (`:104-115`)" in `data.py`.
  10 runs solo and last, and depends on this merging first.

  **The handoff, precisely.** This proposal moves those two loops into one `collect_fields`, changing
  _nothing_ about what they do — the iteration source stays `type(model).model_fields`,
  `spec.yaml_keys` stays the key-name lookup only. `collect_fields` never reads `spec.order`, so it
  survives 10 structurally.

  10 then changes the loop head **once**, inside `collect_fields`:
  `for field_name in type(model).model_fields:` → `for field_name in spec.yaml_keys:`. That is one
  line of _diff_, but it is **not** an isolated edit, and 10 must not discover the rest mid-sweep:
  1. **The `_META_FIELDS` skip becomes structurally dead.** A meta field can never appear in
     `spec.yaml_keys` — `test_spec.py:44-48` asserts `set(spec.yaml_keys) == set(model_fields) - _META_FIELDS`
     for every model, so the guard can no longer fire. Delete it or justify keeping it.
  2. **The `.get(field_name, field_name)` default becomes unreachable**, and its removal is a silent
     semantic change: a field present in `model_fields` but absent from `spec.yaml_keys` goes from
     "emit under the field name" to "not emitted at all". `test_spec.py:44-48` forbids that state
     today, so nothing breaks — but the behaviour is now enforced by a test rather than by the code.
  3. **Docstring rules 1 and 4 are invalidated**, as is the closing line "Returns the
     `{yaml_key: value}` mapping in Pydantic field-declaration order" — after 10 the order is
     `spec.yaml_keys` declaration order, which is exactly what makes it load-bearing (rendering
     `spec.order` derivable, 10's thesis). The docstring is part of 10's diff.
  4. **Two of this proposal's new unit tests must be rewritten**: the meta-field test becomes
     unfalsifiable (the branch it exercises no longer exists), and the rule-4 test's unaliased-field
     case inverts from "lands under its own name" to "is dropped".
  5. **`_META_FIELDS` is left with zero production readers** — after 10 it is referenced only by its
     own definition (`nodes.py:30`) and by `test_spec.py:16,36`. 10 already rewrites `test_spec.py`;
     it should decide there whether `_META_FIELDS` survives as a test-only constant or moves.

  10's Files-involved rows shrink accordingly: **`data.py` drops out of 10's table entirely**, and
  10's `nodes.py` row narrows to `order_entries` plus the `collect_fields` loop head and docstring.
  Probe P6 shows that edit is currently invisible to the suite — 10 supplies its own guard for it;
  this proposal does not attempt to.

- **[09](./09-construction-time-validation-parity.md) — construction-time validation parity.**
  **No overlap, confirmed from this side.** 09's `SPEC.patterns` check is _construction-time_ — a
  Pydantic validator on `GhagenModel` in `models/_base.py`, mirroring TypeScript's unknown-key
  rejection inside `buildYamlData` (`_base.ts:315-365`). `collect_fields` is _emission-time_, in
  `emitter/nodes.py`. Different phase, different package, different file; 09's Files-involved table
  names neither `emitter/nodes.py` nor `emitter/data.py`. **Stated as an invariant, not a
  coincidence: `collect_fields` does not become the home for spec-driven per-field validation.**
  Validation belongs where the value enters the model; collection decides only what is emitted.
- **[12](./12-ts-comment-geometry-module.md) — TS comment geometry.** Confirmed no overlap from this
  side: 12's Python rows are `emitter/comments.py`, `emitter/yaml_writer.py`,
  `tests/test_emitter/test_comments.py`, `tests/test_emitter/test_yaml_writer.py` and
  `tests/test_integration/test_snapshots.py`, and its new files are `comment_geometry.*`. It touches
  neither `nodes.py` nor `data.py`, and it does not touch `test_to_data.py`.
- **[13](./13-unify-format-header-contract.md) — the `format_header` contract.** Confirmed no overlap:
  13's Python rows are `emitter/header.py` and `emitter/yaml_writer.py` (plus header tests,
  `test_snapshots.py` and the fixture set). Neither `nodes.py`, `data.py` nor `test_to_data.py`
  appears. Comment geometry and header rendering both operate on the node tree _after_ emission;
  field collection happens before it.
- **[24](./24-narrow-walk.md) — narrow `walk()`.** The hoisted module shares **nothing** with it, and
  that is a deliberate invariant rather than a coincidence. `GhagenModel.children()`
  (`packages/python/src/ghagen/models/_base.py:142-150`) is a _third_ `type(self).model_fields` loop
  in the Python port, but with opposite semantics: no `_META_FIELDS` skip, no `exclude_unset`, no
  `exclude_none`, no YAML-key mapping — traversal must reach every nested model regardless of whether
  it will be emitted, so it must **not** consume `collect_fields`.
  `docs/specs/0001-python-single-pass-serialization.md:301-302` already states the rule: "`children()`
  / `walk()` / `_scan_for_models` are untouched — they are a separate traversal primitive, not part
  of serialization." 24's own `:585-596` concurs and adds the right refinement: 24 makes `children()`
  skip `"extras"` and re-scan it last, an _ordering_ rule, not the emission-eligibility rule
  `collect_fields` owns.

  **Changed by the amendment above — the file contact between 21 and 24 dissolves.** The earlier
  draft of this proposal put its agreement test in a new file and had it call `GhagenModel.walk()`,
  which gave 24 a call site to update; 24 records that in two places, a conditional Files-involved
  row at `24` §Not touched, deliberately and a reciprocal item at `24` §Test impact. With the agreement invariant staying in
  `test_to_data.py` — which does not call `walk()` — and `test_field_collection.py` reduced to
  per-rule unit tests that have no reason to traverse, **nothing this proposal writes calls
  `walk()`**, and none of this proposal's tests builds a tree whose `extras` node count 24 could
  perturb. `21 — 24` is now a semantic agreement only, with no shared file in either direction; both
  of 24's items should be struck when 24 is next revised. Nothing in `nodes.py` or `data.py` calls
  `walk()` either.

- **Ports:** no TypeScript sibling is affected, because there is no TypeScript change — see
  [Problem](#problem), point 4. Parity is _narrowed and satisfied_ rather than strained: Python ends
  up with a single collection **site** for membership, matching TypeScript's single site. It does not
  match TypeScript's collection _phase_ (construction vs emission) or _source_ (`fieldMap` vs
  `model_fields`), and this proposal does not claim it does — 10 closes the source gap; the phase gap
  is closed by nothing in this round and is not a defect in either port.

## ADR / CONTEXT.md impact

- **ADR-0001 (Document serialization seam), 2026-07-21 amendment — reinforced, not reopened.** The
  amendment's stated reason for moving recursion into the Emitter was that "the Commented/Raw/model/
  dict/list dispatch [was] implemented three times." This proposal applies the same reasoning one
  level up, to the field walk that feeds that dispatch: the Emitter owns serialization, and inside
  the Emitter each serialization rule should have one home. Models are untouched.
- **ADR-0002 (no construction-time config globals) — respected.** The Step `run` dedent stays a
  serialization-time transformation applied at collection, with no model mutation and no copy; the
  docstring in the proposed code says so explicitly, which is more than either current call site does.
- **No ADR contradicted, and no new ADR needed.** This is an internal refactor within one package,
  with no new decision to record.
- **CONTEXT.md — zero regions claimed, in either port.** This proposal makes **no** edit to
  `packages/python/CONTEXT.md` or `packages/typescript/CONTEXT.md` and claims no region in either;
  both files are free for their other claimants. `collect_fields` introduces no domain term — it is
  an implementation-internal seam inside the existing **Emitter**, which the Python glossary
  (`packages/python/CONTEXT.md:34-38`) already describes as owning all serialization recursion and
  exposing `to_data()`. Adding it would be glossary noise, and the **ModelSpec** / **OrderMode**
  entries it would sit near (`:40-47`) are being rewritten by
  [10](./10-delete-modelspec-order.md). If a note is wanted after 10 lands, the natural place is one
  clause in the Emitter entry: that field _membership_, _order_, and _present-null_ each have a single
  home shared by both Emitter passes — a follow-up, not part of this change.
- **`docs/specs/0001-python-single-pass-serialization.md` — cited, not edited.** It is the landed
  record of the single-pass migration and states the collection contract normatively at `:304-326`
  (§4). `collect_fields` is that contract finally having one implementation; the spec text needs no
  change (its §3.3 code block already predates the move of serialization out of `GhagenModel`, so it
  reads as history either way).
- **`docs/issues/` — one new entry to file, not part of this change.** The TypeScript Step-`run`
  dedent is implemented twice with different `autoDedent` defaults — `dedentSteps`
  (`yaml-writer.ts:44-52`, from `toYaml` at `:425`, `?? true`) and inline in `modelToData`
  (`:313,:321-322`, from `toData` at `:302`, `?? false`). That is a real duplication of rule 5 in the
  port this proposal holds up as the reference, and it should be recorded rather than absorbed into a
  Python-only hoist.
