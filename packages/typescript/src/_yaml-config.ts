/**
 * Shared YAML config loading utility.
 *
 * Wraps the `yaml` package with consistent error handling for use
 * across the config and pin subsystems.
 */

import { readFileSync } from "node:fs";
import { parse } from "yaml";

/** Read and parse a YAML config file. Throws on parse errors. */
export function loadYamlConfig(path: string): Record<string, unknown> {
  let text: string;
  try {
    text = readFileSync(path, "utf8");
  } catch (err) {
    throw new Error(`${path}: failed to read YAML file: ${(err as Error).message}`, { cause: err });
  }
  let data: unknown;
  try {
    data = parse(text);
  } catch (err) {
    throw new Error(`${path}: failed to parse YAML: ${(err as Error).message}`, { cause: err });
  }
  if (data === null || data === undefined) return {};
  if (typeof data !== "object" || Array.isArray(data)) {
    throw new Error(`${path}: expected a YAML mapping at top level`);
  }
  return data as Record<string, unknown>;
}
