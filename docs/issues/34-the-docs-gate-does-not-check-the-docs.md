# The docs gate builds the API reference without checking it

**Status:** closed — fixed in round 3.

Issue 12 closed by folding `npm run build` (Astro, which drives TypeDoc over
`packages/typescript/src/_docs-api-*.ts`) into CI's docs job, so the build **is** the docs type
check. That is a real gate and it does catch a deleted entry point. It does not catch a broken
reference inside one, because `docs/astro.config.mjs:18` sets:

```js
const sharedTypeDocConfig = {
  skipErrorChecking: true,
  ...
};
```

`skipErrorChecking` tells TypeDoc not to run the TypeScript compiler's diagnostics over the entry
points at all. Combined with TypeDoc's link validation being off by default, a dangling `{@link}`
resolves to nothing and is published as plain text.

## Measured

Appended to `packages/typescript/src/_docs-api-permissions.ts`:

```ts
/**
 * Probe: {@link ThisSymbolDoesNotExistAnywhere}
 */
export type _DocsProbe = string;
```

`./scripts/typecheck.sh docs` → **exit 0**, no warning, no error, 62 pages built. Reverted; tree
clean.

## Why `skipErrorChecking` is nonetheless defensible

It is not obviously wrong to set it. `tsc --noEmit` (`scripts/typecheck.sh ts`) already compiles
`src/`, `_docs-api-*.ts` included, so TypeDoc re-running the same diagnostics would be duplicated
work in a slower gate. The hole is narrower than "TypeDoc checks nothing": it is specifically
TypeDoc's **own** diagnostics — unresolved links, undocumented exports, entry points that resolve to
nothing — that no gate performs.

## What a fix must do

1. Turn on TypeDoc's `validation` (`invalidLink`, `notExported`, `notDocumented` as appropriate) and
   set `treatValidationWarningsAsErrors`, rather than reaching for `skipErrorChecking: false`, which
   would duplicate `tsc`.
2. Fix whatever the first run surfaces — assume it is not zero.
3. Prove it: re-run the probe above and confirm the docs gate now fails, then confirm it passes once
   the probe is removed.
4. Consider whether the same applies to the Python API reference, which is hand-written Markdown
   under `docs/src/content/docs/python/api/` and has no equivalent check at all. Round 3 found a
   published `PermissionsValue` that existed in neither port (`docs/issues/27`) — that is the same
   class of defect on the side of the docs nothing validates.

## Files

- `docs/astro.config.mjs` — `sharedTypeDocConfig`
- `packages/typescript/src/_docs-api-*.ts` — the entry points
- `docs/issues/12-no-pr-time-docs-gate.md` — the closed issue this is residue from
- `docs/issues/27-published-api-divergences-between-the-ports.md` — the Python-side instance

## Resolution

### The hole was one layer deeper than "the options are off"

TypeDoc's `validation` flags are **already on by default** (`notExported`, `invalidLink`,
`invalidPath`, `rewrittenLink`, `unusedMergeModuleWith` all default to `true`;
`notDocumented` to `false`). Turning them on in `sharedTypeDocConfig` would therefore have
changed nothing, and `treatValidationWarningsAsErrors: true` on its own would have changed
nothing either. Reading the installed packages rather than trusting the option names:

- `notExported`, `notDocumented`, `invalidLink` and `unusedMergeModuleWith` only run inside
  `Application.validate()` (`typedoc/dist/lib/application.js:528`), and `validate()` is called
  **only by TypeDoc's own CLI** (`typedoc/dist/lib/cli.js:77`). It is not called by `convert()`
  and not by `generateOutputs()`.
- `starlight-typedoc` drives `app.convert()` then `app.generateOutputs()` directly
  (`starlight-typedoc/libs/typedoc.ts:78-86`). It never calls `validate()`.
- `treatValidationWarningsAsErrors` is likewise read only by `cli.js`, where it selects an exit
  code. Nothing in the Astro path has an exit code to select.

So the published behaviour was: validation configured, validation never executed.

### The fix

