import type {
  Concurrency as SchemaConcurrency,
  Environment as SchemaEnvironment,
} from "../generated/workflow-types.js";
import type {
  JobModel,
  StepModel,
  PermissionsModel,
  ContainerModel,
  ServiceModel,
  StrategyModel,
  MatrixModel,
  ConcurrencyModel,
  DefaultsModel,
  EnvironmentModel,
  WithMeta,
  Raw,
} from "./_base.js";
import { createModel, extractMeta, mapFields, isModel } from "./_base.js";
import {
  JOB_KEY_ORDER,
  STRATEGY_KEY_ORDER,
  MATRIX_KEY_ORDER,
  CONCURRENCY_KEY_ORDER,
  DEFAULTS_KEY_ORDER,
  ENVIRONMENT_KEY_ORDER,
} from "../emitter/key-order.js";
import type { PermissionsInput } from "./permissions.js";
import { permissions } from "./permissions.js";
import type { ContainerInput } from "./container.js";
import { container, service } from "./container.js";

// ---- Strategy / Matrix ----

/**
 * Input for strategy matrix configuration. Dynamic dimensions (user-defined
 * keys like `"os"` or `"node-version"`) are set as additional properties on
 * this object. Use `include` and `exclude` to add or remove specific
 * combinations.
 *
 * In Python, dynamic dimensions are passed via the `extras` parameter.
 * In TypeScript, they are set directly as index-signature properties.
 */
export interface MatrixInput {
  /** Additional matrix combinations to include. */
  include?: Array<Record<string, unknown>>;
  /** Matrix combinations to exclude. */
  exclude?: Array<Record<string, unknown>>;
  /** Dynamic matrix dimensions (e.g., `{ "node-version": ["18", "20"] }`). */
  [key: string]: unknown;
}

/**
 * Create a matrix model for strategy configuration.
 *
 * @param input - Matrix dimensions, include/exclude lists, and optional model metadata.
 * @returns A `MatrixModel` for use inside a `StrategyInput`.
 *
 * @example
 * ```ts
 * matrix({
 *   "node-version": ["18", "20"],
 *   os: ["ubuntu-latest", "macos-latest"],
 *   include: [{ os: "ubuntu-latest", experimental: true }],
 * })
 * ```
 */
export function matrix(input: WithMeta<MatrixInput>): MatrixModel {
  const [data, meta] = extractMeta(input);
  return createModel(
    "matrix",
    data as Record<string, unknown>,
    meta,
    MATRIX_KEY_ORDER,
  ) as MatrixModel;
}

/**
 * Input for job strategy configuration including matrix builds, fail-fast
 * behavior, and parallelism limits.
 */
export interface StrategyInput {
  /** Matrix configuration. Accepts a pre-built `MatrixModel` or an inline `MatrixInput`. The trailing `_` avoids the reserved word; it is stripped during emission. */
  matrix_?: MatrixModel | MatrixInput;
  /** Whether to cancel all in-progress jobs if any matrix job fails. Serialized as `fail-fast`. */
  failFast?: boolean;
  /** Maximum number of matrix jobs to run in parallel. Serialized as `max-parallel`. */
  maxParallel?: number;
}

/**
 * Create a strategy model for controlling matrix builds.
 *
 * @param input - Strategy properties and optional model metadata.
 * @returns A `StrategyModel` for use in a `JobInput`.
 *
 * @example
 * ```ts
 * strategy({
 *   matrix_: {
 *     "node-version": ["18", "20"],
 *     os: ["ubuntu-latest", "macos-latest"],
 *   },
 *   failFast: false,
 * })
 * ```
 */
export function strategy(input: WithMeta<StrategyInput>): StrategyModel {
  const [rawData, meta] = extractMeta(input);
  const data = rawData as StrategyInput;
  const normalized: Record<string, unknown> = {};
  if (data.matrix_ !== undefined) {
    normalized["matrix"] = isModel(data.matrix_)
      ? data.matrix_
      : matrix(data.matrix_ as MatrixInput);
  }
  if (data.failFast !== undefined) normalized["fail-fast"] = data.failFast;
  if (data.maxParallel !== undefined) normalized["max-parallel"] = data.maxParallel;
  return createModel("strategy", normalized, meta, STRATEGY_KEY_ORDER) as StrategyModel;
}

// ---- Concurrency ----

/**
 * Input for concurrency configuration. Prevents concurrent runs in the
 * same group. Can be used at the workflow or job level.
 */
export interface ConcurrencyInput {
  /** Concurrency group name. Supports GitHub Actions expressions. */
  group: string;
  /** Whether to cancel in-progress runs when a new run is queued. Serialized as `cancel-in-progress`. */
  cancelInProgress?: boolean;
}

const CONCURRENCY_FIELD_MAP = {
  group: "group",
  cancelInProgress: "cancel-in-progress",
} as const satisfies Record<keyof ConcurrencyInput, keyof SchemaConcurrency>;

