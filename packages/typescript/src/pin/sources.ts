/**
 * Determine which TS/JS source files contain each `uses:` ref string.
 *
 * Used by `deps upgrade` to scope `applyUpdates` to user-controlled
 * source files. Distinguishes between user-authored files and ghagen
 * internal files via the same prefix-matching strategy as
 * `_source_location.ts`.
 *
 * Implementation note: jiti's `cache` is not formally documented as
 * public, but it has been stable across the v2 line and is used by
 * several published projects (Nuxt, unjs ecosystem). If a future jiti
 * release breaks cache introspection, switch to a Node loader hook
 * registered via `module.register`.
 */

import { existsSync, readFileSync } from "node:fs";
import { createJiti } from "jiti";
import type { App } from "../app.js";

/**
 * Run `appLoader` and return the user-source files that were loaded as
 * a side effect.
 *
 * Returns absolute file paths. Filters out files in `node_modules` and
 * inside the ghagen package itself.
 */
export async function trackUserFiles(
  configPath: string,
  appLoader?: (configPath: string) => Promise<App>,
): Promise<{ app: App; files: Set<string> }> {
  const jiti = createJiti(configPath, { fsCache: false });
  const beforeKeys = new Set<string>(Object.keys(jiti.cache));

  let app: App;
  if (appLoader) {
    app = await appLoader(configPath);
  } else {
    const mod = (await jiti.import(configPath)) as {
      app?: App;
      createApp?: () => App | Promise<App>;
      default?: { app?: App; createApp?: () => App | Promise<App> };
    };
    const m = mod.default ?? mod;
    if (typeof m.createApp === "function") {
      app = await m.createApp();
    } else if (m.app) {
      app = m.app;
    } else {
      throw new Error(
        `${configPath}: must export 'app' or 'createApp()' (got: ${
          Object.keys(mod).join(", ") || "<empty>"
        })`,
      );
    }
  }

  const afterKeys = new Set<string>(Object.keys(jiti.cache));
  const newKeys = [...afterKeys].filter((k) => !beforeKeys.has(k));

  const files = new Set<string>();
  for (const key of newKeys) {
    if (isUserFile(key)) {
      files.add(key);
    }
  }
  // jiti's import() may not track the entry-point itself in some cases.
  // Always include the config file explicitly.
  if (isUserFile(configPath)) {
    files.add(configPath);
  }

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

// ---- internal helpers ----

const PACKAGE_INTERNAL_DIR: string = (() => {
  try {
    const url = new URL("..", import.meta.url);
    const path = url.pathname;
    return path.endsWith("/") ? path : `${path}/`;
  } catch {
    return "";
  }
})();

function isUserFile(path: string): boolean {
  if (!path) {
    return false;
  }
  if (path.includes("/node_modules/")) {
    return false;
  }
  // Skip URLs that aren't real filesystem paths.
  if (path.startsWith("data:") || path.startsWith("node:")) {
    return false;
  }
  if (PACKAGE_INTERNAL_DIR && path.startsWith(PACKAGE_INTERNAL_DIR)) {
    if (!path.includes(".test.")) {
      return false;
    }
  }
  return true;
}
