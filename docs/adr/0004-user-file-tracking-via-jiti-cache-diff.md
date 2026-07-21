# User-file tracking via jiti module-cache diff

**Status:** accepted

`deps upgrade --apply` must know which user source files were loaded by the config so it can scope
`uses:` rewrites. The TypeScript port determines this by diffing `jiti.cache` keys before and after
importing the user's config (`pin/sources.ts`). This mechanism is **kept deliberately**, guarded by
a real-jiti integration test over a fixture project.

## Why

A migration to jiti's documented `transform` hook was investigated (2026-07-21) and rejected:

- **`jiti.cache` is typed public surface**, not an undocumented internal: jiti's own `types.d.ts`
  declares `Jiti extends NodeRequire { cache: ModuleCache }` with no `@deprecated` marker (unlike
  the direct-call and `resolve` surfaces, which are deprecated). The original "not formally
  documented" concern was overstated.
- **The `transform` hook has strictly worse coverage.** It fires only for modules jiti transpiles:
  a plain-CommonJS `.js` helper goes through native require — no transform call — so its file
  would be silently missed and its `uses:` refs silently not rewritten, which is exactly the
  failure mode being defended against. The hook is also skipped entirely on fsCache hits
  (`transform()` wraps `getCache()`), so correctness would hinge on `fsCache: false` forever.
- Wrapping the hook without importing jiti internals requires delegating to a second instance's
  `.transform()` — more moving parts for less coverage.

The residual risk (a jiti major release changing cache behavior) is converted from a silent no-op
into a red test by the integration test: load a fixture project containing a TS helper, an ESM
helper, and a plain-CJS helper, and assert the exact tracked file set.

## Consequences

- `sources.ts` must keep `fsCache: false` only for freshness reasons, not correctness; the cache
  diff sees natively-required modules that the transform hook cannot.
- Do not re-suggest migrating user-file tracking to the `transform` hook or to `module.register`
  loader hooks unless the integration test breaks and cache introspection is actually gone.
- The fixture-project integration test is the canary; it must not be mocked.

## Known limitation: native-ESM helpers are invisible

Verified empirically (jiti 2.6.1) while writing the canary test: a `.mjs` helper is loaded through
native `import()` and never enters `jiti.cache` (the instance exposes only the CommonJS-side
cache; there is no ESM registry to diff). Its `uses:` refs are therefore silently skipped by
`deps upgrade --apply`. The rejected `transform` hook shares the same blind spot (it never fires
for natively-imported modules), so this was not a factor in choosing between mechanisms. The
canary test pins the `.mjs` absence explicitly, so a future jiti that changes this behavior —
either direction — turns the change into a red test rather than a silent one.
