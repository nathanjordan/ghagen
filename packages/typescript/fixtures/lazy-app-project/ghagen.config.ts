// Fixture for the "lazy createApp()" half of the ADR-0004 canary: NOTHING but
// `App` is imported at module scope. Each helper is imported inside the
// factory, so it is only loaded when `createApp()` runs -- i.e. during app
// resolution, not during the config import. The tracking window therefore has
// to stay open across app resolution for these three files to be seen.
import { App } from "../../src/app.js";

export async function createApp(): Promise<App> {
  const { lazyTsRef } = await import("./lazy-ts-helper.js");
  const { lazyCjsRef } = await import("./lazy-cjs-helper.js");
  const { lazyEsmRef } = await import("./lazy-esm-helper.mjs");
  // Referenced so no bundler/transpiler can argue the imports are dead.
  if (!lazyTsRef || !lazyCjsRef || !lazyEsmRef) {
    throw new Error("lazy fixture helpers did not load");
  }
  return new App();
}
