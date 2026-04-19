/**
 * Project-level options loaded from `.github/ghagen.toml` or
 * `package.json`'s `"ghagen"` field.
 */

import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { loadToml } from "./_toml.js";

/**
 * Options controlling ghagen behaviour.
 *
 * Loaded from `[options]` in `.github/ghagen.toml` or
 * `"ghagen": { "options": {...} }` in `package.json`.
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
    throw new Error(
      `${source}: [options].${key} must be a boolean, got ${typeof value}`,
    );
  }
  return value;
}

function extractFromGhagenToml(path: string): GhagenOptions | null {
  const data = loadToml(path);
  const options = data["options"];
  if (options === undefined || options === null) return null;
  if (typeof options !== "object" || Array.isArray(options)) {
    throw new Error(`${path}: [options] must be a table`);
  }
  const opts = options as Record<string, unknown>;
  return {
    autoDedent: parseBool(
      opts["auto_dedent"] ?? true,
      "auto_dedent",
      path,
    ),
  };
}

function extractFromPackageJson(path: string): GhagenOptions | null {
  let raw: unknown;
  try {
    raw = JSON.parse(readFileSync(path, "utf8"));
  } catch (err) {
    throw new Error(
      `${path}: failed to parse JSON: ${(err as Error).message}`,
      { cause: err },
    );
  }
  if (typeof raw !== "object" || raw === null) return null;
  const pkg = raw as Record<string, unknown>;
  const ghagen = pkg["ghagen"];
  if (ghagen === undefined || ghagen === null) return null;
  if (typeof ghagen !== "object" || Array.isArray(ghagen)) return null;
  const options = (ghagen as Record<string, unknown>)["options"];
  if (options === undefined || options === null) return null;
  if (typeof options !== "object" || Array.isArray(options)) {
    throw new Error(`${path}: "ghagen.options" must be an object`);
  }
  const opts = options as Record<string, unknown>;
  // Accept both autoDedent (camelCase, native to JS) and auto_dedent
  // (snake_case, matches Python). Camel wins if both present.
  const value =
    opts["autoDedent"] ?? opts["auto_dedent"] ?? true;
  return {
    autoDedent: parseBool(value, "autoDedent", path),
  };
}

/**
 * Load project options from standard config file locations.
 *
 * Precedence (highest wins):
 *   1. `.github/ghagen.toml` `[options]` section
 *   2. `package.json` `"ghagen": { "options": {...} }` field
 *   3. Defaults
 */
export function loadOptions(cwd: string): GhagenOptions {
  const ghagenToml = resolve(cwd, ".github", "ghagen.toml");
  const packageJson = resolve(cwd, "package.json");

  if (existsSync(ghagenToml)) {
    const result = extractFromGhagenToml(ghagenToml);
    if (result !== null) return result;
  }

  if (existsSync(packageJson)) {
    const result = extractFromPackageJson(packageJson);
    if (result !== null) return result;
  }

  return { ...DEFAULT_OPTIONS };
}
