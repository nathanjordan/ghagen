# Narrow the Transform interface to `(document) -> document`

**Status:** implemented

## Problem

`Transform` is defined as `(item, ctx) -> item`, where `ctx` is a `SynthContext` carrying
`workflow_key`/`workflowKey`, `item_type`/`itemType`, and `root`. `App.synth` (and `App.check`)
construct one `SynthContext` per item, every synthesis run, in both ports.

The only shipped `Transform` — `PinTransform` — ignores it completely. The Python implementation
(`pin/transform.py:34`) takes `ctx` and never reads it. The TypeScript implementation
(`pin/transform.ts:27`) renames the parameter to `_ctx` to silence the unused-variable lint, which
is itself the signal: the port authors already independently concluded the parameter carries no
information anyone needs.

Deletion test: delete `SynthContext` (class in Python, interface in TS) and the two construction
sites in `_apply_transforms`/`_applyTransforms`. `Transform` collapses to `(document) -> document`.
No caller reconstructs the dropped fields, no test asserts on `ctx.workflow_key`/`ctx.root`
influencing behavior, and no other seam in the codebase grows in complexity to compensate. The
interface is speculative: it was sized for hypothetical future transforms that need to know which
file they're writing to, not for any transform that exists.

This is a **seam** violation, not a leverage problem — `SynthContext` is cheap to build and cheap to
thread, so the cost isn't runtime overhead. The cost is: it's a public type (`ghagen.SynthContext`
in Python, `SynthContext`/`SynthItem` re-exports in TS `index.ts`) that every future `Transform`
author must understand and every future test must construct, in service of zero consumers today.

## Design

- `Transform` becomes `(document) -> document` in both ports:
  - Python: `Protocol.__call__(self, item: Workflow | Action) -> Workflow | Action`
  - TypeScript: `type Transform = (item: SynthItem) => SynthItem`
- Delete `SynthContext`:
  - Python: remove the `@dataclass class SynthContext` from `transforms.py`, and its import in
    `app.py`, `pin/transform.py`, and the `ghagen/__init__.py` re-export (`__all__` entry too).
  - TypeScript: remove the `export interface SynthContext` from `transforms.ts`, and its import in
    `app.ts`, `pin/transform.ts`, and the `export type { ... }` line in `index.ts`.
- `App._apply_transforms` / `App._applyTransforms` stop constructing `ctx` and call
  `transform(working)` instead of `transform(working, ctx)`.
- `PinTransform.__call__` drops the `ctx` parameter (Python). `pinTransform`'s inner closure drops
  the `_ctx` parameter (TypeScript) — the returned function's signature narrows from
  `(item, ctx) => item` to `(item) => item`.
- `SynthItem` (TS) and the `Workflow | Action` union (Python) are unaffected — only the context
  argument is removed.
- No new indirection is introduced. If a future transform genuinely needs `workflow_key`/`root`, add
  it back as a real parameter motivated by a real consumer, not speculatively.

## Before / After

### Python — `transforms.py`

Before:

```python
@dataclass
class SynthContext:
    """Context available to transforms during synthesis."""

    workflow_key: str
    item_type: Literal["workflow", "action"]
    root: Path


@runtime_checkable
class Transform(Protocol):
    def __call__(
        self, item: Workflow | Action, ctx: SynthContext
    ) -> Workflow | Action: ...
```

After:

```python
@runtime_checkable
class Transform(Protocol):
    def __call__(self, item: Workflow | Action) -> Workflow | Action: ...
```

(`Literal`, `Path`, and `dataclass` imports drop out of `transforms.py` if nothing else in the file
uses them — verify at implementation time.)

### Python — `app.py` (`_apply_transforms`)

Before:

```python
working = item.model_copy(deep=True)
item_type = "workflow" if isinstance(item, Workflow) else "action"
ctx = SynthContext(
    workflow_key=rel_path.stem,
    item_type=item_type,
    root=self.root,
)
for transform in transforms:
    working = transform(working, ctx)
return working
```

After:

```python
working = item.model_copy(deep=True)
for transform in transforms:
    working = transform(working)
return working
```

(`rel_path` remains used elsewhere in the method for the write path; `item_type` computation is
deleted outright since it existed only to populate `ctx`.)

### TypeScript — `transforms.ts`

Before:

```typescript
/** Context available to transforms during synthesis. */
export interface SynthContext {
  readonly workflowKey: string;
  readonly itemType: "workflow" | "action";
  readonly root: string;
}

export type Transform = (item: SynthItem, ctx: SynthContext) => SynthItem;
```

After:

```typescript
export type Transform = (item: SynthItem) => SynthItem;
```

### TypeScript — `app.ts` (`_applyTransforms`)

Before:

```typescript
let working = cloneModel(item);
const ctx: SynthContext = {
  workflowKey: stem(relPath),
  itemType: item.kind === "workflow" ? "workflow" : "action",
  root: this.rootAbsPath,
};
for (const transform of transforms) {
  working = transform(working, ctx);
}
return working;
```

After:

```typescript
let working = cloneModel(item);
for (const transform of transforms) {
  working = transform(working);
}
return working;
```

(The private `stem()` helper at the bottom of `app.ts` becomes dead code and is deleted along with
this call site, unless another caller is found at implementation time — verify before removing.)

### `PinTransform` signatures

Python, before: `def __call__(self, item: Workflow | Action, ctx: SynthContext) -> Workflow | Action:`
Python, after: `def __call__(self, item: Workflow | Action) -> Workflow | Action:`

