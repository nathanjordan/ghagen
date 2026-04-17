/**
 * Capture the user-code source location of a model factory call.
 *
 * Walks the V8 stack trace looking for the first frame that is NOT inside
 * the ghagen package or `node_modules`. Returns `null` if no such frame
 * exists (e.g. when constructed entirely from inside ghagen internals).
 */

/** Location of a single source line. */
export interface SourceLocation {
  /** Absolute path to the source file. */
  readonly file: string;
  /** Line number (1-indexed). */
  readonly line: number;
}

// Detect ghagen's own source/dist directory at module-load time. Used to
// recognise ghagen-internal frames in the stack so they can be skipped
// when locating the user's call site.
//
// `import.meta.url` always points at this file. From it we compute the
// "package source root" — the parent of the directory containing this
// file (e.g. `.../packages/typescript/src/` or
// `.../node_modules/@ghagen/ghagen/dist/`). Any frame whose path starts
// with that prefix is treated as internal, EXCEPT test files (whose
// paths contain `.test.`), so that ghagen's own tests can capture
// themselves as the call site.
const PACKAGE_INTERNAL_DIR: string = (() => {
  try {
    const url = new URL(".", import.meta.url);
    const path = url.pathname;
    return path.endsWith("/") ? path : `${path}/`;
  } catch {
    return "";
  }
})();

function isInternalFrame(filename: string): boolean {
  if (filename.includes("/node_modules/")) {
    // node_modules path — but NOT if it's a vitest/mocha test file: in
    // most setups tests don't live under node_modules so this is rare.
    return true;
  }
  if (PACKAGE_INTERNAL_DIR && filename.startsWith(PACKAGE_INTERNAL_DIR)) {
    // Internal to ghagen's own source/dist. Allow `.test.` files
    // through so ghagen's own unit tests can capture themselves.
    if (filename.includes(".test.")) return false;
    return true;
  }
  return false;
}

/**
 * Parse a single V8 stack frame line, extracting `(file:line:col)` or
 * `at file:line:col`. Returns null if the frame can't be parsed.
 */
function parseFrame(frame: string): SourceLocation | null {
  // V8 formats:
  //   at functionName (file:line:col)
  //   at file:line:col
  //   at functionName (file:line:col), with file as URL (file://...)
  // Match the parenthesized form first (most common).
  let match = /\(([^)]+):(\d+):\d+\)\s*$/.exec(frame);
  if (!match) {
    match = /at\s+([^\s(]+):(\d+):\d+\s*$/.exec(frame);
  }
  if (!match) return null;

  let file = match[1]!;
  // Strip file:// URL prefix if present.
  if (file.startsWith("file://")) {
    try {
      file = new URL(file).pathname;
    } catch {
      file = file.slice("file://".length);
    }
  }
  const line = Number.parseInt(match[2]!, 10);
  if (Number.isNaN(line)) return null;

  return { file, line };
}

/**
 * Walk the current stack trace and return the first user-code frame.
 *
 * Skips frames matching `INTERNAL_FRAME_MARKERS` (anything in `/ghagen/`
 * or `/node_modules/`). Also skips this function's own frame and the
 * caller frame (the model factory).
 */
export function captureSourceLocation(): SourceLocation | null {
  const stack = new Error().stack;
  if (!stack) return null;

  const lines = stack.split("\n");
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed.startsWith("at ")) continue;
    const loc = parseFrame(trimmed);
    if (!loc) continue;
    if (isInternalFrame(loc.file)) continue;
    return loc;
  }

  return null;
}
