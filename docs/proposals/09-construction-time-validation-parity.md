# 09 — Construction-time validation actually validates, and both ports agree on what it rejects

**Status:** proposed | **Ports:** typescript (led) / python (mirror) | **Effort:** L | **Depends on:** builds on the `extra="forbid"` (944bd90) and `Raw._validate` (3741a1d) hotfixes already on `main`; **ordered before [22](./22-collapse-ts-factory-bodies.md)** (09 → 22); **conflicts** with [11](./11-shared-spec-surface-table.md) (09 first) and [10](./10-delete-modelspec-order.md) (both edit `models/spec.ts` + `models/spec.py`)

Both ports' models advertise the same thing: a model validates its input when it is constructed.
Python's `CONTEXT.md:100` — "User input is validated at construction (Pydantic)." The TypeScript
port's factories carry the same promise in their doc comments (`image-snapshot.ts:18` documents
the accepted `version` grammar) while `CONTEXT.md:105` says the opposite — "There is no runtime
validation." That is not a language-idiom difference; it is an **interface** claim that one
**implementation** holds and the other does not, with no test binding either.

Two thirds of this landed as hotfixes this morning, both Python-only. What is left is the harder
half: the TypeScript port holds **neither** invariant, and the one value grammar either port
enforces is enforced in one port, wrongly, from a hand-copied regex with no link back to its source.

**Effort is L, not M.** With (b) in, this is 31 modified + 3 new files across both ports; with (b)
deferred (see below) it is 24 modified + 2 new, plus a new `ModelSpec` field that both ports'
construction paths must consume. Sibling [11] is L at 22 modified + 2 new and sibling [10] is L; 09
has more modified files than either in both configurations.

## Files involved

### Modified — unconditional

| Path                                                               | Lines | Role in this proposal                                                                                                                                |
| ------------------------------------------------------------------ | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/typescript/src/models/spec.ts`                           | 91    | fourth declarative field `patterns?: Readonly<Record<string, RegExp>>`, beside `wrap` (`:65`), `dynamicKeys` (`:72`), `presentNullWhenEmpty` (`:90`) |
| `packages/typescript/src/models/_base.ts`                          | 532   | `buildYamlData` gains the unknown-key rejection and the `spec.patterns` check; new `ModelInputError`                                                 |
| `packages/typescript/src/models/image-snapshot.ts`                 | 52    | `IMAGE_SNAPSHOT_SPEC` gains `patterns: { version: … }`; the factory body is untouched                                                                |
| `packages/typescript/src/models/permissions.ts`                    | 96    | add the missing `Raw<string>` escape hatch to every scope (13 today, **16 after [11]**)                                                              |
| `packages/typescript/src/models/trigger.ts`                        | 496   | add `Raw<string>` to `WorkflowDispatchInputDef.type` (`:177`) and `WorkflowCallInputDef.type` (`:270`)                                               |
| `packages/typescript/src/index.ts`                                 | 203   | export `ModelInputError` from the barrel                                                                                                             |
| `packages/typescript/src/_docs-api-output.ts`                      | 8     | TypeDoc entry point for `ModelInputError` (hand-synced with the barrel; `raw` is already there at `:8`)                                              |
| `packages/typescript/src/models/_base.test.ts`                     | 208   | rewrite the test that pins the silent drop (`:188-196`)                                                                                              |
| `packages/typescript/src/models/image-snapshot.test.ts`            | 84    | new version-grammar cases                                                                                                                            |
| `packages/typescript/src/models/conformance.test.ts`               | 191   | bind this port's `spec.patterns` onto the shared value table                                                                                         |
| `packages/typescript/src/emitter/to-data.test.ts`                  | 150   | fix the live `strategy({ matrix: … })` bug at `:126`                                                                                                 |
| `packages/python/src/ghagen/models/spec.py`                        | 41    | mirror field `patterns: Mapping[str, re.Pattern[str]]`, beside `present_null_when_empty` (`:41`)                                                     |
| `packages/python/src/ghagen/models/_base.py`                       | 231   | `GhagenModel` gains the one `model_validator` that applies `SPEC.patterns` — the peer of `buildYamlData`'s check                                     |
| `packages/python/src/ghagen/models/image_snapshot.py`              | 46    | `_VERSION_PATTERN` moves into the spec with `re.ASCII`; the hand-written `_validate_version` (`:38-46`) is **deleted**                               |
| `packages/python/src/ghagen/models/trigger.py`                     | 250   | tighten `WorkflowDispatchInput.type` (`:164`) to the 5-member set and `WorkflowCallInput.type` (`:184`) to the **3**-member set, each `+ Raw[str]`   |
| `packages/python/tests/test_models/test_image_snapshot.py`         | 81    | trailing-newline and Unicode-digit cases                                                                                                             |
| `packages/python/tests/test_models/test_validation.py`             | 64    | the trigger-`type` constraints join the Raw-is-opt-in class                                                                                          |
| `packages/python/tests/test_schema/test_conformance.py`            | 203   | bind this port's `SPEC.patterns` onto the shared value table                                                                                         |
| `docs/src/content/docs/python/api/job.md`                          | 172   | `ImageSnapshot.version` row (`:172`) states the grammar and that it is enforced                                                                      |
| `docs/src/content/docs/python/api/triggers.md`                     | 234   | the two `type` rows (`:155` dispatch, `:212` workflow-call) restate the closed sets — **also [11]'s file**                                           |
| `docs/src/content/docs/guides/escape-hatches.mdx`                  | 218   | `raw()` is now available on TS permission scopes and trigger input types (`:43` names the rule)                                                      |
| `packages/typescript/CONTEXT.md`                                   | 119   | `:105` only — "There is no runtime validation" is no longer true; see last section                                                                   |
| `packages/python/CONTEXT.md`                                       | 114   | `:100` only — mirror the construction-time-invariant wording                                                                                         |
| `docs/adr/0003-schema-sync-dev-only-and-test-based-conformance.md` | 53    | amendment drawing the line this proposal crosses — **also [11]'s amendment target**; see last section                                                |

### Modified — (b) only, pending the Phase 3 decision below

| Path                                                  | Lines | Role in this proposal                                                                                                                        |
| ----------------------------------------------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/typescript/tsconfig.json`                   | 28    | `exclude` (`:21-27`) drops `src/**/*.test.ts` (`:24`) and `src/integration/test-utils.ts` (`:25`); **`src/paths.ts` (`:26`) stays excluded** |
| `packages/typescript/package.json`                    | 76    | `typecheck` script points at the test-inclusive config; `build` is untouched and keeps emitting from `tsconfig.json`                         |
| `packages/typescript/src/emitter/yaml-writer.test.ts` | 244   | 22 pre-existing `toYaml(model)` `Model → Document` narrowing errors (TS2345)                                                                 |
| `packages/typescript/src/models/trigger.test.ts`      | 183   | 1 pre-existing missing-`jobs` error (`:172`)                                                                                                 |
| `packages/typescript/src/pin/collect.test.ts`         | 208   | 1 pre-existing missing-`using` error (`:162`)                                                                                                |
| `packages/typescript/src/pin/sites.test.ts`           | 195   | 1 pre-existing missing-`using` error (`:124`)                                                                                                |
| `packages/typescript/src/integration/test-utils.ts`   | 52    | 2 pre-existing Ajv ESM default-import errors (`:20-21`)                                                                                      |

