/**
 * Project configuration: root discovery, YAML loading, and options loaded
 * from `.ghagen.yml`.
 *
 * This module unifies three concerns that used to live apart (mirroring
 * Python's `config.py`):
 *
 * - **Root discovery** — {@link findAppRoot} walks upward looking for the
 *   `.ghagen.yml` marker. It is the *single* root locator used by both
 *   {@link loadOptions} and the header's `{source_file}` resolution.
 * - **YAML loading** — {@link loadYamlConfig} reads and validates a YAML
 *   mapping file.
 * - **Options** — {@link GhagenOptions} / {@link loadOptions} read the
 *   `options:` section of `.ghagen.yml`.
 */

import { existsSync, readFileSync, statSync } from "node:fs";
import { dirname, isAbsolute, resolve } from "node:path";
import { parse } from "yaml";
import { z } from "zod/v4";

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
  if (data === null || data === undefined) {
    return {};
  }
  if (typeof data !== "object" || Array.isArray(data)) {
    throw new Error(`${path}: expected a YAML mapping at top level`);
  }
  return data as Record<string, unknown>;
}

/**
 * Zod schema for `.ghagen.yml` configuration.
 *
 * Single source of truth for config shape, types, and defaults.
 */
export const optionsSchema = z.object({
  auto_dedent: z.boolean().default(true),
});

export const ghagenYmlSchema = z.object({
  options: optionsSchema.optional(),
  entrypoint: z.string().optional(),
});

export type GhagenYmlConfig = z.infer<typeof ghagenYmlSchema>;
export type GhagenOptions = z.infer<typeof optionsSchema>;

/**
 * Load project options from `.ghagen.yml` at the repo root.
 *
 * The config file is located via {@link findAppRoot} (an ancestor walk from
 * *start*), the same discovery used for the header's `{source_file}`
 * resolution. Falls back to defaults when the file is missing or has no
 * `options:` section.
 *
 * Only the `options` key is parsed -- a malformed `entrypoint:` value
 * elsewhere in the same file does not affect this function (that key is
 * validated separately by `cli/_common.ts`, mirroring Python's
 * `_extract_from_ghagen_yml`, which also only ever inspects `options`).
 */
export function loadOptions(start?: string): GhagenOptions {
  const root = findAppRoot(start);
  if (root !== null) {
    const data = loadYamlConfig(resolve(root, GHAGEN_YML_MARKER));
    const parsed = optionsSchema.optional().parse(data.options);
    if (parsed) {
      return parsed;
    }
  }

  return { auto_dedent: true };
}
