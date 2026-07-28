/**
 * Project configuration: the single owner of `.ghagen.yml`.
 *
 * This module discovers the project root, parses `.ghagen.yml` **once**, and
 * returns a typed {@link ProjectConfig} whose error modes are *values*
 * ({@link ConfigError}), never thrown framework exceptions. Callers pick which
 * errors bind: the CLI renders every error and exits; the header's
 * `{source_file}` path ({@link loadOptions}) keeps only option errors so a
 * malformed `entrypoint:` cannot break it.
 *
 * What lives behind this seam:
 *
 * - **Root discovery** — {@link findAppRoot} walks upward for the
 *   `.ghagen.yml` marker. The *single* root locator, used here and by the
 *   header's `{source_file}` resolution.
 * - **Single parse + validation** — {@link loadProjectConfig} reads the file
 *   once and derives both options and the workflow entrypoint from it.
 * - **Entrypoint resolution** — the `entrypoint:` key, falling back to
 *   {@link CONFIG_SEARCH_PATHS} against a single anchor.
 * - **Module → App resolution** — {@link resolveApp}, the policy shared by the
 *   CLI's `loadApp` and pin's `trackUserFiles` (folded in from the former
 *   `_load.ts`).
 */

import { existsSync, readFileSync, statSync } from "node:fs";
import { dirname, isAbsolute, resolve } from "node:path";
import { parse } from "yaml";
import { App } from "./app.js";

/** Canonical marker file: its presence identifies the ghagen project root. */
export const GHAGEN_YML_MARKER = ".ghagen.yml";

/** Default pin-lockfile path, relative to `App.root`. The single home for this literal. */
export const DEFAULT_LOCKFILE_PATH = ".ghagen.lock.yml";

/**
 * Conventional workflow-config filenames, probed (in order) against the project
 * root — or the cwd when no `.ghagen.yml` marker exists.
 */
