/**
 * Determine which TS/JS source files contain each `uses:` ref string.
 *
 * Used by `deps upgrade` to scope `applyUpdates` to user-controlled
 * source files. Internal vs. user-authored paths are classified with the
 * shared predicate in `_package_paths.ts` (also used by
 * `_source_location.ts`).
 *
 * Implementation note: user-file tracking diffs `jiti.cache` before/after
 * importing the config. `cache` is typed, non-deprecated public surface —
 * jiti's own `types.d.ts` declares `Jiti extends NodeRequire { cache:
 * ModuleCache }` with no `@deprecated` marker (unlike its call/`resolve`
 * signatures). This mechanism is kept deliberately over the `transform`
 * hook, which misses plain-CommonJS helpers (native require, no transform
 * call); see docs/adr/0004-user-file-tracking-via-jiti-cache-diff.md. The
 * real-jiti integration test (`sources.test.ts`) is the canary.
 */

import { existsSync, readFileSync } from "node:fs";
import { createJiti } from "jiti";
import type { App } from "../app.js";
import { resolveAppFromModule } from "../_load.js";
import { isUserFile } from "../_package_paths.js";

/**
 * Import `configPath` through jiti and return both the resolved {@link App}
 * and the user-source files loaded as a side effect.
 *
 * Returns absolute file paths, filtering out `node_modules` and files inside
 * the ghagen package itself. The App is resolved via the shared
 * {@link resolveAppFromModule} policy; pass `appLoader` to override how the
 * App is obtained (the jiti import — and therefore file tracking — always
 * runs regardless, so a custom loader does not disable the cache diff).
 */
export async function trackUserFiles(
  configPath: string,
  appLoader?: (configPath: string) => Promise<App> | App,
): Promise<{ app: App; files: Set<string> }> {
  const jiti = createJiti(configPath, { fsCache: false });
  const beforeKeys = new Set<string>(Object.keys(jiti.cache));

  // Always import through this jiti instance so the cache diff observes
  // every file it loads — including plain-CommonJS helpers routed through
  // native require, the case a `transform` hook would miss (ADR-0004).
  const mod = await jiti.import(configPath);

  const afterKeys = new Set<string>(Object.keys(jiti.cache));
  const files = new Set<string>();
  for (const key of afterKeys) {
    if (!beforeKeys.has(key) && isUserFile(key)) {
      files.add(key);
    }
  }
  // jiti's import() may not surface the entry-point itself in some cases.
  // Always include the config file explicitly.
  if (isUserFile(configPath)) {
    files.add(configPath);
  }

  const app = appLoader ? await appLoader(configPath) : await resolveAppFromModule(mod, configPath);
  return { app, files };
}

/**
 * Search user files for each ref string and return a mapping of ref →
 * files. Refs not found in any user file are omitted from the result.
 */
export function locateUsesRefs(
  refs: ReadonlySet<string>,
  userFiles: ReadonlySet<string>,
): Map<string, string[]> {
  const fileContents = new Map<string, string>();
  for (const path of userFiles) {
    if (!existsSync(path)) {
      continue;
    }
    try {
      fileContents.set(path, readFileSync(path, "utf8"));
    } catch {
      // Skip unreadable files.
    }
  }

  const result = new Map<string, string[]>();
  for (const ref of refs) {
    const matching: string[] = [];
    for (const [path, content] of fileContents.entries()) {
      if (content.includes(ref)) {
        matching.push(path);
      }
    }
    if (matching.length > 0) {
      matching.sort();
      result.set(ref, matching);
    }
  }
  return result;
}
