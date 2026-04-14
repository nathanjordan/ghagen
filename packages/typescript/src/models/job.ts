import type { NormalJob as SchemaJob, Concurrency as SchemaConcurrency, Environment as SchemaEnvironment } from "../generated/workflow-types.js";
import type {
  JobModel, StepModel, PermissionsModel, ContainerModel, ServiceModel,
  StrategyModel, MatrixModel, ConcurrencyModel, DefaultsModel, EnvironmentModel,
  WithMeta, Raw, Model,
} from "./_base.js";
import { createModel, extractMeta, mapFields, isModel } from "./_base.js";
import {
  JOB_KEY_ORDER, STRATEGY_KEY_ORDER, MATRIX_KEY_ORDER,
  CONCURRENCY_KEY_ORDER, DEFAULTS_KEY_ORDER, ENVIRONMENT_KEY_ORDER,
} from "../emitter/key-order.js";
import type { PermissionsInput } from "./permissions.js";
import { permissions } from "./permissions.js";
import type { ContainerInput } from "./container.js";
import { container, service } from "./container.js";

// ---- Strategy / Matrix ----

export interface MatrixInput {
  include?: Array<Record<string, unknown>>;
  exclude?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

export function matrix(input: WithMeta<MatrixInput>): MatrixModel {
  const [data, meta] = extractMeta(input);
  return createModel("matrix", data as Record<string, unknown>, meta, MATRIX_KEY_ORDER) as MatrixModel;
}

export interface StrategyInput {
  matrix_?: MatrixModel | MatrixInput;
  failFast?: boolean;
  maxParallel?: number;
}

const STRATEGY_FIELD_MAP = {
  matrix_: "matrix",
  failFast: "fail-fast",
  maxParallel: "max-parallel",
} as const;

export function strategy(input: WithMeta<StrategyInput>): StrategyModel {
  const [rawData, meta] = extractMeta(input);
  const data = rawData as StrategyInput;
  const normalized: Record<string, unknown> = {};
  if (data.matrix_ !== undefined) {
    normalized["matrix"] = isModel(data.matrix_) ? data.matrix_ : matrix(data.matrix_ as MatrixInput);
  }
  if (data.failFast !== undefined) normalized["fail-fast"] = data.failFast;
  if (data.maxParallel !== undefined) normalized["max-parallel"] = data.maxParallel;
  return createModel("strategy", normalized, meta, STRATEGY_KEY_ORDER) as StrategyModel;
}

// ---- Concurrency ----

export interface ConcurrencyInput {
  group: string;
  cancelInProgress?: boolean;
}

const CONCURRENCY_FIELD_MAP = {
  group: "group",
  cancelInProgress: "cancel-in-progress",
} as const satisfies Record<keyof ConcurrencyInput, keyof SchemaConcurrency>;

export function concurrency(input: WithMeta<ConcurrencyInput>): ConcurrencyModel {
  const [data, meta] = extractMeta(input);
  const yamlData = mapFields(data as Record<string, unknown>, CONCURRENCY_FIELD_MAP);
  return createModel("concurrency", yamlData, meta, CONCURRENCY_KEY_ORDER) as ConcurrencyModel;
}

// ---- Defaults ----

export interface DefaultsRunInput {
  shell?: string;
  workingDirectory?: string;
}

export interface DefaultsInput {
  run?: DefaultsRunInput;
}

export function defaults(input: WithMeta<DefaultsInput>): DefaultsModel {
  const [rawData, meta] = extractMeta(input);
  const data = rawData as DefaultsInput;
  const yamlData: Record<string, unknown> = {};
  if (data.run) {
    const runData: Record<string, unknown> = {};
    if (data.run.shell !== undefined) runData["shell"] = data.run.shell;
    if (data.run.workingDirectory !== undefined) runData["working-directory"] = data.run.workingDirectory;
    yamlData["run"] = runData;
  }
  return createModel("defaults", yamlData, meta, DEFAULTS_KEY_ORDER) as DefaultsModel;
}

// ---- Environment ----

export interface EnvironmentInput {
  name: string;
  url?: string;
}

const ENVIRONMENT_FIELD_MAP = {
  name: "name",
  url: "url",
} as const satisfies Record<keyof EnvironmentInput, keyof SchemaEnvironment>;

export function environment(input: WithMeta<EnvironmentInput>): EnvironmentModel {
  const [data, meta] = extractMeta(input);
  const yamlData = mapFields(data as Record<string, unknown>, ENVIRONMENT_FIELD_MAP);
  return createModel("environment", yamlData, meta, ENVIRONMENT_KEY_ORDER) as EnvironmentModel;
}

// ---- Job output ----

export interface JobOutputInput {
  description?: string;
  value: string;
}

// ---- Job ----

export interface JobInput {
  name?: string;
  runsOn?: string | string[] | Raw<string>;
  needs?: string | string[];
  if_?: string;
  permissions?: PermissionsModel | PermissionsInput | "read-all" | "write-all" | Raw<string>;
  environment?: string | EnvironmentModel | EnvironmentInput;
  strategy?: StrategyModel | StrategyInput;
  env?: Record<string, string>;
  defaults?: DefaultsModel | DefaultsInput;
  steps?: StepModel[];
  outputs?: Record<string, string>;
  timeoutMinutes?: number;
  continueOnError?: boolean | string;
  concurrency?: string | ConcurrencyModel | ConcurrencyInput;
  services?: Record<string, ServiceModel | ContainerInput | string>;
  container?: ContainerModel | ContainerInput | string;
  // Reusable workflow job fields
  uses?: string;
  with_?: Record<string, unknown>;
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
