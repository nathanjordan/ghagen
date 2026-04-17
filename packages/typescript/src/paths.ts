/**
 * Path utilities for locating the ghagen project root.
 */

import { existsSync, statSync } from "node:fs";
import { dirname, isAbsolute, resolve } from "node:path";

/** Canonical marker file: its presence identifies the ghagen project root. */
export const GHAGEN_TOML_MARKER = ".github/ghagen.toml";

/**
 * Walk upward from *start* looking for `.github/ghagen.toml`.
 *
 * Returns the directory containing `.github/ghagen.toml` if found, else
 * `null`. When *start* is omitted, walks from `process.cwd()`. When
 * *start* refers to a file, the search begins at the file's parent
 * directory.
 */
export function findAppRoot(start?: string): string | null {
  let base = start ?? process.cwd();
  if (!isAbsolute(base)) base = resolve(base);

  if (existsSync(base) && statSync(base).isFile()) {
    base = dirname(base);
  }

  let cur = base;
  while (true) {
    const marker = resolve(cur, GHAGEN_TOML_MARKER);
    if (existsSync(marker) && statSync(marker).isFile()) {
      return cur;
    }
    const parent = dirname(cur);
    if (parent === cur) return null;
    cur = parent;
  }
}
