/** Shared CLI helpers used by the top-level command and sub-commands. */

import { createJiti } from "jiti";
import type { App } from "../app.js";
import {
  CONFIG_SEARCH_PATHS,
  GHAGEN_YML_MARKER,
  type ConfigError,
  type ProjectConfig,
  loadProjectConfig,
  resolveApp,
} from "../config.js";
import { CliError } from "./_errors.js";

/** Render the first {@link ConfigError} as a {@link CliError}, if any. */
function renderConfigError(error: ConfigError): never {
  throw new CliError(`Error: ${error.message}`);
}

/** The "no config file found" message — a CLI concern, not a {@link ConfigError}. */
function noConfigFoundMessage(): string {
  return (
    "Error: no config file found. Searched:\n" +
    CONFIG_SEARCH_PATHS.map((p) => `  - ${p}`).join("\n") +
    `\n  - ${GHAGEN_YML_MARKER} (top-level 'entrypoint' key)\n` +
    "\nUse --config to specify a path, set 'entrypoint' in " +
    `${GHAGEN_YML_MARKER}, or run \`ghagen init\` to create one.`
  );
}

/**
 * Resolve the project config for a CLI command: parse `.ghagen.yml` once,
 * render any error and exit, and require a resolved entrypoint.
 *
 * Search order (inside {@link loadProjectConfig}):
 *   1. `--config` CLI flag
 *   2. `entrypoint` key in `.ghagen.yml`
 *   3. Conventional filenames ({@link CONFIG_SEARCH_PATHS})
 */
export function resolveConfig(cliFlag?: string, cwd: string = process.cwd()): ProjectConfig {
  const config = loadProjectConfig(cwd, cliFlag);
  if (config.errors.length > 0) {
    renderConfigError(config.errors[0]!);
  }
  if (config.configPath === null) {
    throw new CliError(noConfigFoundMessage());
  }
  return config;
}

/**
 * Locate the workflow config file. Thin wrapper over {@link resolveConfig}
 * returning just the resolved entrypoint path.
 */
export function findConfig(cliFlag?: string, cwd: string = process.cwd()): string {
  return resolveConfig(cliFlag, cwd).configPath as string;
}

/**
 * Load the user's {@link App} from the resolved config file.
 *
 * Uses `jiti` for on-the-fly TypeScript/ESM transpilation so the CLI can import
 * `.ts` config files without a separate build step. The module → App policy
 * lives in `config.ts` ({@link resolveApp}); this renders its error value as a
 * {@link CliError}.
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
  const resolution = await resolveApp(mod, configPath);
  if (resolution.error) {
    renderConfigError(resolution.error);
  }
  return resolution.app;
}
