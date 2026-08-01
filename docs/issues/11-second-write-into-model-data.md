# A second production write into a model's `data` bag, unnamed by any proposal

**Status:** open — from round 2, found by proposal 10's reviser; no proposal owns it

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