The two `tsconfig` designs are **not** both proposed: a _new_ `tsconfig.typecheck.json` is the one
chosen, and the base `tsconfig.json` change is limited to nothing at all under that design. The row
above describes the rejected in-place variant only so the reader can see what was weighed; the
migration plan implements the new-file variant.

### New

| Path                                                | Role in this proposal                                                                            |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `schema/conformance-values.yml`                     | shared value-grammar table: schema pattern location + accept/reject vectors, read by both sweeps |
| `packages/typescript/src/models/validation.test.ts` | the TS peer of `packages/python/tests/test_models/test_validation.py`                            |
| `packages/typescript/tsconfig.typecheck.json`       | **(b) only** — test-inclusive `tsc --noEmit` config extending `tsconfig.json`                    |

`schema/workflow_schema.json` (1823) is **read** by the new table's path, never edited. Nothing in
`.github/` changes: CI already runs `scripts/typecheck.sh ts` (`.github/workflows/ci.yml:105`),
which shells out to `npm run typecheck`. The TypeScript API pages under
`docs/src/content/docs/typescript/api/` are gitignored TypeDoc output (`.gitignore:45`) and carry no
rows.

## Problem

### 1. TypeScript silently drops unknown input keys — live

`buildYamlData` (`_base.ts:315`) is the single input→`data` path in the TS port: **27**
`buildModel<…>` call sites across eight model modules (`rg 'buildModel<' src -g '!*.test.ts'`
returns 28 matches, one of which is the declaration at `_base.ts:371`), and `new Model(...)` appears
only inside `_base.ts` itself, at `:233` (clone) and `:376` (inside `buildModel`). It iterates the
**spec**, not the input:

```ts
// packages/typescript/src/models/_base.ts:322-349
for (const [camelKey, yamlKey] of Object.entries(spec.fieldMap)) {
  let value = data[camelKey];
  if (value === undefined) {
    continue;
  }
  …
  yamlData[yamlKey] = value;
}
```

An input key not named in `spec.fieldMap` is never read, so it never reaches `data`, so it never
reaches YAML. The only escape is the declared `spec.dynamicKeys` passthrough (`_base.ts:355-362`),
which exactly one spec sets (`MATRIX_SPEC`, `job.ts:79`). This is the peer of the `extra="ignore"`
default that `GhagenModel.model_config` carried until 944bd90 and that now reads `extra="forbid"`
(`packages/python/src/ghagen/models/_base.py:93`).

**The compile-time net catches one position out of five.** `WithMeta<T> = T & ModelMeta`
(`_base.ts:139`); the only compile-time defence against an unknown key is TypeScript's
excess-property check, which fires solely on a **fresh object literal** in the argument position.
Verified against this tree with `npx tsc --noEmit` over a symlink mirror of `packages/typescript/`
under `$TMPDIR` (nothing written into the checkout):

| Call shape                                                                               | `tsc`      | runtime                       |
| ---------------------------------------------------------------------------------------- | ---------- | ----------------------------- |
| `step({ name: "Build", nmae: "Build" })`                                                 | **TS2353** | —                             |
| `const i = { nmae: "Build", run: "echo hi" }; step(i)`                                   | clean      | `data === { run: "echo hi" }` |
| `step({ run: "echo hi", ...{ nmae: "Build" } })`                                         | clean      | key dropped                   |
| `step({ nmae: "Build" } as unknown as WithMeta<StepInput>)`                              | clean      | key dropped                   |
| `const i = { run: "echo hi", nmae: "Build" } satisfies Record<string, unknown>; step(i)` | clean      | key dropped                   |

Reproduced independently on `on()`, whose input has 33 optional properties
(`OnInput`, `trigger.ts:346-414`): a fresh literal carrying
an unmodeled event is **TS2353** (`on({ push: pushTrigger({}), totallyNotAnEvent: {} })`), and
**TS2561** with a rename suggestion when the key near-misses a modelled one
(`merge_group` → "Did you mean to write `mergeGroup`?"); the same key routed through a `const` or a
spread is clean in both cases. Four of the five shapes are ordinary authoring: a helper that builds
an input object and hands it to a factory, a `{ ...base, ...overrides }` merge, a
`satisfies`-annotated config constant. That is the whole point of using a real programming language
to generate YAML (`AGENTS.md`, "Philosophy") — and it is exactly where the compile-time net has
holes.

Contrast `Raw` (see §2): those constraints are enforced by **assignability**, which survives every
one of those indirections. Excess-property checking is the weakest check TypeScript has, and it is
the only thing standing between a typo and a silently missing YAML key.

**It has already caused a live bug in this repo.** `StrategyInput`'s matrix field is named
`matrix_` (`packages/typescript/src/models/job.ts:93`), and `STRATEGY_SPEC.fieldMap` maps
`matrix_ → "matrix"` (`job.ts:120`). The Python peer's field is plain `matrix`
(`packages/python/src/ghagen/models/job.py:129`). A test in the tree writes the Python spelling:

```ts
// packages/typescript/src/emitter/to-data.test.ts:125-127
strategy: strategy({
  matrix: matrix({ extras: { "python-version": ["3.11", "3.12"] } }),
}),
```

`matrix` is not in `STRATEGY_SPEC.fieldMap`, so it is dropped. Confirmed by running the expression:
`toData(strategy({ matrix: matrix({ extras: { "python-version": ["3.11"] } }) }))` returns `{}`,
while the `matrix_` spelling returns `{"matrix":{"python-version":["3.11"]}}`. Inside the test's
document that becomes `strategy: {}`. **The test still passes** — it asserts
`toData(wf)` deep-equals `parse(toYaml(wf))`, and both sides of that oracle drop the key
identically. A round-trip oracle cannot see input that never entered the model.

`tsc` would have caught this one, with the right suggestion —
`to-data.test.ts(126,13): error TS2561: Object literal may only specify known properties, but
'matrix' does not exist in type 'WithMeta<StrategyInput>'. Did you mean to write 'matrix_'?` —
except that `tsconfig.json:24` excludes `src/**/*.test.ts`, so **no TypeScript test file in this
repo is ever typechecked.** Reproduced verbatim by running `tsc` over the symlink mirror with a
test-inclusive config.

**And one existing test pins the drop as intended behaviour**, which is why nobody noticed:

```ts
// packages/typescript/src/models/_base.test.ts:188-196
it("skips undefined values and keys not in the field map", () => {
  …
  const data = { runsOn: "ubuntu-latest", timeoutMinutes: undefined, extra: "ignored" };
  expect(buildYamlData(spec, data)).toEqual({ "runs-on": "ubuntu-latest" });
});
```

`meta.extras` is the sanctioned channel for unmodeled YAML keys in both ports
(`_base.ts:117`, `_base.py:100`, `docs/src/content/docs/guides/escape-hatches.mdx:47-49`), so the
drop buys nothing.

