/**
 * Shared TOML loading/dumping utility.
 *
 * Wraps `smol-toml` (zero native deps, pure TS) with consistent error
 * handling for use across the config and pin subsystems.
 */

import { readFileSync } from "node:fs";
import { parse, stringify } from "smol-toml";

/** Read and parse a TOML file. Throws on parse errors. */
export function loadToml(path: string): Record<string, unknown> {
  let text: string;
  try {
    text = readFileSync(path, "utf8");
  } catch (err) {
    throw new Error(`${path}: failed to read TOML file: ${(err as Error).message}`);
  }
  try {
    return parse(text) as Record<string, unknown>;
  } catch (err) {
    throw new Error(`${path}: failed to parse TOML: ${(err as Error).message}`);
  }
}

/** Serialize a value to a TOML string. */
export function dumpsToml(obj: Record<string, unknown>): string {
  return stringify(obj);
}