/**
 * Create a concurrency model that prevents concurrent runs in the same group.
 *
 * @param input - Concurrency properties and optional model metadata.
 * @returns A `ConcurrencyModel` for use in a workflow or job.
 *
 * @example
 * ```ts
 * concurrency({
 *   group: "deploy-${{ github.ref }}",
 *   cancelInProgress: true,
 * })
 * ```
 */
export function concurrency(input: WithMeta<ConcurrencyInput>): ConcurrencyModel {
  const [data, meta] = extractMeta(input);
  const yamlData = mapFields(data as Record<string, unknown>, CONCURRENCY_FIELD_MAP);
  return createModel("concurrency", yamlData, meta, CONCURRENCY_KEY_ORDER) as ConcurrencyModel;
}

// ---- Defaults ----

/**
 * Input for default shell and working directory settings for `run` steps.
 */
export interface DefaultsRunInput {
  /** Default shell for run steps (e.g., `"bash"`, `"pwsh"`). */
  shell?: string;
  /** Default working directory. Serialized as `working-directory`. */
  workingDirectory?: string;
}

/**
 * Input for default settings applied to all `run` steps in a job or workflow.
 */
export interface DefaultsInput {
  /** Default run step settings. */
  run?: DefaultsRunInput;
}

/**
 * Create a defaults model for setting default shell and working directory
 * for all `run` steps.
 *
 * @param input - Default run settings and optional model metadata.
 * @returns A `DefaultsModel` for use in a workflow or job.
 *
 * @example
 * ```ts
 * defaults({
 *   run: { shell: "bash", workingDirectory: "./src" },
 * })
 * ```
 */
export function defaults(input: WithMeta<DefaultsInput>): DefaultsModel {
  const [rawData, meta] = extractMeta(input);
  const data = rawData as DefaultsInput;
  const yamlData: Record<string, unknown> = {};
  if (data.run) {
    const runData: Record<string, unknown> = {};
    if (data.run.shell !== undefined) runData["shell"] = data.run.shell;
    if (data.run.workingDirectory !== undefined)
      runData["working-directory"] = data.run.workingDirectory;
    yamlData["run"] = runData;
  }
  return createModel("defaults", yamlData, meta, DEFAULTS_KEY_ORDER) as DefaultsModel;
}

// ---- Environment ----

/**
 * Input for job deployment environment configuration.
 */
export interface EnvironmentInput {
  /** The environment name. */
  name: string;
  /** The environment URL. */
  url?: string;
}

const ENVIRONMENT_FIELD_MAP = {
  name: "name",
  url: "url",
} as const satisfies Record<keyof EnvironmentInput, keyof SchemaEnvironment>;

/**
 * Create an environment model for deployment environment configuration.
 *
 * @param input - Environment properties and optional model metadata.
 * @returns An `EnvironmentModel` for use in a `JobInput`.
 *
 * @example
 * ```ts
 * environment({ name: "production", url: "https://example.com" })
 * ```
 */
export function environment(input: WithMeta<EnvironmentInput>): EnvironmentModel {
  const [data, meta] = extractMeta(input);
  const yamlData = mapFields(data as Record<string, unknown>, ENVIRONMENT_FIELD_MAP);
  return createModel("environment", yamlData, meta, ENVIRONMENT_KEY_ORDER) as EnvironmentModel;
}

// ---- Job output ----

/**
 * Input for a job output definition, used when a downstream job needs to
 * consume this job's outputs.
 */
export interface JobOutputInput {
  /** Description of the output. */
  description?: string;
  /** The output value, typically a step output expression (e.g., `"${{ steps.build.outputs.url }}"`). */
  value: string;
}

// ---- Job ----

/**
 * Input for defining a single job within a GitHub Actions workflow. A job
 * can either run steps directly or call a reusable workflow via `uses`.
 */
