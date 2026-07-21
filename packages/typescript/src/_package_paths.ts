/**
 * Classify filesystem paths as ghagen-internal vs. user-authored.
 *
 * Shared by `_source_location.ts` (stack-frame attribution for model
 * factories) and `pin/sources.ts` (deps-upgrade user-file tracking) so a
 * single prefix computation and predicate serve both.
 *
 * `import.meta.url` always points at this file. Its directory is the
 * "package source root" — `.../packages/typescript/src/` in development or
 * `.../node_modules/@ghagen/ghagen/dist/` once published. Any path under
 * that prefix is treated as internal, EXCEPT ghagen's own test files (paths
 * containing `.test.`), so that ghagen's tests can attribute themselves.
 */

const PACKAGE_INTERNAL_DIR: string = (() => {
  try {
    const url = new URL(".", import.meta.url);
    const path = url.pathname;
    return path.endsWith("/") ? path : `${path}/`;
  } catch {
    return "";
  }
})();

/**
 * True if `filename` belongs to ghagen's own source/dist or to
 * `node_modules` — i.e. NOT a user-authored frame. Ghagen's own `.test.`
 * files are treated as external so their frames can be captured.
 */
export function isInternalFrame(filename: string): boolean {
  if (filename.includes("/node_modules/")) {
    return true;
  }
  if (PACKAGE_INTERNAL_DIR && filename.startsWith(PACKAGE_INTERNAL_DIR)) {
    // Allow `.test.` files through so ghagen's own unit tests can capture
    // themselves as the call site.
    if (filename.includes(".test.")) {
      return false;
    }
    return true;
  }
  return false;
}

/**
 * True if `path` is a real user-authored source file: a filesystem path
 * that is neither ghagen-internal, under `node_modules`, nor a non-file
 * URL (`data:` / `node:`). This is the tracking-side counterpart to
 * {@link isInternalFrame}, with the extra URL/empty filtering that
 * `jiti.cache` keys can require.
 */
export function isUserFile(path: string): boolean {
  if (!path) {
    return false;
  }
  // Skip URLs that aren't real filesystem paths.
  if (path.startsWith("data:") || path.startsWith("node:")) {
    return false;
  }
  return !isInternalFrame(path);
}