`docs/astro.config.mjs` now registers a TypeDoc plugin, `typeDocValidationGate`, passed through
the `plugin` option (TypeDoc's `PluginArray` accepts a function directly, so no separate file).
It hooks `Converter.EVENT_END` — the same point in the run at which `cli.js` validates, i.e.
immediately after conversion resolves — calls `app.validate(project)`, and reproduces `cli.js`'s
pass/fail rule: fail if the validators raised an error, or raised any warning and
`treatValidationWarningsAsErrors` is set. "Fail" here means `throw`, which fails `astro build`
and therefore `scripts/typecheck.sh docs`.

`skipErrorChecking: true` is **kept**. Flipping it would make TypeDoc re-run the TypeScript
program diagnostics that `scripts/typecheck.sh ts` already runs — the same errors reported twice,
from a slower gate. What was missing was TypeDoc's own diagnostics, and those are now run.

### Which validations, and why

| flag                    | state   | first-run findings |
| ----------------------- | ------- | ------------------ |
| `invalidLink`           | on      | **15**, all fixed  |
| `invalidPath`           | on      | 0                  |
| `unusedMergeModuleWith` | on      | 0                  |
| `rewrittenLink`         | on      | 0                  |
| `notExported`           | **off** | 65 — see below     |
| `notDocumented`         | **off** | 18 — see below     |

The 15 `invalidLink` findings were all genuine, and all one shape: the API reference is nine
_independent_ TypeDoc projects (one per `_docs-api-*.ts`), so a `{@link}` in a doc comment whose
target is not published by _that_ entry point renders as bare text. Two sub-kinds:

- 11 of "the comment for X links to Y which was resolved but is not included in the
  documentation" — `{@link ContainerModel}`, `{@link ServiceModel}`, `{@link ActionModel}`,
  `{@link ActionInputModel}`, `{@link ActionOutputModel}`, `{@link BrandingModel}`,
  `{@link CompositeRunsModel}`, `{@link StepModel}`, `{@link DockerRunsModel}`,
  `{@link NodeRunsModel}`, `{@link Model}`, `{@link ModelSpec.patterns}`,
  `{@link isIntegerLikeKey}`.
- 4 of "failed to resolve link to X" — `{@link toYaml}` / `{@link toYamlFile}` in
  `models/action.ts`, `{@link workflow}` / `{@link action}` in `emitter/yaml-writer.ts`. These
  never worked even in principle: the file does not import the symbol, so there is nothing for
  TypeDoc to resolve against.

All 15 were fixed by demoting the link to inline code (`` `ContainerModel` ``), which is what the
page actually rendered anyway — the change is that it now says so honestly. Mapping them to `"#"`
via `externalSymbolLinkMappings`, which is what TypeDoc's warning text suggests, would have been
suppression: a link that goes nowhere. If the model types are ever published (see below), these
can become real links again and the gate will keep them honest.

`notExported` is off with a measured reason, not silently. Its 65 findings are one fact repeated:
the entry points publish the builder _functions_ but not the `*Model` / `*Input` types those
functions' signatures name, so a reader gets type names they cannot follow. Satisfying it means
either publishing ~30 model types — a redesign of what the TypeScript API reference _is_ — or
maintaining nine separate `intentionallyNotExported` lists, since a shared list cannot work
(TypeDoc reports entries that went unused in a given run). Both are larger than this issue.

`notDocumented` is off for the same reason of scope, not of principle. Its 18 findings are real
gaps and are worth writing: `App` itself and `App.headerTxt` / `App.lockfilePath` /
`App.rootAbsPath` / `App._userTransforms`; `CommentNode.comment` / `.eolComment` / `.value`;
`ModelInputError.kind` / `.problem`; and the members of the `ModelInputProblem` union. That is
prose work, not gate work.

### The corruption proof

Two probes, both re-run against the finished config.

`{@link ThisSymbolDoesNotExistAnywhere}` appended to `_docs-api-permissions.ts`, `./scripts/typecheck.sh docs`:

```
[WARN] [starlight-typedoc-plugin] Failed to resolve link to "ThisSymbolDoesNotExistAnywhere" in comment for _DocsProbe
[ERROR] [@astrojs/starlight] An unhandled error occurred while running the "astro:config:setup" hook
TypeDoc validation failed -- see the warnings above. Fix the API reference, or adjust `validation` in docs/astro.config.mjs.
EXIT=1
```

A relative link to a nonexistent file (`[the missing file](./this-file-does-not-exist.md)`) in the
same place:

```
[WARN] [starlight-typedoc-plugin] The relative path ./this-file-does-not-exist.md is not a file and will not be copied to the output directory
TypeDoc validation failed -- see the warnings above. Fix the API reference, or adjust `validation` in docs/astro.config.mjs.
EXIT=1
```

Both reverted; the gate is green with zero warnings and 63 pages built:

```
[build] 63 page(s) built in 29.29s
[build] Complete!
EXIT=0
```

Before the change, both probes produced **exit 0 and no output at all**.

### What this still does not cover

The gate covers the _generated_ half of the API reference only. Python's pages under
`docs/src/content/docs/python/api/` are hand-written `.mdx` and no equivalent check exists for
them: nothing verifies that a symbol documented there exists in `packages/python/src/`, which is
exactly the defect `docs/issues/27` found (a published `PermissionsValue` present in neither
port). Closing this issue narrows the hole to the hand-written side; it does not close it.

### Follow-up

1. `notExported` (65) — decide whether the `*Model` / `*Input` types belong in the published API
   reference, then either publish them and turn the check on, or record the decision.
2. `notDocumented` (18) — write the missing doc comments listed above, then turn the check on.
3. A `python/api` equivalent: check that every symbol the hand-written Python pages document
   actually exists in `packages/python/src/`.

### Files touched

- `docs/astro.config.mjs` — `typeDocValidationGate`, `validation`, `treatValidationWarningsAsErrors`
- `packages/typescript/src/models/action.ts`, `models/container.ts`, `models/_base.ts`,
  `emitter/yaml-writer.ts` — the 15 broken `{@link}` references
