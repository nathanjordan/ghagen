/**
 * Capture the user-code source location of a model factory call.
 *
 * Walks the V8 stack trace looking for the first frame that is NOT inside
 * the ghagen package or `node_modules`. Returns `null` if no such frame
 * exists (e.g. when constructed entirely from inside ghagen internals).
 */

import callsites from "callsites";
import { isInternalFrame } from "./_package_paths.js";

/** Location of a single source line. */
export interface SourceLocation {
  /** Absolute path to the source file. */
  readonly file: string;
  /** Line number (1-indexed). */
  readonly line: number;
}

/**
 * Walk the current stack trace and return the first user-code frame.
 *
 * Skips frames internal to ghagen (anything in this package's source/dist
 * directory) and frames from `node_modules`.
 */
export function captureSourceLocation(): SourceLocation | null {
  for (const site of callsites()) {
    const file = site.getFileName();
    if (!file) {
      continue;
    }
    if (isInternalFrame(file)) {
      continue;
    }
    return { file, line: site.getLineNumber() ?? 0 };
  }
  return null;
}
