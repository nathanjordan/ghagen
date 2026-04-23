import type { YAMLMap } from "yaml";
import type { HttpsJsonSchemastoreOrgGithubWorkflowJson as SchemaWorkflow } from "../schema/workflow-types.generated.js";
import {
  WorkflowModel,
  extractMeta,
  isModel,
  isCommented,
  withComment,
  withEolComment,
} from "./_base.js";
import type {
  OnModel,
  PermissionsModel,
  ConcurrencyModel,
  DefaultsModel,
  JobModel,
  WithMeta,
  Raw,
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

const WORKFLOW_FIELD_MAP = {
  name: "name",
  runName: "run-name",
  on: "on",
  permissions: "permissions",
  env: "env",
  defaults: "defaults",
  concurrency: "concurrency",
  jobs: "jobs",
} as const satisfies Record<keyof WorkflowInput, keyof SchemaWorkflow>;

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
  const yamlData: Record<string, unknown> = {};

  for (const [camelKey, yamlKey] of Object.entries(WORKFLOW_FIELD_MAP)) {
    let value = (data as Record<string, unknown>)[camelKey];
    if (value === undefined) continue;

    // Peel off Commented wrapper before auto-wrapping, re-apply after
    let commented: { comment?: string; eolComment?: string } | null = null;
    if (isCommented(value)) {
      commented = { comment: value.comment, eolComment: value.eolComment };
      value = value.value;
    }

    if (camelKey === "on" && !isModel(value)) {
      value = on(value as OnInput);
    } else if (camelKey === "permissions" && typeof value === "object" && !isModel(value)) {
      value = permissions(value as PermissionsInput);
    } else if (camelKey === "defaults" && typeof value === "object" && !isModel(value)) {
      value = defaults(value as DefaultsInput);
    } else if (camelKey === "concurrency" && typeof value === "object" && !isModel(value)) {
      value = concurrency(value as ConcurrencyInput);
    }

    // Re-wrap with Commented if needed
    if (commented) {
      if (commented.comment) value = withComment(value, commented.comment);
      if (commented.eolComment) value = withEolComment(value, commented.eolComment);
    }

    yamlData[yamlKey] = value;
  }

  return new WorkflowModel(yamlData, meta);
}
