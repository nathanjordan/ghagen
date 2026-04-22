/**
 * Lint configuration loaded from `.ghagen.yml`.
 */

import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { loadYamlConfig } from "../_yaml-config.js";
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
      throw new Error(`${source}: severity for '${ruleId}' must be a string, got ${typeof value}`);
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
    throw new Error(`${source}: [lint].disable must be a list, got ${typeof raw}`);
  }
  for (const item of raw) {
    if (typeof item !== "string") {
      throw new Error(`${source}: [lint].disable entries must be strings, got ${typeof item}`);
    }
  }
  return new Set(raw as string[]);
}

function extractFromGhagenYml(path: string): LintConfig | null {
  const data = loadYamlConfig(path);
  const lintSection = data["lint"];
  if (lintSection === undefined || lintSection === null) {
    return null;
  }
  if (typeof lintSection !== "object" || Array.isArray(lintSection)) {
    throw new Error(`${path}: "lint" must be a mapping, got ${Array.isArray(lintSection) ? "array" : typeof lintSection}`);
  }
  const lint = lintSection as Record<string, unknown>;
  return {
    disable: parseDisable(lint["disable"], path),
    severity: parseSeverityMap(lint["severity"], path),
  };
}

/** Result of loading and merging lint configuration. */
export interface LoadLintConfigResult {
  /** The merged lint configuration ready for use by the lint runner. */
  readonly config: LintConfig;
  /** Non-fatal warnings encountered during config loading (always empty; kept for API compat). */
  readonly warnings: readonly string[];
}

/**
 * Load lint config from `.ghagen.yml` and merge CLI overrides.
 *
 * Precedence (highest wins):
 *   1. CLI flags (`cliDisable`) — unioned into the final disable set
 *   2. `.ghagen.yml` `lint:` section
 *   3. Defaults (empty)
 */
export function loadLintConfig(
  cwd: string,
  cliDisable: readonly string[] = [],
): LoadLintConfigResult {
  const warnings: string[] = [];

  const ghagenYml = resolve(cwd, ".ghagen.yml");

  let chosen: LintConfig =
    existsSync(ghagenYml) ? (extractFromGhagenYml(ghagenYml) ?? EMPTY_CONFIG) : EMPTY_CONFIG;

  if (cliDisable.length > 0) {
    chosen = {
      disable: new Set([...chosen.disable, ...cliDisable]),
      severity: chosen.severity,
    };
  }

  return { config: chosen, warnings };
}