export interface JobInput {
  /** Display name for the job. */
  name?: string;
  /** Runner label(s) for this job (e.g., `"ubuntu-latest"`). Serialized as `runs-on`. Use `Raw<string>` via `raw()` for expression values. */
  runsOn?: string | string[] | Raw<string>;
  /** Job ID(s) that must complete before this job runs. */
  needs?: string | string[];
  /** Conditional expression that must evaluate to true for this job to run. Serialized as `if`. The trailing `_` avoids the reserved word; it is stripped during emission. */
  if_?: string;
  /** Token permissions for this job. Accepts a `PermissionsModel`, an inline `PermissionsInput`, a string shorthand, or a `Raw<string>`. */
  permissions?: PermissionsModel | PermissionsInput | "read-all" | "write-all" | Raw<string>;
  /** Deployment environment. Can be a string (name only), an `EnvironmentModel`, or an inline `EnvironmentInput`. */
  environment?: string | EnvironmentModel | EnvironmentInput;
  /** Matrix strategy configuration. Accepts a `StrategyModel` or an inline `StrategyInput`. */
  strategy?: StrategyModel | StrategyInput;
  /** Environment variables for all steps in this job. */
  env?: Record<string, string>;
  /** Default settings for `run` steps. Accepts a `DefaultsModel` or an inline `DefaultsInput`. */
  defaults?: DefaultsModel | DefaultsInput;
  /** Steps to run in this job. */
  steps?: StepModel[];
  /** Job outputs, accessible by downstream jobs. Values are typically step output expressions. */
  outputs?: Record<string, string>;
  /** Maximum minutes the job can run before being cancelled. Serialized as `timeout-minutes`. */
  timeoutMinutes?: number;
  /** Allow the workflow to continue when this job fails. Serialized as `continue-on-error`. */
  continueOnError?: boolean | string;
  /** Concurrency group for this job. Can be a string (group name), a `ConcurrencyModel`, or an inline `ConcurrencyInput`. */
  concurrency?: string | ConcurrencyModel | ConcurrencyInput;
  /** Service containers for the job. Values can be `ServiceModel` objects, `ContainerInput` objects, or image strings. */
  services?: Record<string, ServiceModel | ContainerInput | string>;
  /** Container to run the job in. Can be a `ContainerModel`, a `ContainerInput`, or an image string. */
  container?: ContainerModel | ContainerInput | string;
  // Reusable workflow job fields
  /** Reusable workflow reference (e.g., `"org/repo/.github/workflows/ci.yml@main"`). Mutually exclusive with `steps`. */
  uses?: string;
  /** Input parameters for the reusable workflow. Serialized as `with`. The trailing `_` avoids the reserved word; it is stripped during emission. */
  with_?: Record<string, unknown>;
  /** Secrets to pass to the reusable workflow. Can be a dict or `"inherit"`. */
  secrets?: Record<string, string> | "inherit";
}

const JOB_FIELD_MAP = {
  name: "name",
  runsOn: "runs-on",
  needs: "needs",
  if_: "if",
  permissions: "permissions",
  environment: "environment",
  strategy: "strategy",
  env: "env",
  defaults: "defaults",
  steps: "steps",
  outputs: "outputs",
  timeoutMinutes: "timeout-minutes",
  continueOnError: "continue-on-error",
  concurrency: "concurrency",
  services: "services",
  container: "container",
  uses: "uses",
  with_: "with",
  secrets: "secrets",
} as const;

/**
 * Create a job model for use in a workflow's `jobs` map. Plain-object values
 * for `permissions`, `environment`, `strategy`, `defaults`, `concurrency`,
 * `container`, and `services` entries are automatically wrapped with their
 * respective factory functions.
 *
 * @param input - Job properties and optional model metadata.
 * @returns A `JobModel` for use in a `WorkflowInput.jobs` map.
 *
 * @example
 * ```ts
 * job({
 *   name: "Test",
 *   runsOn: "ubuntu-latest",
 *   steps: [
 *     step({ uses: "actions/checkout@v4" }),
 *     step({ name: "Run tests", run: "npm test" }),
 *   ],
 * })
 * ```
 */
export function job(input: WithMeta<JobInput>): JobModel {
  const [data, meta] = extractMeta(input);
  const yamlData: Record<string, unknown> = {};

  // Map simple fields
  for (const [camelKey, yamlKey] of Object.entries(JOB_FIELD_MAP)) {
    const value = (data as Record<string, unknown>)[camelKey];
    if (value === undefined) continue;

    // Auto-wrap plain objects with appropriate factory
    if (camelKey === "permissions" && typeof value === "object" && !isModel(value)) {
      yamlData[yamlKey] = permissions(value as PermissionsInput);
    } else if (camelKey === "environment" && typeof value === "object" && !isModel(value)) {
      yamlData[yamlKey] = environment(value as EnvironmentInput);
    } else if (camelKey === "strategy" && typeof value === "object" && !isModel(value)) {
      yamlData[yamlKey] = strategy(value as StrategyInput);
    } else if (camelKey === "defaults" && typeof value === "object" && !isModel(value)) {
      yamlData[yamlKey] = defaults(value as DefaultsInput);
    } else if (camelKey === "concurrency" && typeof value === "object" && !isModel(value)) {
      yamlData[yamlKey] = concurrency(value as ConcurrencyInput);
    } else if (camelKey === "container" && typeof value === "object" && !isModel(value)) {
      yamlData[yamlKey] = container(value as ContainerInput);
    } else if (camelKey === "services" && typeof value === "object" && !isModel(value)) {
      const services: Record<string, unknown> = {};
      for (const [name, svc] of Object.entries(value as Record<string, unknown>)) {
        if (typeof svc === "string") {
          services[name] = svc;
        } else if (isModel(svc)) {
          services[name] = svc;
        } else {
          services[name] = service(svc as ContainerInput);
        }
      }
      yamlData[yamlKey] = services;
    } else {
      yamlData[yamlKey] = value;
    }
  }

  return createModel("job", yamlData, meta, JOB_KEY_ORDER) as JobModel;
}
