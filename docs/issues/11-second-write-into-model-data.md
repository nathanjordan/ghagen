# A second production write into a model's `data` bag, unnamed by any proposal

**Status:** closed — from round 2, found by proposal 10's reviser; no proposal owned it, so fixed
directly rather than left for one. `emitter/yaml-writer.ts`'s `toYaml` path (`modelToYamlMap` /
`toYamlValue`) now dedents a Step's `run` at read time, threading `autoDedent` through the
recursion exactly as `toData`'s `modelToData` already did — no clone, no mutation of any model's
`data` bag (ADR-0002; matches Python's `collect_fields`, which never mutated). The `dedentSteps`
clone-then-`walk()`-then-write function is deleted. Production TypeScript now has exactly **one**
runtime write into an existing `model.data`: `pin/sites.ts:48`, sanctioned by `Model`'s own
docstring ("synthesis-time transforms … can rewrite fields after a `cloneModel` deep copy") — the
peer of Python's `pin/sites.py`'s `setattr` on a `GhagenModel` attribute. Bound by
`packages/typescript/src/emitter/yaml-writer.test.ts`'s "does not mutate the model's `data` bag"
tests.

`packages/typescript/src/emitter/yaml-writer.ts:48` assigns into an existing `data` bag:

```ts
node.data["run"] = dedentScript(node.data["run"] as string);
```

It sits alongside the already-known site at `pin/sites.ts:48`. Harmless today — it assigns a key that
is already present, and JavaScript does not reorder an existing key on reassignment — and it runs on
a `cloneModel(model)` result, not on the caller's model.

It matters because **every proposal in round 2 that reasoned about `data` mutability counted one
site.** Anything that later makes `data` read-only, ordered, or copy-on-write has two call sites to
handle, not one.
