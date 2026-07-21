/** Shared CLI helpers used by the top-level command and sub-commands. */

import { existsSync, statSync } from "node:fs";
import { isAbsolute, resolve } from "node:path";
import { createJiti } from "jiti";
import type { App } from "../app.js";
import { CliError, resolveAppFromModule } from "../_load.js";
import { GHAGEN_YML_MARKER, findAppRoot, ghagenYmlSchema, loadYamlConfig } from "../config.js";

// Re-exported so existing `import { CliError } from "./_common.js"` sites
// (main.ts, deps.ts, tests) keep working; the class now lives in `_load.ts`
// alongside the shared `resolveAppFromModule` it is thrown from.
export { CliError } from "../_load.js";

const CONFIG_SEARCH_PATHS: readonly string[] = [
  ".github/ghagen.workflows.ts",
  ".github/ghagen.workflows.js",
  ".github/ghagen.workflows.mjs",
  "ghagen.workflows.ts",
  "ghagen.workflows.js",
  "ghagen.workflows.mjs",
  "ghagen.config.ts",
  "ghagen.config.js",
  "ghagen.config.mjs",
];

/**
 * Return the configured entrypoint path, or `null` if not set.
 *
 * Reads `.ghagen.yml` in *root* (an already-discovered project root, e.g.
 * from {@link findAppRoot}), extracts the top-level `entrypoint` key, and
 * resolves it relative to *root*. Returns `null` if the file or key is
 * absent. Throws {@link CliError} on malformed YAML, a wrong-type value, or
 * a resolved path that does not exist.
 */
function entrypointFromGhagenYml(root: string): string | null {
  const ghagenYml = resolve(root, GHAGEN_YML_MARKER);
  if (!existsSync(ghagenYml) || !statSync(ghagenYml).isFile()) {
    return null;
  }

  let data: Record<string, unknown>;
  try {
    data = loadYamlConfig(ghagenYml);
  } catch (err) {
    throw new CliError(`Error: ${(err as Error).message}`);
  }
  let config;
  try {
    config = ghagenYmlSchema.parse(data);
  } catch (err) {
    throw new CliError(`Error: ${ghagenYml}: ${(err as Error).message}`);
  }
  if (!config.entrypoint) {
    return null;
  }
  const dir = ghagenYml.replace(/[\\/][^\\/]+$/, "");
  const resolved = resolve(dir, config.entrypoint);
  if (!existsSync(resolved) || !statSync(resolved).isFile()) {
    throw new CliError(
      `Error: ${ghagenYml}: entrypoint '${config.entrypoint}' does not exist (resolved to ${resolved})`,
    );
  }
  return resolved;
}

/**
 * Locate the workflow config file.
 *
 * Search order:
 *   1. `--config` CLI flag
 *   2. `entrypoint` key in `.ghagen.yml`
 *   3. Conventional filenames in `.github/` then the cwd
 */
export function findConfig(cliFlag?: string, cwd: string = process.cwd()): string {
  if (cliFlag) {
    const path = isAbsolute(cliFlag) ? cliFlag : resolve(cwd, cliFlag);
    if (!existsSync(path) || !statSync(path).isFile()) {
      throw new CliError(`Error: config file not found: ${path}`);
    }
    return path;
  }

  const root = findAppRoot(cwd);
  if (root !== null) {
    const fromYml = entrypointFromGhagenYml(root);
    if (fromYml !== null) {
      return fromYml;
    }

    for (const candidate of CONFIG_SEARCH_PATHS) {
      const path = resolve(root, candidate);
      if (existsSync(path) && statSync(path).isFile()) {
        return path;
      }
    }
  } else {
    for (const candidate of CONFIG_SEARCH_PATHS) {
      const path = resolve(cwd, candidate);
      if (existsSync(path) && statSync(path).isFile()) {
        return path;
      }
    }
  }

  throw new CliError(
    "Error: no config file found. Searched:\n" +
      CONFIG_SEARCH_PATHS.map((p) => `  - ${p}`).join("\n") +
      `\n  - ${GHAGEN_YML_MARKER} (top-level 'entrypoint' key)\n` +
      "\nUse --config to specify a path, set 'entrypoint' in " +
      `${GHAGEN_YML_MARKER}, or run \`ghagen init\` to create one.`,
  );
}

/**
 * Load the user's {@link App} from the resolved config file.
 *
 * Uses `jiti` for on-the-fly TypeScript/ESM transpilation so the CLI
 * can import `.ts` config files without a separate build step.
 *
 * @param configPath - Absolute path to the workflow config file.
 * @returns The {@link App} instance exported by the config module.
 * @throws {@link CliError} if the module cannot be loaded or does not export an `App`.
 */
export async function loadApp(configPath: string): Promise<App> {
  const jiti = createJiti(import.meta.url, { moduleCache: false });
  let mod: unknown;
  try {
    mod = await jiti.import(configPath);
  } catch (err) {
    throw new CliError(`Error: failed to load ${configPath}: ${(err as Error).message}`);
  }
  return resolveAppFromModule(mod, configPath);
}
