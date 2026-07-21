import type { YAMLMap } from "yaml";
import type { HttpsJsonSchemastoreOrgGithubWorkflowJson as SchemaWorkflow } from "../schema/workflow-types.generated.js";
import { buildModel, extractMeta } from "./_base.js";
import type {
  OnModel,
  PermissionsModel,
  ConcurrencyModel,
  DefaultsModel,
  JobModel,
  WithMeta,
  Raw,
  ModelSpec,
  WorkflowModel,
} from "./_base.js";
import type { OnInput } from "./trigger.js";
import { on } from "./trigger.js";
import type { PermissionsInput } from "./permissions.js";
import { permissions } from "./permissions.js";
import type { ConcurrencyInput } from "./job.js";
import { concurrency, defaults } from "./job.js";
import type { DefaultsInput } from "./job.js";

/**
 * Input for the top-level workflow model, representing a complete GitHub
 * Actions workflow YAML file. Contains the workflow name, triggers,
 * permissions, environment variables, defaults, concurrency settings,
 * and jobs.
 */
export interface WorkflowInput {
  /** The display name of the workflow. */
  name?: string;
  /** Custom name for workflow runs. Supports GitHub Actions expressions. Serialized as `run-name`. */
  runName?: string;
  /** Trigger configuration for the workflow. Accepts a pre-built `OnModel` or an inline `OnInput` object which will be auto-wrapped. */
  on?: OnModel | OnInput;
  /** Token permissions. Can be a `PermissionsModel`, an inline `PermissionsInput`, a string shorthand (`"read-all"` / `"write-all"`), or a `Raw<string>` for arbitrary values. */
  permissions?: PermissionsModel | PermissionsInput | "read-all" | "write-all" | Raw<string>;
  /** Environment variables available to all jobs in the workflow. */
  env?: Record<string, string>;
  /** Default settings for all `run` steps. Accepts a pre-built `DefaultsModel` or an inline `DefaultsInput`. */
  defaults?: DefaultsModel | DefaultsInput;
  /** Concurrency group configuration. Can be a string (group name), a `ConcurrencyModel`, or an inline `ConcurrencyInput`. */
  concurrency?: string | ConcurrencyModel | ConcurrencyInput;
  /** Map of job IDs to job definitions. At least one job is required. Values can be `JobModel` objects or raw `YAMLMap` nodes for passthrough. */
  jobs: Record<string, JobModel | YAMLMap>;
}

/** Serialization spec for {@link WorkflowModel}. */
export const WORKFLOW_SPEC: ModelSpec = {
  kind: "workflow",
  fieldMap: {
    name: "name",
    runName: "run-name",
    on: "on",
    permissions: "permissions",
    env: "env",
    defaults: "defaults",
    concurrency: "concurrency",
    jobs: "jobs",
  } satisfies Record<keyof WorkflowInput, keyof SchemaWorkflow>,
  order: ["name", "run-name", "on", "permissions", "env", "defaults", "concurrency", "jobs"],
  wrap: {
    on: { factory: on, mode: "model" },
    permissions: { factory: permissions, mode: "objectModel" },
    defaults: { factory: defaults, mode: "objectModel" },
    concurrency: { factory: concurrency, mode: "objectModel" },
  },
};

/**
 * Create a workflow model representing a complete GitHub Actions workflow
 * YAML file. Plain-object values for `on`, `permissions`, `defaults`, and
 * `concurrency` are automatically wrapped with their respective factory
 * functions.
 *
 * @param input - Workflow properties and optional model metadata.
 * @returns A `WorkflowModel` that can be serialized to YAML.
 *
 * @example
 * ```ts
 * workflow({
 *   name: "CI",
 *   on: { push: { branches: ["main"] } },
 *   jobs: {
 *     test: job({
 *       runsOn: "ubuntu-latest",
 *       steps: [step({ uses: "actions/checkout@v4" })],
 *     }),
 *   },
 * })
 * ```
 */
export function workflow(input: WithMeta<WorkflowInput>): WorkflowModel {
  const [data, meta] = extractMeta(input);
  return buildModel<WorkflowModel>(WORKFLOW_SPEC, data as Record<string, unknown>, meta);
}
