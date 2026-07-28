/**
 * Determine which TS/JS source files contain each `uses:` ref string.
 *
 * Used by `deps upgrade` to scope `applyUpdates` to user-controlled
 * source files. Internal vs. user-authored paths are classified with the
 * shared predicate in `_package_paths.ts` (also used by
 * `_source_location.ts`).
 *
 * Implementation note: user-file tracking is a UNION of two observations.
 *
 * 1. The primary mechanism diffs `jiti.cache` before/after importing the
 *    config. `cache` is typed, non-deprecated public surface — jiti's own
 *    `types.d.ts` declares `Jiti extends NodeRequire { cache: ModuleCache }`
 *    with no `@deprecated` marker (unlike its call/`resolve` signatures).
 *    It is kept deliberately over the `transform` hook, which misses
 *    plain-CommonJS helpers (native require, no transform call).
 * 2. The cache diff cannot see native-ESM (`.mjs`) helpers: jiti loads them
 *    through a plain in-process dynamic `import()` (its `nativeImport`) that
 *    never enters `jiti.cache`. A Node module-customization hook registered
 *    via `module.register` observes exactly those ESM loads and augments the
 *    diff (see `ensureEsmHook` below).
 *
 * See docs/adr/0004-user-file-tracking-via-jiti-cache-diff.md. The real-jiti
 * integration test (`sources.test.ts`) is the canary for both halves.
 */

import { existsSync, readFileSync } from "node:fs";
import { register } from "node:module";
import { fileURLToPath } from "node:url";
import { MessageChannel } from "node:worker_threads";
import { createJiti } from "jiti";
import type { App } from "../app.js";
import { resolveApp } from "../config.js";
import { isUserFile } from "../_package_paths.js";

/**
 * Absolute-`file:` URLs of every ESM module loaded in this process, recorded
 * by the `module.register` load hook. Native ESM caches process-globally, so
 * a given `.mjs` fires the hook only on its first load — the union in
 * {@link trackUserFiles} therefore reads the whole accumulated set (bounded
 * to genuine user files by {@link isUserFile}) rather than a per-call diff,
 * which would miss modules already imported earlier in the process.
 */
const esmLoadedUrls = new Set<string>();

/**
 * Resolves once the loader thread has run `initialize` and posted its ready
 * sentinel. `trackUserFiles` awaits this before importing so the first import
 * after registration is observed — otherwise the loader-thread handshake can
 * race the import and its `load` messages arrive too late to record. `null`
 * until {@link ensureEsmHook} runs (also its double-registration guard).
 */
let esmHookReady: Promise<void> | null = null;

/**
 * ESM load hook, evaluated on Node's loader thread. `initialize` posts a
 * `{ ready: true }` sentinel so the main thread can await warm-up; `load`
 * posts each loaded module URL, then delegates. Shipped as a `data:` module
 * so no separate compiled file has to be resolved at runtime.
 */
const ESM_TRACK_HOOK = `
  let port;
  export async function initialize(data) {
    port = data.port;
    port.postMessage({ ready: true });
  }
  export async function load(url, context, nextLoad) {
    if (port) port.postMessage({ url });
    return nextLoad(url, context);
  }
`;

/**
 * Register the native-ESM load hook once per process and return a promise
 * that resolves when its loader thread is ready. `module.register` has no
 * deregister, so the hook stays permanently installed but inert: it only
 * appends URLs to {@link esmLoadedUrls}, which callers read on demand.
 */
function ensureEsmHook(): Promise<void> {
  if (esmHookReady) {
    return esmHookReady;
  }
  const { port1, port2 } = new MessageChannel();
  esmHookReady = new Promise<void>((resolve) => {
    port1.on("message", (msg: { ready?: true; url?: string }) => {
      if (msg.ready) {
        resolve();
      } else if (msg.url) {
        esmLoadedUrls.add(msg.url);
      }
    });
  });
  // Recording must not keep the event loop alive on its own.
  port1.unref();
  register(`data:text/javascript,${encodeURIComponent(ESM_TRACK_HOOK)}`, {
    parentURL: import.meta.url,
    data: { port: port2 },
    transferList: [port2],
  });
  return esmHookReady;
}

/**
 * Import `configPath` through jiti and return the imported module together
 * with the user-source files loaded as a side effect. This is the ADR-0004
 * tracking primitive: it runs the jiti-cache diff + ESM-hook union and does
 * NOT resolve an {@link App}, so it can be exercised without the cross-realm
 * `instanceof App` artifact that app resolution hits under Vitest.
 *
 * Returns absolute file paths, filtering out `node_modules` and files inside
 * the ghagen package itself (via {@link isUserFile}).
 */
export async function trackFiles(
  configPath: string,
): Promise<{ mod: unknown; files: Set<string> }> {
  // Wait for the ESM load hook's loader thread to be ready before importing,
  // so even the first import in the process is observed (ADR-0004 union).
  await ensureEsmHook();
  const jiti = createJiti(configPath, { fsCache: false });
  const beforeKeys = new Set<string>(Object.keys(jiti.cache));

  // Always import through this jiti instance so the cache diff observes
  // every file it loads — including plain-CommonJS helpers routed through
  // native require, the case a `transform` hook would miss (ADR-0004).
  const mod = await jiti.import(configPath);

  // The ESM load hook posts URLs cross-thread; let queued messages drain
  // before reading the recorded set. One macrotask turn is enough — the
  // module has already loaded (hook returned) by the time import() resolves.
  await new Promise<void>((resolve) => setTimeout(resolve, 0));

  const afterKeys = new Set<string>(Object.keys(jiti.cache));
  const files = new Set<string>();
  // Primary: files jiti routed through its module cache.
  for (const key of afterKeys) {
    if (!beforeKeys.has(key) && isUserFile(key)) {
      files.add(key);
    }
  }
  // Augment: native-ESM helpers the cache diff cannot see, observed by the
  // `module.register` hook. Read the whole accumulated set (see
  // `esmLoadedUrls`) — a per-call diff would miss modules already imported.
  for (const url of esmLoadedUrls) {
    if (!url.startsWith("file:")) {
      continue;
    }
    const path = fileURLToPath(url);
    if (isUserFile(path)) {
      files.add(path);
    }
  }
  // jiti's import() may not surface the entry-point itself in some cases.
  // Always include the config file explicitly.
  if (isUserFile(configPath)) {
    files.add(configPath);
  }

  return { mod, files };
}

/**
 * Import `configPath` through jiti and return both the resolved {@link App}
 * and the user-source files loaded as a side effect.
 *
 * The file tracking is done by {@link trackFiles} (the ADR-0004 mechanism);
 * the App is resolved from the imported module via the shared
 * {@link resolveApp} policy. The jiti import — and therefore file tracking —
 * always runs, so app resolution never disables the cache diff.
 */
export async function trackUserFiles(
  configPath: string,
): Promise<{ app: App; files: Set<string> }> {
  const { mod, files } = await trackFiles(configPath);
  const resolution = await resolveApp(mod, configPath);
  if (resolution.error) {
    throw new Error(resolution.error.message);
  }
  return { app: resolution.app, files };
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
