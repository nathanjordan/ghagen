/** Shared CLI helpers used by the top-level command and sub-commands. */

import { existsSync, statSync } from "node:fs";
import { isAbsolute, resolve } from "node:path";
import { createJiti } from "jiti";
import { App } from "../app.js";
import { loadToml } from "../_toml.js";

const GHAGEN_TOML_PATH = ".github/ghagen.toml";

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
 * Error type thrown by CLI commands to signal a non-zero exit code.
 *
 * When caught by the top-level CLI runner, `exitCode` is forwarded to
 * `process.exit()` and `message` (if non-empty) is written to stderr.
 */
export class CliError extends Error {
  /** Process exit code returned when this error propagates to the CLI entry point. */
  readonly exitCode: number;
  /**
   * @param message - Human-readable error text written to stderr (pass `""` for silent exits).
   * @param exitCode - Process exit code (default `1`).
   */
  constructor(message: string, exitCode = 1) {
    super(message);
    this.name = "CliError";
    this.exitCode = exitCode;
  }
}

function entrypointFromGhagenToml(cwd: string): string | null {
  const ghagenToml = resolve(cwd, GHAGEN_TOML_PATH);
  if (!existsSync(ghagenToml) || !statSync(ghagenToml).isFile()) return null;

  let data: Record<string, unknown>;
  try {
    data = loadToml(ghagenToml);
  } catch (err) {
    throw new CliError(`Error: ${(err as Error).message}`);
  }
  const raw = data["entrypoint"];
  if (raw === undefined || raw === null) return null;
  if (typeof raw !== "string") {
    throw new CliError(
      `Error: ${ghagenToml}: 'entrypoint' must be a string, got ${typeof raw}`,
    );
  }
  const dir = ghagenToml.replace(/[\\/][^\\/]+$/, "");
  const resolved = resolve(dir, raw);
  if (!existsSync(resolved) || !statSync(resolved).isFile()) {
    throw new CliError(
      `Error: ${ghagenToml}: entrypoint '${raw}' does not exist (resolved to ${resolved})`,
    );
  }
  return resolved;
}

/**
 * Locate the workflow config file.
 *
 * Search order:
 *   1. `--config` CLI flag
 *   2. `entrypoint =` key in `.github/ghagen.toml`
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

  const fromToml = entrypointFromGhagenToml(cwd);
  if (fromToml !== null) return fromToml;

  for (const candidate of CONFIG_SEARCH_PATHS) {
    const path = resolve(cwd, candidate);
    if (existsSync(path) && statSync(path).isFile()) return path;
  }

  throw new CliError(
    "Error: no config file found. Searched:\n" +
      CONFIG_SEARCH_PATHS.map((p) => `  - ${p}`).join("\n") +
      `\n  - ${GHAGEN_TOML_PATH} (top-level 'entrypoint' key)\n` +
      "\nUse --config to specify a path, set 'entrypoint' in " +
      `${GHAGEN_TOML_PATH}, or run \`ghagen init\` to create one.`,
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
    throw new CliError(
      `Error: failed to load ${configPath}: ${(err as Error).message}`,
    );
  }
  return resolveAppFromModule(mod, configPath);
}

/**
 * Extract an `App` from an imported module. Looks for `createApp()`
 * first (allows async setup), then `app`. Used by both `loadApp()`
 * and the pin/sources tracker so behaviour stays consistent.
 */
export async function resolveAppFromModule(
  mod: unknown,
  configPath: string,
): Promise<App> {
  // ESM default-export handling: if the module has a `default` and
  // that has the expected fields, prefer it.
  const candidates = [mod];
  if (mod && typeof mod === "object" && "default" in mod) {
    candidates.unshift((mod as { default: unknown }).default);
  }

  for (const candidate of candidates) {
    if (!candidate || typeof candidate !== "object") continue;
    const obj = candidate as { app?: unknown; createApp?: unknown };
    if (typeof obj.createApp === "function") {
      const result = await (obj.createApp as () => App | Promise<App>)();
      if (!(result instanceof App)) {
        throw new CliError(
          `Error: createApp() in ${configPath} must return an App instance`,
        );
      }
      return result;
    }
    if (obj.app !== undefined) {
      if (!(obj.app instanceof App)) {
        throw new CliError(
          `Error: 'app' in ${configPath} must be an App instance`,
        );
      }
      return obj.app;
    }
  }

  throw new CliError(
    `Error: ${configPath} must export 'app = new App(...)' or 'createApp(): App'`,
  );
}
