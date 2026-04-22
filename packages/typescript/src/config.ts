/**
 * Project-level options loaded from `.ghagen.yml`.
 */

import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { loadYamlConfig } from "./_yaml-config.js";

/**
 * Options controlling ghagen behaviour.
 *
 * Loaded from `options:` section in `.ghagen.yml`.
 */
export interface GhagenOptions {
  /** Whether to auto-dedent `step.run` strings at construction time. */
  autoDedent: boolean;
}

const DEFAULT_OPTIONS: GhagenOptions = {
  autoDedent: true,
};

function parseBool(value: unknown, key: string, source: string): boolean {
  if (typeof value !== "boolean") {
    throw new Error(`${source}: [options].${key} must be a boolean, got ${typeof value}`);
  }
  return value;
}

function extractFromGhagenYml(path: string): GhagenOptions | null {
  const data = loadYamlConfig(path);
  const options = data["options"];
  if (options === undefined || options === null) return null;
  if (typeof options !== "object" || Array.isArray(options)) {
    throw new Error(`${path}: "options" must be a mapping`);
  }
  const opts = options as Record<string, unknown>;
  return {
    autoDedent: parseBool(opts["auto_dedent"] ?? true, "auto_dedent", path),
  };
}

/**
 * Load project options from `.ghagen.yml` at the repo root.
 *
 * Falls back to defaults when the file is missing or has no `options:` section.
 */
export function loadOptions(cwd: string): GhagenOptions {
  const ghagenYml = resolve(cwd, ".ghagen.yml");

  if (existsSync(ghagenYml)) {
    const result = extractFromGhagenYml(ghagenYml);
    if (result !== null) return result;
  }

  return { ...DEFAULT_OPTIONS };
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
