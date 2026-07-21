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
 * The `appLoader` argument only supplies the returned `App`; it exists to
 * sidestep the cross-realm `instanceof App` artifact under Vitest (jiti
 * loads `App` in its own module graph — see cli/main.test.ts). File
 * tracking still runs through the real, unmocked jiti.cache diff plus the
 * real, unmocked `module.register` hook.
 */

import { describe, it, expect } from "vitest";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { App } from "../app.js";
import { trackUserFiles } from "./sources.js";

// Resolve the fixture from this file's location (src/pin/), never from cwd.
const HERE = fileURLToPath(new URL(".", import.meta.url));
const FIXTURE_DIR = resolve(HERE, "../../fixtures/sources-project");
const configPath = resolve(FIXTURE_DIR, "ghagen.config.ts");
const fixtureFile = (name: string) => resolve(FIXTURE_DIR, name);

describe("trackUserFiles (real jiti, ADR-0004 canary)", () => {
  it("tracks the config plus its transpiled, native-required, and native-ESM helpers", async () => {
    const { files } = await trackUserFiles(configPath, async () => new App());

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
    const { files } = await trackUserFiles(configPath, async () => new App());
    expect(files.has(fixtureFile("esm-helper.mjs"))).toBe(true);
  });
});
