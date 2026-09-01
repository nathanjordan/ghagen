# TS: modules imported lazily inside createApp() are not tracked

**Status:** closed — TypeScript's tracking window now closes after App resolution, matching Python;
red-then-green against a new fixture project. Pre-existing, surfaced in round 1 review

TS resolves the App after the jiti cache-diff window, so a helper dynamically imported inside
`createApp()` never enters the tracked file set and its `uses:` refs are silently not rewritten by
`deps upgrade` (ADR-0004's defended failure mode). Python includes App resolution in its snapshot
window and tracks these. Options: move TS resolution inside the diff window, or document the
limitation. Parity gap either way.

## Resolution

The first option. "Document the limitation" was not live: feature parity between the ports is a
repo-level mandate and the sibling port already had the right behaviour, with the reason written
down at `packages/python/src/ghagen/pin/sources.py` — `resolve_app` runs _between_ the
`sys.modules` snapshots precisely so a helper imported inside `create_app()` is tracked.

### Red measurement, taken first

`packages/typescript/fixtures/lazy-app-project/` is a config that imports **nothing but `App`** at
module scope and `await import(...)`s three helpers — `lazy-ts-helper.ts`, `lazy-cjs-helper.js`,
`lazy-esm-helper.mjs` — inside `createApp()`. Against the unmodified `sources.ts` the tracked set
was:

```
['./ghagen.config.ts']
```

All three helpers missed. **Both** halves of ADR-0004's union failed, not just one — the ESM half
looks like it should survive (it reads a process-globally accumulated set, not a per-call diff) but
does not, because the accumulation is _read_ before the factory has run. The union's two halves
fail together here for one boundary reason, which is why the fix is one boundary change rather than
two.

The same measurement outside Vitest, in a fresh Node process against `dist/` (config importing the
built package, so `resolveApp`'s `instanceof App` succeeds): window closed before resolution →
`['ghagen.config.ts']`; window closed after → `['ghagen.config.ts', 'lazy-cjs-helper.js',
'lazy-esm-helper.mjs', 'lazy-ts-helper.ts']`. That second run is what the unit test cannot show:
`trackUserFiles` really does return a resolved `App` _and_ the full set, in the shape `deps upgrade
--apply` uses.

### The mechanism: an `onLoaded` callback, not a moved capture

`trackFiles` gained an optional `onLoaded?: (mod: unknown) => T | Promise<T>`, awaited between
`jiti.import` and the reads of both halves; whatever it returns comes back as `loaded`.
`trackUserFiles` passes `(mod) => resolveApp(mod, configPath)` and reads the resolution off
`loaded`.

The alternative — hoisting the `afterKeys` capture up into `trackUserFiles` — was rejected because
it splits one mechanism across two functions: `trackFiles` would return a half-finished
observation (a `beforeKeys` set and a live jiti instance) that only its caller could complete, and
the ADR's canary would then be testing an assembly rather than the primitive. The callback keeps
the whole union in one function and keeps the documented constraint intact: `trackFiles` still does
not resolve an `App`, is still callable with no callback, and the canary still sidesteps the
cross-realm `instanceof App` artifact that app resolution hits under Vitest.

The generic return type exists to avoid a dead branch. Smuggling the resolution out through a
`let` closure variable forces an `if (!resolution) throw` that can never fire; returning it makes
the type honest with no runtime check. `trackFiles` no longer returns `mod` — with `onLoaded`
receiving it, nothing read the returned copy.

### Two things verified rather than assumed

The brief flagged that the ESM half reads `esmLoadedUrls`, a process-global accumulation, and said
to verify rather than assume how the boundary interacts with it. Two facts came out of that, both
of which constrain what the test may assert (and both now recorded in ADR-0004):

1. **`jiti.cache` is shared across `createJiti` instances** in a process — a brand-new instance's
   cache already lists everything a previous instance loaded. The cache diff is therefore genuinely
   per-call, and a `.ts` helper tracked by one call is absent from the next call's diff.
2. **jiti routes `await import("./helper.js")` from transpiled config code through Node's native
   `import()`**, so a plain-CJS helper imported _lazily_ is recorded by the `module.register` hook
   as well as by the cache diff. Only the `.ts` helper is exclusive to the cache diff.

The practical consequence is the second test's shape: after a resolver-ful call, only
`lazy-ts-helper.ts` can be asserted _absent_ from a resolver-less call. Asserting the other two
absent passes today and would fail the moment anything else in the process touched them — the exact
kind of assertion the repo's canary discipline is against.

### Green

`packages/typescript/src/pin/sources.test.ts` gained a second `describe` covering the new fixture:
the config, both cache-diff helpers, and the `.mjs` are all tracked when the resolver runs inside
the window; the config alone (plus what the process already accumulated) when it does not. It sits
_below_ the existing `sources-project` block on purpose, and says so: that block asserts an exact
tracked set, and the ESM half's process-global accumulation means loading a second fixture's `.mjs`
first would leak into it. The two fixtures keep separate `.mjs` files for the same reason.

Suites: **vitest 1071 passed (46 files)**, was 1069/46. **pytest 1008 passed**, unchanged, and
1008 again under `CI=true`.

### Python needed no peer test

Checked rather than assumed: `TestTrackUserFiles::test_lazy_create_app_import_is_tracked` in
`packages/python/tests/test_pin/test_sources.py` already asserts exactly this — a helper imported
inside `create_app()`, tracked — and already cites ADR-0004 for why. Parity holds in the suites as
well as the source, so nothing was added there. Python has no ESM/CJS split, so the two-halves
distinction has no Python peer to write.

### Deliberately not done

- **No CLI-level `deps upgrade --apply` test.** The rewrite path (`locateUsesRefs` → `applyUpdates`)
  is unchanged and already covered; what was broken was the input set, and that is now pinned at the
  primitive. The port has no subprocess harness, and `deps upgrade` reaches the GitHub API, so an
  end-to-end test would have to mock the thing ADR-0004 says must not be mocked to be worth
  anything. The out-of-Vitest `dist/` run above is the end-to-end evidence instead, recorded here
  rather than automated.
- **ADR-0004's mechanism is untouched.** The `transform` hook and `module.register`-as-replacement
  are still refused, per its Consequences. This moved _when_ the window closes; the cache diff and
  the ESM hook are byte-for-byte the same. The ADR gained a dated `Resolved` section and its
  opening sentence now describes the wider window, since the old wording ("before and after
  importing the user's config") had become false.

## Files

- `packages/typescript/src/pin/sources.ts` — `onLoaded`, and the window it defines
- `packages/typescript/src/pin/sources.test.ts` — the red-then-green block
- `packages/typescript/fixtures/lazy-app-project/` — the new fixture
- `packages/python/src/ghagen/pin/sources.py` — the correct behaviour this matched
- `docs/adr/0004-user-file-tracking-via-jiti-cache-diff.md` — updated
