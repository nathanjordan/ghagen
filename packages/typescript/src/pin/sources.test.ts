/**
 * Real-jiti integration test for `trackUserFiles` — the ADR-0004 canary.
 *
 * jiti is NOT mocked here: `trackUserFiles` runs the genuine
 * `createJiti(...).import()` + `jiti.cache` diff over a fixture project
 * (`fixtures/sources-project/`). Its whole purpose is to turn a silent
 * regression (jiti changing cache behavior -> empty file set -> no-op
 * `deps upgrade`) into a red test.
 *
 * The fixture's config imports one helper of each flavour:
 *   - `ts-helper.ts`   — transpiled by jiti (in cache)
 *   - `cjs-helper.js`  — plain CommonJS, native require (in cache; the case
 *                        a `transform` hook would miss — the point of ADR-0004)
 *   - `esm-helper.mjs` — native ESM, loaded via `import()` and NEVER entered
 *                        into `jiti.cache`; caught instead by the
 *                        `module.register` ESM load hook (ADR-0004 union)
 * plus a `node_modules/ghagen-internal` package that must be excluded.
 *
 * The canary exercises `trackFiles`, the ADR-0004 tracking primitive, rather
 * than `trackUserFiles`: it asserts only the tracked `files` set and does not
 * need a resolved `App`, so it sidesteps the cross-realm `instanceof App`
 * artifact under Vitest (jiti loads `App` in its own module graph — see
 * cli/main.test.ts). File tracking runs through the real, unmocked jiti.cache
 * diff plus the real, unmocked `module.register` hook.
 */

import { describe, it, expect } from "vitest";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { trackFiles } from "./sources.js";

// Resolve the fixture from this file's location (src/pin/), never from cwd.
const HERE = fileURLToPath(new URL(".", import.meta.url));
const FIXTURE_DIR = resolve(HERE, "../../fixtures/sources-project");
const configPath = resolve(FIXTURE_DIR, "ghagen.config.ts");
const fixtureFile = (name: string) => resolve(FIXTURE_DIR, name);

const LAZY_DIR = resolve(HERE, "../../fixtures/lazy-app-project");
const lazyConfigPath = resolve(LAZY_DIR, "ghagen.config.ts");
const lazyFile = (name: string) => resolve(LAZY_DIR, name);

describe("trackUserFiles (real jiti, ADR-0004 canary)", () => {
  it("tracks the config plus its transpiled, native-required, and native-ESM helpers", async () => {
    const { files } = await trackFiles(configPath);

    expect(files.has(configPath)).toBe(true);
    expect(files.has(fixtureFile("ts-helper.ts"))).toBe(true);
    // The plain-CommonJS helper is the case a jiti `transform` hook would
    // miss (native require, no transform call); the cache diff catches it.
    expect(files.has(fixtureFile("cjs-helper.js"))).toBe(true);
    // The native-ESM helper never enters `jiti.cache`; the `module.register`
    // load hook catches it and the union folds it in (ADR-0004 resolution).
    expect(files.has(fixtureFile("esm-helper.mjs"))).toBe(true);

    // node_modules (including the fixture's ghagen-internal package) and
    // ghagen's own source are excluded.
    expect([...files].some((f) => f.includes("/node_modules/"))).toBe(false);
    expect([...files].some((f) => f.includes("ghagen-internal"))).toBe(false);

    // Exact tracked set: the config and all three helper flavours.
    expect(files).toEqual(
      new Set([
        configPath,
        fixtureFile("ts-helper.ts"),
        fixtureFile("cjs-helper.js"),
        fixtureFile("esm-helper.mjs"),
      ]),
    );
  });

  it("tracks native-ESM .mjs helpers via the module.register hook", async () => {
    // A native ESM `.mjs` helper is loaded through Node's `import()` and
    // never enters `jiti.cache`, so the cache diff alone cannot see it. The
    // `module.register` load hook observes exactly those ESM loads, so the
    // union tracks it. Asserting its presence makes the canary fire if a
    // future jiti or Node release breaks the hook in either direction.
    const { files } = await trackFiles(configPath);
    expect(files.has(fixtureFile("esm-helper.mjs"))).toBe(true);
  });
});

/**
 * Issue 03: helpers imported lazily *inside* `createApp()`.
 *
 * This block must stay BELOW the one above. `esmLoadedUrls` in `sources.ts` is
 * a process-globally accumulated set (ADR-0004's ESM half reads the whole set,
 * not a per-call diff), so loading this fixture's `.mjs` first would leak it
 * into the exact-set assertion above. The two fixtures keep separate `.mjs`
 * files for the same reason.
 */
describe("trackFiles with app resolution (lazy createApp imports)", () => {
  it("tracks helpers first imported while the resolver runs", async () => {
    // The fixture config imports NOTHING but `App` at module scope: all three
    // helpers are `await import(...)`ed inside `createApp()`, so they load
    // only while the resolver callback runs. Before that callback existed the
    // window closed on the config import and every one of them was missed --
    // `deps upgrade --apply` reported success and left their pins stale.
    //
    // The callback stands in for `resolveApp` without its `instanceof App`
    // check, which is unreliable here because jiti loads `App` in its own
    // module graph (see this file's header). What is under test is *when* the
    // window closes, not the resolution policy -- so the stand-in runs the
    // real factory, which is all the window has to observe.
    const { files } = await trackFiles(lazyConfigPath, async (mod) => {
      const factory = (mod as { createApp?: () => Promise<unknown> }).createApp;
      expect(typeof factory).toBe("function");
      await factory?.();
    });

    expect(files.has(lazyConfigPath)).toBe(true);
    // Cache-diff half of the ADR-0004 union: only jiti transpiles the `.ts`
    // helper, so it exists nowhere else.
    expect(files.has(lazyFile("lazy-ts-helper.ts"))).toBe(true);
    expect(files.has(lazyFile("lazy-cjs-helper.js"))).toBe(true);
    // ESM half: the `.mjs` never enters `jiti.cache`, so only the
    // `module.register` hook sees it -- and only if the drain and the read
    // happen after the factory ran.
    expect(files.has(lazyFile("lazy-esm-helper.mjs"))).toBe(true);
  });

  it("stays usable without a resolver, tracking only eager imports", async () => {
    // `trackFiles` remains the standalone tracking primitive: the resolver is
    // optional, so the canary above still needs no resolved App. Its window
    // then really does close on the import -- the `.ts` helper the factory
    // would have pulled in stays untracked.
    const { files } = await trackFiles(lazyConfigPath);
    expect(files.has(lazyConfigPath)).toBe(true);
    expect(files.has(lazyFile("lazy-ts-helper.ts"))).toBe(false);
    // Only the `.ts` helper can be asserted absent, and only because the
    // cache diff is genuinely per-call. The other two are not: jiti routes
    // both `await import("./lazy-cjs-helper.js")` and the `.mjs` through
    // Node's ESM loader, so the previous test recorded them in the
    // process-globally accumulated `esmLoadedUrls` that this call re-reads.
  });
});