export const CONFIG_SEARCH_PATHS: readonly string[] = [
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

/** Project options loaded from the `options:` section of `.ghagen.yml`. */
export interface GhagenOptions {
  /** Dedent each Step's `run` script at emit time. The single default `true` lives here. */
  readonly auto_dedent: boolean;
}

/** Discriminator for {@link ConfigError}. */
export type ConfigErrorKind =
  | "parse"
  | "not-a-mapping"
  | "bad-entrypoint-type"
  | "entrypoint-missing"
  | "bad-option-type"
  | "app-resolution";

/**
 * A `.ghagen.yml` (or entrypoint-module) problem, surfaced as a value. Callers
 * decide which kinds are fatal.
 */
export interface ConfigError {
  readonly kind: ConfigErrorKind;
  /** The `.ghagen.yml` (or resolved entrypoint) the error concerns. */
  readonly path: string;
  /** Human-readable text; renderers prepend `Error: `. */
  readonly message: string;
}

/** The result of a single `.ghagen.yml` discovery + parse + validation. */
export interface ProjectConfig {
  /** Directory containing `.ghagen.yml`, or `null` when no marker was found. */
  readonly root: string | null;
  /** Resolved workflow entrypoint, or `null` when none could be resolved. */
  readonly configPath: string | null;
  /** Always fully populated (defaults applied). */
  readonly options: GhagenOptions;
  /** The raw `entrypoint` string from the file, or `null`. */
  readonly entrypoint: string | null;
  /** Empty on success. */
  readonly errors: readonly ConfigError[];
}

/**
 * Walk upward from *start* looking for `.ghagen.yml`.
 *
 * Returns the directory containing `.ghagen.yml` if found, else `null`. When
 * *start* is omitted, walks from `process.cwd()`. When *start* refers to a
 * file, the search begins at the file's parent directory.
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

/** Read and parse a YAML config file. Throws on read/parse errors. */
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

/** The `.ghagen.yml` mapping, or a `parse`/`not-a-mapping` {@link ConfigError}. */
interface ReadResult {
  readonly data: Record<string, unknown> | null;
  readonly error: ConfigError | null;
}

/**
 * Parse `.ghagen.yml` at *path* once, classifying user-input failures as
 * values. `readFileSync` I/O faults (an unreadable file the OS refuses) still
 * throw — those are not config errors.
 */
function readGhagenYml(path: string): ReadResult {
  const text = readFileSync(path, "utf8");
  let raw: unknown;
  try {
    raw = parse(text);
  } catch (err) {
    return {
      data: null,
      error: {
        kind: "parse",
        path,
        message: `${path}: failed to parse YAML: ${(err as Error).message}`,
      },
    };
  }
  if (raw === null || raw === undefined) {
    return { data: {}, error: null };
  }
  if (typeof raw !== "object" || Array.isArray(raw)) {
    return {
      data: null,
      error: {
        kind: "not-a-mapping",
        path,
        message: `${path}: expected a YAML mapping at top level`,
      },
    };
  }
  return { data: raw as Record<string, unknown>, error: null };
}

/** Validate the `options:` section into a fully-populated {@link GhagenOptions}. */
function readOptions(
  data: Record<string, unknown>,
  path: string,
): { options: GhagenOptions; error: ConfigError | null } {
  const raw = data["options"];
  if (raw === undefined || raw === null) {
    return { options: { auto_dedent: true }, error: null };
  }
  if (typeof raw !== "object" || Array.isArray(raw)) {
    return {
      options: { auto_dedent: true },
      error: { kind: "bad-option-type", path, message: `${path}: [options] must be a table` },
    };
  }
  const autoDedent = (raw as Record<string, unknown>)["auto_dedent"];
  if (autoDedent === undefined) {
    return { options: { auto_dedent: true }, error: null };
  }
  if (typeof autoDedent !== "boolean") {
    return {
      options: { auto_dedent: true },
      error: {
        kind: "bad-option-type",
        path,
        message: `${path}: [options].auto_dedent must be a boolean, got ${typeof autoDedent}`,
      },
    };
  }
  return { options: { auto_dedent: autoDedent }, error: null };
}

/**
 * Discover the project root, parse `.ghagen.yml` **once**, resolve the workflow
 * entrypoint (the `entrypoint` key, else {@link CONFIG_SEARCH_PATHS}), and read
 * options. Never throws for user-input problems: they are returned in `errors`.
 * `cliConfigFlag` short-circuits discovery when the user passed `--config`.
 */
export function loadProjectConfig(start?: string, cliConfigFlag?: string): ProjectConfig {
  const cwd = start ?? process.cwd();
  const root = findAppRoot(cwd);
  const errors: ConfigError[] = [];
  let options: GhagenOptions = { auto_dedent: true };
  let entrypoint: string | null = null;
  let entrypointValid = false;

  // Single read of the marker file: both options and the entrypoint key come
  // from this one parse.
  if (root !== null) {
    const ghagenYml = resolve(root, GHAGEN_YML_MARKER);
    const { data, error: readErr } = readGhagenYml(ghagenYml);
    if (readErr) {
      errors.push(readErr);
    }
    if (data) {
      const { options: opts, error: optErr } = readOptions(data, ghagenYml);
      options = opts;
      if (optErr) {
        errors.push(optErr);
      }
      const rawEntry = data["entrypoint"];
      if (rawEntry !== undefined && rawEntry !== null) {
        if (typeof rawEntry !== "string") {
          errors.push({
            kind: "bad-entrypoint-type",
            path: ghagenYml,
            message: `${ghagenYml}: 'entrypoint' must be a string, got ${typeof rawEntry}`,
          });
        } else {
          entrypoint = rawEntry;
          entrypointValid = true;
        }
      }
    }
  }

  // `--config` short-circuits the search entirely.
  if (cliConfigFlag) {
    const flagPath = isAbsolute(cliConfigFlag) ? cliConfigFlag : resolve(cwd, cliConfigFlag);
    if (!existsSync(flagPath) || !statSync(flagPath).isFile()) {
      errors.push({
        kind: "entrypoint-missing",
        path: flagPath,
        message: `config file not found: ${flagPath}`,
      });
      return { root, configPath: null, options, entrypoint, errors };
    }
    return { root, configPath: flagPath, options, entrypoint, errors };
  }

  // Resolve the entrypoint key when present and valid.
  if (root !== null && entrypointValid && entrypoint !== null) {
    const resolved = resolve(root, entrypoint);
    if (!existsSync(resolved) || !statSync(resolved).isFile()) {
      errors.push({
        kind: "entrypoint-missing",
        path: resolve(root, GHAGEN_YML_MARKER),
        message: `${resolve(root, GHAGEN_YML_MARKER)}: entrypoint '${entrypoint}' does not exist (resolved to ${resolved})`,
      });
      return { root, configPath: null, options, entrypoint, errors };
    }
    return { root, configPath: resolved, options, entrypoint, errors };
  }

  // A bad entrypoint type is fatal to config resolution — do not fall through
  // to the search paths (the caller renders `errors`).
  if (errors.some((e) => e.kind === "bad-entrypoint-type")) {
    return { root, configPath: null, options, entrypoint, errors };
  }

  // The two former search loops collapse into one anchored probe: the only
  // thing that differed between them was the anchor.
  const anchor = root ?? cwd;
  for (const candidate of CONFIG_SEARCH_PATHS) {
    const path = resolve(anchor, candidate);
    if (existsSync(path) && statSync(path).isFile()) {
      return { root, configPath: path, options, entrypoint, errors };
    }
  }

  return { root, configPath: null, options, entrypoint, errors };
}

/**
 * Read only options for a given root — the header's `{source_file}` path, which
 * must never fail on a bad `entrypoint:`. Keeps only `bad-option-type` errors
 * (rethrown so a malformed `options:` is not silently ignored) and swallows
 * every other kind, so a malformed `entrypoint:` or YAML cannot break it.
 */
export function loadOptions(start?: string): GhagenOptions {
  const config = loadProjectConfig(start);
  const optionErr = config.errors.find((e) => e.kind === "bad-option-type");
  if (optionErr) {
    throw new Error(optionErr.message);
  }
  return config.options;
}

/** The outcome of {@link resolveApp}: exactly one of `app` / `error` is set. */
export type AppResolution =
  | { readonly app: App; readonly error: null }
  | {
      readonly app: null;
      readonly error: ConfigError;
    };

/**
 * Extract an {@link App} from an imported config module, as an error *value*.
 * Looks for `createApp()` first (allows async setup), then `app`, unwrapping an
 * ESM `default` export first. The single module → App policy shared by the
 * CLI's `loadApp()` and pin's `trackUserFiles()`.
 */
export async function resolveApp(mod: unknown, configPath: string): Promise<AppResolution> {
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
        return {
          app: null,
          error: {
            kind: "app-resolution",
            path: configPath,
            message: `createApp() in ${configPath} must return an App instance`,
          },
        };
      }
      return { app: result, error: null };
    }
    if (obj.app !== undefined) {
      if (!(obj.app instanceof App)) {
        return {
          app: null,
          error: {
            kind: "app-resolution",
            path: configPath,
            message: `'app' in ${configPath} must be an App instance`,
          },
        };
      }
      return { app: obj.app, error: null };
    }
  }

  return {
    app: null,
    error: {
      kind: "app-resolution",
      path: configPath,
      message: `${configPath} must export 'app = new App(...)' or 'createApp(): App'`,
    },
  };
}