TypeScript, before: `return function pin(item: SynthItem, _ctx: SynthContext): SynthItem {`
TypeScript, after: `return function pin(item: SynthItem): SynthItem {`

## Breaking change note

Repo is pre-1.0; breaking changes are freely allowed, no deprecation shim required.

Public API surface that disappears:

- Python: `ghagen.SynthContext` (exported from `ghagen/__init__.py`, both the import and the
  `__all__` entry).
- TypeScript: `SynthContext` type, re-exported from `index.ts` alongside `Transform` and
  `SynthItem`. `SynthItem` itself is retained (it names the item union, independent of context).
- The `Transform` type/protocol signature changes shape in both ports — any third-party code
  implementing a custom `Transform` with the two-argument signature must drop the second parameter.
  Since `Transform` has exactly one first-party implementation (`PinTransform`), this is expected to
  be low-blast-radius, but it is a signature-breaking change to a documented public type.

## Test plan

- Python `packages/python/tests/test_pin/test_transform.py`: delete the `SynthContext` import
  (line 18), delete the `_ctx()` and `_action_ctx()` helpers (lines 26-31), and update all 10 call
  sites that currently pass `_ctx()`/`_action_ctx()` as a second argument to `transform(wf)` /
  `transform(action)`.
- TypeScript `packages/typescript/src/pin/transform.test.ts`: delete the `const ctx = {...}` literal
  (line 11), and update the 6 call sites (`transform(cloned, ctx)`,
  `pinTransform(makeLockfile())(cloned, ctx)`, etc.) to drop the second argument. The
  `{ ...ctx, itemType: "action" }` call site (line 133) collapses to just `cloned`.
- No other test files reference `SynthContext` (confirmed by repo-wide grep in both packages).
- Both suites (`pytest`, `vitest`) must pass green after the change; no new tests are needed since
  no new behavior is introduced — this is a pure interface narrowing.

## Acceptance criteria

- [x] `SynthContext` class/interface no longer exists in `packages/python/src/ghagen/transforms.py`
      or `packages/typescript/src/transforms.ts`.
- [x] `Transform` is `(item) -> item` / `(item: SynthItem) => SynthItem` in both ports, with no
      context parameter.
- [x] `App._apply_transforms` / `App._applyTransforms` no longer construct a context object; call
      sites pass a single argument to each transform.
- [x] `PinTransform.__call__` (Python) and the `pin()` closure (TypeScript) drop the context
      parameter.
- [x] `SynthContext` is removed from `ghagen/__init__.py`'s `__all__` (Python) and from
      `index.ts`'s type re-exports (TypeScript).
- [x] Both test suites updated per the test plan above and passing.
- [x] `docs/adr/0002-no-construction-time-config-globals.md` reviewed per the note below; touched up
      or left as-is with rationale recorded in the implementing PR.
- [x] No remaining references to `SynthContext` anywhere in `packages/python/src` or
      `packages/typescript/src` (verify with a repo-wide grep as a final check).

## ADR-0002 accuracy note

ADR-0002 ("No construction-time config globals") states that `auto_dedent` is "applied at
serialization time and threaded explicitly — through `SynthContext` on the `App.synth` path and
through a `to_yaml(auto_dedent=...)` parameter on the standalone path."

This is not what the code does today, independent of this spec. `SynthContext` has never carried an
`auto_dedent` field (Python: `workflow_key`, `item_type`, `root`; TypeScript:
`workflowKey`, `itemType`, `root`). `auto_dedent` is threaded the same way on both paths: as an
explicit `auto_dedent`/`autoDedent` keyword argument to `to_yaml_file`/`to_yaml`/`toYaml`
(`app.py:167-169,186-188`; `app.ts:119,140`), read from `self._auto_dedent`/`this.autoDedent` (set
in `App.__init__`/constructor from parsed project options). `SynthContext` was never in the
`auto_dedent` path.

ADR-0002's _substance_ — no module-level mutable global carries configuration; options are threaded
explicitly to the serialization call — is preserved by this spec and unaffected by deleting
`SynthContext`. Only the ADR's _wording_ is stale: the "through `SynthContext` on the `App.synth`
path" clause should be corrected to describe the actual `auto_dedent=self._auto_dedent` keyword-arg
threading, independent of whether `SynthContext` exists. Recommend a one-line wording fix to
ADR-0002 (paragraph under "No construction-time config globals", first sentence) either alongside
this change or as a separate, unrelated cleanup — it is not blocked by or dependent on this spec's
implementation.

## Conflicts

Touches: `packages/python/src/ghagen/transforms.py`, `packages/python/src/ghagen/app.py`,
`packages/python/src/ghagen/pin/transform.py`, `packages/python/src/ghagen/__init__.py`,
`packages/python/tests/test_pin/test_transform.py`, `packages/typescript/src/transforms.ts`,
`packages/typescript/src/app.ts`, `packages/typescript/src/pin/transform.ts`,
`packages/typescript/src/index.ts`, `packages/typescript/src/pin/transform.test.ts`.

No overlap with spec 0001 or 0003 (emitter / `_base` model layer — different files, different
seam), spec 0004 (config — this spec does not touch `config.py`/`config.ts` or `.ghagen.yml`
parsing; the ADR-0002 wording note above is documentation-only and non-blocking), or spec 0005
(engine JSON — unrelated subsystem). Safe to implement in parallel with all of them.
