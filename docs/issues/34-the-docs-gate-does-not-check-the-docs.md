# The docs gate builds the API reference without checking it

**Status:** open — found in round 3 while auditing issue 12's fix

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
