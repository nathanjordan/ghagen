/**
 * Project-level options loaded from `.ghagen.yml`.
 */

import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { ghagenYmlSchema, type GhagenOptions } from "./_config-schema.js";
import { loadYamlConfig } from "./_yaml-config.js";

export type { GhagenOptions };

/**
 * Load project options from `.ghagen.yml` at the repo root.
 *
 * Falls back to defaults when the file is missing or has no `options:` section.
 */
export function loadOptions(cwd: string): GhagenOptions {
  const ghagenYml = resolve(cwd, ".ghagen.yml");

  if (existsSync(ghagenYml)) {
    const data = loadYamlConfig(ghagenYml);
    const config = ghagenYmlSchema.parse(data);
    if (config.options) return config.options;
  }

  return { auto_dedent: true };
}

/**
 * Module-level flag controlling whether `step({ run: ... })` values are
 * auto-dedented at construction time. Defaults to true. Set via
 * `setAutoDedent(false)` or `options: { auto_dedent: false }` in
 * `.ghagen.yml`.
 *
 * NOTE: This is module-level mutable state. It is not safe for concurrent
 * App instances with different configs. Fine for ghagen's single-threaded
 * CLI usage.
 */
let autoDedentFlag = true;

/** Read the current auto-dedent flag. */
export function getAutoDedent(): boolean {
  return autoDedentFlag;
}

/** Set the module-level auto-dedent flag. */
export function setAutoDedent(value: boolean): void {
  autoDedentFlag = value;
}
