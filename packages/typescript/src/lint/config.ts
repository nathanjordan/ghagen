/**
 * Lint configuration loaded from `.github/ghagen.toml` or `package.json`.
 */

import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { loadToml } from "../_toml.js";
import type { Severity } from "./violation.js";
import { SEVERITY_VALUES } from "./violation.js";

/** Configuration controlling which lint rules run and at what severity. */
export interface LintConfig {
  /** Rule IDs to skip entirely (e.g. from `--disable` or `[lint].disable`). */
  readonly disable: ReadonlySet<string>;
  /** Per-rule severity overrides (keys are rule IDs, values are `"error"` or `"warning"`). */
  readonly severity: ReadonlyMap<string, Severity>;
}

const EMPTY_CONFIG: LintConfig = {
  disable: new Set(),
  severity: new Map(),
};

function parseSeverityMap(raw: unknown, source: string): Map<string, Severity> {
  if (raw === undefined || raw === null) return new Map();
  if (typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error(
      `${source}: [lint.severity] must be a table, got ${Array.isArray(raw) ? "array" : typeof raw}`,
    );
  }
  const result = new Map<string, Severity>();
  for (const [ruleId, value] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof value !== "string") {
      throw new Error(
        `${source}: severity for '${ruleId}' must be a string, got ${typeof value}`,
      );
    }
    if (!SEVERITY_VALUES.includes(value as Severity)) {
      const valid = SEVERITY_VALUES.join(", ");
      throw new Error(
        `${source}: invalid severity '${value}' for rule '${ruleId}' (valid values: ${valid})`,
      );
    }
    result.set(ruleId, value as Severity);
  }
  return result;
}

function parseDisable(raw: unknown, source: string): Set<string> {
  if (raw === undefined || raw === null) return new Set();
  if (!Array.isArray(raw)) {
    throw new Error(
      `${source}: [lint].disable must be a list, got ${typeof raw}`,
    );
  }
  for (const item of raw) {
    if (typeof item !== "string") {
      throw new Error(
        `${source}: [lint].disable entries must be strings, got ${typeof item}`,
      );
    }
  }
  return new Set(raw as string[]);
}

function extractFromGhagenToml(path: string): LintConfig | null {
  const data = loadToml(path);
  const lintSection = data["lint"];
  if (lintSection === undefined || lintSection === null) {
    // Returning null means "no [lint] section" — defer to next source.
    // Caller still uses the table-existence check to emit the multi-
    // source warning.
    return null;
  }
  if (typeof lintSection !== "object" || Array.isArray(lintSection)) {
    throw new Error(`${path}: [lint] must be a table`);
  }
  const lint = lintSection as Record<string, unknown>;
  return {
    disable: parseDisable(lint["disable"], path),
    severity: parseSeverityMap(lint["severity"], path),
  };
}

function extractFromPackageJson(path: string): LintConfig | null {
  let raw: unknown;
  try {
    raw = JSON.parse(readFileSync(path, "utf8"));
  } catch (err) {
    throw new Error(
      `${path}: failed to parse JSON: ${(err as Error).message}`,
    );
  }
  if (typeof raw !== "object" || raw === null) return null;
  const ghagen = (raw as Record<string, unknown>)["ghagen"];
  if (typeof ghagen !== "object" || ghagen === null || Array.isArray(ghagen)) {
    return null;
  }
  const lint = (ghagen as Record<string, unknown>)["lint"];
  if (lint === undefined || lint === null) return null;
  if (typeof lint !== "object" || Array.isArray(lint)) {
    throw new Error(`${path}: "ghagen.lint" must be an object`);
  }
  const lintObj = lint as Record<string, unknown>;
  return {
    disable: parseDisable(lintObj["disable"], path),
    severity: parseSeverityMap(lintObj["severity"], path),
  };
}

/** Result of loading and merging lint configuration from all sources. */
export interface LoadLintConfigResult {
  /** The merged lint configuration ready for use by the lint runner. */
  readonly config: LintConfig;
  /** Non-fatal warnings encountered during config loading (e.g. duplicate config sources). */
  readonly warnings: readonly string[];
}

/**
 * Load lint config from standard locations and merge CLI overrides.
 *
 * Precedence (highest wins):
 *   1. CLI flags (`cliDisable`) — unioned into the final disable set
 *   2. `.github/ghagen.toml` `[lint]` section
 *   3. `package.json` `"ghagen": { "lint": {...} }` field
 *   4. Defaults (empty)
 *
 * When both `.github/ghagen.toml` and `package.json` provide a lint
 * config, the former wins and a warning is appended describing which
 * was used.
 */
export function loadLintConfig(
  cwd: string,
  cliDisable: readonly string[] = [],
): LoadLintConfigResult {
  const warnings: string[] = [];

  const ghagenToml = resolve(cwd, ".github", "ghagen.toml");
  const packageJson = resolve(cwd, "package.json");

  const ghagenConfig = existsSync(ghagenToml)
    ? extractFromGhagenToml(ghagenToml)
    : null;
  const packageConfig = existsSync(packageJson)
    ? extractFromPackageJson(packageJson)
    : null;

  let chosen: LintConfig;
  if (ghagenConfig !== null && packageConfig !== null) {
    warnings.push(
      "lint config found in multiple locations:\n" +
        `  - ${ghagenToml} (used)\n` +
        `  - ${packageJson} \"ghagen.lint\" (ignored)\n` +
        "Remove one to silence this warning.",
    );
    chosen = ghagenConfig;
  } else if (ghagenConfig !== null) {
    chosen = ghagenConfig;
  } else if (packageConfig !== null) {
    chosen = packageConfig;
  } else {
    chosen = EMPTY_CONFIG;
  }

  if (cliDisable.length > 0) {
    chosen = {
      disable: new Set([...chosen.disable, ...cliDisable]),
      severity: chosen.severity,
    };
  }

  return { config: chosen, warnings };
}