**Blast radius of closing it is two tests.** Patching `buildYamlData` to throw on any key not in
`fieldMap` (when `!spec.dynamicKeys`) and running the full vitest suite gives **2 failed / 513
passed of 515**: `to-data.test.ts` (the live bug above) and `_base.test.ts:188` (the test that pins
the drop). No factory, no transform, no CLI path, no integration snapshot relies on the drop.

### 2. The TypeScript `Raw` analogue _does_ constrain — the brief's suspicion does not hold, but the surface diverges

`Raw<T>` is a branded interface over a `unique symbol` (`_base.ts:85-101`); the only way to produce
one is `raw()` (`_base.ts:99-101`). Because `Raw<string>` sits in a **union** in the field's declared
type, the check is assignability, not excess-property checking, so it holds through every
indirection that defeats §1. Verified — all three of these are `tsc` errors on this tree:

```
step({ ...{ run: "x", shell: "powershel" } })                       → TS2345 'string' is not
step({ run: "x", ...{ shell: "powershel" } })                       → TS2345 '"powershel"' is not
step({ run: "x", shell: "powershel" } satisfies Record<string,…>)   → TS2345 'string' is not
```

So the TS peer of the `Raw._validate` auto-wrap hole (3741a1d, `_raw.py:70-85`) **does not exist**.
Required-field checks behave the same way (`imageSnapshot({ version: "1" })` through a variable is
TS2345, "Property 'imageName' is missing"). This is the one place the ports are genuinely,
defensibly different: TS enforces union membership and required-ness at compile time, Python at
construction. No change is warranted.

What _is_ wrong is the **surface** the two ports offer around `Raw`, and it is wrong in both
directions:

