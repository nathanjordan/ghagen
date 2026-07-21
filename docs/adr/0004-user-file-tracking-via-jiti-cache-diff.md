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
- Do not re-suggest migrating user-file tracking to the `transform` hook, or replacing the cache
  diff with `module.register` loader hooks, unless the integration test breaks and cache
  introspection is actually gone. (A `module.register` hook is used _as an ESM augmentation_ to the
  cache diff — see "Resolved" below — but not as a replacement for it.)
- The fixture-project integration test is the canary; it must not be mocked.

## Resolved (2026-07-21): native-ESM helpers, previously invisible

Originally a known limitation. Verified empirically (jiti 2.6.1) while writing the canary test: a
`.mjs` helper is loaded through native `import()` and never enters `jiti.cache` (the instance
exposes only the CommonJS-side cache; there is no ESM registry to diff). Its `uses:` refs were
therefore silently skipped by `deps upgrade --apply`. The rejected `transform` hook shares the same
blind spot (it never fires for natively-imported modules).

**Resolution — augment, don't replace.** `trackUserFiles` now tracks the **union** of two
observations:

1. The `jiti.cache` before/after diff (primary, unchanged) — covers TS/JS helpers, including
   plain-CommonJS ones the `transform` hook would miss.
2. A Node module-customization hook registered via `module.register` (`node:module`, supported
   since Node 18.19 / 20.6). jiti's `nativeImport` is a plain in-process dynamic `import()`, so the
   hook's `load` callback observes exactly the native-ESM loads the cache diff misses. The hook runs
   on Node's loader thread and posts each loaded module URL back over a `MessageChannel`;
   `trackUserFiles` reads the recorded set and folds it into the tracked files.

Both halves are filtered through the same `isUserFile` predicate, so `node_modules` and ghagen's own
source stay excluded. `module.register` has no deregister, so the hook is registered once per
process (guarded) and left permanently installed but inert — it only appends to a set the caller
reads. Because native ESM caches process-globally (a given `.mjs` fires the hook only on its first
load), the union reads the whole accumulated set, not a per-call diff, so repeated tracking in one
process stays correct.

Feasibility was verified empirically before landing: the `module.register` + jiti combination
observes the `.mjs` load both standalone and under Vitest's worker pool, so the static import-scan
fallback was not needed. The canary test now asserts the `.mjs` is _present_ in the tracked set, so
a future jiti or Node release that breaks either half — in either direction — turns the change into
a red test rather than a silent one.
