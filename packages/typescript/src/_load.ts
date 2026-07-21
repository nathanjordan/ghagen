/**
 * Config-loading primitives shared by the CLI and the deps-upgrade tracker.
 *
 * `resolveAppFromModule` is the single module -> {@link App} resolution
 * policy used by both `cli/_common.ts` (`loadApp`) and `pin/sources.ts`
 * (`trackUserFiles`). It lives at the package root rather than in `cli/`
 * because `cli/` already depends on `pin/` (`cli/deps.ts` imports
 * `pin/index.js`); a neutral module keeps that dependency acyclic instead
 * of forcing `pin/` to import from `cli/`. `CliError` lives here too so the
 * resolver can signal load failures without either side reaching across the
 * layer boundary.
 */

import { App } from "./app.js";

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

/**
 * Extract an {@link App} from an imported config module. Looks for
 * `createApp()` first (allows async setup), then `app`, unwrapping an ESM
 * `default` export first. Used by both the CLI's `loadApp()` and the
 * deps-upgrade `trackUserFiles()` so resolution behaviour stays consistent.
 *
 * @throws {@link CliError} if no usable `app`/`createApp` export is present
 *   or the resolved value is not an {@link App} instance.
 */
export async function resolveAppFromModule(mod: unknown, configPath: string): Promise<App> {
  // ESM default-export handling: if the module has a `default` and
  // that has the expected fields, prefer it.
  const candidates = [mod];
  if (mod && typeof mod === "object" && "default" in mod) {
    candidates.unshift((mod as { default: unknown }).default);
  }

  for (const candidate of candidates) {
    if (!candidate || typeof candidate !== "object") {
      continue;
    }
    const obj = candidate as { app?: unknown; createApp?: unknown };
    if (typeof obj.createApp === "function") {
      const result = await (obj.createApp as () => App | Promise<App>)();
      if (!(result instanceof App)) {
        throw new CliError(`Error: createApp() in ${configPath} must return an App instance`);
      }
      return result;
    }
    if (obj.app !== undefined) {
      if (!(obj.app instanceof App)) {
        throw new CliError(`Error: 'app' in ${configPath} must be an App instance`);
      }
      return obj.app;
    }
  }

  throw new CliError(`Error: ${configPath} must export 'app = new App(...)' or 'createApp(): App'`);
}