- **TS permission scopes have no escape hatch at all.** `PermissionsInput`
  (`packages/typescript/src/models/permissions.ts:11-38`) types every one of its 13 scopes as bare
  `PermissionLevel`. Python types all 13 as `PermissionLevel | Raw[str] | None`
  (`packages/python/src/ghagen/models/permissions.py:55-67`) — and 3741a1d's message names those
  scopes as a headline beneficiary. `permissions({ contents: raw("future-level") })` is a `tsc`
  error today; `Permissions(contents=Raw("future-level"))` is a documented, tested Python call
  (`test_validation.py:59-60`). **Live**, and it contradicts `AGENTS.md`'s "allow for customization
  with escape hatches" plus `escape-hatches.mdx:43`'s claim that `raw` is for "a field [with] a
  constrained type (like `shell`'s predefined set…)". **[11] adds three more scopes**
  (`artifactMetadata`, `attestations`, `models` — 11's `:26-27`, `:152`), so the count 09 must apply
  `Raw<string>` to is **16 post-11**, not 13.
- **Python trigger input types have no constraint at all.** `WorkflowDispatchInput.type` and
  `WorkflowCallInput.type` are both `str | Raw[str] | None`
  (`packages/python/src/ghagen/models/trigger.py:164,184`) — `str` already accepts everything, so
  the `Raw[str]` member is decorative and the union constrains nothing. **Live** (Python accepts
  `type="chioce"` on either class).
- **The two TS unions are correct, different, and only one of them was surveyed.** They are _not_
  the same set, and the schema says they should not be:

  |                                  | schema                                                                                              | TS today                                        | Python today                                 |
  | -------------------------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------- | -------------------------------------------- |
  | `workflow_dispatch` input `type` | `["string","choice","boolean","number","environment"]` (`workflow_schema.json:973`)                 | 5-member union, optional (`trigger.ts:177`)     | `str \| Raw[str] \| None` (`trigger.py:164`) |
  | `workflow_call` input `type`     | `["boolean","number","string"]` (`workflow_schema.json:1702`), **`"required": ["type"]`** (`:1706`) | 3-member union, **required** (`trigger.ts:270`) | `str \| Raw[str] \| None` (`trigger.py:184`) |

  So TS has exactly the half Python is missing on _both_ rows, and Python additionally has an
  optionality divergence on the workflow-call row that the schema settles. Widening Python's
  `WorkflowCallInput.type` to the 5-member dispatch set would make Python accept `"choice"` and
  `"environment"` where both the schema and the TS port reject them — a _new_ divergence
  manufactured inside a parity proposal. (d) below tightens each class to its own set.

### 3. `ImageSnapshot`'s version grammar — three grammars where there should be one

The canonical Snapshot is unambiguous:

```json
// schema/workflow_schema.json:732-736
"version": {
  "$comment": "https://docs.github.com/…#specifying-a-version-in-your-workflow",
  "pattern": "^\\d+(\\.\\d+|\\*)?$",
  "type": "string"
}
```

**Python implements a superset of it, in two independent ways.** `image_snapshot.py:21`
hand-copies the pattern; the validator uses `re.match`:

```python
# packages/python/src/ghagen/models/image_snapshot.py:38-46
@field_validator("version")
@classmethod
def _validate_version(cls, value: str | None) -> str | None:
    if value is not None and not _VERSION_PATTERN.match(value):
        raise ValueError(...)
```

1. **`re.match` anchors only the start, and Python's `$` matches before a trailing newline**, so the
   accepted language is _schema language ∪ {s + "\n"}_. Verified against this tree:
   `ImageSnapshot(image_name="custom", version="1\n")` constructs, and `to_data(...)` returns
   `{'image-name': 'custom', 'version': '1\n'}` — a value the schema rejects, headed for the
   emitter.
2. **`\d` is Unicode by default in Python's `re`, and ASCII-only in ECMA-262.** Even with
   `re.fullmatch` applied, `ImageSnapshot(image_name="x", version="١")` (ARABIC-INDIC DIGIT
   ONE) still constructs, while the identical pattern under JavaScript's `/^\d+(\.\d+|\*)?$/.test()`
   is false — and JSON Schema's regex dialect is ECMA-262, so the schema rejects it too. Verified on
   this tree: `re.compile(r"^\d+(\.\d+|\*)?$").fullmatch("١")` is truthy;
   `re.compile(r"^\d+(\.\d+|\*)?$", re.ASCII).fullmatch("١")` is `None`, and the flag leaves
   `.pattern` byte-identical (`re.ASCII` changes matching, not the source string), so pattern
   identity against the Snapshot survives the fix. `re.ASCII` still accepts every schema-valid
   vector (`"1"`, `"01"`, `"1.2"`, `"12.34"`, `"1*"` — all verified).

Both are dialect defects in the port that supposedly enforces the grammar, and neither is visible to
a shared pattern **string**: `.pattern` is identical in all three worlds. Only executed vectors
catch them, which is why the shared table below carries vectors and not just a path.

**TypeScript implements nothing.** `ImageSnapshotInput.version` is `string`
(`packages/typescript/src/models/image-snapshot.ts:19`) with the grammar stated only in the doc
comment on the line above (`:18`) — "Optional image version (e.g. `"1"`, `"1.2"`, `"1*"`). Patch
versions are not supported." `imageSnapshot()` (`:49-52`) hands the input straight to `buildModel`.
Every one of these constructs and emits, verified by running them:

| `version`                                                             | schema     | Python (today)     | TypeScript (today)                                                  |
| --------------------------------------------------------------------- | ---------- | ------------------ | ------------------------------------------------------------------- |
| `"1"` `"01"` `"1.2"` `"12.34"` `"1*"`                                 | accept     | accept             | accept                                                              |
| `"1\n"` `"1.2\n"` `"1*\n"`                                            | **reject** | **accept** (bug 1) | reject-by-luck (no check runs, but the value is also never checked) |
| `"١"` `"١.٢"`                                                         | **reject** | **accept** (bug 2) | reject-by-luck, as above                                            |
| `""` `" 1"` `"1."` `"1.2.3"` `"1.*"` `"1.2*"` `"*"` `"v1"` `"latest"` | reject     | reject             | **accept**                                                          |

The ports agree on exactly one row: the schema language. They disagree on the other three. Both
halves are **live**: `imageSnapshot({ imageName: "x", version: "9.9.9" })` emits `version: 9.9.9`
into a workflow file today.

`image_name` is unconstrained in both ports; the schema constrains it only to `type: string`
(`workflow_schema.json:729-731`), so that is correct and stays.

### 4. Nothing binds any of this

`schema/conformance-scopes.yml` and `schema/conformance-gaps.yml` already give the two ports a
shared, machine-readable conformance table with a key-set parity guard
(`conformance.test.ts:39,76-78,182-189`; `test_conformance.py:46,93,186-203`). It covers **property
coverage** only — which keys a `ModelSpec` / model exposes. No shared artifact says anything about
what **values** a field accepts, so the version grammar exists as a regex literal in one port, a
sentence in a doc comment in the other, and a JSON string in the Snapshot, with no assertion tying
any two of them together. Neither port's conformance sweep would notice if the upstream pattern
changed.

## Current interface

- **Python `GhagenModel`** — construction validates: unknown keywords raise (`_base.py:93`), union
  membership is enforced, `Raw` is opt-in (`_raw.py:70-85`), and `ImageSnapshot.version` is checked
  by a per-model `field_validator` against a hand-copied regex whose dialect is wrong twice.
- **Python `ModelSpec`** (`spec.py:39-41`) — `yaml_keys`, `order`, `present_null_when_empty`. Read
  only by the Emitter; nothing in the spec participates in construction.
- **TypeScript `ModelSpec`** (`spec.ts:57-91`) — `kind`, `fieldMap`, `order`, and three optional
  declarative fields `wrap` (`:65`), `dynamicKeys` (`:72`), `presentNullWhenEmpty` (`:90`).
  `buildYamlData` consumes `wrap` and `dynamicKeys`; the Emitter consumes `order` and
  `presentNullWhenEmpty`.
- **TypeScript factories** — `buildModel` never inspects the input beyond `spec.fieldMap`
  (`_base.ts:315-365`). Unknown keys vanish; value grammars are documented, not enforced. The
  compile-time net covers union membership and required-ness in all positions, and unknown keys in
  one position.
- **Test surface** — Python model invariants are pinned by `tests/test_models/test_validation.py`
  (64 lines, added this morning). TypeScript has no peer file, and its test sources are excluded
  from `tsc` entirely (`tsconfig.json:24`), so even the compile-time half is unenforced _in tests_
  — which is where the live `matrix` bug lives.

A caller reading either port's docs concludes "the model checks my input." A caller of the TS port
is wrong about that, in a way that costs a silently-missing YAML key.

## Proposed interface

Three changes land; one is deferred to a Phase 3 decision. None adds an imperative hook; the one new
spec field is data.

### (a) `buildYamlData` rejects unknown input keys

The peer of `extra="forbid"`, in the one place all 27 factories already funnel through:

```ts
// packages/typescript/src/models/_base.ts, before the fieldMap loop
export type ModelInputProblem =
  | { readonly reason: "unknownKeys"; readonly keys: readonly string[] }
  | {
      readonly reason: "pattern";
      readonly field: string;
      readonly value: string;
      readonly pattern: string;
    };

export class ModelInputError extends Error {
  constructor(
    readonly kind: ModelKind,
    readonly problem: ModelInputProblem,
  ) {
    super(formatModelInputProblem(kind, problem));
    this.name = "ModelInputError";
  }
}

if (!spec.dynamicKeys) {
  const known = new Set(Object.keys(spec.fieldMap));
  const unknown = Object.keys(data).filter((k) => !known.has(k));
  if (unknown.length > 0) {
    throw new ModelInputError(spec.kind, { reason: "unknownKeys", keys: unknown });
  }
}
```

The payload is a **discriminated data shape**, not a callback: one error type, one `instanceof` for
callers, and both failure modes carry the model kind and one message vocabulary. The unknown-key
message names `extras` as the sanctioned channel.

`extractMeta` (`_base.ts:144-155`) has already removed `comment`/`eolComment`/`extras`/`postProcess`
by the time `data` arrives, so metadata is unaffected. `spec.dynamicKeys` stays the declared
exemption — `MATRIX_SPEC` (`job.ts:79`) is the sole spec that sets it, and that exemption is exactly
what makes the rule expressible rather than special-cased. `ModelInputError` is exported from the
barrel (`index.ts:19-28`) and added to `_docs-api-output.ts` alongside `raw` (`:8`).

Python needs nothing here. Note one surface asymmetry that stays and is correct: TS `matrix()` takes
dynamic axes inline (`dynamicKeys: true`), Python's `Matrix` takes them via `extras=`
(`models/job.py:101-121`), so `extra="forbid"` applies to it unchanged. The **invariant** — "an
unknown key is an error unless the model declares dynamic keys" — is now identical; only the
declaration site differs by idiom. The two ports raise different exception _types_
(`ModelInputError` vs Pydantic's `ValidationError`), exactly as they already do for the unknown-key
case today; parity is of the invariant, not of the class name.

### (b) TypeScript typechecks its own tests

**Open — Phase 3 decision:** whether this becomes a 17th proposal, **25**, with 09 depending on it,
or stays inside 09 with the collisions declared. It is not decided here.

The measurement is settled either way. `tsconfig.json` stops excluding `src/**/*.test.ts` (`:24`)
and `src/integration/test-utils.ts` (`:25`) for the _typecheck_ config only — `src/paths.ts` (`:26`)
must stay excluded in both configs. The chosen shape is a new `tsconfig.typecheck.json` extending
the base with `noEmit` and the narrowed `exclude`, with `package.json`'s `typecheck` script pointing
at it; `tsconfig.json` itself is unchanged so `build` keeps emitting exactly what it emits today.
`scripts/typecheck.sh` and `.github/workflows/ci.yml:105` are unchanged.

Measured cost on this tree, by running `tsc --noEmit` against that config over a symlink mirror
under `$TMPDIR`: **28 errors across 6 files** — 25 `TS2345`, 1 `TS2561`, 1 `TS2351`, 1 `TS2349`:

- 22 × `TS2345` `Model → ActionModel` narrowing in `yaml-writer.test.ts`;
- 3 × `TS2345` missing required field — `trigger.test.ts(172,34)` (`jobs`),
  `collect.test.ts(162,26)` and `sites.test.ts(124,24)` (`using`);
- `TS2351` + `TS2349` Ajv ESM default-import at `integration/test-utils.ts(20,19)` and `(21,3)`;
- `TS2561` at `to-data.test.ts(126,13)` — the one real bug.

All mechanical. **Three reasons this is a proposal boundary, not a cheap add-on:**

1. It is **6 of the 31 modified files and the largest single share of the diff** — the most expensive
   part of this proposal, not the cheapest.
2. It has **no Python peer** and touches nothing to do with validation. The Python analogue was
   measured and rejected below (673 pyright errors).
3. **It voids a premise two siblings rely on.** [11]'s justification for putting `registry.ts` in
   `src/` rather than a test file is precisely that `tsconfig.json:24` keeps `tsc` away from every
   test file, and [22] quotes that reasoning approvingly at its `:279-286`. If (b) lands, that
   rationale evaporates and 11 must restate why `registry.ts` is a source module. It also edits five
   test files three other proposals claim (`yaml-writer.test.ts` → [10]; `trigger.test.ts` → [11];
   `_base.test.ts` → [10] and [22]).

The one thing 09 keeps unconditionally is the **`to-data.test.ts:126` fix** — `matrix` → `matrix_`.
That is not part of (b): with (a) in place the current spelling throws at runtime, so the test must
be fixed whether or not tests are typechecked.

### (c) One home for the version grammar: a fourth declarative `ModelSpec` field, bound by a shared value table

**The single home for the grammar is the canonical Snapshot** — `schema/workflow_schema.json:734`.
It cannot be the _runtime_ home in either port: the wheel packages only
`packages/python/src/ghagen` (repo-root `pyproject.toml:35`) and the npm package only `dist`
(`packages/typescript/package.json:23-25`), so `schema/` is not installed anywhere a model can read
it, and ADR-0003 keeps schema handling dev-only on purpose.

So each port keeps a one-line pattern literal — **in its `ModelSpec`, not in a factory body**:

```ts
// packages/typescript/src/models/spec.ts — fourth declarative field
export interface ModelSpec {
  readonly kind: ModelKind;
  readonly fieldMap: Readonly<Record<string, string>>;
  readonly order: OrderMode;
  readonly wrap?: Readonly<Record<string, WrapRule>>;
  readonly dynamicKeys?: boolean;
  readonly presentNullWhenEmpty?: readonly string[];
  /**
   * Value grammars for individual input fields, keyed by the same camelCase
   * input names as `fieldMap`. Checked in `buildYamlData` against the peeled
   * value; non-string values (including `Raw`) are skipped, so the escape hatch
   * stays opt-in. Patterns carry no flags — `RegExp.test` is stateful under `/g`.
   */
  readonly patterns?: Readonly<Record<string, RegExp>>;
}
```

```python
# packages/python/src/ghagen/models/spec.py — the mirror
    yaml_keys: Mapping[str, str]
    order: tuple[str, ...] | None = field(default_factory=tuple)
    present_null_when_empty: frozenset[str] = frozenset()
    patterns: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
```

```ts
// image-snapshot.ts — the whole of this port's change; the factory body is untouched
export const IMAGE_SNAPSHOT_SPEC: ModelSpec = {
  kind: "imageSnapshot",
  fieldMap: IMAGE_SNAPSHOT_FIELD_MAP,
  order: { kind: "explicit", keys: ["image-name", "version"] },
  patterns: { version: /^\d+(\.\d+|\*)?$/ },
};
```

```python
# image_snapshot.py — the ``_validate_version`` field_validator (:38-46) is DELETED
IMAGE_SNAPSHOT_SPEC = ModelSpec(
    yaml_keys={"image_name": "image-name", "version": "version"},
    order=("image-name", "version"),
    # ``re.ASCII`` matches ECMA-262's ``\d``; the flag leaves ``.pattern``
    # byte-identical to the Snapshot's string.
    patterns={"version": re.compile(r"^\d+(\.\d+|\*)?$", re.ASCII)},
)
```

Each port consumes `patterns` in the one place it already consumes the rest of the spec at
construction:

- **TypeScript** — inside `buildYamlData`'s `fieldMap` loop, after the `Commented` peel
  (`_base.ts:329-333`) and before `applyWrapRule`, so a `withComment(...)` wrapper does not defeat
  the check. `pattern.test(value)` runs only when `typeof value === "string"`, which skips `Raw`
  (a frozen object) — the escape hatch stays opt-in, matching Python. Failure throws
  `ModelInputError(spec.kind, { reason: "pattern", field, value, pattern: pattern.source })`.
- **Python** — one `model_validator(mode="after")` on `GhagenModel` (`_base.py`) that walks
  `getattr(type(self), "SPEC", None).patterns` and calls `pattern.fullmatch(value)` on each `str`
  field value, raising `ValueError` (Pydantic wraps it into `ValidationError`, as the deleted
  `field_validator` did). `fullmatch` is what kills the trailing-newline dialect bug; `re.ASCII` on
  the compiled pattern is what kills the Unicode-digit one. The `^`/`$` anchors are redundant under
  `fullmatch` and are kept solely so `.pattern` stays byte-identical to the Snapshot string.
  It runs after `_preserve_commented`'s `handler(clean)` (`_base.py:131`), so it sees unwrapped
  values.

**Why a spec field and not a `ModelSpec.validate?: (data) => void` hook.** The hook was and stays
rejected: an opaque function on a spec is exactly the optional-knob surface [20] exists to delete,
and — decisively — **a callback cannot be compared to the Snapshot.** Assertion 1 below reads
`spec.patterns[field].source` and string-compares it to `workflow_schema.json:734`. There is no way
to ask a callback what grammar it implements. `patterns` is not a hook in disguise; it is the
in-code half of the shared conformance-values table, and it is what makes the port's grammar
_enumerable_ rather than _hidden inside a function body_.

**Why a spec field and not a hand-written check in `imageSnapshot()`.** That was this proposal's
earlier design, and it was argued with a deletion test run in a world [22] removes. [22] collapses
all 27 factory bodies (30 after [11]) into `defineFactory<M,I>(SPEC)` one-liners, leaving nowhere for
a hand-written version check; since 09 → 11 → 22 puts 22 last, 22 would simply delete it. The two
alternatives to `patterns` were weighed and rejected: excluding `imageSnapshot` from 22's sweep
costs 22 its whole thesis for one factory and does not scale — the Snapshot has four more `pattern`s
(`workflow_schema.json:255,334,689,839`), each of which would re-except another factory; and the
`validate` callback fails for the reason above.

**Deletion test for `patterns`.** Remove it and three things re-grow: [22] acquires a permanent
exception to its 27→30 collapse so `imageSnapshot()` can keep a hand-written body; Python re-grows a
per-model `field_validator` (the 9 lines at `image_snapshot.py:38-46`); and **assertion 1 loses its
subject** — with the grammar inside a function body there is nothing enumerable for the sweep to
read, so pattern identity reverts to a hand-exported per-model constant, which is precisely the
"hand-copied regex with no link back to its source" §3 exists to delete. That is an earned keep, not
a pass-through. It is also the shape `ModelSpec` already uses: `dynamicKeys` has exactly one adapter
(`MATRIX_SPEC`, `job.ts:79`) and `presentNullWhenEmpty` has exactly one (`ON_SPEC`, `trigger.ts:464`
/ `trigger.py:119`); both were accepted by [06] on this argument, and both are consumed by exactly
one reader per port.

**The binding is test-based**, in the house style ADR-0003 already prescribes and
`conformance-scopes.yml` already proves. New shared table:

```yaml
# schema/conformance-values.yml
workflow_schema.json:
  imageSnapshot.version:
    # keys to walk into the loaded schema to reach the pattern string
    path: [definitions, snapshot, oneOf, 1, properties, version, pattern]
    accept: ["1", "01", "12", "1.2", "12.34", "1*"]
    reject:
      ["", " 1", "1.", "1.2.3", "1.*", "1.2*", "*", "v1", "latest", "1\n", "1.2\n", "١", "١.٢"]
```

The table's key format is `kind.field` — `imageSnapshot.version` — which is exactly `spec.kind` plus
the `patterns` key. The shared table therefore _is_ the spec data under one join: the TS sweep reads
`spec.kind` off the spec directly; the Python sweep supplies the `kind` half from the model table it
already maintains (`test_conformance.py:71`, `_MODELS`), because Python's `ModelSpec` has no `kind`
field — a pre-existing asymmetry between the two spec shapes, not one this proposal introduces.

Each sweep asserts three things:

1. **Pattern identity.** The port's pattern source string equals the schema's pattern string at
   `path`. Python `SPEC.patterns["version"].pattern`, TS `SPEC.patterns.version.source` — both render
   `^\d+(\.\d+|\*)?$`, so this is a literal string comparison, and it survives `re.ASCII` (verified:
   `re.compile(p, re.ASCII).pattern == re.compile(p).pattern`). The TS half additionally asserts
   `.flags === ""`, so a stray `/g` cannot make `RegExp.test` stateful. Upstream drift fails the
   sweep; the existing `schema-drift.yml` workflow already turns upstream change into a PR.
2. **Vectors.** Every `accept` constructs; every `reject` raises. This is the assertion that catches
   what pattern identity cannot — both dialect bugs are invisible to a string comparison and
   immediately visible to `"1\n"` and `"١"` in `reject`.
3. **Key-set parity.** Both sweeps assert their bound key set equals the shared file's, so a grammar
   enforced in one port and not the other fails a test. Same guard the scope table already carries
   (`conformance.test.ts:182`, `test_conformance.py:186`).

### (d) Close the `Raw`-surface divergences, per union, without inventing a new one

- `PermissionsInput`'s scopes become `PermissionLevel | Raw<string>` (`permissions.ts:11-38`),
  matching `permissions.py:55-67`. That is **13 scopes today and 16 after [11]** adds
  `artifactMetadata`, `attestations` and `models`. `PERMISSIONS_SPEC`'s
  `satisfies Record<keyof PermissionsInput, keyof SchemaPermissions>` (`permissions.ts:57`) is keyed
  on field names and is unaffected.
- `WorkflowDispatchInputDef.type` keeps its **5**-member union and gains `| Raw<string>`
  (`trigger.ts:177`). Python's `WorkflowDispatchInput.type` (`trigger.py:164`) tightens to
  `Literal["boolean","number","string","choice","environment"] | Raw[str] | None`.
- `WorkflowCallInputDef.type` keeps its **3**-member union and gains `| Raw<string>`
  (`trigger.ts:270`). Python's `WorkflowCallInput.type` (`trigger.py:184`) tightens to
  `Literal["boolean","number","string"] | Raw[str]` — **and loses its default**, because the schema
  marks it required (`workflow_schema.json:1706`) and the TS port already does. Every in-tree
  construction already passes `type=` (`test_full_workflow.py:146-155,315-319`), so nothing breaks;
  `.github/ghagen_workflows.py` constructs only bare `WorkflowDispatchTrigger()` (`:185`, `:489`)
  and no `WorkflowCallInput` at all.
- This is the shape that already makes `Raw` load-bearing on `Step.shell` and the permission scopes
  (`_raw.py:74-76` names exactly those unions).

**Invariants / error modes after this:** in both ports, constructing a model with an unknown input
key is an error; constructing one with a value outside a declared union is an error unless wrapped
in the explicit `Raw` escape hatch; and every grammar declared in a spec's `patterns` is enforced at
construction, in the same dialect, in both ports. Emitted bytes for every currently-valid document
are unchanged — every new failure mode fires on input that today produces silently wrong or silently
missing YAML.

## What sits behind the seam

`buildYamlData` is already the one input→`data` path in the TS port; it gains the two invariants
that made that centralisation worth having. **Leverage:** 27 factories (30 after [11]) acquire
unknown-key rejection and grammar enforcement without a line of code each, and 26 of them without
any spec change (`MATRIX_SPEC` already declares its exemption). **Locality:** the answer to "what
happens to a key the model does not know?" is one `if` in one file per port, instead of a
per-factory reading exercise and a `tsconfig` exclusion. Deletion test: remove the block and every
factory needs its own check, or the silent drop returns for all 27.

`ModelSpec.patterns` is where a value grammar lives so that it is _declared_ rather than
_implemented_. **Leverage:** it survives [22]'s collapse of every factory body untouched, because a
`defineFactory(SPEC)` one-liner still routes through `buildModel` → `buildYamlData`, which is the
reader. **Locality:** "what does this model accept in this field?" is answered next to `fieldMap`
and `order`, in the same literal, for both ports. Deletion test: above.

`schema/conformance-values.yml` becomes the second thing the two conformance sweeps hold in common,
after `conformance-scopes.yml`. **Leverage:** adding a grammar means adding a table row and one
`patterns` entry per port, and the parity guard makes a one-port grammar impossible. **Locality:**
the question "does ghagen agree with the Snapshot about what this field accepts?" gets one answer,
in one file, for both ports. Deletion test: remove it and each port re-grows a private vector list,
the version grammar loses its link to `schema/workflow_schema.json:734`, and there is no mechanism
at all that would have caught either dialect bug — the same class of divergence
`conformance-scopes.yml` was created to prevent.

## Migration plan

Pre-1.0; clean breaks. Ordered so each step's failures are attributable. **09 lands before both
[11] and [22]** (see _Risks_).

1. **(b), if the Phase 3 decision keeps it here.** Add `tsconfig.typecheck.json`, point
   `package.json`'s `typecheck` at it, and fix the 28 surfaced errors. Nothing else in this proposal
   is visible yet; the suite must be green here. If (b) becomes proposal 25, this step is 25's and
   09 depends on it.
2. TS: add `ModelInputError` + `ModelInputProblem` and the unknown-key rejection to `buildYamlData`;
   export from `index.ts` and `_docs-api-output.ts`; rewrite `_base.test.ts:188-196` to assert the
   throw; fix `to-data.test.ts:126` to `matrix_` (required regardless of step 1 — the old spelling
   now throws).
3. Add `patterns` to `ModelSpec` in both ports (`spec.ts`, `spec.py`) with a behaviour-preserving
   default (absent / empty). Both suites stay green: no spec sets it yet.
4. Consume it: TS in `buildYamlData`'s loop; Python in `GhagenModel`'s new `model_validator`. Move
   the grammar into `IMAGE_SNAPSHOT_SPEC` in both ports (`re.ASCII` on the Python side) and **delete**
   `image_snapshot.py`'s `_validate_version`.
5. Add `schema/conformance-values.yml`; bind it in both sweeps with the three assertions from (c),
   modelled line-for-line on the scope-table binding (`conformance.test.ts:76-78,182-189`;
   `test_conformance.py:93,186-203`).
6. `Raw` surface parity: TS permissions + both trigger `type` unions gain `Raw<string>`; Python's two
   trigger `type` fields tighten to their own closed unions and `WorkflowCallInput.type` becomes
   required. Extend `test_validation.py`'s `TestRawIsOptIn` and the new TS `validation.test.ts` in
   the same commit.
7. Docs: `job.md:172` states the enforced grammar; `triggers.md:155,212` restate the two closed sets
   and the required-ness change; `escape-hatches.mdx` notes `raw()` on TS permission scopes and
   trigger input types. TypeDoc output regenerates (it is gitignored).
8. Full gates: `scripts/typecheck.sh all`, `scripts/test.sh all`, `uv run ghagen check-synced`,
   `PYTHONPATH=scripts uv run python -m ghagen_schema check`. `check-synced` must stay byte-identical
   — nothing here changes emission for valid input.

## Test impact

Baseline: pytest 562, vitest 515.

- **New (TS):** `src/models/validation.test.ts`, the peer of `test_validation.py`. Unknown-key
  rejection across all five call shapes from §1's table (the four that `tsc` cannot catch are the
  point — they are written with `as` casts so the file typechecks if (b) lands); `extras` still
  works; `matrix()` still accepts dynamic axes; the `Raw` escape hatch on permissions and both
  trigger `type` unions. ~12 cases.
- **New (TS):** `image-snapshot.test.ts` gains the accept/reject vectors, including `"1\n"` and
  `"١"`.
- **New (both):** the value-table binding in each conformance sweep — pattern identity (plus
  `.flags === ""` on the TS side), vectors, key-set parity. 3 assertions per port, parametrized over
  the table.
- **New (Python):** `test_image_snapshot.py` gains the trailing-newline and Unicode-digit rejects
  that `re.match` accepts today; `test_validation.py` gains both trigger-`type` constraints and the
  `WorkflowCallInput.type`-is-required case.
- **Rewritten (TS):** `_base.test.ts:188-196` — "skips … keys not in the field map" inverts to
  "rejects keys not in the field map", keeping the `undefined`-skipping half.
- **Fixed (TS):** `to-data.test.ts:126` `matrix` → `matrix_`. This test's `toData` ≡
  `parse(toYaml(...))` oracle is self-consistent and therefore blind to dropped input; the fix makes
  it actually exercise a matrix.
- **Deleted (Python):** `image_snapshot.py`'s `_validate_version` — the behaviour it guarded is now
  the base-class check, and the existing `test_image_snapshot.py` cases keep passing against it.
- **Fixed (TS), (b) only:** the 27 non-bug type errors surfaced by step 1, across
  `yaml-writer.test.ts` (22), `trigger.test.ts`, `collect.test.ts`, `sites.test.ts`,
  `integration/test-utils.ts` (2).
- **Unchanged:** all integration snapshots and `check-synced` output. No valid document's bytes move.

Net: roughly +27 vitest, +10 pytest, 1 Python validator deleted.

## Risks & alternatives

- **Ordering against [22]: `09 → 22`, a real order edge.** [22] collapses all 27 factory bodies (30
  after [11]) into `defineFactory<M,I>(SPEC)` one-liners and already declares
  `image-snapshot.ts` a "**Conflict edge 09 — 22**" in its own Files-involved table. With `patterns`
  on `ModelSpec`, 09's grammar work leaves the factory body empty of anything 22 would have to
  preserve, so 22's collapse of `imageSnapshot()` is unconditional. If 22 landed first, 09 would have
  to un-collapse one factory. 09 first.
- **Ordering against [11]: a conflict edge, not an order edge, with 09 first.** [11]'s header
  currently declares `Depends on: 09` while an earlier draft of this section said to "land 11's table
  shape first" — a declared cycle, and neither direction survives. 11's stated need is a _contract_,
  not code: 11's own `:122` says it was "verified live against the tree with `extra="forbid"` in
  place" and its `:514-517` says it "_consumes_ it and adds no new validation semantics" — and
  `extra="forbid"` is already on `main` at `_base.py:93`. The TypeScript half of the same contract is
  likewise already true without 09: an unmodeled event in a fresh `on({...})` literal is **TS2353**
  today, or **TS2561** with a rename suggestion when it near-misses a modelled key (both reproduced
  above). So 09 gives 11 nothing it does not already have. **The order edge is deleted; what remains
  is a file conflict.**
- **That conflict is real and larger than an earlier draft admitted.** The two proposals share
  **thirteen** paths, not the three previously claimed: `models/_base.ts`, `models/trigger.ts`,
  `models/trigger.py`, `models/permissions.ts`, `src/index.ts`, `models/conformance.test.ts`,
  `tests/test_schema/test_conformance.py`, `models/trigger.test.ts` (09's only under (b)),
  `docs/…/python/api/job.md`, `docs/…/python/api/triggers.md`, `packages/typescript/CONTEXT.md`,
  `packages/python/CONTEXT.md`, and **`docs/adr/0003-…md` — both append an amendment to the same
  53-line ADR**. There is also a substantive coupling: 11 adds three permission scopes and three new
  `workflowCall*` model kinds, so 09's "`Raw<string>` on every scope" is **16 scopes post-11**, and
  its `patterns` field must exist on the `ModelSpec` shape 11's `registry.ts`
  (`satisfies Record<ModelKind, ModelSpec>`) types over. Sequencing 09 first makes both mechanical.
- **Ordering against [10]: a file conflict on the spec modules.** [10] rewrites
  `packages/typescript/src/models/spec.ts` (91) and `packages/python/src/ghagen/models/spec.py` (41)
  — collapsing `OrderMode` and deleting `extrasPlacement` — which are now 09's files too. `patterns`
  is orthogonal to `order`, so the merge is additive whichever lands first, but 09 is now **on 10's
  critical path** and must be named in 10's conflict list.
- **Open — Phase 3 decision: who owns the `matrix_` rename.** TS's `StrategyInput.matrix_`
  (`job.ts:93`, `fieldMap` at `job.ts:120`) versus Python's `Strategy.matrix` (`job.py:129`) is a
  live cross-port naming divergence. An earlier draft of this section said 09 "hands [11] the
  rename" — **[11] never mentions it** (the string `matrix_` does not appear in 11 at all) and 11
  explicitly carves `definitions.matrix` out of its sweep (11 `:85-92`, `:544-546`). Nobody owns it.
  Worse, 09 makes it _less_ visible: today `to-data.test.ts:126` accidentally documents the
  divergence by writing the wrong spelling, and after 09 that test is fixed and nothing in the tree
  flags `job.ts:93` against `job.py:129`. 09 does **not** decide the rename; it fixes only the test
  the divergence broke and records the loss of the accidental canary here.
- **Open — Phase 3 decision: whether (b) becomes proposal 25.** See (b) above for the three reasons
  it is a boundary and for what it costs [11]'s `registry.ts` rationale.
- **This reopens ADR-0003, narrowly, and says so.** ADR-0003:33-34 reads "**TypeScript**:
  compile-time author-conformance. … No runtime validation," under a heading that says "do not 'fix'
  this into false parity" (`:31`). The subject of that sentence is **schema conformance** — whether
  the hand-written model surface matches the Snapshot — and nothing here touches it: generated types
  stay imported into the models, `tsc` stays the conformance check, and generated Python models stay
  deleted. What (a) and (c) add is the model's own **input contract**, which is a different
  invariant, and one the TS port already enforces at runtime elsewhere: `config.ts` hand-validates
  every `.ghagen.yml` key (`config.ts:141,176,198,208,285`) and `pin/lockfile.ts` validates every
  lockfile entry (`lockfile.ts:131-158`). "The TS port does no runtime validation" is already false
  of the package; it is true only of the models, and only because nobody wrote it. The amendment in
  the last section draws that line explicitly so the next reader does not have to re-derive it.
- **Risk: the unknown-key throw breaks downstream user code that currently "works."** Accepted —
  pre-1.0, and the code it breaks is code whose keys are being silently discarded right now. The
  error message names `extras` as the sanctioned channel. The in-repo blast radius is measured, not
  guessed: 2 of 515 tests, one of which is a real bug.
- **Alternative for (a): warn instead of throw.** Rejected — Python raises, so warning re-creates
  the divergence in a quieter form, and a warning printed during synthesis is not a check.
- **Alternative for (a): put the check in `extractMeta` instead.** Rejected — `extractMeta`
  (`_base.ts:144-155`) does not see the spec, so it cannot know which keys are legitimate.
  `buildYamlData` is the only place that holds both the input and the `fieldMap`.
- **Alternative for (c): generate the pattern into each port from the Snapshot.** Rejected on two
  counts. It would put a generated artifact back into the Python package, which ADR-0003 explicitly
  removed and tells future readers not to re-suggest; and it would not have caught either bug — a
  generated-identical pattern string is still applied through `re.match` and still resolves `\d`
  against Unicode. The vector table catches dialect, which is where both actual divergences were.
- **Alternative for (c): a `ModelSpec.validate?: (data) => void` hook.** Rejected — see (c). The
  short form: an opaque callback is the optional-knob surface [20] exists to delete, and it makes
  assertion 1 unwritable, because a function cannot be string-compared to `workflow_schema.json:734`.
  When the four remaining Snapshot patterns (`workflow_schema.json:255,334,689,839`) are enforced,
  they are four more `patterns` entries and four more table rows — no new spec surface at all.
- **Alternative for (b): also run pyright over `packages/python/tests/`.** Rejected for this
  proposal. Measured: `uv run pyright packages/python/tests/` reports **673 errors** on this tree,
  against 28 for the TS side. That is a separate project with a separate risk profile. The asymmetry
  is real and should be tracked; it is not blocking, because Python's construction-time checks are
  runtime checks that the test suite actually executes, whereas TS's are compile-time checks that
  were simply not being run.
- **Risk: `conformance-values.yml`'s `path` indexes `snapshot.oneOf` positionally**, so an upstream
  reordering of that `oneOf` breaks the sweep. Accepted, and arguably desired: ADR-0003's whole
  posture is that upstream change should surface as a failing conformance check, and
  `schema-drift.yml` already converts upstream change into a PR where the path is updated alongside
  the Snapshot. Note [11] independently widens the shared `SchemaPath` type to admit integer
  segments (11 `:431-432`), which this table's `oneOf, 1` needs; if 09 lands first it carries that
  widening for the values table only.
- **No overlap with [21].** [21] hoists an emission-time field-collection loop in
  `emitter/nodes.py` / `emitter/data.py`; 09 is construction-time work in `models/`. Different
  package, different phase, zero shared paths.
- **[20]'s separate note.** `zod` is a declared dependency of `packages/typescript/package.json`
  (`:57`) with **zero** importers in `src/` since 5e9b944 collapsed `_config-schema.ts` into
  `config.ts` — that is 20's to remove, not this proposal's, and this proposal does not reintroduce
  it: the checks proposed here are ~20 lines of hand-written predicate plus one `RegExp.test`, not a
  validation framework.

## ADR / CONTEXT.md impact

- **ADR-0003 — amend, do not contradict.** Add an amendment paragraph: _the two ports still enforce
  schema conformance differently (TS compile-time via generated types, Python test-based), and
  generated Python models stay removed. Construction-time **input** invariants are a separate
  concern and are port-symmetric: unknown input keys are an error, escape hatches are opt-in, and
  value grammars declared in a model's `ModelSpec` are enforced. The shared
  `schema/conformance-values.yml` extends the `conformance-scopes.yml` mechanism from property
  coverage to value grammars; the Snapshot remains the single home for each grammar and the ports
  remain bound to it by test, not by codegen._ Without this, `:34`'s "No runtime validation" reads as
  a prohibition on (a) and (c). **[11] amends the same 53-line file** — the two amendments are
  adjacent paragraphs under one "Amendments" heading, 09's first.
- **ADR-0001 (Document serialization seam):** unaffected and mildly reinforced — the new checks run
  at construction, in the factory / model layer, and add nothing to the Emitter.
- **ADR-0002 (no construction-time config globals):** unaffected — `patterns` holds per-spec static
  literals, not runtime config; the shared table is read only by tests.
- **`packages/typescript/CONTEXT.md:105` — 09's only region in this file.** "There is no runtime
  validation" must change. Proposed replacement: _generated types give compile-time
  author-conformance against the schema (ADR-0003); separately, factories enforce their
  construction-time input contract at runtime — unknown input keys raise `ModelInputError` (use
  `extras`), and a **value grammar** declared in a spec's `patterns` (e.g. `ImageSnapshot.version`)
  is checked against the canonical Snapshot's pattern._ The term **value grammar** is defined inline
  in this sentence rather than as a separate glossary entry, because the glossary sits outside 09's
  assigned region; the **ModelSpec** entry at `:40-46` is [22]'s and is not touched here.
  Note that `:104-105` is one bullet and [11] also claims `:104-105`; 09 first, then 11 appends.
- **`packages/python/CONTEXT.md:100` — 09's only region in this file.** Keep "User input is validated
  at construction (Pydantic)" and add the parity sentence — _the TypeScript port enforces the same
  construction-time input contract; declared value grammars live in each port's `ModelSpec` and the
  two are bound to the Snapshot by `schema/conformance-values.yml`._
