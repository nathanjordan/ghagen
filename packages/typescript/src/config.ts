/**
 * Project configuration: root discovery and options loaded from `.ghagen.yml`.
 *
 * `findAppRoot` is the single root locator used by both `loadOptions` and the
 * header's `{source_file}` resolution.
 */

import { existsSync, statSync } from "node:fs";
import { dirname, isAbsolute, resolve } from "node:path";
import { ghagenYmlSchema, type GhagenOptions } from "./_config-schema.js";
import { loadYamlConfig } from "./_yaml-config.js";

export type { GhagenOptions };

/** Canonical marker file: its presence identifies the ghagen project root. */
export const GHAGEN_YML_MARKER = ".ghagen.yml";

/**
 * Walk upward from *start* looking for `.ghagen.yml`.
 *
 * Returns the directory containing `.ghagen.yml` if found, else
 * `null`. When *start* is omitted, walks from `process.cwd()`. When
 * *start* refers to a file, the search begins at the file's parent
 * directory.
 */
export function findAppRoot(start?: string): string | null {
  let base = start ?? process.cwd();
  if (!isAbsolute(base)) {
    base = resolve(base);
  }

  if (existsSync(base) && statSync(base).isFile()) {
    base = dirname(base);
  }

  let cur = base;
  while (true) {
    const marker = resolve(cur, GHAGEN_YML_MARKER);
    if (existsSync(marker) && statSync(marker).isFile()) {
      return cur;
    }
    const parent = dirname(cur);
    if (parent === cur) {
      return null;
    }
    cur = parent;
  }
}

/**
 * Load project options from `.ghagen.yml` at the repo root.
 *
 * The config file is located via {@link findAppRoot} (an ancestor walk from
 * *start*), the same discovery used for the header's `{source_file}`
 * resolution. Falls back to defaults when the file is missing or has no
 * `options:` section.
 */
export function loadOptions(start?: string): GhagenOptions {
  const root = findAppRoot(start);
  if (root !== null) {
    const data = loadYamlConfig(resolve(root, GHAGEN_YML_MARKER));
    const config = ghagenYmlSchema.parse(data);
    if (config.options) {
      return config.options;
    }
  }

  return { auto_dedent: true };
}
